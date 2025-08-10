from django.contrib import admin
from .models import (User,)


class SettingAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'title', 'time_create', 'is_published')

admin.site.register([User,])