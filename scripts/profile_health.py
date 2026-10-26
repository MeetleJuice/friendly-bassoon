"""Offline health timing probe. Prints check identities/counts/timings, never content."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import tempfile
import threading

parser = argparse.ArgumentParser()
parser.add_argument("--source-root", type=Path, default=Path.cwd())
parser.add_argument("--memory-proof", action="store_true")
args = parser.parse_args()
sys.path.insert(0, str(args.source_root.resolve()))

# Select an explicit source snapshot before importing its application modules.
from aigentics import __version__  # noqa: E402
from aigentics.credentials import Credentials  # noqa: E402
from aigentics.diagnostics import DiagnosticRunner  # noqa: E402
from aigentics.store import Store  # noqa: E402

if args.memory_proof:
    # Controlled diagnostic of ONLY the new disposable harness fixture. Does not
    # change the real data store or the installed database durability diagnostic.
    import aigentics.self_checks_0200 as proof

    proof.Store = lambda path, credentials: Store(Path(":memory:"), credentials)

credentials = Credentials()
credentials._values = {}
with tempfile.TemporaryDirectory(prefix="aigentics-health-profile-") as folder:
    with closing(Store(Path(folder) / "health.sqlite3", credentials)) as store:
        report = DiagnosticRunner(store, credentials).run(threading.Event(), include_network=False)
        print(
            json.dumps(
                {
                    "version": __version__,
                    "memory_proof": args.memory_proof,
                    "duration_ms": report["duration_ms"],
                    "summary": report["summary"],
                }
            ),
            flush=True,
        )
        for row in report["checks"]:
            print(
                json.dumps({"check": row["id"], "status": row["status"], "duration_ms": row["duration_ms"]}),
                flush=True,
            )
        print(
            "::notice title=Offline health timing::"
            + json.dumps(
                {
                    "version": __version__,
                    "memory_proof": args.memory_proof,
                    "duration_ms": report["duration_ms"],
                    "slowest": [
                        {"check": r["id"], "duration_ms": r["duration_ms"]}
                        for r in sorted(report["checks"], key=lambda r: r["duration_ms"], reverse=True)[:6]
                    ],
                    "verification_ms": next(
                        (r["duration_ms"] for r in report["checks"] if r["id"] == "verification_fixture"),
                        None,
                    ),
                }
            ),
            flush=True,
        )
        if report["state"] != "passed":
            raise SystemExit(1)
