"""Seed/verify synthetic history for the actual Windows installer upgrade smoke."""

import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone


def main():
    action, folder = sys.argv[1], Path(sys.argv[2])
    with sqlite3.connect(folder / "aigentics.sqlite3") as db:
        if action == "seed":
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version != 2:
                raise RuntimeError("Previous release did not initialize schema v2")
            agent = db.execute("SELECT data FROM agents LIMIT 1").fetchone()[0]
            db.execute(
                "INSERT OR REPLACE INTO settings VALUES(?,?)", ("upgrade_sentinel", '"preserve-settings"')
            )
            stamp = datetime.now(timezone.utc).isoformat()
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
            (folder / "expected-agent-id.txt").write_text(json.loads(agent)["id"], encoding="utf-8")
        elif action == "verify":
            if db.execute("PRAGMA user_version").fetchone()[0] != 3:
                raise RuntimeError("Upgrade did not migrate to schema v3")
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
            db.execute("SELECT COUNT(*) FROM diagnostics").fetchone()
        else:
            raise ValueError("Use seed or verify")
    print("Upgrade preservation probe:", action, "passed")


if __name__ == "__main__":
    main()
