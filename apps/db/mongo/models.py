from .db import get_db

def get_users_collection():
    db = get_db()
    return db["admin"]
