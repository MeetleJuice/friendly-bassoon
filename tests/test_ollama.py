"""Opt-in real model workflow. Never requires a cloud key."""

import os
import pytest
from aigentics.models import Agent, Profile, ModelRef
from aigentics.runtime import Runtime


@pytest.mark.skipif(
    not os.getenv("AIGENTICS_TEST_OLLAMA_MODEL"),
    reason="Set AIGENTICS_TEST_OLLAMA_MODEL to opt into real local inference",
)
def test_real_ollama_coding_workflow(store, credentials, tmp_path):
    model = os.environ["AIGENTICS_TEST_OLLAMA_MODEL"]
    store.save_profile(
        Profile(
            id="ollama",
            name="Ollama integration test",
            base_url=os.getenv("AIGENTICS_TEST_OLLAMA_URL", "http://127.0.0.1:11434"),
        )
    )
    (tmp_path / "input.txt").write_text("hello aigentics\n", encoding="utf-8")
    agent = Agent(
        primary=ModelRef(profile_id="ollama", model=model),
        tools=["list_files", "read_file", "write_file"],
        max_steps=8,
        max_seconds=300,
    )
    sid, state = Runtime(store, credentials).run(
        agent,
        tmp_path,
        "Read input.txt using the read_file tool. Create output.txt with the exact uppercase version of its contents. Use write_file, expected_sha256='new'. Do not use commands.",
        lambda kind, details: kind == "write_file" and details["path"] == "output.txt",
    )
    assert state == "completed", store.events(sid)
    assert (tmp_path / "output.txt").read_text(encoding="utf-8") == "HELLO AIGENTICS\n"
    assert any(e["kind"] == "tool.result" and e["data"].get("verified") for e in store.events(sid))
