from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Task)
@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified', 'expires_at', 'is_expired')
    list_filter = ('is_verified',)
