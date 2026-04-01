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
            # ✅ Validate ID
            if not ObjectId.is_valid(id):
                return JsonResponse({"error": "Invalid ID"}, status=400)

            mentor = mentors_collection.find_one({"_id": ObjectId(id)})

            if not mentor:
                return JsonResponse({"error": "Mentor not found"}, status=404)

            # ✅ Convert ObjectId
            mentor["_id"] = str(mentor["_id"])

            return JsonResponse(mentor)

        except Exception as e:
            print("ERROR:", str(e))
            return JsonResponse({"error": str(e)}, status=500)


def get_all_mentors(request):
    if request.method == "GET":
        try:
            mentors = list(mentors_collection.find({}, {
                "name": 1,
                "expertise": 1,
                "image": 1
            }))

            for m in mentors:
                m["_id"] = str(m["_id"])

            return JsonResponse(mentors, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

# ✅ UPDATE MENTOR
@csrf_exempt
def update_mentor(request, id):
    if request.method == "PUT":
        try:
            if not ObjectId.is_valid(id):
                return JsonResponse({"error": "Invalid ID"}, status=400)

            # ✅ Parse JSON body
            body = json.loads(request.body)

            # ❌ prevent _id update
            body.pop("_id", None)

            # ✅ Handle image (base64 or URL expected)
            image_url = body.get("imageUrl")
            public_id = body.get("public_id")

            # OPTIONAL: If sending base64 image
            if body.get("image"):
                upload_result = cloudinary.uploader.upload(body["image"])
                image_url = upload_result["secure_url"]
                public_id = upload_result["public_id"]

                body["imageUrl"] = image_url
                body["public_id"] = public_id

            # ✅ Convert numbers if needed
            if "experience" in body:
                try:
                    body["experience"] = int(body["experience"])
                except:
                    pass

            result = mentors_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": body}
            )

            if result.matched_count == 0:
                return JsonResponse({"error": "Mentor not found"}, status=404)

            return JsonResponse({
                "message": "Mentor updated successfully",
                "imageUrl": image_url
            })

        except Exception as e:
            print("UPDATE ERROR:", str(e))
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
        

def search_mentors(request):
    if request.method == "GET":
        try:
            query = request.GET.get("q", "")

            mentors = list(mentors_collection.find({
                "name": {"$regex": query, "$options": "i"}
            }, {
                "name": 1,
                "expertise": 1,
            }).limit(10))  # 🔥 limit for performance

            for m in mentors:
                m["_id"] = str(m["_id"])

            return JsonResponse(mentors, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)