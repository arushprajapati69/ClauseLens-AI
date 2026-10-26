"""Pytest configuration — ensures clauselens-ai/ is on sys.path regardless of
where pytest is invoked from (project root or parent directory)."""
import sys
import os

# Add the project root (directory containing this file) to sys.path so that
# `import ingest`, `import config`, etc. always resolve correctly.
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
