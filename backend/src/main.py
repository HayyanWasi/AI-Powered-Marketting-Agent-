"""AI Social Campaign Manager API entry point.

Uses the api.py factory to create a versioned FastAPI application.
"""

from dotenv import load_dotenv

load_dotenv()

from src.api.api import get_app

app = get_app()
