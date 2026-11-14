import os, sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.getenv("ASTRA_DB_PATH", str(Path(__file__).resolve().parents[1] / "astramind.db"))
SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS astronauts(id TEXT PRIMARY KEY,name TEXT,mission TEXT,mission_day INTEGER,created_at TEXT);
CREATE TABLE IF NOT EXISTS observations(
 id TEXT PRIMARY KEY, astronaut_id TEXT, domain TEXT, metric TEXT, value REAL, unit TEXT,
 observed_at TEXT, source TEXT, provenance TEXT, quality REAL, metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_obs_subject_metric ON observations(astronaut_id,domain,metric,observed_at);
CREATE TABLE IF NOT EXISTS alerts(
 id TEXT PRIMARY KEY, astronaut_id TEXT, domain TEXT, metric TEXT, severity TEXT,
 title TEXT, message TEXT, observed_value REAL, baseline_value REAL, deviation REAL,
 created_at TEXT, acknowledged INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sync_events(event_id TEXT PRIMARY KEY, astronaut_id TEXT, received_at TEXT);
"""
@contextmanager
def db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
def init_db():
    with db() as conn:
        conn.executescript(SCHEMA)
