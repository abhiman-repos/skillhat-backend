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
from apps.db.mongo.collections import admin_access_collection
from django.conf import settings

load_dotenv()
RESENT_API_KEY = os.getenv("RESENT_API_KEY")
print("this is resent", RESENT_API_KEY)

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
            "last_login": None,
            "otp": None,                        # OTP field
            "otp_created_at": None              # OTP creation timestamp
        })

        return JsonResponse({"message": "Admin added successfully"}, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def list_admins(request):
    try:
        admins = list(admin_access_collection.find({}, {
            "last_login": 1, 
            "email": 1, 
            "expires_at": 1, 
            "created_at": 1,
            "otp": 1,
            "otp_created_at": 1
        }))

        for admin in admins:
            admin["_id"] = str(admin["_id"])
            # Convert datetime to ISO string for frontend
            if "expires_at" in admin and isinstance(admin["expires_at"], datetime.datetime):
                admin["expires_at"] = admin["expires_at"].isoformat()
            if "created_at" in admin and isinstance(admin["created_at"], datetime.datetime):
                admin["created_at"] = admin["created_at"].isoformat()
            if "last_login" in admin and isinstance(admin["last_login"], datetime.datetime):
                admin["last_login"] = admin["last_login"].isoformat()
            if "otp_created_at" in admin and isinstance(admin["otp_created_at"], datetime.datetime):
                admin["otp_created_at"] = admin["otp_created_at"].isoformat()
            # Remove OTP value from response for security
            if "otp" in admin:
                del admin["otp"]

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

        # Find admin record
        admin_record = admin_access_collection.find_one({"email": email})
        if not admin_record:
            return JsonResponse({"error": "Access denied: Not an authorized admin"}, status=403)

        # Check if admin access has expired
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        expires_at = admin_record.get("expires_at")
        
        if isinstance(expires_at, datetime.datetime) and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)

        if now_utc > expires_at:
            return JsonResponse({"error": "Admin access has expired"}, status=403)

        # Generate OTP - store as string consistently
        otp = str(random.randint(100000, 999999))
        
        # Store OTP and its creation time in the admin document
        result = admin_access_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "otp": otp,  # Store as string
                    "otp_created_at": now_utc
                }
            }
        )
        
        logger.info(f"OTP generated for {email}: {otp}")
        logger.debug(f"Update result: matched={result.matched_count}, modified={result.modified_count}")

        # Send email with OTP
        try:
            # Try to import and use Resend
            try:
                from apps.utils.email import send_otp_email
                send_otp_email(email, otp, expiry_minutes=5)
            except ImportError as ie:
                logger.warning(f"Email module not found: {ie}")
                # Print OTP to console for development
                print(f"\n{'='*50}")
                print(f"🔐 OTP for {email}: {otp}")
                print(f"⏰ Expires in: 5 minutes")
                print(f"{'='*50}\n")
            except Exception as email_error:
                logger.error(f"Failed to send email: {str(email_error)}")
                # Print OTP to console as fallback
                print(f"\n{'='*50}")
                print(f"🔐 OTP for {email}: {otp} (Email failed: {email_error})")
                print(f"{'='*50}\n")
                
        except Exception as email_error:
            logger.error(f"Email error: {str(email_error)}")
            # Still return success since OTP is stored
            # User can check console/logs for OTP

        return JsonResponse({"message": "OTP sent successfully to your email"})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    except ValueError as ve:
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
        
        # Handle OTP - convert to string and remove any whitespace
        otp = str(otp).strip()
        
        # Validate OTP is exactly 6 digits
        if not otp.isdigit() or len(otp) != 6:
            return JsonResponse({"error": "Invalid OTP format"}, status=400)

        # Find admin record with OTP
        admin_record = admin_access_collection.find_one({"email": email})

        if not admin_record:
            return JsonResponse({"error": "Admin not found"}, status=404)

        # Check if OTP exists - handle both string and integer OTPs
        stored_otp = admin_record.get("otp")
        otp_created_at = admin_record.get("otp_created_at")

        if not stored_otp or not otp_created_at:
            return JsonResponse({"error": "No OTP request found"}, status=404)

        # Convert stored OTP to string for comparison (handle int/string)
        stored_otp_str = str(stored_otp).strip()
        
        # Debug logging
        logger.info(f"Verifying OTP for {email}")
        logger.debug(f"Stored OTP: {stored_otp_str}, Received OTP: {otp}")

        # Safe datetime comparison
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # Make otp_created_at timezone-aware if it's naive
        if otp_created_at.tzinfo is None:
            otp_created_at = otp_created_at.replace(tzinfo=datetime.timezone.utc)

        # Check if OTP is older than 5 minutes
        time_diff = (now_utc - otp_created_at).total_seconds()
        if time_diff > 300:
            # Clear expired OTP
            admin_access_collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "otp": None,
                        "otp_created_at": None
                    }
                }
            )
            return JsonResponse({"error": "OTP has expired"}, status=400)

        # Check OTP value - case insensitive comparison
        if stored_otp_str != otp:
            return JsonResponse({"error": "Invalid OTP"}, status=400)

        # JWT Token Generation
        token = jwt.encode(
            {
                "email": email,
                "exp": now_utc + datetime.timedelta(hours=2)
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )

        # Update last_login and clear OTP
        admin_access_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "last_login": now_utc,
                    "otp": None,           # Clear OTP after successful verification
                    "otp_created_at": None
                }
            }
        )

        return JsonResponse({
            "message": "Login successful",
            "token": token
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    except jwt.PyJWTError as jwt_err:
        logger.error(f"JWT Error: {jwt_err}")
        return JsonResponse({"error": "Token generation failed"}, status=500)
    except Exception as e:
        logger.error(f"Verify OTP Error: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)