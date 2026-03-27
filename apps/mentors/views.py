from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from apps.db.mongo.collections import mentors_collection

@csrf_exempt
def create_mentor(request):
    if request.method == "POST":
        data = json.loads(request.body)

        mentor = {
            "name": data.get("name"),
            "email": data.get("email"),
            "expertise": data.get("expertise", []),
            "bio": data.get("bio", "")
        }

        result = mentors_collection().insert_one(mentor)

        return JsonResponse({
            "message": "Mentor created",
            "id": str(result.inserted_id)
        })


def list_mentors(request):
    mentors = list(mentors_collection().find())

    for m in mentors:
        m["_id"] = str(m["_id"])

    return JsonResponse(mentors, safe=False)