from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from apps.db.mongo.collections import courses_collection

@csrf_exempt
def create_course(request):
    if request.method == "POST":
        data = json.loads(request.body)

        course = {
            "title": data.get("title"),
            "description": data.get("description"),
            "price": data.get("price"),
            "mentor_id": data.get("mentor_id")
        }

        result = courses_collection().insert_one(course)

        return JsonResponse({
            "message": "Course created",
            "id": str(result.inserted_id)
        })


def list_courses(request):
    courses = list(courses_collection().find())

    for c in courses:
        c["_id"] = str(c["_id"])

    return JsonResponse(courses, safe=False)