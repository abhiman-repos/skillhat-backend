from django.urls import path
from .views import (
    create_mentor,
    list_mentors,
    get_mentor,
    update_mentor,
    delete_mentor,
)

urlpatterns = [
    path("mentor/", create_mentor),
    path("mentors/list/", list_mentors),
    path("get_mentor/<str:id>/", get_mentor),
    path("update_mentor/<str:id>/", update_mentor),
    path("delete_mentor/<str:id>/", delete_mentor),
]