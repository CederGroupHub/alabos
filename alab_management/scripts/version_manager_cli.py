#!/usr/bin/env python3
"""
ALAB Version Manager CLI.

This script provides command-line interface for managing ALAB versions,
viewing version history, and performing restoration operations.
"""

import argparse
import sys
from pathlib import Path

from alab_management.utils.version_manager import VersionManager


def list_versions(version_manager: VersionManager, verbose: bool = False):
    """List all recorded versions."""
    versions = version_manager.list_versions()

    if not versions:
        print("No versions recorded yet.")
        return

    print(f"Found {len(versions)} recorded versions:")
    print("-" * 80)

    for i, version in enumerate(versions, 1):
        print(f"{i}. Version: {version['version_hash'][:12]}...")
        print(f"   Name: {version['version_name']}")
        print(f"   Created: {version['created_at']}")
        print(f"   Task ID: {version['task_id']}")
        print(f"   Description: {version['description']}")

        if verbose:
            files = version_manager.get_version_files(version["version_hash"])
            print(f"   Files: {len(files)} files backed up")
            for file_info in files[:5]:  # Show first 5 files
                print(f"     - {file_info['file_path']}")
            if len(files) > 5:
                print(f"     ... and {len(files) - 5} more files")

        print()


def show_version_details(version_manager: VersionManager, version_hash: str):
    """Show detailed information about a specific version."""
    versions = version_manager.list_versions()
    target_version = None

    for version in versions:
        if version["version_hash"] == version_hash:
            target_version = version
            break

    if not target_version:
        print(f"Version {version_hash} not found.")
        return

    print("Version Details:")
    print(f"Hash: {target_version['version_hash']}")
    print(f"Name: {target_version['version_name']}")
    print(f"Created: {target_version['created_at']}")
    print(f"Task ID: {target_version['task_id']}")
    print(f"Description: {target_version['description']}")
    print()

    files = version_manager.get_version_files(version_hash)
    print(f"Backed up files ({len(files)}):")
    for file_info in files:
        print(f"  - {file_info['file_path']}")
        print(f"    Hash: {file_info['file_hash'][:12]}...")
        print(f"    Backup: {file_info['backup_path']}")


def restore_version(
    version_manager: VersionManager,
    version_hash: str,
    target_dir: Path | None = None,
    dry_run: bool = False,
):
    """Restore a specific version."""
    if dry_run:
        print(f"DRY RUN: Would restore version {version_hash}")
        files = version_manager.get_version_files(version_hash)
        print(f"Files that would be restored ({len(files)}):")
        for file_info in files:
            print(f"  - {file_info['file_path']}")
        return

    print(f"Restoring version {version_hash}...")
    success = version_manager.restore_version(version_hash, target_dir)

    if success:
        print("Restoration completed successfully!")
    else:
        print("Restoration failed. Version not found or invalid.")


def create_restoration_script(
    version_manager: VersionManager, version_hash: str, output_path: Path
):
    """Create a restoration script for a specific version."""
    print(f"Creating restoration script for version {version_hash}...")
    success = version_manager.create_restoration_script(version_hash, output_path)

    if success:
        print(f"Restoration script created: {output_path}")
        print("You can run this script to restore the version:")
        print(f"  python {output_path}")
    else:
        print(
            "Failed to create restoration script. Version not found or no files to restore."
        )


def cleanup_versions(version_manager: VersionManager, keep_count: int):
    """Clean up old versions."""
    print(f"Cleaning up old versions, keeping {keep_count} most recent...")
    removed_count = version_manager.cleanup_old_versions(keep_count)

    if removed_count > 0:
        print(f"Cleaned up {removed_count} old versions.")
    else:
        print("No versions to clean up.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ALAB Version Manager - Manage task definition versions and restoration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all versions
  python version_manager_cli.py list

  # List versions with details
  python version_manager_cli.py list --verbose

  # Show details of a specific version
  python version_manager_cli.py show <version_hash>

  # Restore a version (dry run)
  python version_manager_cli.py restore <version_hash> --dry-run

  # Restore a version
  python version_manager_cli.py restore <version_hash>

  # Create restoration script
  python version_manager_cli.py create-script <version_hash> restore_script.py

  # Clean up old versions
  python version_manager_cli.py cleanup --keep 10
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all recorded versions")
    list_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )

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

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old versions")
    cleanup_parser.add_argument(
        "--keep", type=int, default=10, help="Number of recent versions to keep"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        version_manager = VersionManager()

        if args.command == "list":
            list_versions(version_manager, args.verbose)
        elif args.command == "show":
            show_version_details(version_manager, args.version_hash)
        elif args.command == "restore":
            restore_version(
                version_manager, args.version_hash, args.target_dir, args.dry_run
            )
        elif args.command == "create-script":
            create_restoration_script(
                version_manager, args.version_hash, args.output_path
            )
        elif args.command == "cleanup":
            cleanup_versions(version_manager, args.keep)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
