from django.contrib import admin
from .models import Station, ServiceArea, SystemSetting

admin.site.register(Station)
admin.site.register(ServiceArea)
admin.site.register(SystemSetting)