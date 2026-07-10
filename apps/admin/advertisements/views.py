# advertisements/views.py
import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes 
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import json
from rest_framework import status
from bson import ObjectId
from apps.db.mongo.collections import advertisements_collection
import cloudinary.uploader
from apps.internship.views import decode_admin_token
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)


# ─── Admin decorator that wraps your decode_admin_token ─────────────────
import functools

def admin_required_fast(view_func):
    """
    Fast admin check – only decodes the JWT and verifies `role == "admin"`.
    No database queries.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response({"error": "Auth required"}, status=401)
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            if payload.get("role") != "admin":
                return Response({"error": "Admin access required"}, status=403)
            request.user_payload = payload
        except jwt.ExpiredSignatureError:
            return Response({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    @functools.wraps(view_func)          # ← CRITICAL: preserves function metadata
    def wrapper(request, *args, **kwargs):
        admin, error_response = decode_admin_token(request)
        if error_response is not None:
            try:
                error_data = json.loads(error_response.content.decode('utf-8'))
                status_code = error_response.status_code
            except (json.JSONDecodeError, AttributeError):
                error_data = {"error": "Authentication failed"}
                status_code = 401
            return Response(error_data, status=status_code)
        request.admin = admin
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── Public: active ads (no auth required) ────────────────────────────────
@csrf_exempt
@api_view(["GET"])
@permission_classes([AllowAny])
def active_ads(request):
    index = request.query_params.get("index")
    ads = list(advertisements_collection.find({"active": True}).sort("order", 1))
    
    if index is not None:
        try:
            idx = int(index)
            if idx < len(ads):
                ad = ads[idx]
                ad["_id"] = str(ad["_id"])
                return Response(ad)
            else:
                return Response({"error": "No more ads"}, status=404)
        except ValueError:
            return Response({"error": "Invalid index"}, status=400)
    
    # original behaviour: return all
    for ad in ads:
        ad["_id"] = str(ad["_id"])
    return Response(ads)


# ─── Admin: list all ads ─────────────────────────────────────────────────
@csrf_exempt
@admin_required
@api_view(["GET"])
def list_ads(request):
    ads = list(advertisements_collection.find().sort("order", 1))
    for ad in ads:
        ad["_id"] = str(ad["_id"])
    return Response(ads)


# ─── Admin: create ad ───────────────────────────────────────────────────
import traceback

@csrf_exempt
@admin_required
@api_view(["POST"])
def create_ad(request):
    try:
        data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy()

        image_file = request.FILES.get('image_file')
        if not image_file:
            return Response({"error": "Image file is required."}, status=400)

        # Upload to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(image_file, folder="ads/")
            data['image'] = upload_result['secure_url']
        except Exception as e:
            return Response({"error": f"Image upload failed: {str(e)}"}, status=400)

        # ⚠️ REMOVE the raw file object – MongoDB cannot store it
        data.pop("image_file", None)

        # Set defaults
        data.setdefault("height", "")
        data.setdefault("width", "")
        data.setdefault("buttonText", "")
        data.setdefault("buttonLink", "")
        data.setdefault("buttonColor", "#ffffff")
        data.setdefault("buttonBg", "#0f172a")
        data.setdefault("buttonSize", "medium")
        data.setdefault("buttonBorderRadius", "8px")
        data.setdefault("autoCloseSeconds", 0)
        data.setdefault("active", True)
        data.setdefault("order", 1)
        data.setdefault("views", 0)
        data.setdefault("clicks", 0)

        # Now safe to insert
        result = advertisements_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return Response(data, status=201)

    except Exception as e:
        traceback.print_exc()
        return Response(
            {"error": f"Server error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
# ─── Admin: retrieve single ad ───────────────────────────────────────────
@csrf_exempt
@admin_required
@api_view(["GET"])

def get_ad(request, ad_id):
    try:
        ad = advertisements_collection.find_one({"_id": ObjectId(ad_id)})
    except:
        return Response({"error": "Invalid ID"}, status=400)
    if not ad:
        return Response({"error": "Ad not found"}, status=404)
    ad["_id"] = str(ad["_id"])
    return Response(ad)


# ─── Admin: update ad ───────────────────────────────────────────────────
@csrf_exempt
@admin_required
@api_view(["PUT"])

def update_ad(request, ad_id):
    try:
        obj_id = ObjectId(ad_id)
    except:
        return Response({"error": "Invalid ID"}, status=400)

    data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy()
    existing = advertisements_collection.find_one({"_id": obj_id})
    if not existing:
        return Response({"error": "Ad not found"}, status=404)

    image_file = request.FILES.get('image_file')
    if image_file:
        try:
            upload_result = cloudinary.uploader.upload(image_file, folder="ads/")
            data['image'] = upload_result['secure_url']
        except Exception as e:
            return Response({"error": f"Image upload failed: {str(e)}"}, status=400)

    update_fields = {}
    allowed = {
        "image", "height", "width",
        "buttonText", "buttonLink",
        "buttonColor", "buttonBg", "buttonSize", "buttonBorderRadius",
        "autoCloseSeconds",
    }
    for key in allowed:
        if key in data:
            update_fields[key] = data[key]

    if not update_fields:
        return Response({"error": "No valid fields to update"}, status=400)

    advertisements_collection.update_one({"_id": obj_id}, {"$set": update_fields})
    updated = advertisements_collection.find_one({"_id": obj_id})
    updated["_id"] = str(updated["_id"])
    return Response(updated)


# ─── Admin: partial update ──────────────────────────────────────────────
@csrf_exempt
@admin_required
@api_view(["PATCH"])

def patch_ad(request, ad_id):
    try:
        obj_id = ObjectId(ad_id)
    except:
        return Response({"error": "Invalid ID"}, status=400)

    data = request.data
    allowed = {
        "image", "height", "width",
        "buttonText", "buttonLink",
        "buttonColor", "buttonBg", "buttonSize", "buttonBorderRadius",
        "autoCloseSeconds",
        "active",
    }
    update_fields = {k: v for k, v in data.items() if k in allowed}
    if not update_fields:
        return Response({"error": "No valid fields"}, status=400)

    advertisements_collection.update_one({"_id": obj_id}, {"$set": update_fields})
    updated = advertisements_collection.find_one({"_id": obj_id})
    updated["_id"] = str(updated["_id"])
    return Response(updated)


# ─── Admin: delete ad ───────────────────────────────────────────────────
@csrf_exempt
@admin_required
@api_view(["DELETE"])

def delete_ad(request, ad_id):
    try:
        obj_id = ObjectId(ad_id)
    except:
        return Response({"error": "Invalid ID"}, status=400)
    result = advertisements_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        return Response({"error": "Ad not found"}, status=404)
    return Response({"message": "Ad deleted"})


# ─── Public: track view / click (unchanged) ─────────────────────────────
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def track_view(request, ad_id):
    try:
        obj_id = ObjectId(ad_id)
    except:
        return Response({"error": "Invalid ID"}, status=400)
    advertisements_collection.update_one({"_id": obj_id}, {"$inc": {"views": 1}})
    return Response({"status": "ok"})

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def track_click(request, ad_id):
    try:
        obj_id = ObjectId(ad_id)
    except:
        return Response({"error": "Invalid ID"}, status=400)
    advertisements_collection.update_one({"_id": obj_id}, {"$inc": {"clicks": 1}})
    return Response({"status": "ok"})