"""AI Social Campaign Manager API entry point.

Uses the api.py factory to create a versioned FastAPI application.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure 'backend' directory is in sys.path so 'src' can be imported when running from project root
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

load_dotenv(dotenv_path=backend_dir / ".env")

from src.api.api import get_app  # noqa: E402

app = get_app()
