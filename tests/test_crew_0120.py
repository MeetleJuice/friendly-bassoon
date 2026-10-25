"""Actual saved-roster preservation and reproducible permission boundaries."""

import pytest

from aigentics.crew import CREW_VERSION, ROLES, ensure_roster, make_agent
from aigentics.models import Agent, ModelRef
from aigentics.registry import TOOL_REGISTRY
from aigentics.store import Store


@pytest.fixture
def primary():
    return ModelRef(profile_id="ollama", model="synthetic-local:8b")


@pytest.mark.parametrize("role", ROLES)
def test_baselines_are_independent_bounded_and_same_model(role, primary):
    agent = make_agent(role, primary)
    assert agent.primary == primary
    assert agent.primary is not primary
    assert agent.fallbacks == []
    assert not agent.allow_commands
    assert "run_command" not in agent.tools
    assert all(name in TOOL_REGISTRY for name in agent.tools)
    assert agent.max_steps == 12 and agent.max_seconds == 300
    agent.primary.model = "changed"
    agent.tools.clear()
    assert make_agent(role, primary).primary.model == "synthetic-local:8b"
    assert make_agent(role, primary).tools


@pytest.mark.parametrize("role", ("scout", "sentinel"))
def test_read_only_roles_have_no_mutation_tools(role, primary):
    agent = make_agent(role, primary)
    assert not agent.allow_writes
    assert all(TOOL_REGISTRY[name].read_only for name in agent.tools)


def test_existing_user_agents_and_edited_roster_are_preserved(store, primary):
    personal = store.save_agent(Agent(name="George", instructions="My personal instructions"))
    roster = ensure_roster(store, primary)
    ada = roster["ada"]
    ada.instructions = "User edited Ada instructions"
    ada.primary.model = "my-other-local-model"
    ada.allow_writes = False
    saved = store.save_agent(ada)
    again = ensure_roster(store, ModelRef(profile_id="ollama", model="new-campaign-model"))
    assert len(store.agents()) == 7
    assert again["ada"] == saved
    assert next(a for a in store.agents() if a.id == personal.id) == personal
    assert again["george"].primary == primary
    assert make_agent("ada", primary).primary == primary
    assert make_agent("ada", primary).allow_writes


def test_repeat_install_does_not_create_revisions(store, primary):
    first = ensure_roster(store, primary)
    second = ensure_roster(store, primary)
    assert first == second
    assert len(store.agents()) == 6
    with store.lock:
        count = store.db.execute("SELECT COUNT(*) FROM agent_revisions").fetchone()[0]
    assert count == 6


def test_roster_survives_actual_store_restart(tmp_path, credentials, primary):
    path = tmp_path / "crew.sqlite3"
    with_store = Store(path, credentials)
    expected = ensure_roster(with_store, primary)
    with_store.close()
    reopened = Store(path, credentials)
    try:
        actual = ensure_roster(reopened, primary)
        assert actual == expected
        assert len(reopened.agents()) == 6
    finally:
        reopened.close()


def test_missing_role_recreates_without_revising_survivors(store, primary):
    first = ensure_roster(store, primary)
    store.delete_agent(first["atlas"].id)
    second = ensure_roster(store, primary)
    assert len(store.agents()) == 6
    assert second["george"] == first["george"]
    assert second["atlas"].primary == primary


def test_registry_is_immutable_and_unknown_role_fails(primary):
    with pytest.raises(TypeError):
        ROLES["other"] = ROLES["george"]
    with pytest.raises(KeyError):
        make_agent("unknown", primary)
    assert CREW_VERSION == "midnight-crew-2"
