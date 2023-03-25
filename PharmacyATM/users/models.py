from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(choices=[('PharmacyOwner', 'Pharmacy Owner'), ('Patient', 'Patient'), ('Doctor', 'Doctor')], max_length=50)

    class Meta:
        ordering = ['user__first_name', 'user__last_name']  # order by first name and last name of the related User

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Patient(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='patients')

    def __str__(self):
        return self.user_profile.user.get_full_name()