from django.contrib import admin
from .models import UserProfile, Patient

admin.site.register(UserProfile)
admin.site.register(Patient)

