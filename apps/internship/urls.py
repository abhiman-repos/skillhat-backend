from django.urls import path
from .views import (
    create_internship,
    list_internships,
    upload_internship_image,
    delete_internship,
    update_internship,
    get_internship,
    internship,
    enroll_internship,
    all_enrollments,
    remove_enrollment,
    send_certificate
    
)

urlpatterns = [
    path('internship/', create_internship),
    path('internship/images/', upload_internship_image),
    path('internships/list/', list_internships),
    path('delete_internship/<str:id>/', delete_internship),
    path('update_internship/<str:id>/', update_internship),
    path('edit/<str:id>/', get_internship),
    path('internship/<str:id>/', internship),
    path("enroll/", enroll_internship),
    path("remove-enrollment/<str:enrollment_id>/", remove_enrollment),
    path("enrollments/", all_enrollments),
    path("send-certificate/", send_certificate)

    
]