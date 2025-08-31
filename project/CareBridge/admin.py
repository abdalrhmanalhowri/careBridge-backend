from django.contrib import admin
from .models import *


admin.site.register(Elder)
admin.site.register(Visit)
admin.site.register(Volunteer)
admin.site.register(Medication)
admin.site.register(Analysis)
admin.site.register(Notification)

# Register your models here.
