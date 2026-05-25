from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Courses
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/moderators/', views.course_moderators, name='course_moderators'),
    path('courses/<int:pk>/requests/', views.enrollment_requests, name='enrollment_requests'),
    path('courses/<int:pk>/requests/<int:req_pk>/<str:action>/', views.enrollment_review, name='enrollment_review'),

    # Enrollment via shareable link
    path('unirse/<str:code>/', views.course_enroll, name='course_enroll'),

    # Sessions
    path('courses/<int:course_pk>/sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),

    # Materials
    path('sessions/<int:session_pk>/materials/upload/', views.material_upload, name='material_upload'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),

    # Activities
    path('sessions/<int:session_pk>/activities/create/', views.activity_create, name='activity_create'),
    path('activities/<int:pk>/', views.activity_detail, name='activity_detail'),

    # Submissions
    path('activities/<int:activity_pk>/submissions/', views.submissions_list, name='submissions_list'),
    path('submissions/<int:pk>/grade/', views.grade_submission, name='grade_submission'),
]
