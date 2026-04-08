"""Task #27: Deeper test coverage for synthesizer.py."""
import pytest
from unittest.mock import MagicMock

from domain.core.synthesizer import InsightSynthesizer


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.complete = MagicMock(return_value="Narrative about the soul's growth.")
    return llm


@pytest.fixture
def synthesizer(mock_llm):
    return InsightSynthesizer(mock_llm)


class TestConstructPrompt:
    def test_empty_metrics(self, synthesizer):
        prompt = synthesizer._construct_prompt({}, [], {})
        assert "None detected." in prompt
        assert "No clusters detected." in prompt
        assert "No bridges detected." in prompt

    def test_empty_communities_with_metrics(self, synthesizer):
        metrics = {"n1": {"degree": 0.8, "betweenness": 0.3}}
        prompt = synthesizer._construct_prompt(metrics, [], {"n1": "Python"})
        assert "No clusters detected." in prompt
        assert "Python" in prompt

    def test_community_truncation_at_five(self, synthesizer):
        """Communities with >5 nodes should only show the first 5."""
        big_community = {f"n{i}" for i in range(10)}
        metrics = {f"n{i}": {"degree": 0.1, "betweenness": 0.1} for i in range(10)}
        metadata = {f"n{i}": f"Node{i}" for i in range(10)}
        prompt = synthesizer._construct_prompt(metrics, [big_community], metadata)
        # The cluster line should contain at most 5 node names
        cluster_line = [l for l in prompt.split("\n") if l.startswith("Cluster 1:")][0]
        # Count the commas — 5 items = 4 commas
        assert cluster_line.count(",") == 4

    def test_multiple_pillars(self, synthesizer):
        """Three nodes should produce three pillar entries."""
        metrics = {
            "a": {"degree": 0.9, "betweenness": 0.1},
            "b": {"degree": 0.7, "betweenness": 0.2},
            "c": {"degree": 0.5, "betweenness": 0.3},
        }
        prompt = synthesizer._construct_prompt(metrics, [], {"a": "Alpha", "b": "Beta", "c": "Gamma"})
        assert "Alpha" in prompt
        assert "Beta" in prompt
        assert "Gamma" in prompt


class TestSynthesizeReport:
    def test_system_prompt_passed_to_llm(self, mock_llm, synthesizer):
        metrics = {"n1": {"degree": 0.5, "betweenness": 0.2}}
        synthesizer.synthesize_report(metrics, [], {"n1": "Test"})

        mock_llm.complete.assert_called_once()
        call_args = mock_llm.complete.call_args
        # system_prompt should be the second argument or keyword
        assert "system_prompt" in call_args.kwargs or len(call_args.args) >= 2
        if "system_prompt" in call_args.kwargs:
            assert "Voice of the Soul" in call_args.kwargs["system_prompt"]
        else:
            assert "Voice of the Soul" in call_args.args[1]

    def test_report_header(self, mock_llm, synthesizer):
        result = synthesizer.synthesize_report({"n1": {"degree": 0.5, "betweenness": 0.1}}, [], {})
        assert result.startswith("# State of the Soul")
