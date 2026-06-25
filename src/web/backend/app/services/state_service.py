"""
State management service for EcoRetrofit.
Uses SQLite to store and update live environment and override variables,
ensuring process safety across multiple backend worker processes.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict


class StateService:
    def __init__(self, db_path: Path) -> None:
        self.db_path: Path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create the app_state table if it does not already exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def get(self, key: str, default: Any) -> Any:
        """Retrieve a state value from the SQLite store, falling back to default."""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM app_state WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return default
        except Exception:
            return default

    def set(self, key: str, value: Any) -> None:
        """Save/overwrite a state value in the SQLite store."""
        val_str: str = json.dumps(value)
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
                (key, val_str)
            )
            conn.commit()

    def get_environment(self) -> Dict[str, float]:
        """Fetch the current indoor and outdoor temperature states."""
        return {
            "indoor_temp": float(self.get("indoor_temp", 21.5)),
            "outdoor_temp": float(self.get("outdoor_temp", 15.0)),
        }

    def set_environment(self, indoor_temp: float, outdoor_temp: float) -> None:
        """Update the current indoor and outdoor temperature states."""
        self.set("indoor_temp", indoor_temp)
        self.set("outdoor_temp", outdoor_temp)

    def get_override(self) -> bool:
        """Fetch the current manual override active state."""
        return bool(self.get("override_active", False))

    def set_override(self, active: bool) -> None:
        """Update the manual override active state."""
        self.set("override_active", active)
