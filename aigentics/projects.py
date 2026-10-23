"""Remembered project definitions. No automatic indexing or source-content persistence."""

from pathlib import Path
from uuid import uuid4
from .store import now
from .tools import Workspace


class Projects:
    def __init__(self, store):
        self.store = store

    def remember(self, path, name=None, brief=None):
        root = Workspace(path).root
        name = (name or root.name or str(root))[:100]
        if brief is not None and (len(brief) > 4000 or self.store.credentials.redact(brief) != brief):
            raise ValueError("Project brief must be at most 4000 characters and contain no credentials")
        with self.store.lock, self.store.db:
            previous = self.store.db.execute("SELECT * FROM projects WHERE path=?", (str(root),)).fetchone()
            identity = previous["id"] if previous else str(uuid4())
            stamp = now()
            self.store.db.execute(
                "INSERT INTO projects VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                "name=excluded.name,brief=excluded.brief,updated=excluded.updated",
                (
                    identity,
                    str(root),
                    name,
                    brief if brief is not None else previous["brief"] if previous else "",
                    previous["created"] if previous else stamp,
                    stamp,
                ),
            )
            self.store.db.execute(
                "DELETE FROM projects WHERE id NOT IN (SELECT id FROM projects ORDER BY updated DESC LIMIT 100)"
            )
        return next(row for row in self.recent() if row["id"] == identity)

    def recent(self):
        with self.store.lock:
            return [
                dict(row)
                for row in self.store.db.execute("SELECT * FROM projects ORDER BY updated DESC LIMIT 100")
            ]

    def forget(self, identity):
        with self.store.lock, self.store.db:
            self.store.db.execute("DELETE FROM projects WHERE id=?", (identity,))
        self.store.compact()

    def sessions(self, path):
        # Canonical paths are local metadata, never public diagnostic fields.
        root = str(Path(path).resolve())
        return [row for row in self.store.sessions() if row["workspace"] == root]
