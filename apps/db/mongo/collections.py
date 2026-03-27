from .db import get_db


def get_collection(name: str):
    return get_db()[name]


# 🔹 Specific collections (recommended)
def users_collection():
    return get_collection("users")


def mentors_collection():
    return get_collection("mentors")


def courses_collection():
    return get_collection("courses")