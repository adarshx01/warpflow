import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Get a new database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
