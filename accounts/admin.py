from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Message

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'is_email_verified', 'is_phone_verified', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Verification', {'fields': ('is_email_verified', 'is_phone_verified', 'phone_number', 'otp', 'otp_created_at')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Message)
