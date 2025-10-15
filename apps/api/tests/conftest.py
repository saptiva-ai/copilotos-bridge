"""
Pytest configuration and fixtures for API tests.

This file is automatically loaded by pytest before running tests.
It configures the Python path to enable proper imports.
"""

import sys
from pathlib import Path

# Add the app directory to Python path (not src/)
# This allows tests to import as: from src.main import app
# This way, src is treated as a package and relative imports work
app_path = Path(__file__).parent.parent
if str(app_path) not in sys.path:
    sys.path.insert(0, str(app_path))

print(f"✓ Added {app_path} to PYTHONPATH for tests (import as: from src.module import ...)")
