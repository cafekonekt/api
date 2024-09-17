from django.contrib import admin
from authentication.models import CustomUser, OTP

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone_number', 'role', 'is_active', 'is_staff', 'created_at', 'updated_at')
    search_fields = ('email', 'phone_number', 'role')
    list_filter = ('role', 'is_active', 'is_staff')
    
    fieldsets = (
        (None, {'fields': ('email', 'phone_number', 'role', 'is_active', 'is_staff')}),
    )    
     
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone_number', 'role', 'is_active', 'is_staff', 'password1', 'password2'),       
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(OTP)
