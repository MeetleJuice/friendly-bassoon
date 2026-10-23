"""Seed/verify synthetic history for the actual Windows installer upgrade smoke."""

import json
import hashlib
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone


def main():
    action, folder = sys.argv[1], Path(sys.argv[2])
    with sqlite3.connect(folder / "aigentics.sqlite3") as db:
        if action == "seed":
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version != 4:
                raise RuntimeError("Previous release did not initialize schema v4")
            agent = db.execute("SELECT data FROM agents LIMIT 1").fetchone()[0]
            db.execute(
                "INSERT OR REPLACE INTO settings VALUES(?,?)", ("upgrade_sentinel", '"preserve-settings"')
            )
            stamp = datetime.now(timezone.utc).isoformat()
            profile = json.loads(db.execute("SELECT data FROM profiles LIMIT 1").fetchone()[0])
            signature = hashlib.sha256(
                json.dumps(
                    {key: profile[key] for key in ("kind", "base_url", "credential_ref")}, sort_keys=True
                ).encode()
            ).hexdigest()
            db.execute(
                "INSERT OR REPLACE INTO model_catalogs VALUES(?,?,?,?,?)",
                (profile["id"], signature, stamp, json.dumps(["synthetic-preserved-model"]), 0),
            )
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "upgrade-fixture",
                    stamp,
                    stamp,
                    "completed",
                    "synthetic-workspace",
                    agent,
                    1,
                    None,
                    "synthetic completion",
                ),
            )
            db.execute(
                "INSERT INTO messages VALUES(?,?,?)",
                ("upgrade-fixture", 0, json.dumps({"role": "user", "content": "Synthetic upgrade history"})),
            )
            db.execute(
                "INSERT INTO diagnostics(id,created,state,payload,submission_state) VALUES(?,?,?,?,?)",
                (
                    "upgrade-diagnostic",
                    stamp,
                    "passed",
                    json.dumps({"id": "upgrade-diagnostic", "created": stamp, "state": "passed"}),
                    "draft_opened",
                ),
            )
            (folder / "expected-agent-id.txt").write_text(json.loads(agent)["id"], encoding="utf-8")
        elif action == "verify":
            if db.execute("PRAGMA user_version").fetchone()[0] != 5:
                raise RuntimeError("Upgrade did not migrate to schema v5")
            if (
                db.execute("SELECT value FROM settings WHERE key='upgrade_sentinel'").fetchone()[0]
                != '"preserve-settings"'
            ):
                raise RuntimeError("User setting was lost")
            message = json.loads(
                db.execute("SELECT data FROM messages WHERE session_id='upgrade-fixture'").fetchone()[0]
            )
            if message["content"] != "Synthetic upgrade history":
                raise RuntimeError("Session history was lost")
            expected = (folder / "expected-agent-id.txt").read_text(encoding="utf-8")
            if not db.execute("SELECT id FROM agents WHERE id=?", (expected,)).fetchone():
                raise RuntimeError("Saved agent identity was lost")
            report = db.execute(
                "SELECT submission_state FROM diagnostics WHERE id='upgrade-diagnostic'"
            ).fetchone()
            if not report or report[0] != "draft_opened":
                raise RuntimeError("Diagnostic history/sharing state was lost")
            db.execute("SELECT COUNT(*) FROM model_catalogs").fetchone()
            if not db.execute(
                "SELECT models FROM model_catalogs WHERE models LIKE '%synthetic-preserved-model%'"
            ).fetchone():
                raise RuntimeError("Saved model catalog was lost")
            db.execute("SELECT COUNT(*) FROM projects").fetchone()
        else:
            raise ValueError("Use seed or verify")
    print("Upgrade preservation probe:", action, "passed")


if __name__ == "__main__":
    main()
