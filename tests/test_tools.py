import pytest

from src.tools import FLAKY_QUERY, web_search


class FakeRedis:
    def __init__(self):
        self.store = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]


def test_web_search_langgraph(monkeypatch):
    monkeypatch.setattr("src.tools.redis_client", FakeRedis())
    result = web_search("LangGraph features", "task-1")
    assert "LangGraph" in result


def test_flaky_tool_retries(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("src.tools.redis_client", fake)
    with pytest.raises(RuntimeError):
        web_search(FLAKY_QUERY, "task-flaky")
    result = web_search(FLAKY_QUERY, "task-flaky")
    assert result
