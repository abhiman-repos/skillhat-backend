from django.urls import path
from .views import verify_otp, send_otp,  add_admin, delete_admin, list_admins

urlpatterns = [
    path('admins/', list_admins, name='list_admins'),
    path('add-admin/', add_admin, name='add_admin'),           # or change to consistent /auth/add-admin
    path('delete-admin/<str:admin_id>', delete_admin, name='delete_admin'),
    path('send-otp/', send_otp, name='send_otp'),
    path('verify-otp/', verify_otp, name='verify_otp'),
]
