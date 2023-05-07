from .models import Medicine, PrescriptionAddress, Prescription, PrescriptionMedicine, ATM, PrescriptionFulfillment, ATMMedicine
from django.contrib import admin

admin.site.register(Medicine)
admin.site.register(Prescription)
admin.site.register(PrescriptionMedicine)
admin.site.register(PrescriptionAddress)
admin.site.register(ATM)
admin.site.register(ATMMedicine)


class PrescriptionFulfillmentAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'atm', 'total_price', 'fulfilled_at')


admin.site.register(PrescriptionFulfillment, PrescriptionFulfillmentAdmin)

