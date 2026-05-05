

from django.contrib import admin
from .models import UserProfile, UserHealthProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'role', 'plan', 'is_active', 'is_admin', 'date_joined')
    list_filter = ('role', 'plan', 'is_active', 'is_admin')
    search_fields = ('full_name', 'email')
    ordering = ('-date_joined',)

@admin.register(UserHealthProfile)
class UserHealthProfileAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'gender', 'country', 'height_cm', 'weight_kg', 'goal')
    search_fields = ('user_id',)
