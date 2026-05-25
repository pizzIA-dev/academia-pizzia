from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Courses
    path('courses/create/', views.course_create_view, name='course_create'),
    path('courses/join/', views.course_join_view, name='course_join'),
    path('courses/<int:pk>/', views.course_detail_view, name='course_detail'),
    path('courses/<int:pk>/moderators/', views.course_moderators_view, name='course_moderators'),

    # Sessions
    path('courses/<int:course_pk>/sessions/create/', views.session_create_view, name='session_create'),
    path('sessions/<int:pk>/', views.session_detail_view, name='session_detail'),
    path('sessions/<int:session_pk>/materials/upload/', views.material_upload_view, name='material_upload'),
    path('materials/<int:pk>/delete/', views.material_delete_view, name='material_delete'),

    # Activities
    path('sessions/<int:session_pk>/activities/create/', views.activity_create_view, name='activity_create'),
    path('activities/<int:pk>/', views.activity_detail_view, name='activity_detail'),
    path('activities/<int:activity_pk>/submissions/', views.submissions_list_view, name='submissions_list'),
    path('submissions/<int:pk>/grade/', views.grade_submission_view, name='grade_submission'),
]
