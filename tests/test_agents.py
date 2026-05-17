from src.agents import run_writing


class FakeRedis:
    def __init__(self, data=None):
        self.data = data or {}

    def hget(self, key, field):
        return self.data.get(field)

    def hset(self, key, mapping=None, **kwargs):
        if mapping:
            self.data.update(mapping)


def test_run_writing_uses_workspace(monkeypatch):
    fake = FakeRedis({"research": "LangGraph vs CrewAI research notes"})
    monkeypatch.setattr("src.agents.redis_client", fake)
    monkeypatch.setattr("src.agents.workspace_key", lambda tid: f"task:{tid}:workspace")
    draft = run_writing("abc-123")
    assert "LangGraph" in draft
    assert fake.data.get("draft")
