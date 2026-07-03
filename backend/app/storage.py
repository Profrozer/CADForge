"""History persistence: sqlite for records, filesystem for geometry files."""

import base64
import json
import shutil
import sqlite3
import time
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PARTS_DIR = DATA_DIR / "parts"
DB_PATH = DATA_DIR / "cadforge.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS versions (
    part_id     TEXT NOT NULL,
    version     INTEGER NOT NULL,
    created_at  REAL NOT NULL,
    prompt      TEXT NOT NULL,
    spec        TEXT,
    code        TEXT NOT NULL,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL,
    exports     TEXT NOT NULL,
    stats       TEXT,
    thumbnail   TEXT,
    PRIMARY KEY (part_id, version)
);
"""


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def version_dir(part_id: str, version: int) -> Path:
    return PARTS_DIR / part_id / f"v{version}"


def new_part_id() -> str:
    return uuid.uuid4().hex[:12]


def next_version(part_id: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT MAX(version) AS v FROM versions WHERE part_id = ?", (part_id,)
        ).fetchone()
    return (row["v"] or 0) + 1


def save_version(part_id: str, version: int, *, prompt: str, spec: str | None,
                 code: str, provider: str, model: str, exports: dict,
                 stats: dict | None) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO versions (part_id, version, created_at, prompt, spec, code,"
            " provider, model, exports, stats) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (part_id, version, time.time(), prompt, spec, code, provider, model,
             json.dumps(exports), json.dumps(stats or {})),
        )
    return get_version(part_id, version)


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["exports"] = json.loads(d["exports"])
    d["stats"] = json.loads(d["stats"]) if d.get("stats") else {}
    return d


def get_version(part_id: str, version: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM versions WHERE part_id = ? AND version = ?",
            (part_id, version),
        ).fetchone()
    if row is None:
        raise KeyError(f"Unknown version {part_id}/v{version}")
    return _row_to_dict(row)


def list_history() -> list[dict]:
    """Latest version of every part, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT v.* FROM versions v JOIN (SELECT part_id, MAX(version) AS mv"
            " FROM versions GROUP BY part_id) latest"
            " ON v.part_id = latest.part_id AND v.version = latest.mv"
            " ORDER BY v.created_at DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_versions(part_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM versions WHERE part_id = ? ORDER BY version", (part_id,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def delete_part(part_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM versions WHERE part_id = ?", (part_id,))
    shutil.rmtree(PARTS_DIR / part_id, ignore_errors=True)


def set_thumbnail(part_id: str, version: int, data_url: str) -> None:
    """Store a client-rendered PNG thumbnail (data URL) alongside the version."""
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise ValueError("Thumbnail must be a PNG data URL.")
    png = base64.b64decode(data_url[len(prefix):])
    if len(png) > 2_000_000:
        raise ValueError("Thumbnail too large.")
    vdir = version_dir(part_id, version)
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "thumb.png").write_bytes(png)
    with _connect() as conn:
        conn.execute(
            "UPDATE versions SET thumbnail = 'thumb.png' WHERE part_id = ? AND version = ?",
            (part_id, version),
        )
