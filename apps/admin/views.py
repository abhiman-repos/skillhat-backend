from django.http import JsonResponse

def home(request):
    if not request.session.get("user_id"):
        return JsonResponse(
            {"error": "Unauthorized"},
            status=401
        )

    return JsonResponse({
        "message": "Welcome to Home Page"
    })
