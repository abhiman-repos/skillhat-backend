from django.urls import path
from .views import (
    create_internship,
    list_internships,
    upload_internship_image,
    delete_internship,
    update_internship,
    get_internship,
    internship
    
)

urlpatterns = [
    path('internship/', create_internship),
    path('internship/images/', upload_internship_image),
    path('internships/list/', list_internships),
    path('delete_internship/<str:id>/', delete_internship),
    path('update_internship/<str:id>/', update_internship),
    path('edit/<str:id>/', get_internship),
    path('internship/<str:id>/', internship),
    
]