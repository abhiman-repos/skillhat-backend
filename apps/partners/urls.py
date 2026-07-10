from django.urls import path
from .views import (
    partner_register,
    partner_login,
    get_partner_by_id,
    get_partner_requests,
    partner_detail,
    partner_update_status,
    partner_delete
)

urlpatterns = [
    path("login/", partner_login),
    path("register/", partner_register),
    path('requests/<str:partner_id>/', get_partner_by_id),
    path('requests/', get_partner_requests, name='partner_requests'),
    path('requests/profile/<str:partner_id>/', partner_detail, name='partner_detail'),
    path('requests/<str:partner_id>/status/', partner_update_status, name='partner-status'),
    path('requests/<str:partner_id>/delete/', partner_delete, name='partner-delete'),
]