import pickle
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_SHARED_STORE = ROOT_DIR / "data" / "temp_uploads" / "shared_data_store"


class DataMemory:
    """Disk-backed object registry that works across multiple MCP processes."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        base_dir = Path(storage_dir) if storage_dir else DEFAULT_SHARED_STORE
        base_dir.mkdir(parents=True, exist_ok=True)

        self._db_path = base_dir / "data_memory.sqlite3"
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, timeout=30, isolation_level=None)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS data_store (
                    address TEXT PRIMARY KEY,
                    payload BLOB NOT NULL,
                    type_name TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def store(self, obj: Any) -> str:
        address = uuid.uuid4().hex
        payload = pickle.dumps(obj)
        type_name = type(obj).__name__
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO data_store(address, payload, type_name, created_at) VALUES(?, ?, ?, ?)",
                    (address, sqlite3.Binary(payload), type_name, time.time()),
                )
        return address

    def get(self, address: Optional[str]) -> Optional[Any]:
        if not address:
            return None
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM data_store WHERE address = ?", (address,)).fetchone()
        if not row:
            return None
        return pickle.loads(row[0])

    def release(self, address: Optional[str]) -> bool:
        if not address:
            return False
        with self._lock:
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM data_store WHERE address = ?", (address,))
                return cur.rowcount > 0

    def info(self, address: Optional[str]) -> Optional[Dict[str, Any]]:
        if not address:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT address, type_name, LENGTH(payload) FROM data_store WHERE address = ?",
                (address,),
            ).fetchone()
        if not row:
            return None
        return {"address": row[0], "type": row[1], "bytes": int(row[2]) if row[2] is not None else None}


data_memory = DataMemory()
