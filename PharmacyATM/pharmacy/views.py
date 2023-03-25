from django.shortcuts import render, redirect, reverse, get_object_or_404
from .forms import PrescriptionForm, PrescriptionMedicineForm, AddMedicineToPrescriptionForm, SelectATMForm
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
from users.models import UserProfile
from .models import Prescription, ATM, ATMMedicine
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from pyzbar.pyzbar import decode
from PIL import Image
import io
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def home(request):
    return render(request, 'pharmacy/home.html')

def atm_list(request):
    atms = ATM.objects.all()
    return render(request, 'pharmacy/atm_list.html', {'atms': atms})

def atm_detail(request, pk):
    atm = get_object_or_404(ATM, pk=pk)
    atm_medicines = ATMMedicine.objects.filter(atm=atm).select_related('medicine')
    context = {
        'atm': atm,
        'atm_medicines': atm_medicines,
    }
    return render(request, 'pharmacy/atm_detail.html', context)


def qr_upload(request):
    if request.method == 'POST':
        # Handle uploaded file
        qr_file = request.FILES.get('qr_file')
        # Read file contents into memory
        file_contents = qr_file.read()
        try:
            # Extract prescription ID from QR code data
            qr_code = Image.open(io.BytesIO(file_contents))
            qr_code_data = decode(qr_code)[0].data.decode('utf-8')
            prescription_id = int(qr_code_data)
            prescription = get_object_or_404(Prescription, pk=prescription_id)
            return redirect(reverse('prescription_transaction', args=[prescription_id]))
        except:
            # If the file is not a valid QR image, display an error message
            error_message = 'The uploaded file is not a valid QR image.'
            return render(request, 'pharmacy/qrupload.html', {'error_message': error_message})
    # If not a POST request, render the upload form
    return render(request, 'pharmacy/qrupload.html')





def add_medicine_to_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    if request.method == 'POST':
        form = AddMedicineToPrescriptionForm(request.POST)
        if form.is_valid():
            prescription_medicine = form.save(commit=False)
            prescription_medicine.prescription = prescription
            prescription_medicine.save()
            return redirect('prescription_details', pk=prescription.pk)
    else:
        form = AddMedicineToPrescriptionForm()
    return render(request, 'pharmacy/add_medicine_to_prescription.html', {'form': form, 'prescription': prescription})

def prescription_details(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    return render(request, 'pharmacy/prescription_details.html', {'prescription': prescription})

def prescription_transaction(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    return render(request, 'pharmacy/prescription_transaction.html', {'prescription': prescription})


def patient_prescriptions(request, pk):
    patient = get_object_or_404(UserProfile, pk=pk)
    prescriptions = patient.prescriptions.all()
    return render(request, 'pharmacy/patient_prescriptions.html', {'patient': patient, 'prescriptions': prescriptions})

@login_required
def my_prescriptions(request):
    patient = request.user.userprofile
    prescriptions = patient.prescriptions.all()
    return render(request, 'pharmacy/my_prescriptions.html', {'patient': patient, 'prescriptions': prescriptions})

@login_required
def get_medicine_from_atm(request, pk):
    prescription = get_object_or_404(Prescription, pk=pk)
    patient = prescription.patient.user
    prescription_medicines = prescription.prescriptionmedicine_set.all()

    if request.method == 'POST':
        atm_form = SelectATMForm(request.POST)
        if atm_form.is_valid():
            atm = atm_form.cleaned_data['atm']
            # Initialize variable to keep track of the total cost of the prescription
            total_cost = 0

            for prescription_medicine in prescription_medicines:
                medicine = prescription_medicine.medicine
                quantity = prescription_medicine.quantity
                price = medicine.price

                try:
                    atm_stock = ATMMedicine.objects.get(atm=atm, medicine=medicine)
                except ATMMedicine.DoesNotExist:
                    # If the ATM doesn't have the medicine in stock, display an error message and redirect back to the form
                    messages.error(request, f"The ATM '{atm}' doesn't have '{medicine}' in stock.")
                    return redirect('get_medicine_from_atm', pk=pk)
                if atm_stock.stock_level < quantity:
                    # If the ATM doesn't have enough of the medicine in stock, display an error message and redirect back to the form
                    messages.error(request, f"The ATM '{atm}' doesn't have enough '{medicine}' in stock.")
                    return redirect('get_medicine_from_atm', pk=pk)
                # Decrease the stock level of the medicine in the ATM stock by the quantity in the prescription
                atm_stock.stock_level -= quantity
                atm_stock.save()

                # Calculate the cost of the medicine and add it to the total cost of the prescription
                cost = quantity * price
                total_cost += cost

            # Update the cash balance of the ATM with the total cost of the prescription
            atm.total_cash += total_cost
            atm.save()

            # create a new PrescriptionFulfillment instance and save it to the database
            messages.success(request, f"You have successfully obtained your medicine from the ATM '{atm}'!")
            return redirect('prescription_details', pk=pk)
    else:
        atm_form = SelectATMForm()
        total_price = sum(
            prescription_medicine.medicine.price * prescription_medicine.quantity for prescription_medicine in
            prescription_medicines)
    return render(request, 'pharmacy/get_medicine_from_atm.html', {'prescription': prescription, 'atm_form': atm_form, 'total_price': total_price})



def give_prescription(request):
    if request.method == 'POST':
        prescription_form = PrescriptionForm(request.POST)
        medicine_form = PrescriptionMedicineForm(request.POST)
        if prescription_form.is_valid() and medicine_form.is_valid():
            prescription = prescription_form.save(commit=False)
            prescription.doctor = request.user.userprofile   # set the doctor field to the logged in user
            prescription.save()
            medicine = medicine_form.save(commit=False)
            medicine.prescription = prescription
            medicine.save()

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(prescription.id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Save QR code image to media directory
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root:
                fs = FileSystemStorage(media_root)
                filename = f'qr_{prescription.id}.png'
                filepath = os.path.join('qr_codes', filename)
                with fs.open(filepath, 'wb+') as destination:
                    img.save(destination, 'PNG')
            return redirect(reverse('prescription_details', args=[prescription.id]))
    else:
        prescription_form = PrescriptionForm()
        medicine_form = PrescriptionMedicineForm()
    return render(request, 'pharmacy/prescription_form.html', {'prescription_form': prescription_form, 'medicine_form': medicine_form})