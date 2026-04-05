from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import cloudinary.uploader
from apps.db.mongo.collections import internships_collection, mentors_collection
from bson import ObjectId
from bson.errors import InvalidId


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