from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.contrib.auth.hashers import make_password
from .models import UserProfile, UserHealthProfile
import logging

logger = logging.getLogger(__name__)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        'pk',   
        'user_id_with_name', 'email', 'role', 'plan',
        'is_active', 'is_admin', 'date_joined',
        'reset_password_button',
    )
    list_filter   = ('role', 'plan', 'is_active', 'is_admin', 'nutritionist_type')
    search_fields = ('full_name', 'email')
    ordering      = ('-date_joined',)
    readonly_fields = ('date_joined',)

    # ✅ Duplicate name check — ID sirf tab dikhayega jab same naam ho
    def user_id_with_name(self, obj):
        duplicate_exists = UserProfile.objects.filter(
            full_name=obj.full_name
        ).exclude(pk=obj.pk).exists()

        if duplicate_exists:
            return format_html(
                '<span>{} <span style="color:#888;font-size:11px;">(#{})</span></span>',
                obj.full_name, obj.pk
            )
        return obj.full_name

    user_id_with_name.short_description = 'Full Name'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:user_id>/reset-password/',
                self.admin_site.admin_view(self.reset_password_view),
                name='users_userprofile_reset_password',
            ),
        ]
        return custom + urls

    def reset_password_button(self, obj):
        return format_html(
            '<a href="/admin/users/userprofile/{}/reset-password/" '
            'style="background:#417690;color:white;padding:4px 10px;'
            'border-radius:4px;text-decoration:none;font-size:12px;">'
            '🔑 Reset</a>', obj.pk
        )
    reset_password_button.short_description = 'Reset Password'

    def reset_password_view(self, request, user_id):
        user = get_object_or_404(UserProfile, pk=user_id)
        error_msg = ""

        print(f"[ResetPassword] Request method: {request.method} | User ID: {user_id}")
        logger.debug(f"[ResetPassword] Request method: {request.method} | User ID: {user_id}")

        if request.method == 'POST':
            new_password     = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()

            print(f"[ResetPassword] new_password length: {len(new_password)} | confirm match: {new_password == confirm_password}")

            if not new_password:
                error_msg = "Password cannot be empty."
            elif new_password != confirm_password:
                error_msg = "Passwords do not match."
            elif len(new_password) < 6:
                error_msg = "Password must be at least 6 characters."
            else:
                try:
                    user.password = make_password(new_password)
                    user.save()
                    print(f"[ResetPassword] ✅ Password saved successfully for user: {user.email}")
                    logger.debug(f"[ResetPassword] Password saved for: {user.email}")
                    return HttpResponseRedirect('/admin/users/userprofile/')
                except Exception as e:
                    error_msg = f"Error saving password: {str(e)}"
                    print(f"[ResetPassword] ❌ Save error: {e}")
                    logger.error(f"[ResetPassword] Save error: {e}")
        else:
            print(f"[ResetPassword] GET request — showing form for user: {user.email}")

        context = {
            'user': user,
            'error_msg': error_msg,
        }
        return render(request, 'admin/users/reset_password.html', context)


@admin.register(UserHealthProfile)
class UserHealthProfileAdmin(admin.ModelAdmin):
    list_display  = ('user_id', 'gender', 'country', 'city', 'height_cm', 'weight_kg', 'goal')
    search_fields = ('user_id',)
    list_filter   = ('gender', 'goal', 'diet_type', 'is_diabetic', 'is_hypertensive')
