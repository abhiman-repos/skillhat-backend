from django.urls import path
from .views import (
    create_course,
    list_courses,
    get_course,
    update_course,
    delete_course,
    enroll_course
)

urlpatterns = [
    path('add/', create_course),                     # POST: Naya course banane ke liye
    path('list/', list_courses),                     # GET: Saare courses ki list (Next.js frontend ke liye)
    path('<str:id>/', get_course),                   # GET: Ek specific course ki detail
    path('update/<str:id>/', update_course),         # PUT/POST: Course ko edit karne ke liye
    path('delete/<str:id>/', delete_course),         # DELETE: Course udane ke liye
    path('enroll/', enroll_course),                  # POST: Course me student enroll karne ke liye
]