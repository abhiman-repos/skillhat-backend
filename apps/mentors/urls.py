from django.urls import path
from .views import create_mentor, list_mentors

urlpatterns = [
    path("create/", create_mentor),
    path("all/", list_mentors),
]