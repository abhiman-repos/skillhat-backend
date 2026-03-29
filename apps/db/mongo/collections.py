from .db import get_db

db = get_db()

# 🔹 Generic
def get_collection(name: str):
    return db[name]

# 🔹 Specific collections (recommended)
users_collection = db["users"]
mentors_collection = db["mentors"]
courses_collection = db["courses"]
internships_collection = db["internships"]