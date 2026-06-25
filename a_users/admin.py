from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, BlockedUsername, TestModel

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('name', 'image', 'bio', 'website', 'birthday', 'notifications', 'darkmode')}),    
    ) + UserAdmin.fieldsets # type: ignore
    list_display = ('username', 'name', 'email', 'is_staff')
    
    
admin.site.register(BlockedUsername)
admin.site.register(TestModel)