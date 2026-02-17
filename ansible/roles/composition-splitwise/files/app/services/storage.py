import json
import os
from pathlib import Path
from typing import Any, Dict, List
import fcntl
from contextlib import contextmanager


class FileStorage:
    """File-based storage with locking for concurrent access."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self.groups_dir = self.data_dir / "groups"
        self.groups_dir.mkdir(exist_ok=True)

    @contextmanager
    def _lock_file(self, file_path: Path):
        """Context manager for file locking."""
        lock_file = file_path.with_suffix(file_path.suffix + ".lock")
        lock_file.touch(exist_ok=True)
        with open(lock_file, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _read_json(self, file_path: Path, default: Any = None) -> Any:
        """Read JSON file with locking."""
        if not file_path.exists():
            return default if default is not None else {}
        with self._lock_file(file_path):
            with open(file_path, "r") as f:
                return json.load(f)

    def _write_json(self, file_path: Path, data: Any) -> None:
        """Write JSON file with locking."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_file(file_path):
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

    # User operations
    def get_users(self) -> List[Dict]:
        """Get all users."""
        data = self._read_json(self.users_file, {"users": []})
        return data.get("users", [])

    def get_user_by_id(self, user_id: str) -> Dict | None:
        """Get user by ID."""
        users = self.get_users()
        return next((u for u in users if u["id"] == user_id), None)

    def get_user_by_username(self, username: str) -> Dict | None:
        """Get user by username."""
        users = self.get_users()
        return next((u for u in users if u["username"] == username), None)

    def get_user_by_token(self, token: str) -> Dict | None:
        """Get user by API token."""
        users = self.get_users()
        return next((u for u in users if u.get("api_token") == token), None)

    def create_user(self, user_data: Dict) -> Dict:
        """Create a new user."""
        users = self.get_users()
        users.append(user_data)
        self._write_json(self.users_file, {"users": users})
        return user_data

    # Group operations
    def get_groups(self) -> List[Dict]:
        """Get all groups."""
        groups = []
        for group_dir in self.groups_dir.iterdir():
            if group_dir.is_dir():
                metadata_file = group_dir / "metadata.json"
                if metadata_file.exists():
                    metadata = self._read_json(metadata_file)
                    groups.append(metadata)
        return groups

    def get_group(self, group_id: str) -> Dict | None:
        """Get group by ID."""
        metadata_file = self.groups_dir / group_id / "metadata.json"
        if not metadata_file.exists():
            return None
        return self._read_json(metadata_file)

    def create_group(self, group_data: Dict) -> Dict:
        """Create a new group."""
        group_id = group_data["id"]
        group_dir = self.groups_dir / group_id
        group_dir.mkdir(parents=True, exist_ok=True)
        (group_dir / "transactions").mkdir(exist_ok=True)

        metadata_file = group_dir / "metadata.json"
        self._write_json(metadata_file, group_data)
        return group_data

    def update_group(self, group_id: str, group_data: Dict) -> Dict:
        """Update group metadata."""
        metadata_file = self.groups_dir / group_id / "metadata.json"
        self._write_json(metadata_file, group_data)
        return group_data

    # Transaction operations
    def get_transactions(self, group_id: str) -> List[Dict]:
        """Get all transactions for a group."""
        transactions_dir = self.groups_dir / group_id / "transactions"
        if not transactions_dir.exists():
            return []

        transactions = []
        for tx_file in transactions_dir.glob("*.json"):
            tx_data = self._read_json(tx_file)
            transactions.append(tx_data)

        # Sort by created_at descending
        transactions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return transactions

    def get_transaction(self, group_id: str, transaction_id: str) -> Dict | None:
        """Get a specific transaction."""
        tx_file = self.groups_dir / group_id / "transactions" / f"{transaction_id}.json"
        if not tx_file.exists():
            return None
        return self._read_json(tx_file)

    def create_transaction(self, group_id: str, transaction_data: Dict) -> Dict:
        """Create a new transaction."""
        transaction_id = transaction_data["id"]
        tx_file = self.groups_dir / group_id / "transactions" / f"{transaction_id}.json"
        self._write_json(tx_file, transaction_data)
        return transaction_data

    def update_transaction(self, group_id: str, transaction_id: str, transaction_data: Dict) -> Dict:
        """Update a transaction."""
        tx_file = self.groups_dir / group_id / "transactions" / f"{transaction_id}.json"
        self._write_json(tx_file, transaction_data)
        return transaction_data

    def delete_transaction(self, group_id: str, transaction_id: str) -> bool:
        """Delete a transaction."""
        tx_file = self.groups_dir / group_id / "transactions" / f"{transaction_id}.json"
        if tx_file.exists():
            tx_file.unlink()
            return True
        return False
