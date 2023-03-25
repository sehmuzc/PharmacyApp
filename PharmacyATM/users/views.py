from .forms import UserRegisterForm
from .models import Patient, UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect


# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data.get('role')
            UserProfile.objects.create(user=user, role=role)
            messages.success(request, f'Your account has been created, now you can login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def doctor_patients(request):
    doctor_profile = request.user.userprofile
    patients = Patient.objects.filter(doctor=doctor_profile)
    context = {'patients': patients}
    return render(request, 'users/doctor_patients.html', context)