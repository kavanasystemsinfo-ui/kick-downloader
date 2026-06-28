"""Pytest configuration - sets up environment before tests run."""
import os
import sys

# Set cleanup time to 0 for tests BEFORE any other imports
os.environ["CLEANUP_GRACE_SECONDS"] = "0"

# Force reload of main module if already imported
if "main" in sys.modules:
    import importlib
    importlib.reload(sys.modules["main"])