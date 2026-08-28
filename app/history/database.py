from __future__ import annotations

import datetime
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("locali2v.history")

DEFAULT_DB_PATH = Path("outputs/locali2v_history.db")


class HistoryDatabase:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_image TEXT,
                    raw_output TEXT,
                    enhanced_output TEXT,
                    user_prompt TEXT,
                    inference_prompt TEXT,
                    seed INTEGER,
                    mode TEXT,
                    preserve TEXT,
                    motion TEXT,
                    camera_preset TEXT,
                    subject_mode TEXT,
                    enhance_enabled INTEGER DEFAULT 0,
                    settings_json TEXT,
                    error_message TEXT
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs (job_id);")

    def create_job(
        self,
        job_id: str,
        source_image: str | None = None,
        user_prompt: str = "",
        inference_prompt: str = "",
        seed: int = -1,
        mode: str = "raw",
        preserve: str = "normal",
        motion: str = "normal",
        camera_preset: str = "static",
        subject_mode: str = "single",
        enhance_enabled: bool = False,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.datetime.now().isoformat()
        settings_str = json.dumps(settings or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, created_at, updated_at, status, source_image,
                    user_prompt, inference_prompt, seed, mode, preserve,
                    motion, camera_preset, subject_mode, enhance_enabled,
                    settings_json, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    job_id, now, now, "QUEUED", source_image,
                    user_prompt, inference_prompt, seed, mode, preserve,
                    motion, camera_preset, subject_mode, 1 if enhance_enabled else 0,
                    settings_str, None
                ),
            )
        return self.get_job(job_id) or {}

    def update_job_status(
        self,
        job_id: str,
        status: str,
        raw_output: str | None = None,
        enhanced_output: str | None = None,
        inference_prompt: str | None = None,
        error_message: str | None = None,
        settings_update: dict[str, Any] | None = None,
    ):
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            # If settings need update
            if settings_update is not None:
                cur = conn.execute("SELECT settings_json FROM jobs WHERE job_id = ?", (job_id,))
                row = cur.fetchone()
                existing_settings = json.loads(row["settings_json"]) if row and row["settings_json"] else {}
                existing_settings.update(settings_update)
                settings_str = json.dumps(existing_settings)
            else:
                settings_str = None

            query = "UPDATE jobs SET updated_at = ?, status = ?"
            params: list[Any] = [now, status]

            if raw_output is not None:
                query += ", raw_output = ?"
                params.append(raw_output)
            if enhanced_output is not None:
                query += ", enhanced_output = ?"
                params.append(enhanced_output)
            if inference_prompt is not None:
                query += ", inference_prompt = ?"
                params.append(inference_prompt)
            if error_message is not None:
                query += ", error_message = ?"
                params.append(error_message)
            if settings_str is not None:
                query += ", settings_json = ?"
                params.append(settings_str)

            query += " WHERE job_id = ?"
            params.append(job_id)

            conn.execute(query, params)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            return None

    def get_latest_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]

    def delete_job(self, job_id: str) -> bool:
        with self._get_connection() as conn:
            res = conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
            return res.rowcount > 0
