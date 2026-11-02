"""Only configuration is persisted; live state belongs to the current session."""
import sqlite3
from pathlib import Path
from .models import Settings, default_settings


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS config (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)")

    def load(self) -> Settings:
        row = self.db.execute("SELECT value FROM config WHERE id=1").fetchone()
        return Settings.model_validate_json(row[0]) if row else default_settings()

    def save(self, settings: Settings):
        with self.db:
            self.db.execute("INSERT INTO config VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET value=excluded.value",
                            (settings.model_dump_json(),))

    def close(self):
        self.db.close()
