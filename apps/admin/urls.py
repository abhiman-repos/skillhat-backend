from django.urls import path
from apps.admin.views import verify_otp, send_otp, add_admin, delete_admin, list_admins, admin_certificates, delete_certificate
from apps.admin.advertisements.views import (
    create_ad,
    list_ads,
    active_ads,
    ad_detail,
    track_view,
    track_click,
)

urlpatterns = [
    path('admins/', list_admins, name='list_admins'),
    path('add-admin/', add_admin, name='add_admin'),           # or change to consistent /auth/add-admin
    path('delete-admin/<str:admin_id>', delete_admin, name='delete_admin'),
    path('send-otp/', send_otp, name='send_otp'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path("certificates/", admin_certificates),
    path("certificates/delete/<str:certificate_id>/", delete_certificate),

    # ── Ads ──────────────────────────────────────────────────────────
    # IMPORTANT: literal paths ("active/", "list/") MUST be registered
    # BEFORE the dynamic "<str:ad_id>/" pattern, or Django will try to
    # match "active"/"list" as an ad_id since it resolves top-to-bottom.
    path("ads/active/", active_ads),          # GET  — public, active ads only
    path("ads/list/", list_ads),              # GET  — admin, all ads
    path("ads/", create_ad),                  # POST — admin, create
    path("ads/<str:ad_id>/", ad_detail),      # GET/PUT/PATCH/DELETE — admin, ONE entry handles all methods
    path("ads/<str:ad_id>/view/", track_view),    # POST — public, increment view count
    path("ads/<str:ad_id>/click/", track_click),  # POST — public, increment click count
]