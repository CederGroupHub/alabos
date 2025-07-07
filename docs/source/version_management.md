# Version Management

ALAB includes a comprehensive version management system that automatically records hash versions of task definitions when tasks complete, creates space-efficient backups, and provides restoration capabilities.

## Overview

The version management system provides:

1. **Automatic Version Recording**: Records hash versions of task definitions after each task completion
2. **Space-Efficient Backups**: Only backs up files that have changed since the last version
3. **Restoration Tools**: Multiple ways to restore previous versions
4. **Configuration Management**: Easy enable/disable and customization

## Configuration

Version management can be configured in your `config.toml` file:

```toml
[version_management]
# Enable version recording and backup functionality
enabled = true
# Number of recent versions to keep (older versions will be cleaned up)
keep_versions = 10
```

### Configuration Options

- `enabled`: Enable or disable version management (default: `true`)
- `keep_versions`: Number of recent versions to keep (default: `10`)

## How It Works

### Version Recording

When a task completes successfully, the system:

1. Calculates a SHA256 hash of all relevant files (`.py`, `.toml`, `.yaml`, `.yml`, `.json`)
2. Compares it with the previous version hash
3. If changes are detected, records the new version in the database
4. Backs up only the files that have changed

### Space-Efficient Backups

The system uses a differential backup approach:

- Only files that have changed since the last version are backed up
- Files are stored in `.alab_backups/<version_hash>/` directory
- Each version maintains a complete set of changed files
- Old versions are automatically cleaned up based on configuration

### Database Storage

Version information is stored in a SQLite database at `.alab_backups/version_tracking.db`:

- **versions table**: Stores version metadata (hash, name, creation time, task ID)
- **version_files table**: Stores file information (path, hash, backup location)

## Usage

### Command Line Tools

#### Version Manager CLI

The main CLI tool for managing versions:

```bash
# List all versions
python -m alab_management.scripts.version_manager_cli list

# List versions with detailed information
python -m alab_management.scripts.version_manager_cli list --verbose

# Show details of a specific version
python -m alab_management.scripts.version_manager_cli show <version_hash>

# Restore a version (dry run)
python -m alab_management.scripts.version_manager_cli restore <version_hash> --dry-run

# Restore a version
python -m alab_management.scripts.version_manager_cli restore <version_hash>

# Create a restoration script
python -m alab_management.scripts.version_manager_cli create-script <version_hash> restore_script.py

# Clean up old versions
python -m alab_management.scripts.version_manager_cli cleanup --keep 10
```

#### Standalone Restoration Tool

A standalone restoration tool that can be used independently:

```bash
# List available versions
python -m alab_management.scripts.restore_version list

# Show details of a version
python -m alab_management.scripts.restore_version show <version_hash>

# Restore a version (dry run)
python -m alab_management.scripts.restore_version restore <version_hash> --dry-run

# Restore a version
python -m alab_management.scripts.restore_version restore <version_hash>

# Create restoration script
python -m alab_management.scripts.restore_version create-script <version_hash> restore_script.py
```

### Programmatic Usage

You can also use the version management system programmatically:

```python
from alab_management.utils.version_manager import VersionManager

# Initialize version manager
version_manager = VersionManager()

# List all versions
versions = version_manager.list_versions()
for version in versions:
    print(f"Version: {version['version_hash']}")
    print(f"Task ID: {version['task_id']}")
    print(f"Created: {version['created_at']}")

# Get files for a specific version
files = version_manager.get_version_files("abc123...")

# Restore a version
success = version_manager.restore_version("abc123...")

# Create restoration script
version_manager.create_restoration_script("abc123...", "restore_script.py")

# Clean up old versions
removed_count = version_manager.cleanup_old_versions(keep_count=10)
```

## Database Integration

Version information is also stored in the main ALAB database:

- When a task completes, the `version_hash` field is added to the task document
- This allows you to query which version was used for each task
- Example query: Find all tasks that used a specific version

```python
from alab_management.task_view import TaskView

task_view = TaskView()
tasks_with_version = task_view._task_collection.find({"version_hash": "abc123..."})
```

## File Structure

The backup system creates the following structure:

```
.alab_backups/
├── version_tracking.db          # SQLite database with version metadata
├── abc123def456/               # Version directory
│   ├── tasks/
│   │   └── my_task.py
│   └── devices/
│       └── my_device.py
└── def789ghi012/               # Another version directory
    └── config.toml
```

## Best Practices

### 1. Regular Cleanup

Configure appropriate `keep_versions` to prevent disk space issues:

```toml
[version_management]
keep_versions = 20  # Keep last 20 versions
```

### 2. Backup Verification

Before restoring, always use dry-run mode to verify what will be restored:

```bash
python -m alab_management.scripts.version_manager_cli restore <version_hash> --dry-run
```

### 3. Restoration Scripts

For important restorations, create standalone scripts:

```bash
python -m alab_management.scripts.version_manager_cli create-script <version_hash> important_restore.py
```

### 4. Monitoring

Check version management status regularly:

```bash
# List recent versions
python -m alab_management.scripts.version_manager_cli list

# Check backup disk usage
du -sh .alab_backups/
```

## Troubleshooting

### Common Issues

1. **Version Management Disabled**
   - Check `config.toml` for `[version_management]` section
   - Ensure `enabled = true`

2. **Backup Directory Not Found**
   - Look for `.alab_backups` directory in your working directory
   - Check file permissions

3. **Restoration Fails**
   - Verify version hash exists: `list` command
   - Check backup files exist in version directory
   - Use dry-run mode first

4. **Disk Space Issues**
   - Reduce `keep_versions` in configuration
   - Run manual cleanup: `cleanup --keep 5`

### Logs

Version management activities are logged in the main ALAB logs:

- `VersionRecorded`: When a new version is recorded
- `VersionRecordFailed`: When version recording fails

### Manual Recovery

If the version management system is corrupted:

1. Backup the `.alab_backups` directory
2. Delete the `version_tracking.db` file
3. Restart ALAB to reinitialize the system

## Security Considerations

- Backup files contain your task and device definitions
- Ensure `.alab_backups` directory has appropriate permissions
- Consider encrypting sensitive backup data
- Regularly audit version history for sensitive information

## Performance Impact

- Version recording adds minimal overhead to task completion
- Hash calculation is fast for typical file sizes
- Backup operations are asynchronous and don't block task execution
- Database queries are optimized for typical usage patterns 