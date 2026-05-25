from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Courses CRUD
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('courses/<int:pk>/moderators/', views.course_moderators, name='course_moderators'),

    # Enrollment
    path('courses/<int:pk>/requests/', views.enrollment_requests, name='enrollment_requests'),
    path('courses/<int:pk>/requests/<int:req_pk>/<str:action>/', views.enrollment_review, name='enrollment_review'),
    path('courses/<int:pk>/students/<int:student_pk>/remove/', views.remove_student, name='remove_student'),
    path('unirse/<str:code>/', views.course_enroll, name='course_enroll'),

    # Sessions CRUD
    path('courses/<int:course_pk>/sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),

    # Materials
    path('sessions/<int:session_pk>/materials/upload/', views.material_upload, name='material_upload'),
    path('materials/<int:pk>/delete/', views.material_delete, name='material_delete'),
    path('materials/<int:pk>/download/', views.download_material, name='material_download'),
    path('materials/<int:pk>/view/', views.view_material, name='material_view'),

    # Activities CRUD
    path('sessions/<int:session_pk>/activities/create/', views.activity_create, name='activity_create'),
    path('activities/<int:pk>/', views.activity_detail, name='activity_detail'),
    path('activities/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('activities/<int:pk>/delete/', views.activity_delete, name='activity_delete'),

    # Submissions & Grading
    path('activities/<int:activity_pk>/submissions/', views.submissions_list, name='submissions_list'),
    path('submissions/<int:pk>/grade/', views.grade_submission, name='grade_submission'),
]
