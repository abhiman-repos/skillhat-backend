import logging
from apps.db.mongo.collections import users_collection

logger = logging.getLogger(__name__)

def verify_google_token(token):
    """Verify the Google OAuth2 ID token and return the decoded payload."""
    try:
        from google.oauth2 import id_token  # type: ignore[import]
        from google.auth.transport import requests  # type: ignore[import]
    except ImportError:
        logger.error("Google OAuth2 library not available")
        return None

    from django.conf import settings

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        logger.info("✅ Google token verified successfully")
        return idinfo
    except Exception as e:
        logger.error(f"❌ Google token verification failed: {e}")
        return None


def get_or_create_google_user(idinfo):
    """
    Create a new user document in MongoDB if email does not exist,
    otherwise return the existing user document.
    Returns:
        (user_dict, created_flag)
        - user_dict: dict with MongoDB document fields (including '_id' as string)
        - created: bool indicating if a new document was inserted
    """
    email = idinfo.get("email")
    name = idinfo.get("name", "")
    picture = idinfo.get("picture", "")

    if not email:
        raise ValueError("Email not present in Google token")

    # Check for existing user in MongoDB
    existing_user = users_collection.find_one({"email": email})

    if existing_user:
        # Return existing user, ensuring _id is stringified
        existing_user["_id"] = str(existing_user["_id"])
        # Optionally update the picture if changed
        if picture and existing_user.get("picture") != picture:
            users_collection.update_one(
                {"_id": existing_user["_id"]},
                {"$set": {"picture": picture}}
            )
        return existing_user, False

    # Create new user document with the same structure as email registration
    new_user = {
        "full_name": name,
        "email": email,
        "password": "",                # no password for Google users
        "phone": "",
        "gender": "",
        "dob": "",
        "college": "",
        "course": "",
        "branch": "",
        "year": "",
        "state": "",
        "city": "",
        "skills": [],
        "bio": "",
        "linkedin": "",
        "github": "",
        "certificates": [],
        "internships": [],
        "is_active": True,
        "auth_provider": "google",
        "picture": picture,           # store Google profile picture if needed
    }

    result = users_collection.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)
    return new_user, True