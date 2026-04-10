# apps/users/views.py

import json
import bcrypt
import jwt
from bson import ObjectId
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from apps.db.mongo.collections import users_collection, address_collection, enrollments_collection, internships_collection
from apps.utils.logger import log_error, log_info


# ================= COMMON HELPERS ================= #

def decode_token(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None, JsonResponse({"error": "Unauthorized"}, status=401)

    try:
        token = auth_header.split(" ")[1]

        # ❗ Fix: check empty token
        if not token or token in ["undefined", "null"]:
            return None, JsonResponse({"error": "Invalid token"}, status=401)

        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        user_id = decoded.get("user_id")

        user = users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            return None, JsonResponse({"error": "User not found"}, status=404)

        return user, None

    except jwt.DecodeError:
        return None, JsonResponse({"error": "Invalid token format"}, status=401)

    except jwt.ExpiredSignatureError:
        return None, JsonResponse({"error": "Token expired"}, status=401)

    except Exception as e:
        log_error(f"JWT ERROR: {str(e)}")
        return None, JsonResponse({"error": "Unauthorized"}, status=401)


def safe_json(request):
    try:
        return json.loads(request.body)
    except:
        return {}


# ================= AUTH ================= #

@csrf_exempt
def user_register(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = safe_json(request)

        required_fields = ["full_name", "email", "password", "college", "course"]

        if not all(data.get(field) for field in required_fields):
            return JsonResponse({"error": "Missing required fields"}, status=400)

        if users_collection.find_one({"email": data["email"]}):
            return JsonResponse({"error": "User already exists"}, status=400)

        hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()

        user_doc = {
            # 🔐 Basic
            "full_name": data["full_name"],
            "email": data["email"],
            "password": hashed,

            # 📞 Personal
            "phone": data.get("phone", ""),
            "gender": data.get("gender", ""),
            "dob": data.get("dob", ""),

            # 🎓 Education
            "college": data.get("college", ""),
            "course": data.get("course", ""),
            "branch": data.get("branch", ""),
            "year": data.get("year", ""),

            # 📍 Location
            "state": data.get("state", ""),
            "city": data.get("city", ""),

            # 💼 Career
            "skills": data.get("skills", []),
            "bio": data.get("bio", ""),
            "linkedin": data.get("linkedin", ""),
            "github": data.get("github", ""),

            # 🏆 Learning
            "certificates": [],
            "internships": [],

            # ⚙️ Meta
            "is_active": True,
        }

        result = users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)

        token = jwt.encode(
            {"user_id": user_id},
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        return JsonResponse({
            "message": "User registered",
            "token": token,
            "user": {
                "id": user_id,
                "full_name": user_doc["full_name"],
                "email": user_doc["email"],
                "college": user_doc["college"],
                "course": user_doc["course"],
            }
        }, status=201)

    except Exception as e:
        log_error(f"REGISTER ERROR: {str(e)}")
        return JsonResponse({"error": "Server error"}, status=500)


@csrf_exempt
def user_login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = safe_json(request)

        email = data.get("email")
        password = data.get("password")

        user = users_collection.find_one({"email": email})

        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        if not bcrypt.checkpw(password.encode(), user["password"].encode()):
            return JsonResponse({"error": "Invalid password"}, status=401)

        token = jwt.encode(
            {"user_id": str(user["_id"])},
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        log_info(f"User login: {email}")

        return JsonResponse({
            "token": token,
            "user": {
                "id": str(user["_id"]),
                "name": user.get("name"),
                "email": user.get("email"),
            }
        })

    except Exception as e:
        log_error(f"LOGIN ERROR: {str(e)}")
        return JsonResponse({"error": "Server error"}, status=500)


# ================= PROFILE ================= #

@csrf_exempt
def get_profile(request):
    user, error = decode_token(request)
    if error:
        return error

    return JsonResponse({
        "id": str(user["_id"]),
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "gender": user.get("gender"),
        # 🎓 Education
        "college": user.get("college"),
        "course": user.get("course"),
        "branch": user.get("branch"),
        "graduation_year": user.get("graduation_year"),

        # 📍 Location
        "state": user.get("state"),
        "city": user.get("city"),

        # 💼 Career
        "skills": user.get("skills"),
        "linkedin": user.get("linkedin"),

        # 🏆 Learning
        "certificates": user.get("certificates"),
        "internships": user.get("internships"),

    })

@csrf_exempt
def update_profile(request):
    if request.method != "PUT":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user, error = decode_token(request)
    if error:
        return error

    data = safe_json(request)

    allowed_fields = [
        "full_name", "phone", "gender", "dob",
        "college", "course", "branch", "graduation_year",
        "state", "city",
        "skills", "bio", "linkedin", "github", 
    ]

    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if "password" in data:
        update_data["password"] = bcrypt.hashpw(
            data["password"].encode(), bcrypt.gensalt()
        ).decode()

    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": update_data}
    )

    return JsonResponse({"message": "Profile updated"})


@csrf_exempt
def delete_user(request):
    if request.method != "DELETE":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user, error = decode_token(request)
    if error:
        return error

    users_collection.delete_one({"_id": user["_id"]})

    log_info(f"User deleted: {user['email']}")

    return JsonResponse({"message": "User deleted"})


# ================= ADDRESS ================= #

@csrf_exempt
def add_address(request):
    user, error = decode_token(request)
    if error:
        return error

    data = safe_json(request)

    address = {
        "user_id": user["_id"],
        "name": data.get("name"),
        "address": data.get("address"),
        "city": data.get("city"),
        "state": data.get("state"),
        "pincode": data.get("pincode"),
        "phone": data.get("phone"),
        "college": data.get("lat"),
        "course": data.get("lng"),
        "": False,
    }

    result = address_collection.insert_one(address)

    return JsonResponse({
        "message": "Address added",
        "id": str(result.inserted_id)
    })


@csrf_exempt
def get_addresses(request):
    user, error = decode_token(request)
    if error:
        return error

    addresses = list(address_collection.find({"user_id": user["_id"]}))

    for a in addresses:
        a["_id"] = str(a["_id"])

    return JsonResponse({"addresses": addresses})


@csrf_exempt
def delete_address(request, address_id):
    user, error = decode_token(request)
    if error:
        return error

    address_collection.delete_one({
        "_id": ObjectId(address_id),
        "user_id": user["_id"]
    })

    return JsonResponse({"message": "Deleted"})

@csrf_exempt
def logout_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    user, error = decode_token(request)
    if error:
        return error

    try:
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"is_active": False}}
        )

        return JsonResponse({"message": "Logged out successfully"})

    except Exception as e:
        return JsonResponse({"error": "Server error"}, status=500)
    
@csrf_exempt
def my_enrollments(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    user, error = decode_token(request)
    if error:
        return error

    enrollments = list(enrollments_collection.find({
        "user_id": user["_id"]
    }))

    result = []

    for e in enrollments:
        internship = internships_collection.find_one({
            "_id": e["internship_id"]
        })

        if internship:
            internship["_id"] = str(internship["_id"])
            result.append(internship)

    return JsonResponse({"enrollments": result})
    
def my_certificates(request):
    user, error = decode_token(request)
    if error:
        return error

    enrollments = list(enrollments_collection.find({
        "user_id": user["_id"],
        "certificate_issued": True
    }))

    result = []

    for e in enrollments:
        internship = internships_collection.find_one({
            "_id": e["internship_id"]
        })

        result.append({
            "id": str(e["_id"]),
            "title": internship.get("title"),
            "course": internship.get("title"),
            "issuedDate": e.get("issued_at"),
            "certificateId": f"CERT-{str(e['_id'])[:6]}"
        })

    return JsonResponse({"certificates": result})