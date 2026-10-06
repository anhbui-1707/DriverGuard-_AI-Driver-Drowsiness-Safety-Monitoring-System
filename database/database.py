"""SQLite with per-thread connections and additive migrations."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from config import SETTINGS


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Repository:
    def __init__(self, path=SETTINGS.database_path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS sessions(
                id INTEGER PRIMARY KEY, start_time TEXT, end_time TEXT,
                avg_risk REAL DEFAULT 0, max_risk REAL DEFAULT 0,
                yawn_count INTEGER DEFAULT 0, drowsiness_count INTEGER DEFAULT 0,
                distraction_count INTEGER DEFAULT 0, emergency_count INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id),
                event_type TEXT, timestamp TEXT, risk_score REAL, description TEXT,
                snapshot_path TEXT);
            CREATE INDEX IF NOT EXISTS events_session ON events(session_id);
            CREATE TABLE IF NOT EXISTS risk_samples(
                id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id),
                elapsed REAL, risk_score REAL);
            CREATE INDEX IF NOT EXISTS samples_session ON risk_samples(session_id);
        ''')
        additions = {"duration": "REAL DEFAULT 0", "status": "TEXT DEFAULT 'COMPLETED'",
                     "source": "TEXT DEFAULT 'CAMERA'", "report": "TEXT DEFAULT ''",
                     "report_source": "TEXT DEFAULT ''"}
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(sessions)")}
        for name, sql_type in additions.items():
            if name not in columns:
                self.db.execute(f"ALTER TABLE sessions ADD COLUMN {name} {sql_type}")
        self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def recover_interrupted(self):
        self.db.execute("UPDATE sessions SET status='INTERRUPTED',end_time=? WHERE status='RUNNING'", (timestamp(),))
        self.db.commit()

    def start_session(self, source):
        cur = self.db.execute("INSERT INTO sessions(start_time,status,source) VALUES(?,?,?)", (timestamp(), "RUNNING", source))
        self.db.commit()
        return cur.lastrowid

    def save_event(self, sid, event_type, risk, description, snapshot=""):
        when = timestamp()
        cur = self.db.execute("INSERT INTO events(session_id,event_type,timestamp,risk_score,description,snapshot_path) VALUES(?,?,?,?,?,?)", (sid, event_type, when, risk, description, snapshot))
        self.db.commit()
        return dict(id=cur.lastrowid, event_type=event_type, timestamp=when,
                    risk_score=risk, description=description, snapshot_path=snapshot)

    def sample(self, sid, elapsed, risk):
        self.db.execute("INSERT INTO risk_samples(session_id,elapsed,risk_score) VALUES(?,?,?)", (sid, elapsed, risk))
        self.db.commit()

    def checkpoint(self, sid, stats, status="RUNNING"):
        self.db.execute('''UPDATE sessions SET duration=?,avg_risk=?,max_risk=?,
            yawn_count=?,drowsiness_count=?,distraction_count=?,emergency_count=?,status=?
            WHERE id=?''', (stats["duration"], stats["avg_risk"], stats["max_risk"],
                          stats["yawn_count"], stats["drowsiness_count"], stats["distraction_count"],
                          stats["emergency_count"], status, sid))
        if status != "RUNNING":
            self.db.execute("UPDATE sessions SET end_time=? WHERE id=?", (timestamp(), sid))
        self.db.commit()

    def sessions(self):
        return [dict(row) for row in self.db.execute("SELECT * FROM sessions ORDER BY id DESC")]

    def events(self, sid):
        return [dict(row) for row in self.db.execute("SELECT * FROM events WHERE session_id=? ORDER BY id", (sid,))]

    def samples(self, sid):
        return [dict(row) for row in self.db.execute("SELECT elapsed,risk_score FROM risk_samples WHERE session_id=? ORDER BY id", (sid,))]

    def save_report(self, sid, report, source):
        self.db.execute("UPDATE sessions SET report=?,report_source=? WHERE id=?", (report, source, sid))
        self.db.commit()
