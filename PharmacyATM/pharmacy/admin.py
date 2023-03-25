from .models import Medicine, Prescription, PrescriptionMedicine, ATM, ATMMedicine
from django.contrib import admin

admin.site.register(Medicine)
admin.site.register(Prescription)
admin.site.register(PrescriptionMedicine)
admin.site.register(ATM)
admin.site.register(ATMMedicine)

