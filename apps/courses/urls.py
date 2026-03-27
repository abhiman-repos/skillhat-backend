from django.urls import path
from .views import create_course, list_courses

urlpatterns = [
    path("create/", create_course),
    path("all/", list_courses),
]