from .db import get_db

db = get_db()

# 🔹 Generic
def get_collection(name: str):
    return db[name]

# 🔹 Specific collections (recommended)
users_collection = db["users"]
address_collection = db["user_data"]
mentors_collection = db["mentors"]
internships_collection = db["internships"]
enrollments_collection = db["enrollments"]
certificates_collection = db["certificates"]
otp_collection = db["otp"]
admin_access_collection= db["admin_auth"]