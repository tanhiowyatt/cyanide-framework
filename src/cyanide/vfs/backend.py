import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class VFSBackend(ABC):
    @abstractmethod
    def get_config(self, path: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_content(self, path: str) -> Optional[Union[str, bytes]]:
        pass

    @abstractmethod
    def list_dir(self, path: str) -> List[str]:
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        pass

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        pass

    def close(self):
        """Optional cleanup for the backend."""
        pass


class SqliteBackend(VFSBackend):
    is_shared: bool = False
    tracer: Any = None

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            from opentelemetry import trace

            self.tracer = trace.get_tracer(__name__)
        except ImportError:
            self.tracer = None

    def get_config(self, path: str) -> Optional[Dict[str, Any]]:
        if self.tracer:
            with self.tracer.start_as_current_span("vfs.get_config") as span:
                span.set_attribute("vfs.path", path)
                return self._get_config_query(path)
        return self._get_config_query(path)

    def _get_config_query(self, path: str) -> Optional[Dict[str, Any]]:
        cursor = self._conn.execute(
            "SELECT type, owner, group_name as 'group', perm, size, mtime FROM vfs WHERE path = ?",
            (path,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_content(self, path: str) -> Optional[Union[str, bytes]]:
        cursor = self._conn.execute("SELECT content FROM vfs WHERE path = ?", (path,))
        row = cursor.fetchone()
        return row["content"] if row else None

    def list_dir(self, path: str) -> List[str]:
        if self.tracer:
            with self.tracer.start_as_current_span("vfs.list_dir") as span:
                span.set_attribute("vfs.path", path)
                return self._list_dir_query(path)
        return self._list_dir_query(path)

    def _list_dir_query(self, path: str) -> List[str]:
        cursor = self._conn.execute("SELECT name FROM vfs WHERE parent_path = ?", (path,))
        return [row["name"] for row in cursor.fetchall()]

    def exists(self, path: str) -> bool:
        cursor = self._conn.execute("SELECT 1 FROM vfs WHERE path = ?", (path,))
        if cursor.fetchone():
            return True
        cursor = self._conn.execute("SELECT 1 FROM vfs WHERE parent_path = ? LIMIT 1", (path,))
        return cursor.fetchone() is not None

    def is_dir(self, path: str) -> bool:
        cursor = self._conn.execute("SELECT type FROM vfs WHERE path = ?", (path,))
        row = cursor.fetchone()
        if row:
            return str(row["type"]) == "dir"
        return self.exists(path)

    def close(self):
        if hasattr(self, "_conn") and self._conn:
            self._conn.close()

    def __del__(self):
        self.close()
