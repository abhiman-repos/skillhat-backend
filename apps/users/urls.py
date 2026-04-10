# apps/users/urls.py

from django.urls import path
from . import views


urlpatterns = [
    # ================= AUTH ================= #
    path("register/", views.user_register, name="user_register"),
    path("login/", views.user_login, name="user_login"),
    path("logout/", views.logout_user, name="user_logout"),

    # ================= PROFILE ================= #
    path("profile/", views.get_profile, name="get_profile"),
    path("profile/update/", views.update_profile, name="update_profile"),
    path("profile/delete/", views.delete_user, name="delete_user"),

    # ================= ADDRESS ================= #
    path("address/add/", views.add_address, name="add_address"),
    path("address/", views.get_addresses, name="get_addresses"),
    path("address/delete/<str:address_id>/", views.delete_address, name="delete_address"),

    path("my-enrollments/", views.my_enrollments),
    path("my-certificates/", views.my_certificates),


    # ================= PASSWORD ================= #
   # path("forgot-password/", views.forgot_password, name="forgot_password"),
    #path("reset-password/", views.reset_password, name="reset_password"),
]