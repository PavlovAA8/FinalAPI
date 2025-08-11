from django.contrib import admin
from .models import (User,
                     Coords,
                     Level,
                     Image,
                     ActivityType,
                     PerevalAdded,
                     PerevalImage)

admin.site.register([User,
                     Coords,
                     Level,
                     Image,
                     ActivityType,
                     PerevalAdded,
                     PerevalImage])