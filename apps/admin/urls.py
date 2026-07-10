from django.urls import path
from .views import verify_otp, send_otp,  add_admin, delete_admin, list_admins, admin_certificates, delete_certificate
from .advertisements.views import create_ad , list_ads ,delete_ad, update_ad, patch_ad, get_ad, active_ads
urlpatterns = [
    path('admins/', list_admins, name='list_admins'),
    path('add-admin/', add_admin, name='add_admin'),           # or change to consistent /auth/add-admin
    path('delete-admin/<str:admin_id>', delete_admin, name='delete_admin'),
    path('send-otp/', send_otp, name='send_otp'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path("certificates/", admin_certificates),
    path("certificates/delete/<str:certificate_id>/", delete_certificate),
    path("ads/active/", active_ads),
    path("ads/", create_ad),
    path("ads/<str:ad_id>/", update_ad),
    path("ads/list/", list_ads),
    path("ads/<str:ad_id>/", delete_ad),
    path("ads/patch/", patch_ad),
    path("ads/get/", get_ad),
]
