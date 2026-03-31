from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import cloudinary.uploader

from apps.db.mongo.collections import mentors_collection
from bson.objectid import ObjectId


# ✅ CREATE MENTOR (FORM-DATA)
@csrf_exempt
def create_mentor(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            email = request.POST.get("email")
            expertise = request.POST.get("expertise")
            bio = request.POST.get("bio")
            experience = request.POST.get("experience")
            rating = request.POST.get("rating")
            total_students = request.POST.get("totalStudents")
            status = request.POST.get("status", "Active")

            # 🔒 Validation
            if not name or not email:
                return JsonResponse(
                    {"error": "Name and Email are required"},
                    status=400
                )

            file = request.FILES.get("image")

            image_url = None
            public_id = None

            # 📤 Upload image
            if file:
                result = cloudinary.uploader.upload(file)
                image_url = result["secure_url"]
                public_id = result["public_id"]

            mentor = {
                "name": name,
                "email": email,
                "expertise": expertise,
                "bio": bio,
                "experience": experience,
                "rating": int(rating) if rating else 0,
                "totalStudents": int(total_students) if total_students else 0,
                "status": status,
                "imageUrl": image_url,
                "public_id": public_id,
            }

            result = mentors_collection.insert_one(mentor)

            return JsonResponse({
                "message": "Mentor created successfully",
                "id": str(result.inserted_id),
                "imageUrl": image_url
            })

        except Exception as e:
            print("CREATE ERROR:", str(e))
            return JsonResponse({"error": str(e)}, status=500)


# ✅ LIST MENTORS
def list_mentors(request):
    if request.method == "GET":
        try:
            mentors = list(mentors_collection.find())

            for m in mentors:
                m["_id"] = str(m["_id"])

            return JsonResponse(mentors, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ✅ GET SINGLE MENTOR (EDIT PAGE)
def get_mentor(request, id):
    if request.method == "GET":
        try:
            mentor = mentors_collection.find_one({"_id": ObjectId(id)})

            if not mentor:
                return JsonResponse({"error": "Not found"}, status=404)

            mentor["_id"] = str(mentor["_id"])

            return JsonResponse(mentor)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ✅ UPDATE MENTOR
@csrf_exempt
def update_mentor(request, id):
    if request.method == "PUT":
        try:
            if not ObjectId.is_valid(id):
                return JsonResponse({"error": "Invalid ID"}, status=400)

            # ✅ Get data from FormData
            data = request.POST.dict()

            # Convert numbers properly
            if "rating" in data:
                data["rating"] = float(data["rating"])
            if "totalStudents" in data:
                data["totalStudents"] = int(data["totalStudents"])

            # ❌ prevent _id update
            data.pop("_id", None)

            # 📸 Handle image
            if request.FILES.get("image"):
                image = request.FILES["image"]
                data["image"] = image.name  # or save path if needed

            result = mentors_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": data}
            )

            if result.matched_count == 0:
                return JsonResponse({"error": "Mentor not found"}, status=404)

            return JsonResponse({"message": "Mentor updated successfully"})

        except Exception as e:
            print("ERROR:", str(e))
            return JsonResponse({"error": str(e)}, status=500)


# ✅ DELETE MENTOR (WITH CLOUDINARY CLEANUP)
@csrf_exempt
def delete_mentor(request, id):
    if request.method == "DELETE":
        try:
            mentor = mentors_collection.find_one({"_id": ObjectId(id)})

            if not mentor:
                return JsonResponse({"error": "Not found"}, status=404)

            # 🧹 delete image from cloudinary
            if mentor.get("public_id"):
                cloudinary.uploader.destroy(mentor["public_id"])

            mentors_collection.delete_one({"_id": ObjectId(id)})

            return JsonResponse({"message": "Mentor deleted"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)