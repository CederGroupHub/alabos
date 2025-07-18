import sys
from contextlib import suppress
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Ensure proper import order to avoid circular imports
def pytest_configure(config):
    """Configure pytest to handle circular imports."""
    # Import modules in the correct order to avoid circular imports
    with suppress(ImportError):
        import alab_management  # noqa: F401
