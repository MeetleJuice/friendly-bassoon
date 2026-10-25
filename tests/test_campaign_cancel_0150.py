"""Stopping during a model call is missing evidence, never a model failure."""

import threading

import pytest

from aigentics.campaign import run_campaign
from aigentics.measurement import summarize_trials
from aigentics.models import Agent, Profile, Reply


@pytest.mark.parametrize("mode", ["measurement", "deep"])
def test_stop_during_native_model_call_is_unknown(store, credentials, mode):
    store.save_profile(Profile(id="ollama", name="Local fixture"))
    cancel = threading.Event()

    class InterruptedProvider:
        def __init__(self, *args):
            pass

        def capabilities(self, *args):
            return {
                "tools": True,
                "thinking_support": "reported",
                "thinking_values": [False, True],
                "thinking_default": True,
            }

        def chat(self, *args):
            cancel.set()
            return Reply(content="Interrupted synthetic response")

    report = run_campaign(
        store, credentials, Agent(), cancel, lambda e: None, mode=mode, provider_factory=InterruptedProvider
    )[1]
    assert report["state"] == "cancelled" and len(report["checks"]) == 1
    row = report["checks"][0]
    assert row["evidence"]["runtime_state"] == "cancelled"
    assert row["code"] == "CANCELLED"
    if mode == "measurement":
        group = summarize_trials([row])["groups"][0]
        assert group["interrupted_unknown"] == 1 and group["failed"] == 0
        assert group["eligible_repetitions"] == 0 and group["success_rate"] is None
