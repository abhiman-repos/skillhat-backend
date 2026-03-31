from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import cloudinary.uploader
from apps.db.mongo.collections import internships_collection , mentors_collection

from bson import ObjectId


@csrf_exempt
def upload_internship_image(request):
    if request.method == "POST":
        try:
            file = request.FILES.get("image")

            if not file:
                return JsonResponse({"error": "No file"}, status=400)

            result = cloudinary.uploader.upload(file)

            return JsonResponse({
                "imageUrl": result["secure_url"],
                "publicId": result["public_id"]
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
# ✅ CREATE INTERNSHIP (WITH IMAGE)
@csrf_exempt
def create_internship(request):
    if request.method == "POST":
        try:
            body = request.body.decode("utf-8")

            if not body:
                return JsonResponse({"error": "Empty body"}, status=400)

            data = json.loads(body)

            # ✅ mentor names from frontend
            mentor_names = data.get("mentorNames", [])

            mentors = []

            if mentor_names:
                mentors_cursor = mentors_collection.find({
                    "name": {"$in": mentor_names}
                })

                for mentor in mentors_cursor:
                    mentors.append({
                        "name": mentor.get("name"),
                        "expertise": mentor.get("expertise"),
                    })
            

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

                # 🔥 store mentors by name
                "mentors": mentors,
                "youtube": data.get("youtube")
            }

            print("Mentor Names from frontend:", mentor_names)
            print("Mentors saved:", mentors)

            result = internships_collection.insert_one(internship_data)

            return JsonResponse({
                "message": "Internship created successfully",
                "id": str(result.inserted_id)
            })

        except Exception as e:
            print("ERROR:", str(e))
            return JsonResponse({"error": str(e)}, status=500)


# ✅ LIST INTERNSHIPS
def list_internships(request):
    if request.method == "GET":
        internships = list(internships_collection.find())

        for i in internships:
            i["_id"] = str(i["_id"])

        return JsonResponse(internships, safe=False)


# ✅ DELETE INTERNSHIP (WITH CLOUDINARY DELETE)
@csrf_exempt
def delete_internship(request, id):
    if request.method == "DELETE":
        try:
            internship = internships_collection.find_one({"_id": ObjectId(id)})

            # 🧹 delete image from Cloudinary
            if internship and internship.get("public_id"):
                cloudinary.uploader.destroy(internship["public_id"])

            internships_collection.delete_one({"_id": ObjectId(id)})

            return JsonResponse({"message": "Internship deleted successfully"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ✅ UPDATE INTERNSHIP
@csrf_exempt
def update_internship(request, id):
    if request.method == "PUT":
        try:
            data = json.loads(request.body)

            mentor_names = data.get("mentorNames", [])

            mentors = []

            if mentor_names:
                mentors_cursor = mentors_collection.find({
                    "name": {"$in": mentor_names}
                })

                for mentor in mentors_cursor:
                    mentors.append({
                        "name": mentor.get("name"),
                        "expertise": mentor.get("expertise"),
                    })

            # ✅ replace mentorNames with mentors
            data["mentors"] = mentors
            data.pop("mentorNames", None)

            internships_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": data}
            )

            return JsonResponse({"message": "Internship updated successfully"})

        except Exception as e:
            print("UPDATE ERROR:", str(e))
            return JsonResponse({"error": str(e)}, status=500)


def get_internship(request, id):
    if request.method == "GET":
        try:
            internship = internships_collection.find_one({"_id": ObjectId(id)})

            if not internship:
                return JsonResponse({"error": "Not found"}, status=404)

            internship["_id"] = str(internship["_id"])

            return JsonResponse(internship)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
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