from datetime import datetime, timedelta, timezone

import pytest

from domain.supporting.ledger import StructuralLedger
from domain.core.models import Project, Skill, IdentityMarker, RelationalEdge


@pytest.fixture
def ledger(tmp_path):
    return StructuralLedger(str(tmp_path / "ledger_test.db"))


class TestAddProject:
    def test_creates_project(self, ledger):
        pid = ledger.add_project("TestProj", "https://example.com")
        assert pid.startswith("proj_")

    def test_upsert_returns_same_id(self, ledger):
        pid1 = ledger.add_project("TestProj")
        pid2 = ledger.add_project("TestProj")
        assert pid1 == pid2

    def test_upsert_updates_url(self, ledger):
        ledger.add_project("TestProj")
        ledger.add_project("TestProj", "https://new.url")
        with ledger.session_scope() as s:
            p = s.query(Project).filter_by(name="TestProj").first()
            assert p.repository_url == "https://new.url"


class TestAddSkill:
    def test_creates_skill(self, ledger):
        sid = ledger.add_skill("Python", "Language")
        assert sid.startswith("sk_")

    def test_upsert_raises_proficiency(self, ledger):
        ledger.add_skill("Python", "Language", proficiency=0.3)
        ledger.add_skill("Python", "Language", proficiency=0.8)
        with ledger.session_scope() as s:
            skill = s.query(Skill).filter_by(name="Python").first()
            assert skill.proficiency_level == 0.8

    def test_upsert_does_not_lower_proficiency(self, ledger):
        ledger.add_skill("Python", "Language", proficiency=0.9)
        ledger.add_skill("Python", "Language", proficiency=0.2)
        with ledger.session_scope() as s:
            skill = s.query(Skill).filter_by(name="Python").first()
            assert skill.proficiency_level == 0.9


class TestAddMilestone:
    def test_creates_milestone(self, ledger):
        mid = ledger.add_milestone("M1", "First milestone")
        assert mid.startswith("ms_")

    def test_with_project(self, ledger):
        pid = ledger.add_project("Proj")
        mid = ledger.add_milestone("M1", "desc", project_id=pid)
        milestones = ledger.get_all_milestones()
        found = [m for m in milestones if m["id"] == mid]
        assert len(found) == 1
        assert found[0]["title"] == "M1"


class TestAddEdge:
    def test_creates_edge(self, ledger):
        s1 = ledger.add_skill("A", "a")
        s2 = ledger.add_skill("B", "b")
        eid = ledger.add_edge(s1, s2, "related")
        assert eid.startswith("edge_")


class TestIdentityMarker:
    def test_set_new(self, ledger):
        mid = ledger.set_identity_marker("name", "Hermes")
        assert mid.startswith("id_")

    def test_upsert_updates_value(self, ledger):
        ledger.set_identity_marker("name", "Hermes")
        ledger.set_identity_marker("name", "Hermes v2")
        with ledger.session_scope() as s:
            marker = s.query(IdentityMarker).filter_by(key="name").first()
            assert marker.value == "Hermes v2"


class TestGetAllMilestones:
    def test_empty(self, ledger):
        assert ledger.get_all_milestones() == []

    def test_returns_all(self, ledger):
        ledger.add_milestone("M1", "d1")
        ledger.add_milestone("M2", "d2")
        assert len(ledger.get_all_milestones()) == 2


class TestPruneStaleEdges:
    def _add_aged_edge(self, ledger, source, target, weight, age_days):
        """Add an edge and backdate its created_at."""
        eid = ledger.add_edge(source, target, "test", weight=weight)
        with ledger.session_scope() as s:
            edge = s.query(RelationalEdge).filter_by(id=eid).one()
            edge.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
        return eid

    def test_prunes_old_low_weight(self, ledger):
        s1 = ledger.add_skill("A", "a")
        s2 = ledger.add_skill("B", "b")
        self._add_aged_edge(ledger, s1, s2, weight=0.2, age_days=100)
        assert ledger.count_edges() == 1
        pruned = ledger.prune_stale_edges(max_age_days=90, min_weight=0.5)
        assert pruned == 1
        assert ledger.count_edges() == 0

    def test_keeps_recent_low_weight(self, ledger):
        s1 = ledger.add_skill("C", "c")
        s2 = ledger.add_skill("D", "d")
        ledger.add_edge(s1, s2, "test", weight=0.2)
        pruned = ledger.prune_stale_edges(max_age_days=90, min_weight=0.5)
        assert pruned == 0
        assert ledger.count_edges() == 1

    def test_keeps_old_high_weight(self, ledger):
        s1 = ledger.add_skill("E", "e")
        s2 = ledger.add_skill("F", "f")
        self._add_aged_edge(ledger, s1, s2, weight=0.9, age_days=100)
        pruned = ledger.prune_stale_edges(max_age_days=90, min_weight=0.5)
        assert pruned == 0

    def test_hard_cap_removes_weakest(self, ledger):
        s1 = ledger.add_skill("G", "g")
        s2 = ledger.add_skill("H", "h")
        s3 = ledger.add_skill("I", "i")
        ledger.add_edge(s1, s2, "test", weight=0.9)
        ledger.add_edge(s1, s3, "test", weight=0.1)
        ledger.add_edge(s2, s3, "test", weight=0.5)
        assert ledger.count_edges() == 3
        pruned = ledger.prune_stale_edges(max_age_days=9999, min_weight=0.0, max_edges=2)
        assert pruned == 1
        assert ledger.count_edges() == 2
