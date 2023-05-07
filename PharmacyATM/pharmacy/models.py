from django.contrib.auth.models import User
from django.db import models
from users.models import UserProfile
from django.utils.translation import gettext_lazy as _

class ATM(models.Model):
    city = models.CharField(max_length=100)
    county = models.CharField(max_length=100)
    owner_email = models.EmailField()
    medicines = models.ManyToManyField('Medicine', through='ATMMedicine')
    total_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    class Meta:
        unique_together = ('city', 'county')
    def __str__(self):
        return f"{self.city} {self.county} ATM"

class Medicine(models.Model):
    name = models.CharField(max_length=100)
    manufacturer = models.CharField(max_length=100, blank=True, default='')
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ATMMedicine(models.Model):
    atm = models.ForeignKey(ATM, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    stock_level = models.IntegerField(default=0)
    threshold_stock_level = models.IntegerField(default=10)

    def __str__(self):
        return f"{self.atm} - {self.medicine}"




class Prescription(models.Model):
    STATUS_CHOICES = (
        ('active', 'active'),
        ('dispensed', 'dispensed'),
        ('cancelled', 'cancelled'),
    )
    patient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    medicines = models.ManyToManyField(Medicine, through='PrescriptionMedicine')
    date_prescribed = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Prescription #{self.pk} - {self.patient.user.username} ({self.date_prescribed})"

class PrescriptionMedicine(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    dosage_instructions = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

class PrescriptionFulfillment(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    atm = models.ForeignKey(ATM, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    fulfilled_at = models.DateTimeField(auto_now_add=True)

class PrescriptionAddress(models.Model):
    prescription = models.OneToOneField(Prescription, on_delete=models.CASCADE, related_name='address')
    city = models.CharField(_('City'), max_length=255)
    county = models.CharField(_('County'), max_length=255)
    address_text = models.TextField(_('Address Text'))

    class Meta:
        verbose_name = _('Prescription Address')
        verbose_name_plural = _('Prescription Addresses')

    def __str__(self):
        return f'{self.city}, {self.county}, {self.address_text}'