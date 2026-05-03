from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime
import cloudinary.uploader
from apps.db.mongo.collections import internships_collection, mentors_collection, enrollments_collection, users_collection, admin_access_collection, certificates_collection
from bson import ObjectId
from bson.errors import InvalidId
from apps.users.views import decode_token
import jwt 
from django.conf import settings
import uuid



def decode_admin_token(request):
    auth_header = request.headers.get("Authorization")

    # 🔥 CHECK HEADER
    if not auth_header:
        return None, JsonResponse({"error": "Authorization header missing"}, status=401)

    if not auth_header.startswith("Bearer "):   # ✅ IMPORTANT SPACE
        return None, JsonResponse({"error": "Invalid auth format"}, status=401)

    try:
        token = auth_header.split(" ")[1].strip()

        # 🔥 TOKEN VALIDATION
        if not token or token in ["undefined", "null"]:
            return None, JsonResponse({"error": "Invalid token"}, status=401)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])  # 🔥 DEBUG

        # 🔥 SUPPORT MULTIPLE PAYLOAD TYPES
        email = payload.get("email")
        admin_id = payload.get("id")

        admin = None

        if email:
            admin = admin_access_collection.find_one({
                "email": email.lower().strip()
            })

        elif admin_id:
            from bson import ObjectId
            admin = admin_access_collection.find_one({
                "_id": ObjectId(admin_id)
            })

        if not admin:
            return None, JsonResponse({"error": "Admin not found"}, status=403)

        return admin, None

    except jwt.ExpiredSignatureError:
        return None, JsonResponse({"error": "Token expired"}, status=401)

    except jwt.DecodeError:
        return None, JsonResponse({"error": "Invalid token format"}, status=401)

    except Exception as e:
        print("ADMIN AUTH ERROR:", str(e))
        return None, JsonResponse({"error": "Unauthorized"}, status=401)


# ---------------------------
# 🔧 UTIL FUNCTIONS
# ---------------------------

def get_mentors_by_names(mentor_names):
    """
    Case-insensitive mentor fetch
    """
    if not mentor_names:
        return []

    try:
        normalized_names = [name.strip().lower() for name in mentor_names]

        mentors_cursor = mentors_collection.find({
            "$expr": {
                "$in": [
                    {"$toLower": "$name"},
                    normalized_names
                ]
            }
        })

        mentors = []
        for mentor in mentors_cursor:
            mentors.append({
                "name": mentor.get("name"),
                "expertise": mentor.get("expertise"),
            })

        return mentors

    except Exception as e:
        print("MENTOR FETCH ERROR:", str(e))
        return []


def parse_json(request):
    try:
        body = request.body.decode("utf-8")
        return json.loads(body) if body else {}
    except Exception:
        return None


# ---------------------------
# 📤 IMAGE UPLOAD
# ---------------------------

@csrf_exempt
def upload_internship_image(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        file = request.FILES.get("image")

        if not file:
            return JsonResponse({"error": "No file provided"}, status=400)

        result = cloudinary.uploader.upload(file)

        return JsonResponse({
            "imageUrl": result.get("secure_url"),
            "publicId": result.get("public_id")
        })

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        return JsonResponse({"error": "Image upload failed"}, status=500)


# ---------------------------
# 🆕 CREATE INTERNSHIP
# ---------------------------

@csrf_exempt
def create_internship(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = parse_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        mentor_names = data.get("mentorNames", [])
        mentors = get_mentors_by_names(mentor_names)

        if mentor_names and not mentors:
            return JsonResponse({
                "error": "Mentors not found",
                "provided": mentor_names
            }, status=400)

        internship_data = {
            "title": data.get("title"),
            "company": data.get("company"),
            "location": data.get("location"),
            "duration": data.get("duration"),
            "stipend": data.get("stipend"),
            "description": data.get("description"),
            "requirements": data.get("requirements"),
            "status": data.get("status", "Active"),
            "imageUrl": data.get("imageUrl"),
            "public_id": data.get("public_id"),
            "mentors": mentors,
            "youtube": data.get("youtube")
        }

        result = internships_collection.insert_one(internship_data)

        return JsonResponse({
            "message": "Internship created successfully",
            "id": str(result.inserted_id)
        })

    except Exception as e:
        print("CREATE ERROR:", str(e))
        return JsonResponse({"error": "Failed to create internship"}, status=500)


# ---------------------------
# 📋 LIST INTERNSHIPS
# ---------------------------

def list_internships(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        internships = list(internships_collection.find())

        for i in internships:
            i["_id"] = str(i["_id"])

        return JsonResponse(internships, safe=False)

    except Exception as e:
        print("LIST ERROR:", str(e))
        return JsonResponse({"error": "Failed to fetch internships"}, status=500)


# ---------------------------
# ❌ DELETE INTERNSHIP
# ---------------------------

@csrf_exempt
def delete_internship(request, id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        internship = internships_collection.find_one({"_id": ObjectId(id)})

        if not internship:
            return JsonResponse({"error": "Not found"}, status=404)

        if internship.get("public_id"):
            cloudinary.uploader.destroy(internship["public_id"])

        internships_collection.delete_one({"_id": ObjectId(id)})

        return JsonResponse({"message": "Deleted successfully"})

    except InvalidId:
        return JsonResponse({"error": "Invalid ID"}, status=400)

    except Exception as e:
        print("DELETE ERROR:", str(e))
        return JsonResponse({"error": "Delete failed"}, status=500)


# ---------------------------
# ✏️ UPDATE INTERNSHIP
# ---------------------------

@csrf_exempt
def update_internship(request, id):
    if request.method != "PUT":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = parse_json(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        update_data = data.copy()

        # Handle mentors safely
        if "mentorNames" in data:
            mentor_names = data.get("mentorNames", [])
            mentors = get_mentors_by_names(mentor_names)

            if mentor_names and not mentors:
                return JsonResponse({
                    "error": "Mentors not found",
                    "provided": mentor_names
                }, status=400)

            update_data["mentors"] = mentors
            update_data.pop("mentorNames", None)

        result = internships_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return JsonResponse({"error": "Internship not found"}, status=404)

        return JsonResponse({"message": "Updated successfully"})

    except InvalidId:
        return JsonResponse({"error": "Invalid ID"}, status=400)

    except Exception as e:
        print("UPDATE ERROR:", str(e))
        return JsonResponse({"error": "Update failed"}, status=500)


# ---------------------------
# 🔍 GET INTERNSHIP
# ---------------------------

def get_internship(request, id):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        internship = internships_collection.find_one({"_id": ObjectId(id)})

        if not internship:
            return JsonResponse({"error": "Not found"}, status=404)

        internship["_id"] = str(internship["_id"])

        return JsonResponse(internship)

    except InvalidId:
        return JsonResponse({"error": "Invalid ID"}, status=400)

    except Exception as e:
        print("GET ERROR:", str(e))
        return JsonResponse({"error": "Fetch failed"}, status=500)
        
def internship(request, id):
    if request.method == "GET":
        try:
            internship = internships_collection.find_one({
                "_id": ObjectId(id)
            })

            if not internship:
                return JsonResponse(
                    {"error": "Internship not found"},
                    status=404
                )

            # ✅ Convert ObjectId to string
            internship["_id"] = str(internship["_id"])

            return JsonResponse(internship)

        except Exception as e:
            print("GET INTERNSHIP ERROR:", str(e))

            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def enroll_internship(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    user, error = decode_token(request)
    if error:
        return error

    data = parse_json(request)
    internship_id = data.get("internship_id")

    if not internship_id:
        return JsonResponse({"error": "internship_id required"}, status=400)

    try:
        # 🔥 Prevent duplicate enrollment
        existing = enrollments_collection.find_one({
            "user_id": user["_id"],
            "internship_id": ObjectId(internship_id)
        })

        if existing:
            return JsonResponse({"message": "Already enrolled"})

        # 🔥 Insert enrollment
        enrollments_collection.insert_one({
            "user_id": user["_id"],
            "internship_id": ObjectId(internship_id),
            "created_at": datetime.utcnow()
        })

        return JsonResponse({"message": "Enrolled successfully"})

    except Exception as e:
        print("ENROLL ERROR:", str(e))
        return JsonResponse({"error": "Enrollment failed"}, status=500)
    
@csrf_exempt
def all_enrollments(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        enrollments = list(enrollments_collection.find())

        result = []

        for e in enrollments:
            try:
                user_id = e.get("user_id")

                # 🔥 Ensure ObjectId
                if isinstance(user_id, str):
                    user_id = ObjectId(user_id)

                user = users_collection.find_one({"_id": user_id})

            except Exception:
                user = None

            internship = internships_collection.find_one({"_id": e["internship_id"]})

            result.append({
                "_id": str(e["_id"]),

                "user": {
                    "id": str(user["_id"]),
                    "name": user.get("full_name") or user.get("name") or "Unknown User",
                    "email": user.get("email") or "N/A",
                } if user else {
                    "id": None,
                    "name": "User not found",
                    "email": "N/A"
                },

                "internship": {
                    "id": str(internship["_id"]),
                    "title": internship.get("title"),
                    "company": internship.get("company"),
                } if internship else None,

                "created_at": e.get("created_at"),
                "certificate_issued": e.get("certificate_issued", False),
            })

        return JsonResponse({"enrollments": result})

    except Exception as e:
        print("ADMIN ERROR:", str(e))
        return JsonResponse({"error": "Failed"}, status=500)
    

@csrf_exempt
def remove_enrollment(request, enrollment_id):
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    admin, error = decode_admin_token(request)
    if error:
        return error

    try:
        if not ObjectId.is_valid(enrollment_id):
            return JsonResponse({"error": "Invalid ID"}, status=400)

        result = enrollments_collection.delete_one({
            "_id": ObjectId(enrollment_id)
        })

        if result.deleted_count == 0:
            return JsonResponse({"error": "Enrollment not found"}, status=404)

        return JsonResponse({"message": "Enrollment removed successfully"})

    except Exception as e:
        print("REMOVE ERROR:", str(e))
        return JsonResponse({"error": "Failed to remove enrollment"}, status=500)
    
@csrf_exempt
def send_certificate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    admin, error = decode_admin_token(request)
    if error:
        return error

    try:
        data = json.loads(request.body or "{}")

        user_id = data.get("user_id")
        internship_id = data.get("internship_id")

        # 🔒 Validate IDs
        if not ObjectId.is_valid(user_id) or not ObjectId.is_valid(internship_id):
            return JsonResponse({"error": "Invalid IDs"}, status=400)

        user_oid = ObjectId(user_id)
        internship_oid = ObjectId(internship_id)

        # 🔍 Check already exists
        existing = certificates_collection.find_one({
            "user_id": user_oid,
            "internship_id": internship_oid,
            "status": {"$ne": "deleted"}
        })

        if existing:
            return JsonResponse({
                "error": "Certificate already issued",
                "certificate_id": existing["certificate_id"]
            }, status=400)

        # 🔥 Fetch data safely
        user = users_collection.find_one({"_id": user_oid})
        internship = internships_collection.find_one({"_id": internship_oid})

        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        if not internship:
            return JsonResponse({"error": "Internship not found"}, status=404)

        # 🔥 SAFE FIELD HANDLING
        user_name = (
            user.get("full_name")
            or user.get("name")
            or user.get("username")
            or "Unknown User"
        )

        user_email = (
            user.get("email")
            or user.get("user_email")
            or "no-email@skillhat.com"
        )

        internship_title = internship.get("title") or "Internship"
        company_name = internship.get("company") or "SkillHat"

        mentor_name = None
        if internship.get("mentors") and len(internship["mentors"]) > 0:
            mentor_name = internship["mentors"][0].get("name")

        # 🔥 Better certificate ID
        certificate_id = f"CERT-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"

        # 🔥 Insert
        certificates_collection.insert_one({
            "certificate_id": certificate_id,
            "user_id": user_oid,
            "internship_id": internship_oid,

            # ✅ SNAPSHOT (FIXED)
            "user_name": user_name,
            "user_email": user_email,
            "internship_title": internship_title,
            "company_name": company_name,
            "mentor_name": mentor_name,

            "issued_by": str(admin.get("_id")),
            "issued_at": datetime.utcnow(),
            "status": "valid"
        })

        return JsonResponse({
            "message": "Certificate issued successfully",
            "certificate_id": certificate_id
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": "Failed"}, status=500)

def verify_certificate(request, certificate_id):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        cert = certificates_collection.find_one({
            "certificate_id": certificate_id
        })

        if not cert:
            return JsonResponse({
                "valid": False,
                "message": "Certificate not found"
            }, status=404)

        return JsonResponse({
            "valid": True,
            "certificate_id": cert.get("certificate_id"),
            "user_name": cert.get("user_name"),
            "user_email": cert.get("user_email"),
            "internship_title": cert.get("internship_title"),
            "company_name": cert.get("company_name"),
            "mentor_name": cert.get("mentor_name"),
            "issued_at": cert.get("issued_at").isoformat() if cert.get("issued_at") else None,
            "status": cert.get("status", "valid")
        })

    except Exception as e:
        print("VERIFY ERROR:", str(e))
        return JsonResponse({"error": "Failed"}, status=500)