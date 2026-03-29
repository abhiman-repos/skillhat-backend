import os
from .connection import get_client


def get_db():
    db_name = os.getenv("MONGO_DB_NAME")

    if not db_name:
        raise ValueError("❌ MONGO_DB_NAME not set")

    client = get_client()
    return client[db_name]

