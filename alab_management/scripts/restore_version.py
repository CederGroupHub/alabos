#!/usr/bin/env python3
"""
ALAB Version Restoration Program.

This standalone script can restore ALAB configurations to a specific version.
It can be used independently of the main ALAB system.
"""

import argparse
import os
import shutil
import sqlite3
import sys
from pathlib import Path


class StandaloneRestorer:
    """Standalone version restoration utility."""

    def __init__(self, backup_dir: Path):
        """Initialize the restorer with backup directory."""
        self.backup_dir = backup_dir
        self.db_path = backup_dir / "version_tracking.db"

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Version tracking database not found: {self.db_path}"
            )

    def list_versions(self) -> list[dict]:
        """List all available versions."""
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

    def get_version_files(self, version_hash: str) -> list[dict]:
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
        self, version_hash: str, target_dir: Path, dry_run: bool = False
    ) -> bool:
        """
        Restore a specific version to the target directory.

        Args:
            version_hash: The version hash to restore
            target_dir: Target directory for restoration
            dry_run: If True, only show what would be restored

        Returns
        -------
            True if restoration was successful
        """
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
            print(f"Error: Version {version_hash} not found.")
            return False

        conn.close()

        # Get all files for this version
        files = self.get_version_files(version_hash)

        if not files:
            print(f"Error: No files found for version {version_hash}")
            return False

        if dry_run:
            print(f"DRY RUN: Would restore version {version_hash}")
            print(f"Target directory: {target_dir}")
            print(f"Files to restore ({len(files)}):")
            for file_info in files:
                backup_path = Path(file_info["backup_path"])
                target_path = target_dir / file_info["file_path"]
                print(f"  {backup_path} -> {target_path}")
            return True

        # Create backup of current state
        backup_current_state(target_dir)

        # Restore each file
        restored_count = 0
        for file_info in files:
            backup_path = Path(file_info["backup_path"])
            target_path = target_dir / file_info["file_path"]

            if backup_path.exists():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target_path)
                print(f"Restored: {file_info['file_path']}")
                restored_count += 1
            else:
                print(f"Warning: Backup file not found: {backup_path}")

        print(f"Restoration completed! {restored_count} files restored.")
        return True

    def create_restoration_script(self, version_hash: str, output_path: Path) -> bool:
        """Create a standalone restoration script."""
        files = self.get_version_files(version_hash)
        if not files:
            return False

        script_content = f"""#!/usr/bin/env python3
\"\"\"
ALAB Version Restoration Script
Version: {version_hash}
Generated: {__import__('datetime').datetime.now().isoformat()}

This script restores the ALAB configuration to version {version_hash}.
\"\"\"

import os
import shutil
from pathlib import Path

def backup_current_state(target_dir):
    \"\"\"Create a backup of the current state before restoration.\"\"\"
    backup_dir = target_dir / ".restoration_backup"
    backup_dir.mkdir(exist_ok=True)

    for file_path in target_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in [".py", ".toml", ".yaml", ".yml", ".json"]:
            if ".restoration_backup" in str(file_path):
                continue
            rel_path = file_path.relative_to(target_dir)
            backup_path = backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)

    print(f"Current state backed up to: {{backup_dir}}")

def restore_version():
    \"\"\"Restore the ALAB configuration to the specified version.\"\"\"

    # Backup files
    backup_files = {files}

    # Get current working directory
    current_dir = Path.cwd()

    print(f"Restoring ALAB configuration to version {version_hash}...")

    # Create backup of current state
    backup_current_state(current_dir)

    # Restore files
    restored_count = 0
    for file_info in backup_files:
        backup_path = Path(file_info['backup_path'])
        target_path = current_dir / file_info['file_path']

        if backup_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target_path)
            print(f"Restored: {{file_info['file_path']}}")
            restored_count += 1
        else:
            print(f"Warning: Backup file not found: {{backup_path}}")

    print(f"Restoration completed! {{restored_count}} files restored.")

if __name__ == "__main__":
    restore_version()
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Make script executable
        os.chmod(output_path, 0o755)

        return True


def backup_current_state(target_dir: Path):
    """Create a backup of the current state before restoration."""
    backup_dir = target_dir / ".restoration_backup"
    backup_dir.mkdir(exist_ok=True)

    for file_path in target_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix in [
            ".py",
            ".toml",
            ".yaml",
            ".yml",
            ".json",
        ]:
            if ".restoration_backup" in str(file_path):
                continue
            rel_path = file_path.relative_to(target_dir)
            backup_path = backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)

    print(f"Current state backed up to: {backup_dir}")


def find_backup_directory(start_dir: Path) -> Path | None:
    """Find the .alab_backups directory."""
    for path in [start_dir, start_dir.parent]:
        backup_dir = path / ".alab_backups"
        if backup_dir.exists() and (backup_dir / "version_tracking.db").exists():
            return backup_dir
    return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ALAB Version Restoration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available versions
  python restore_version.py list

  # Show details of a version
  python restore_version.py show <version_hash>

  # Restore a version (dry run)
  python restore_version.py restore <version_hash> --dry-run

  # Restore a version
  python restore_version.py restore <version_hash>

  # Create restoration script
  python restore_version.py create-script <version_hash> restore_script.py
        """,
    )

    parser.add_argument(
        "--backup-dir", type=Path, help="Path to .alab_backups directory"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    subparsers.add_parser("list", help="List all available versions")

    # Show command
    show_parser = subparsers.add_parser(
        "show", help="Show details of a specific version"
    )
    show_parser.add_argument("version_hash", help="Version hash to show details for")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a specific version")
    restore_parser.add_argument("version_hash", help="Version hash to restore")
    restore_parser.add_argument(
        "--target-dir", type=Path, help="Target directory for restoration"
    )
    restore_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be restored without actually restoring",
    )

    # Create script command
    script_parser = subparsers.add_parser(
        "create-script", help="Create a restoration script"
    )
    script_parser.add_argument("version_hash", help="Version hash to create script for")
    script_parser.add_argument(
        "output_path", type=Path, help="Output path for the restoration script"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Find backup directory
    if args.backup_dir:
        backup_dir = args.backup_dir
    else:
        backup_dir = find_backup_directory(Path.cwd())
        if not backup_dir:
            print("Error: Could not find .alab_backups directory.")
            print("Please specify the backup directory with --backup-dir")
            sys.exit(1)

    try:
        restorer = StandaloneRestorer(backup_dir)

        if args.command == "list":
            versions = restorer.list_versions()
            if not versions:
                print("No versions found.")
                return

            print(f"Found {len(versions)} versions:")
            print("-" * 80)
            for i, version in enumerate(versions, 1):
                print(
                    f"{i}. {version['version_hash'][:12]}... - {version['version_name']}"
                )
                print(f"   Created: {version['created_at']}")
                print(f"   Task ID: {version['task_id']}")
                print()

        elif args.command == "show":
            versions = restorer.list_versions()
            target_version = None

            for version in versions:
                if version["version_hash"] == args.version_hash:
                    target_version = version
                    break

            if not target_version:
                print(f"Version {args.version_hash} not found.")
                return

            print("Version Details:")
            print(f"Hash: {target_version['version_hash']}")
            print(f"Name: {target_version['version_name']}")
            print(f"Created: {target_version['created_at']}")
            print(f"Task ID: {target_version['task_id']}")
            print(f"Description: {target_version['description']}")
            print()

            files = restorer.get_version_files(args.version_hash)
            print(f"Backed up files ({len(files)}):")
            for file_info in files:
                print(f"  - {file_info['file_path']}")

        elif args.command == "restore":
            target_dir = args.target_dir or Path.cwd()
            restorer.restore_version(args.version_hash, target_dir, args.dry_run)

        elif args.command == "create-script":
            restorer.create_restoration_script(args.version_hash, args.output_path)

        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
