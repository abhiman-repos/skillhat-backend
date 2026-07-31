import json
import datetime
from bson.objectid import ObjectId
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from apps.db.mongo.collections import courses_collection, course_enrollments_collection
# ================= 1. CREATE COURSE =================
@csrf_exempt
@require_http_methods(["POST"])
def create_course(request):
    try:
        data = json.loads(request.body)
        
        if not data.get("title") or not data.get("price"):
            return JsonResponse({"error": "Title and Price are required"}, status=400)
            
        course_data = {
            "title": data.get("title"),
            "description": data.get("description", ""),
            "instructor": data.get("instructor", "Admin"),
            "price": data.get("price"),
            "duration": data.get("duration", ""),
            "category": data.get("category", "General"),
            "image_url": data.get("image_url", ""),
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
        
        result = courses_collection.insert_one(course_data)
        return JsonResponse({"message": "Course created successfully", "id": str(result.inserted_id)}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ================= 2. LIST ALL COURSES =================
@require_http_methods(["GET"])
def list_courses(request):
    try:
        courses = list(courses_collection.find().sort("created_at", -1))
        for course in courses:
            course["_id"] = str(course["_id"])
            if "created_at" in course and isinstance(course["created_at"], datetime.datetime):
                course["created_at"] = course["created_at"].isoformat()
        return JsonResponse(courses, safe=False, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ================= 3. GET SINGLE COURSE DETAIL =================
@require_http_methods(["GET"])
def get_course(request, id):
    try:
        if not ObjectId.is_valid(id):
            return JsonResponse({"error": "Invalid Course ID"}, status=400)
            
        course = courses_collection.find_one({"_id": ObjectId(id)})
        if not course:
            return JsonResponse({"error": "Course not found"}, status=404)
            
        course["_id"] = str(course["_id"])
        if "created_at" in course and isinstance(course["created_at"], datetime.datetime):
            course["created_at"] = course["created_at"].isoformat()
            
        return JsonResponse(course, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ================= 4. UPDATE COURSE =================
@csrf_exempt
@require_http_methods(["PUT", "POST"])
def update_course(request, id):
    try:
        if not ObjectId.is_valid(id):
            return JsonResponse({"error": "Invalid Course ID"}, status=400)
            
        data = json.loads(request.body)
        if "_id" in data:
            del data["_id"] # ID ko update nahi kar sakte
            
        data["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        
        result = courses_collection.update_one({"_id": ObjectId(id)}, {"$set": data})
        if result.matched_count == 0:
            return JsonResponse({"error": "Course not found"}, status=404)
            
        return JsonResponse({"message": "Course updated successfully"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ================= 5. DELETE COURSE =================
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_course(request, id):
    try:
        if not ObjectId.is_valid(id):
            return JsonResponse({"error": "Invalid Course ID"}, status=400)
            
        result = courses_collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count == 0:
            return JsonResponse({"error": "Course not found"}, status=404)
            
        return JsonResponse({"message": "Course deleted successfully"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ================= 6. COURSE ENROLLMENT =================
@csrf_exempt
@require_http_methods(["POST"])
def enroll_course(request):
    try:
        data = json.loads(request.body)
        user_email = data.get("user_email")
        course_id = data.get("course_id")
        
        if not user_email or not course_id:
            return JsonResponse({"error": "Email and Course ID required"}, status=400)
            
        # Prevent duplicate enrollment
        if course_enrollments_collection.find_one({"user_email": user_email, "course_id": course_id}):
            return JsonResponse({"error": "User already enrolled in this course"}, status=400)
            
        enrollment_data = {
            "user_email": user_email,
            "course_id": course_id,
            "enrolled_at": datetime.datetime.now(datetime.timezone.utc),
            "status": "active"
        }
        
        course_enrollments_collection.insert_one(enrollment_data)
        return JsonResponse({"message": "Enrolled in course successfully"}, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)