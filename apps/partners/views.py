import json
import jwt
import datetime
import cloudinary.uploader

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from bson.objectid import ObjectId
from django.views.decorators.http import require_http_methods
from apps.internship.views import decode_admin_token
# Import your MongoDB collection
from apps.db.mongo.collections import partners_collection

@csrf_exempt
def partner_register(request):
    if request.method != 'POST':
        return JsonResponse({"message": "Method not allowed"}, status=405)
        
    data = request.POST

    # === IMPROVED EMAIL HANDLING ===
    email = data.get('email') or data.get('Email')  # Handle possible case mismatch
    email = str(email).strip().lower() if email else ''

    # Debug: Print all keys received (remove in production)
    # print("Received keys:", list(data.keys()))

    if not email:
        return JsonResponse({
            "message": "Email is required",
            "received_keys": list(data.keys())  # Helpful for debugging
        }, status=400)

    # 1. Check if email already exists
    if partners_collection.find_one({"email": email}):
        return JsonResponse({
            "message": "An account with this email already exists."
        }, status=400)

    try:
        # 2. Cloudinary Uploads
        uploaded_urls = {}
        file_fields = ['profilePhoto', 'aadhaarFile', 'panFile', 'resumeFile']
        
        for field in file_fields:
            file_obj = request.FILES.get(field)
            if file_obj:
                upload_result = cloudinary.uploader.upload(
                    file_obj,
                    folder="partner_documents/"
                )
                uploaded_urls[f"{field}Url"] = upload_result.get('secure_url')

        # Improved list handler
        def get_list(key):
            if hasattr(data, 'getlist'):
                return data.getlist(key)
            value = data.get(key)
            return [value] if value else []

        # 3. Partner Document
        partner_document = {
            "fullName": data.get("fullName", "").strip(),
            "email": email,
            "password": make_password(data.get("password")),
            "phone": data.get("phone", "").strip(),
            
            "currentRole": data.get("currentRole"),
            "company": data.get("company"),
            "yearsOfExperience": data.get("yearsOfExperience"),
            "expertise": get_list('expertise'),
            "skills": data.get("skills"),
            "linkedinProfile": data.get("linkedinProfile"),
            "portfolioUrl": data.get("portfolioUrl"),
            "bio": data.get("bio"),
            "achievements": data.get("achievements"),
            
            "offeringType": get_list('offeringType'),
            "teachingStyle": data.get("teachingStyle"),
            "targetAudience": data.get("targetAudience"),
            "priceRange": data.get("priceRange"),
            "weeklyAvailability": data.get("weeklyAvailability"),
            "preferredLanguages": get_list('preferredLanguages'),
            "pastMentoringExp": data.get("pastMentoringExp"),
            
            "aadhaarNumber": data.get("aadhaarNumber"),
            "panNumber": data.get("panNumber"),
            **uploaded_urls,
            
            "status": "pending",
            "agreeToTerms": data.get("agreeToTerms") in ['true', 'True', True, '1', 'on'],
            "agreeToBackground": data.get("agreeToBackground") in ['true', 'True', True, '1', 'on'],
            "createdAt": datetime.datetime.utcnow()
        }

        result = partners_collection.insert_one(partner_document)
        
        return JsonResponse({
            "message": "Registration successful. Your profile is under review.",
            "partner_id": str(result.inserted_id)
        }, status=201)

    except Exception as e:
        return JsonResponse({
            "message": f"An error occurred: {str(e)}"
        }, status=500)

@csrf_exempt
def partner_login(request):
    """
    Handles Mentor/Partner Login. Strictly checks for 'approved' status.
    Expects data as 'application/json'.
    """
    if request.method != 'POST':
        return JsonResponse({"message": "Method not allowed"}, status=405)
        
    try:
        # Parse JSON body for login
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password')
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON data provided."}, status=400)

    # 1. Fetch user from MongoDB
    partner = partners_collection.find_one({"email": email})

    if not partner:
        return JsonResponse({"message": "Invalid email or password."}, status=401)

    # 2. Verify Password
    if not check_password(password, partner['password']):
        return JsonResponse({"message": "Invalid email or password."}, status=401)

    # 3. Check Approval Status
    partner_status = partner.get("status", "pending")
    
    if partner_status == "pending":
        return JsonResponse({
            "message": "Your application is still under review by our admin team."
        }, status=403)
        
    if partner_status == "rejected":
        return JsonResponse({
            "message": "Your application to become a partner was declined."
        }, status=403)

    # 4. Generate JWT Token (if approved)
    token_payload = {
        'user_id': str(partner['_id']),
        'email': partner['email'],
        'role': 'partner',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow()
    }

    token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm='HS256')

    return JsonResponse({
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": str(partner['_id']),
            "fullName": partner['fullName'],
            "email": partner['email'],
            "profilePhotoUrl": partner.get('profilePhotoUrl', '')
        }
    }, status=200)

@csrf_exempt
def get_partner_by_id(request, partner_id):
    """
    Get full details of a partner by ID
    """
    if request.method != 'GET':
        return JsonResponse({"message": "Method not allowed"}, status=405)

    try:
        # Convert to ObjectId safely
        if not partner_id or len(partner_id) != 24:
            return JsonResponse({"message": "Invalid partner ID format"}, status=400)

        obj_id = ObjectId(partner_id)
        
        partner = partners_collection.find_one({"_id": obj_id})

        if not partner:
            return JsonResponse({"message": "Partner not found"}, status=404)

        # Remove sensitive information
        sensitive = ['password', 'aadhaarNumber', 'panNumber', 'aadhaarFileUrl', 'panFileUrl']
        for field in sensitive:
            partner.pop(field, None)

        # Convert ObjectId and datetime for JSON
        partner['_id'] = str(partner['_id'])
        if isinstance(partner.get('createdAt'), datetime.datetime):
            partner['createdAt'] = partner['createdAt'].isoformat()

        return JsonResponse({
            "message": "Partner details fetched successfully",
            "partner": partner
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "message": f"Invalid partner ID or error: {str(e)}"
        }, status=400)
    
@csrf_exempt
def get_partner_requests(request):
    if request.method != 'GET':
        return JsonResponse({"message": "Method not allowed"}, status=405)

    try:
        status_filter = request.GET.get('status')

        query = {}
        if status_filter in ['pending', 'approved', 'rejected']:
            query['status'] = status_filter

        partners = list(partners_collection.find(
            query,
            {
                "_id": 1,
                "fullName": 1,
                "email": 1,
                "currentRole": 1,
                "company": 1,
                "createdAt": 1,
                "status": 1,
                "profilePhotoUrl": 1
            }
        ).sort("createdAt", -1))

        for partner in partners:
            partner['_id'] = str(partner['_id'])
            if isinstance(partner.get('createdAt'), datetime.datetime):
                partner['createdAt'] = partner['createdAt'].isoformat()

        return JsonResponse({
            "message": "Success",
            "requests": partners,
            "total": len(partners)
        })

    except Exception as e:
        return JsonResponse({
            "message": f"Error fetching partner requests: {str(e)}"
        }, status=500)
    
def partner_detail(request, partner_id):
    if request.method != 'GET':
        return JsonResponse({"message": "Method not allowed"}, status=405)
    
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(partner_id)
    except:
        return JsonResponse({"message": "Invalid ID format"}, status=400)
    
    partner = partners_collection.find_one({"_id": obj_id})
    if not partner:
        return JsonResponse({"message": "Partner not found"}, status=404)
    
    # Convert ObjectId to string for JSON serialization
    partner["_id"] = str(partner["_id"])
    
    # Add Cloudinary URLs if they exist (already stored in DB)
    # partner already has profilePhotoUrl, aadhaarFileUrl, etc.
    
    return JsonResponse(partner, safe=False)

@csrf_exempt
@require_http_methods(["PATCH"])
def partner_update_status(request, partner_id):
    admin = decode_admin_token(request)
    if not admin:
        return JsonResponse({"message": "Unauthorized"}, status=401)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        if new_status not in ['approved', 'rejected']:
            return JsonResponse({"message": "Invalid status"}, status=400)
    except:
        return JsonResponse({"message": "Invalid JSON"}, status=400)
    
    try:
        obj_id = ObjectId(partner_id)
    except:
        return JsonResponse({"message": "Invalid ID"}, status=400)
    
    result = partners_collection.update_one(
        {"_id": obj_id},
        {"$set": {"status": new_status}}
    )
    if result.matched_count == 0:
        return JsonResponse({"message": "Partner not found"}, status=404)
    
    return JsonResponse({"message": f"Status updated to {new_status}"})

@csrf_exempt
@require_http_methods(["DELETE"])
def partner_delete(request, partner_id):
    admin = decode_admin_token(request)
    if not admin:
        return JsonResponse({"message": "Unauthorized"}, status=401)
    
    try:
        obj_id = ObjectId(partner_id)
    except:
        return JsonResponse({"message": "Invalid ID"}, status=400)
    
    result = partners_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        return JsonResponse({"message": "Partner not found"}, status=404)
    
    return JsonResponse({"message": "Partner deleted successfully"})