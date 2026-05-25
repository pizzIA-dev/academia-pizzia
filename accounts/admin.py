from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Extra", {"fields": ("bio",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Info personal", {"fields": ("first_name", "last_name", "email")}),
    )
