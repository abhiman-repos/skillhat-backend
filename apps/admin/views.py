import random
import datetime
import json
import os
from dotenv import load_dotenv
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import jwt
from bson.objectid import ObjectId
from apps.db.mongo.collections import otp_collection, admin_access_collection

load_dotenv()
SECRET = os.getenv("JWT_SECRET")
RESENT_API_KEY= os.getenv("RESENT_API_KEY")
print("this is resent",RESENT_API_KEY)

logger = logging.getLogger(__name__)
# ====================== ADMIN MANAGEMENT ======================

@csrf_exempt
@require_http_methods(["POST"])
def add_admin(request):
    try:
        body = json.loads(request.body)
        email = body.get("email")
        expires_at_str = body.get("expires_at")  # ISO string from frontend

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        if not expires_at_str:
            return JsonResponse({"error": "expires_at is required"}, status=400)

        # Parse ISO datetime from frontend (datetime-local)
        try:
            expires_at = datetime.datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return JsonResponse({"error": "Invalid expires_at format. Use ISO datetime"}, status=400)

        if expires_at <= datetime.datetime.now(datetime.timezone.utc):
            return JsonResponse({"error": "Expiry must be in the future"}, status=400)

        # Limit max 3 admins
        if admin_access_collection.count_documents({}) >= 3:
            return JsonResponse({"error": "Maximum 3 admins allowed"}, status=400)

        # Prevent duplicates
        if admin_access_collection.find_one({"email": email.lower().strip()}):
            return JsonResponse({"error": "Admin with this email already exists"}, status=400)

        admin_access_collection.insert_one({
            "email": email.lower().strip(),
            "expires_at": expires_at,           # Stored as UTC datetime
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "last_login": None
        })

        return JsonResponse({"message": "Admin added successfully"}, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def list_admins(request):
    try:
        admins = list(admin_access_collection.find({}, {"last_login": 1, "email": 1, "expires_at": 1, "created_at": 1}))

        for admin in admins:
            admin["_id"] = str(admin["_id"])
            # Convert datetime to ISO string for frontend
            if "expires_at" in admin and isinstance(admin["expires_at"], datetime.datetime):
                admin["expires_at"] = admin["expires_at"].isoformat()
            if "created_at" in admin and isinstance(admin["created_at"], datetime.datetime):
                admin["created_at"] = admin["created_at"].isoformat()
            if "last_login" in admin and isinstance(admin["last_login"], datetime.datetime):
                admin["last_login"] = admin["last_login"].isoformat()

        return JsonResponse(admins, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_admin(request, admin_id):
    try:
        if not ObjectId.is_valid(admin_id):
            return JsonResponse({"error": "Invalid admin ID"}, status=400)

        # Prevent deleting the last admin
        if admin_access_collection.count_documents({}) <= 1:
            return JsonResponse({"error": "At least one admin must remain"}, status=400)

        result = admin_access_collection.delete_one({"_id": ObjectId(admin_id)})

        if result.deleted_count == 0:
            return JsonResponse({"error": "Admin not found"}, status=404)

        return JsonResponse({"message": "Admin access revoked successfully"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ====================== OTP AUTH ======================

@csrf_exempt
@require_http_methods(["POST"])
def send_otp(request):
    try:
        body = json.loads(request.body)
        email = body.get("email")

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        email = email.lower().strip()

        record = admin_access_collection.find_one({"email": email})
        if not record:
            return JsonResponse({"error": "Access denied: Not an authorized admin"}, status=403)

        # Safe expiry check...
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        expires_at = record.get("expires_at")
        if isinstance(expires_at, datetime.datetime) and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

        if now_utc > expires_at:
            return JsonResponse({"error": "Admin access has expired"}, status=403)

        otp = str(random.randint(100000, 999999))

        otp_collection.update_one(
            {"email": email},
            {"$set": {"otp": otp, "created_at": now_utc}},
            upsert=True
        )

        # Send via Resend
        from apps.utils.email import send_otp_email
        send_otp_email(email, otp, expiry_minutes=5)

        return JsonResponse({"message": "OTP sent successfully to your email"})

    except ValueError as ve:   # Catches missing API key
        logger.error(str(ve))
        return JsonResponse({"error": "Email service configuration error"}, status=500)
    except Exception as e:
        logger.error(f"Send OTP Error: {str(e)}")
        return JsonResponse({"error": "Failed to send OTP. Please try again later."}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    try:
        body = json.loads(request.body)
        email = body.get("email")
        otp = body.get("otp")

        if not email or not otp:
            return JsonResponse({"error": "Email and OTP are required"}, status=400)

        email = email.lower().strip()
        otp = str(otp).strip()

        record = otp_collection.find_one({"email": email})

        if not record:
            return JsonResponse({"error": "No OTP request found"}, status=404)

        # ====================== FIXED: Safe datetime comparison ======================
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        created_at = record.get("created_at")

        if not isinstance(created_at, datetime.datetime):
            return JsonResponse({"error": "Invalid OTP record"}, status=500)

        # Make created_at timezone-aware if it's naive (common with PyMongo)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=datetime.timezone.utc)

        # Check if OTP is older than 5 minutes
        if (now_utc - created_at).total_seconds() > 300:
            otp_collection.delete_one({"email": email})
            return JsonResponse({"error": "OTP has expired"}, status=400)

        # Check OTP value
        if record.get("otp") != otp:
            return JsonResponse({"error": "Invalid OTP"}, status=400)

        # ====================== JWT Token Generation ======================
        token = jwt.encode(
            {
                "email": email,
                "exp": now_utc + datetime.timedelta(hours=2)
            },
            SECRET,
            algorithm="HS256"
        )

        # Update last_login with consistent UTC aware datetime
        admin_access_collection.update_one(
            {"email": email},
            {"$set": {"last_login": now_utc}}
        )

        # Clean up used OTP
        otp_collection.delete_one({"email": email})

        return JsonResponse({
            "message": "Login successful",
            "token": token
        })

    except jwt.PyJWTError as jwt_err:
        print(f"JWT Error: {jwt_err}")
        return JsonResponse({"error": "Token generation failed"}, status=500)
    except Exception as e:
        print(f"Verify OTP Error: {str(e)}")  # Better logging
        return JsonResponse({"error": "Internal server error"}, status=500)