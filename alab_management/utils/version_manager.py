"""
Version management system for ALAB.

This module provides functionality for:
1. Recording hash versions of task definitions when tasks complete
2. Auto backup of changed files in a space-efficient manner
3. Restoration of previous versions
"""

import contextlib
import hashlib
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from alab_management.config import AlabOSConfig


class VersionManager:
    """Manages version recording, backup, and restoration for task definitions."""

    def __init__(self):
        """Initialize the version manager."""
        self.config = AlabOSConfig()
        self.working_dir = Path(self.config["general"]["working_dir"])
        if not self.working_dir.is_absolute():
            self.working_dir = self.config.path.parent / self.working_dir

        # Create backup directory
        self.backup_dir = self.working_dir / ".alab_backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Initialize SQLite database for version tracking
        self.db_path = self.backup_dir / "version_tracking.db"
        self._init_database()

        # Track current version
        self._current_version = None
        self._current_hash = None

    def _init_database(self):
        """Initialize the SQLite database for version tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create version tracking table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_hash TEXT UNIQUE NOT NULL,
                version_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                task_id TEXT,
                description TEXT
            )
        """
        )

        # Create file tracking table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS version_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_hash TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                backup_path TEXT,
                FOREIGN KEY (version_hash) REFERENCES versions (version_hash)
            )
        """
        )

        conn.commit()
        conn.close()

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (FileNotFoundError, PermissionError):
            return ""

    def _get_directory_hash(
        self, directory: Path, extensions: list[str] | None = None
    ) -> str:
        """Calculate hash of all relevant files in a directory."""
        if extensions is None:
            extensions = [".py", ".toml", ".yaml", ".yml", ".json"]

        file_hashes = []
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                # Skip backup directory and other system files
                if ".alab_backups" in str(file_path) or file_path.name.startswith("."):
                    continue
                file_hash = self._get_file_hash(file_path)
                if file_hash:
                    file_hashes.append(
                        (str(file_path.relative_to(directory)), file_hash)
                    )

        # Sort for consistent hash generation
        file_hashes.sort()

        # Create combined hash
        combined_content = "\n".join(
            [f"{path}:{hash_val}" for path, hash_val in file_hashes]
        )
        return hashlib.sha256(combined_content.encode()).hexdigest()

    def get_current_version_hash(self) -> str:
        """Get the current version hash of the working directory."""
        return self._get_directory_hash(self.working_dir)

    def record_task_completion(self, task_id: str, task_type: str) -> str | None:
        """
        Record the current version hash when a task completes.

        Args:
            task_id: The ID of the completed task
            task_type: The type of task that completed

        Returns
        -------
            The version hash that was recorded, or None if no changes detected
        """
        # Check if version management is enabled
        if not self.config.get("version_management", {}).get("enabled", False):
            return None

        current_hash = self.get_current_version_hash()

        # Check if this is a new version
        if current_hash == self._current_hash:
            return None  # No changes detected

        # Record the new version
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO versions (version_hash, version_name, task_id, description)
                VALUES (?, ?, ?, ?)
            """,
                (
                    current_hash,
                    f"Task_{task_type}_{task_id}",
                    task_id,
                    f"Task completion: {task_type}",
                ),
            )

            # Backup changed files
            self._backup_changed_files(current_hash)

            conn.commit()
            self._current_hash = current_hash

            # Clean up old versions if configured
            keep_count = self.config.get("version_management", {}).get(
                "keep_versions", 10
            )
            self.cleanup_old_versions(keep_count)

            return current_hash

        except sqlite3.IntegrityError:
            # Version already exists
            return current_hash
        finally:
            conn.close()

    def _backup_changed_files(self, version_hash: str):
        """Backup only the files that have changed since the last version."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the previous version hash
        cursor.execute(
            """
            SELECT version_hash FROM versions
            WHERE version_hash != ?
            ORDER BY created_at DESC
            LIMIT 1
        """,
            (version_hash,),
        )

        result = cursor.fetchone()
        previous_hash = result[0] if result else None

        # Get files from previous version
        previous_files = {}
        if previous_hash:
            cursor.execute(
                """
                SELECT file_path, file_hash FROM version_files
                WHERE version_hash = ?
            """,
                (previous_hash,),
            )
            previous_files = {row[0]: row[1] for row in cursor.fetchall()}

        # Check current files
        current_files = {}
        backup_files = []

        for file_path in self.working_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [
                ".py",
                ".toml",
                ".yaml",
                ".yml",
                ".json",
            ]:
                if ".alab_backups" in str(file_path) or file_path.name.startswith("."):
                    continue

                rel_path = str(file_path.relative_to(self.working_dir))
                current_hash = self._get_file_hash(file_path)
                current_files[rel_path] = current_hash

                # Check if file has changed
                if (
                    rel_path not in previous_files
                    or previous_files[rel_path] != current_hash
                ):
                    # File is new or changed, backup it
                    backup_path = self.backup_dir / version_hash / rel_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, backup_path)
                    backup_files.append(
                        (version_hash, rel_path, current_hash, str(backup_path))
                    )

        # Record file information
        cursor.executemany(
            """
            INSERT INTO version_files (version_hash, file_path, file_hash, backup_path)
            VALUES (?, ?, ?, ?)
        """,
            backup_files,
        )

        conn.commit()
        conn.close()

    def list_versions(self) -> list[dict[str, Any]]:
        """List all recorded versions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT version_hash, version_name, created_at, task_id, description
            FROM versions
            ORDER BY created_at DESC
        """
        )

        versions = []
        for row in cursor.fetchall():
            versions.append(
                {
                    "version_hash": row[0],
                    "version_name": row[1],
                    "created_at": row[2],
                    "task_id": row[3],
                    "description": row[4],
                }
            )

        conn.close()
        return versions

    def get_version_files(self, version_hash: str) -> list[dict[str, str]]:
        """Get all files for a specific version."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT file_path, file_hash, backup_path
            FROM version_files
            WHERE version_hash = ?
        """,
            (version_hash,),
        )

        files = []
        for row in cursor.fetchall():
            files.append(
                {"file_path": row[0], "file_hash": row[1], "backup_path": row[2]}
            )

        conn.close()
        return files

    def restore_version(
        self, version_hash: str, target_dir: Path | None = None
    ) -> bool:
        """
        Restore a specific version to the target directory.

        Args:
            version_hash: The version hash to restore
            target_dir: Target directory for restoration (defaults to working_dir)

        Returns
        -------
            True if restoration was successful, False otherwise
        """
        if target_dir is None:
            target_dir = self.working_dir

        # Verify version exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) FROM versions WHERE version_hash = ?
        """,
            (version_hash,),
        )

        if cursor.fetchone()[0] == 0:
            conn.close()
            return False

        # Get all files for this version
        files = self.get_version_files(version_hash)

        # Restore each file
        for file_info in files:
            backup_path = Path(file_info["backup_path"])
            target_path = target_dir / file_info["file_path"]

            if backup_path.exists():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target_path)

        conn.close()
        return True

    def create_restoration_script(self, version_hash: str, output_path: Path) -> bool:
        """
        Create a restoration script for a specific version.

        Args:
            version_hash: The version hash to create script for
            output_path: Path where to save the restoration script

        Returns
        -------
            True if script was created successfully
        """
        files = self.get_version_files(version_hash)
        if not files:
            return False

        script_content = f"""#!/usr/bin/env python3
\"\"\"
ALAB Version Restoration Script
Version: {version_hash}
Generated: {datetime.now().isoformat()}

This script restores the ALAB configuration to version {version_hash}.
\"\"\"

import os
import shutil
from pathlib import Path

def restore_version():
    \"\"\"Restore the ALAB configuration to the specified version.\"\"\"

    # Backup files
    backup_files = {files}

    # Get current working directory
    current_dir = Path.cwd()

    print(f"Restoring ALAB configuration to version {version_hash}...")

    for file_info in backup_files:
        backup_path = Path(file_info['backup_path'])
        target_path = current_dir / file_info['file_path']

        if backup_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target_path)
            print(f"Restored: {{file_info['file_path']}}")
        else:
            print(f"Warning: Backup file not found: {{backup_path}}")

    print("Restoration completed!")

if __name__ == "__main__":
    restore_version()
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Make script executable
        os.chmod(output_path, 0o755)

        return True

    def cleanup_old_versions(self, keep_count: int = 10) -> int:
        """
        Clean up old versions, keeping only the most recent ones.

        Args:
            keep_count: Number of recent versions to keep

        Returns
        -------
            Number of versions cleaned up
        """
        versions = self.list_versions()
        if len(versions) <= keep_count:
            return 0

        versions_to_remove = versions[keep_count:]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        removed_count = 0
        for version in versions_to_remove:
            version_hash = version["version_hash"]

            # Remove backup files
            files = self.get_version_files(version_hash)
            for file_info in files:
                backup_path = Path(file_info["backup_path"])
                if backup_path.exists():
                    backup_path.unlink()
                    # Remove empty directories
                    with contextlib.suppress(OSError):
                        backup_path.parent.rmdir()

            # Remove from database
            cursor.execute(
                "DELETE FROM version_files WHERE version_hash = ?", (version_hash,)
            )
            cursor.execute(
                "DELETE FROM versions WHERE version_hash = ?", (version_hash,)
            )
            removed_count += 1

        conn.commit()
        conn.close()

        return removed_count
