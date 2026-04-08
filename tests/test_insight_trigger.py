import os
import uuid
import pytest
import pytest_asyncio

from domain.supporting.ledger import StructuralLedger
from domain.supporting.monitor_models import AnomalyEvent
from domain.core.insight_trigger import InsightTrigger


class _MockGoalRunner:
    """Records calls to run_goal and optionally raises."""
    def __init__(self, *, should_raise=False):
        self.calls = []
        self.should_raise = should_raise

    async def run_goal(self, goal, context):
        self.calls.append((goal, context))
        if self.should_raise:
            raise RuntimeError("goal runner boom")
        return {"orchestration_summary": {"aggregate_confidence": 0.9}}


def _make_anomaly(anomaly_type="HUB_EMERGENCE", description="test", trigger_data=None):
    return AnomalyEvent(
        id=str(uuid.uuid4()),
        anomaly_type=anomaly_type,
        description=description,
        severity="medium",
        trigger_data=trigger_data or {},
        processed=False,
    )


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "trigger_test.db")


@pytest.fixture
def ledger(db_path):
    return StructuralLedger(db_path)


def _insert_anomaly(ledger, anomaly):
    with ledger.session_scope() as session:
        session.add(anomaly)
        session.flush()
        session.expunge(anomaly)


@pytest.mark.asyncio
async def test_no_anomalies_does_not_call_runner(ledger):
    runner = _MockGoalRunner()
    trigger = InsightTrigger(ledger, runner)
    await trigger.process_new_anomalies()
    assert len(runner.calls) == 0


@pytest.mark.asyncio
async def test_processes_unprocessed_anomaly(ledger):
    anomaly = _make_anomaly(trigger_data={"node_id": "skill_1", "new_degree": 0.8})
    _insert_anomaly(ledger, anomaly)

    runner = _MockGoalRunner()
    trigger = InsightTrigger(ledger, runner)
    await trigger.process_new_anomalies()

    assert len(runner.calls) == 1
    goal_text = runner.calls[0][0]
    assert "skill_1" in goal_text

    # Verify anomaly is now marked processed
    with ledger.session_scope() as session:
        row = session.get(AnomalyEvent, anomaly.id)
        assert row.processed is True


@pytest.mark.asyncio
async def test_skips_already_processed(ledger):
    anomaly = _make_anomaly()
    anomaly.processed = True
    _insert_anomaly(ledger, anomaly)

    runner = _MockGoalRunner()
    trigger = InsightTrigger(ledger, runner)
    await trigger.process_new_anomalies()

    assert len(runner.calls) == 0


@pytest.mark.asyncio
async def test_runner_failure_still_marks_processed(ledger):
    """Failed goal runs mark anomalies as processed to prevent infinite retry loops."""
    anomaly = _make_anomaly()
    _insert_anomaly(ledger, anomaly)

    runner = _MockGoalRunner(should_raise=True)
    trigger = InsightTrigger(ledger, runner)
    await trigger.process_new_anomalies()

    assert len(runner.calls) == 1

    with ledger.session_scope() as session:
        row = session.get(AnomalyEvent, anomaly.id)
        assert row.processed is True


@pytest.mark.asyncio
async def test_partial_failure_does_not_rollback_others(ledger):
    """Both successful and failed anomalies should be marked processed."""
    a1 = _make_anomaly(anomaly_type="DENSITY_SHIFT", description="first")
    a2 = _make_anomaly(anomaly_type="DENSITY_SHIFT", description="second")
    _insert_anomaly(ledger, a1)
    _insert_anomaly(ledger, a2)

    call_count = 0

    class _FailOnSecond:
        async def run_goal(self, goal, context):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("second fails")
            return {}

    trigger = InsightTrigger(ledger, _FailOnSecond())
    await trigger.process_new_anomalies()

    with ledger.session_scope() as session:
        rows = session.query(AnomalyEvent).all()
        processed_count = sum(1 for r in rows if r.processed)
        # Both should be processed — failures are marked to prevent retry loops
        assert processed_count == 2


@pytest.mark.asyncio
async def test_generate_goal_community_shift(ledger):
    anomaly = _make_anomaly(
        anomaly_type="COMMUNITY_SHIFT",
        trigger_data={"old_count": 3, "new_count": 7},
    )
    _insert_anomaly(ledger, anomaly)

    runner = _MockGoalRunner()
    trigger = InsightTrigger(ledger, runner)
    await trigger.process_new_anomalies()

    goal_text = runner.calls[0][0]
    assert "community" in goal_text.lower()
    assert "3" in goal_text
    assert "7" in goal_text


@pytest.mark.asyncio
async def test_generate_goal_unknown_type(ledger):
    anomaly = _make_anomaly(anomaly_type="SOMETHING_NEW", description="novel event")
    _insert_anomaly(ledger, anomaly)

    runner = _MockGoalRunner()
    trigger = InsightTrigger(ledger, runner)
    await trigger.process_new_anomalies()

    goal_text = runner.calls[0][0]
    assert "SOMETHING_NEW" in goal_text


@pytest.mark.asyncio
async def test_limits_to_five_anomalies(ledger):
    for _ in range(8):
        _insert_anomaly(ledger, _make_anomaly())

    runner = _MockGoalRunner()
    trigger = InsightTrigger(ledger, runner)
    await trigger.process_new_anomalies()

    assert len(runner.calls) == 5
