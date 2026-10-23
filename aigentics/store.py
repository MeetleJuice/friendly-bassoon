"""Local evidence store, schema migrations, retention, export, and recovery."""

from contextlib import closing
import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4
from . import __version__
from .models import Agent, Profile


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path, credentials, recover=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.credentials = credentials
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA secure_delete=ON")
        self._migrate()
        if recover:
            for row in self.db.execute("SELECT id FROM sessions WHERE state='running'").fetchall():
                self.finish(row["id"], "interrupted", "Previous process stopped before session completion")
            self.recover_diagnostics()
        self.prune()

    def recover_diagnostics(self):
        with self.lock:
            rows = self.db.execute("SELECT payload FROM diagnostics WHERE state='running'").fetchall()
        for row in rows:
            payload = json.loads(row["payload"])
            payload["state"] = "interrupted"
            self.save_diagnostic(payload)

    def _migrate(self):
        with self.lock, self.db:
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            if version > 4:
                raise RuntimeError("Database is newer than this application; upgrade the application")
            if version < 1:
                self.db.executescript("""
                CREATE TABLE agents(id TEXT PRIMARY KEY, revision INTEGER, name TEXT, data TEXT);
                CREATE TABLE agent_revisions(agent_id TEXT, revision INTEGER, data TEXT,
                    PRIMARY KEY(agent_id,revision));
                CREATE TABLE profiles(id TEXT PRIMARY KEY, data TEXT);
                CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE sessions(id TEXT PRIMARY KEY, created TEXT, updated TEXT, state TEXT,
                    workspace TEXT, agent TEXT, capture INTEGER, parent TEXT, outcome TEXT);
                CREATE TABLE events(sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE,
                    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE, timestamp TEXT,
                    kind TEXT, data TEXT, app_version TEXT);
                CREATE INDEX events_session ON events(session_id,sequence);
                CREATE TABLE messages(session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
                    position INTEGER, data TEXT, PRIMARY KEY(session_id,position));
                PRAGMA user_version=1;
                """)

            if version < 2:
                self.db.executescript("""
                CREATE TABLE assessments(session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
                    label TEXT NOT NULL, note TEXT NOT NULL, updated TEXT NOT NULL);
                PRAGMA user_version=2;
                """)

            if version < 3:
                self.db.executescript("""
                CREATE TABLE IF NOT EXISTS diagnostics(id TEXT PRIMARY KEY, created TEXT, state TEXT,
                    payload TEXT, submission_state TEXT NOT NULL DEFAULT 'local', submission_url TEXT);
                PRAGMA user_version=3;
                """)

            if version < 4:
                self.db.executescript("""
                CREATE TABLE IF NOT EXISTS model_catalogs(profile_id TEXT PRIMARY KEY,
                    signature TEXT, fetched TEXT, models TEXT, partial INTEGER);
                PRAGMA user_version=4;
                """)

    @staticmethod
    def catalog_signature(profile):
        return Store.fingerprint(
            {key: getattr(profile, key) for key in ("kind", "base_url", "credential_ref")}
        )

    def save_catalog(self, profile, models, partial=False):
        if len(models) > 5000 or any(not isinstance(m, str) or len(m) > 200 for m in models):
            raise ValueError("Model catalog exceeds limits")
        with self.lock, self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO model_catalogs VALUES(?,?,?,?,?)",
                (
                    profile.id,
                    self.catalog_signature(profile),
                    now(),
                    self.credentials.json(models),
                    int(partial),
                ),
            )

    def catalogs(self):
        profiles = {p.id: p for p in self.profiles()}
        with self.lock:
            rows = self.db.execute("SELECT * FROM model_catalogs ORDER BY profile_id").fetchall()
        return {
            r["profile_id"]: dict(r) | {"models": json.loads(r["models"])}
            for r in rows
            if r["profile_id"] in profiles
            and r["signature"] == self.catalog_signature(profiles[r["profile_id"]])
        }

    def clear_catalogs(self):
        with self.lock, self.db:
            self.db.execute("DELETE FROM model_catalogs")
        self.compact()

    def data_inventory(self):
        """Local counts/sizes, never source files or credential files."""
        with self.lock:
            result = {
                table: self.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("sessions", "messages", "events", "diagnostics", "model_catalogs")
            }
        result["database_bytes"] = sum(
            p.stat().st_size
            for p in (self.path, Path(str(self.path) + "-wal"), Path(str(self.path) + "-shm"))
            if p.is_file()
        )
        for name, pattern in (("backups", "aigentics-*.sqlite3"), ("updates", "Aigentics-Setup-*.exe")):
            files = [p for p in (self.path.parent / name).glob(pattern) if p.is_file() and not p.is_symlink()]
            result[name + "_count"] = len(files)
            result[name + "_bytes"] = sum(p.stat().st_size for p in files)
        return result

    def save_diagnostic(self, report):
        raw = self.credentials.json(report)
        if len(raw.encode("utf-8")) > 250000:
            raise ValueError("Diagnostic report exceeds the storage limit")
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO diagnostics(id,created,state,payload) VALUES(?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET state=excluded.state,payload=excluded.payload",
                (report["id"], report["created"], report["state"], raw),
            )

    def diagnostic_reports(self):
        with self.lock:
            return [
                dict(row) | {"payload": json.loads(row["payload"])}
                for row in self.db.execute("SELECT * FROM diagnostics ORDER BY created DESC LIMIT 232")
            ]

    def diagnostic_submission(self, report_id, state, url=""):
        with self.lock, self.db:
            self.db.execute(
                "UPDATE diagnostics SET submission_state=?,submission_url=? WHERE id=?",
                (state, url, report_id),
            )
        self.event(None, "diagnostic.sharing_state", {"report_id": report_id, "state": state})

    def delete_diagnostic(self, report_id):
        with self.lock, self.db:
            self.db.execute("DELETE FROM diagnostics WHERE id=? AND state != 'running'", (report_id,))
        self.compact()

    def assess(self, sid, label, note=""):
        if label not in ("goal_met", "needs_work"):
            raise ValueError("Unknown assessment label")
        if len(note) > 2000:
            raise ValueError("Assessment notes must be at most 2000 characters")
        with self.lock, self.db:
            state = self.db.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
            if not state or state[0] == "running":
                raise ValueError("Assess a completed or stopped run")
            self.db.execute(
                "INSERT OR REPLACE INTO assessments VALUES(?,?,?,?)",
                (sid, label, self.credentials.redact(note), now()),
            )
        self.event(
            sid, "evaluation.user_feedback", {"label": label, "source": "user", "note_saved": bool(note)}
        )

    def assessment(self, sid):
        with self.lock:
            row = self.db.execute("SELECT * FROM assessments WHERE session_id=?", (sid,)).fetchone()
            return dict(row) if row else None

    def setting(self, name, default):
        with self.lock:
            row = self.db.execute("SELECT value FROM settings WHERE key=?", (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, name, value):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (name, json.dumps(value)))

    def save_agent(self, agent):
        with self.lock, self.db:
            row = self.db.execute(
                "SELECT MAX(revision) FROM agent_revisions WHERE agent_id=?", (agent.id,)
            ).fetchone()
            revision = (row[0] or 0) + 1
            agent = agent.model_copy(update={"revision": revision})
            raw = agent.model_dump_json()
            if self.credentials.scrub(agent.model_dump()) != agent.model_dump():
                raise ValueError("Agent contains a credential-like value. Use credential references instead.")
            self.db.execute(
                "INSERT OR REPLACE INTO agents VALUES(?,?,?,?)", (agent.id, revision, agent.name, raw)
            )
            self.db.execute("INSERT INTO agent_revisions VALUES(?,?,?)", (agent.id, revision, raw))
        self.event(None, "configuration.agent_saved", {"agent_id": agent.id, "revision": revision})
        # Keep bounded recent definitions; session snapshots preserve definitions used in retained runs.
        with self.lock, self.db:
            self.db.execute(
                "DELETE FROM agent_revisions WHERE agent_id=? AND revision <= ?", (agent.id, revision - 100)
            )
        return agent

    def agents(self):
        with self.lock:
            return [
                Agent.model_validate_json(r[0])
                for r in self.db.execute("SELECT data FROM agents ORDER BY name")
            ]

    def delete_agent(self, agent_id):
        with self.lock, self.db:
            self.db.execute("DELETE FROM agents WHERE id=?", (agent_id,))
            self.db.execute("DELETE FROM agent_revisions WHERE agent_id=?", (agent_id,))

        self.event(None, "configuration.agent_deleted", {"agent_id": agent_id})

    def save_profile(self, profile):
        raw = profile.model_dump_json()
        if self.credentials.scrub(profile.model_dump()) != profile.model_dump():
            raise ValueError("Profile contains a credential-like value; use a credential reference")
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO profiles VALUES(?,?)", (profile.id, raw))

        self.event(None, "configuration.profile_saved", {"profile_id": profile.id, "kind": profile.kind})

    def profiles(self):
        with self.lock:
            return [
                Profile.model_validate_json(r[0])
                for r in self.db.execute("SELECT data FROM profiles ORDER BY id")
            ]

    def start(self, agent, workspace, capture=False, parent=None):
        sid = str(uuid4())
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    sid,
                    now(),
                    now(),
                    "running",
                    str(workspace),
                    self.credentials.json(agent.model_dump()),
                    int(capture),
                    parent,
                    "",
                ),
            )
        self.event(
            sid,
            "session.started",
            {"agent_id": agent.id, "revision": agent.revision, "capture_content": capture, "parent": parent},
        )
        return sid

    def event(self, sid, kind, data):
        encoded = self.credentials.json(data, ensure_ascii=False, default=str)
        # Prevent a single event from growing without bound; preserve valid JSON.
        if len(encoded) > 32000:
            encoded = json.dumps({"truncated": True, "preview": encoded[:30000]})
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO events(id,session_id,timestamp,kind,data,app_version) VALUES(?,?,?,?,?,?)",
                (str(uuid4()), sid, now(), kind, encoded, __version__),
            )
            if sid:
                self.db.execute("UPDATE sessions SET updated=? WHERE id=?", (now(), sid))
        return {"kind": kind, "data": json.loads(encoded)}

    def messages(self, sid, messages=None):
        with self.lock, self.db:
            if messages is not None:
                capture = self.db.execute("SELECT capture FROM sessions WHERE id=?", (sid,)).fetchone()[0]
                if capture:
                    self.db.execute("DELETE FROM messages WHERE session_id=?", (sid,))
                    for i, message in enumerate(messages):
                        self.db.execute(
                            "INSERT INTO messages VALUES(?,?,?)",
                            (sid, i, self.credentials.json(message)),
                        )
            return [
                json.loads(r[0])
                for r in self.db.execute(
                    "SELECT data FROM messages WHERE session_id=? ORDER BY position", (sid,)
                )
            ]

    def finish(self, sid, state, outcome):
        outcome = self.credentials.redact(outcome)[:2000]
        with self.lock, self.db:
            self.db.execute(
                "UPDATE sessions SET state=?,updated=?,outcome=? WHERE id=?", (state, now(), outcome, sid)
            )
        self.event(sid, "session." + state, {"outcome": outcome})

    def sessions(self):
        with self.lock:
            return [
                dict(r) for r in self.db.execute("SELECT * FROM sessions ORDER BY created DESC LIMIT 500")
            ]

    def events(self, sid):
        with self.lock:
            return [
                dict(r) | {"data": json.loads(r["data"])}
                for r in self.db.execute(
                    "SELECT * FROM events WHERE session_id IS ? ORDER BY sequence", (sid,)
                )
            ]

    def metrics(self):
        """Descriptive evidence, not a model-generated quality score."""
        with self.lock:
            states = {
                r[0]: r[1] for r in self.db.execute("SELECT state,COUNT(*) FROM sessions GROUP BY state")
            }
            assessments = {
                r[0]: r[1] for r in self.db.execute("SELECT label,COUNT(*) FROM assessments GROUP BY label")
            }
            tool_rows = self.db.execute("SELECT data FROM events WHERE kind='tool.result'").fetchall()
            model_rows = self.db.execute("SELECT data FROM events WHERE kind='model.responded'").fetchall()
        tools = {}
        for row in tool_rows:
            event = json.loads(row[0])
            item = tools.setdefault(event["tool"], {"succeeded": 0, "failed": 0, "total_duration_ms": 0})
            item[event["status"]] += 1
            item["total_duration_ms"] += event.get("duration_ms", 0)
        models = {}
        for row in model_rows:
            event = json.loads(row[0])
            key = event["profile"] + "/" + event["model"]
            item = models.setdefault(key, {"responses": 0, "total_duration_ms": 0, "reported_usage": {}})
            item["responses"] += 1
            item["total_duration_ms"] += event.get("duration_ms", 0)
            for metric, value in event.get("usage", {}).items():
                if isinstance(value, (int, float)):
                    item["reported_usage"][metric] = item["reported_usage"].get(metric, 0) + value
        return {
            "sessions_by_state": states,
            "user_assessments": assessments,
            "tools": tools,
            "models": models,
            "note": "Model completion is not verified task success. Usage units depend on provider; Ollama total_duration is nanoseconds.",
        }

    def export(self, sid, path):
        with self.lock:
            session = dict(self.db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone())
        payload = {
            "export_version": 1,
            "session": session,
            "events": self.events(sid),
            "messages": self.messages(sid),
            "user_assessment": self.assessment(sid),
        }
        path.write_text(self.credentials.json(payload, indent=2), encoding="utf-8")

    def delete_session(self, sid):
        with self.lock, self.db:
            self.db.execute("DELETE FROM sessions WHERE id=? AND state != 'running'", (sid,))
        self.compact()

    def prune(self):
        days = max(1, min(3650, int(self.setting("retention_days", 30))))
        cap = max(100, min(1000000, int(self.setting("max_events", 20000))))
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        report_cap = max(5, min(200, int(self.setting("max_reports", 20))))
        byte_cap = max(1, min(100, int(self.setting("report_storage_mb", 10)))) * 1024 * 1024
        with self.lock, self.db:
            self.db.execute("DELETE FROM sessions WHERE updated < ? AND state != 'running'", (cutoff,))
            self.db.execute("DELETE FROM diagnostics WHERE created < ? AND state != 'running'", (cutoff,))
            self.db.execute(
                "DELETE FROM diagnostics WHERE state != 'running' AND id NOT IN "
                "(SELECT id FROM diagnostics WHERE state != 'running' ORDER BY created DESC LIMIT ?)",
                (report_cap,),
            )
            self.db.execute("DELETE FROM model_catalogs WHERE fetched < ?", (cutoff,))

            # Bound retained diagnostic payloads and model catalogs together. Keep active reports.
            def report_bytes():
                return self.db.execute(
                    "SELECT COALESCE((SELECT SUM(length(CAST(payload AS BLOB))) FROM diagnostics),0) + "
                    "COALESCE((SELECT SUM(length(CAST(models AS BLOB))) FROM model_catalogs),0)"
                ).fetchone()[0]

            for row in self.db.execute(
                "SELECT 'report',id,created FROM diagnostics WHERE state != 'running' UNION ALL "
                "SELECT 'catalog',profile_id,fetched FROM model_catalogs ORDER BY 3"
            ).fetchall():
                if report_bytes() <= byte_cap:
                    break
                if row[0] == "report":
                    self.db.execute("DELETE FROM diagnostics WHERE id=?", (row[1],))
                else:
                    self.db.execute("DELETE FROM model_catalogs WHERE profile_id=?", (row[1],))
            self.db.execute("DELETE FROM events WHERE session_id IS NULL AND timestamp < ?", (cutoff,))
            self.db.execute(
                "DELETE FROM events WHERE session_id IS NULL AND sequence NOT IN (SELECT sequence FROM events WHERE session_id IS NULL ORDER BY sequence DESC LIMIT ?)",
                (cap // 4,),
            )
            # Delete whole oldest completed sessions, preserving coherent evidence for retained sessions.
            for row in self.db.execute(
                "SELECT id FROM sessions WHERE state != 'running' ORDER BY created"
            ).fetchall():
                count = self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                if count <= cap:
                    break
                self.db.execute("DELETE FROM sessions WHERE id=?", (row[0],))
        self.prune_backups(days)
        self.compact()

    def prune_backups(self, days=None):
        days = days or max(1, min(3650, int(self.setting("retention_days", 30))))
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        for index, old in enumerate(
            sorted((self.path.parent / "backups").glob("aigentics-*.sqlite3"), reverse=True)
        ):
            if not old.is_symlink() and (index >= 3 or old.stat().st_mtime < cutoff):
                old.unlink()

    def compact(self):
        with self.lock:
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.execute("VACUUM")

    @staticmethod
    def fingerprint(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    def backup(self):
        """Consistent pre-update snapshot. Keep the newest three in the local data directory."""
        folder = self.path.parent / "backups"
        folder.mkdir(exist_ok=True)
        path = folder / ("aigentics-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".sqlite3")
        with self.lock:
            with closing(sqlite3.connect(path)) as destination:
                self.db.backup(destination)
        self.prune_backups()
        return path

    def close(self):
        with self.lock:
            self.db.close()
