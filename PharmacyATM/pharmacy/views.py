from django.shortcuts import render, redirect, reverse, get_object_or_404
from .forms import PrescriptionForm, PrescriptionMedicineForm, AddMedicineToPrescriptionForm, SelectATMForm, ATMForm, ATMMedicineForm
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
from users.models import UserProfile, Patient
from django.forms import inlineformset_factory
from .models import Prescription, ATM, ATMMedicine, PrescriptionFulfillment, PrescriptionMedicine, PrescriptionAddress
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from pyzbar.pyzbar import decode
from PIL import Image
import io
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
import math
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404
from datetime import datetime, timedelta
from .models import ATM, Prescription, Medicine, ATMMedicine, PrescriptionMedicine
from datetime import timedelta, date
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F


def home(request):
    return render(request, 'pharmacy/home.html')

ATMMedicineFormSet = inlineformset_factory(
    ATM, ATMMedicine,
    fields=('threshold_stock_level',),
    extra=0
)

@login_required
def get_medicine_delivered(request, pk):
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
                    return redirect('get_medicine_delivered', pk=pk)
                if atm_stock.stock_level < quantity:
                    # If the ATM doesn't have enough of the medicine in stock, display an error message and redirect back to the form
                    messages.error(request, f"The ATM '{atm}' doesn't have enough '{medicine}' in stock.")
                    return redirect('get_medicine_delivered', pk=pk)
                # Decrease the stock level of the medicine in the ATM stock by the quantity in the prescription
                atm_stock.stock_level -= quantity
                atm_stock.save()

                # Calculate the cost of the medicine and add it to the total cost of the prescription
                cost = quantity * price
                total_cost += cost

            # Update the cash balance of the ATM with the total cost of the prescription
            atm.total_cash += total_cost
            atm.save()

            # Create a new PrescriptionAddress instance and save it to the database
            address = PrescriptionAddress(
                prescription=prescription,
                city=request.POST.get('city'),
                county=request.POST.get('county'),
                address_text=request.POST.get('address_text')
            )
            address.save()

            # Create a new PrescriptionFulfillment instance and save it to the database
            fulfillment = PrescriptionFulfillment(
                prescription=prescription,
                atm=atm,
                total_price=total_cost,
            )
            fulfillment.save()

            # Change the status of the prescription to 'dispensed'
            prescription.status = 'dispensed'
            prescription.save()

            messages.success(request, f"Your medicines will be sent to your address from the ATM '{atm}'!")
            return redirect('prescription_details', pk=pk)
    else:
        atm_form = SelectATMForm()
        total_price = sum(
            prescription_medicine.medicine.price * prescription_medicine.quantity for prescription_medicine in
            prescription_medicines)
    return render(request, 'pharmacy/get_medicine_delivered.html', {'prescription': prescription, 'atm_form': atm_form, 'total_price': total_price})






def update_thresholds(request, pk):
    atm = get_object_or_404(ATM, pk=pk)
    formset = ATMMedicineFormSet(request.POST, instance=atm)

    if formset.is_valid():
        formset.save()
        messages.success(request, 'Thresholds updated successfully.')
        return redirect('atm_detail', pk=pk)

    context = {
        'atm': atm,
        'formset': formset,
        'medicines': atm.medicines.all()  # include the related medicines in the context
    }
    return render(request, 'pharmacy/update_thresholds.html', context)


@receiver(post_save, sender=ATMMedicine)
def check_stock_level(sender, instance, **kwargs):
    low_stock_medicines = ATMMedicine.objects.filter(atm=instance.atm, stock_level__lt=F('threshold_stock_level'))
    if low_stock_medicines.exists():
        subject = f"Low stock level at {instance.atm.city} {instance.atm.county} ATM"
        message = "Please order more of the following medicines:\n\n"
        for atm_medicine in low_stock_medicines:
            message += f"{atm_medicine.medicine.name} - current stock level is {atm_medicine.stock_level}\n"
        message += f"\n\nFor {instance.atm.city} {instance.atm.county} ATM"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [instance.atm.owner_email]
        send_mail(subject, message, from_email, recipient_list)



def medicine_usages(request, pk):
    # Set the current timezone
    current_timezone = timezone.get_current_timezone()
    # Get the current date
    today = timezone.now().date()
    atm = get_object_or_404(ATM, pk=pk)
    twenty_eight_days_ago = today - timedelta(days=28)
    twenty_eight_days_ago = timezone.make_aware(
        datetime.combine(twenty_eight_days_ago, datetime.min.time()),
        current_timezone
    )
    prescriptions = atm.prescriptionfulfillment_set.filter(atm=atm, fulfilled_at__gte=twenty_eight_days_ago).values_list(
        'prescription__medicines__id', 'prescription__prescriptionmedicine__quantity')

    weekly_usages = {}

    week_dates = []
    for i in range(4):
        start_date = today - timedelta(days=today.weekday(), weeks=i)
        start_date = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time()),
            current_timezone
        )
        end_date = start_date + timedelta(days=6)
        end_date = timezone.make_aware(
            datetime.combine(end_date, datetime.max.time()),
            current_timezone
        )
        week_dates.append((start_date, end_date))

    updated_medicines = set()  # keep track of medicines that have already been updated
    for medicine_id, quantity in prescriptions:
        medicine = Medicine.objects.get(id=medicine_id)

        if medicine in updated_medicines:
            continue  # skip this medicine if it has already been updated

        weekly_usages.setdefault(medicine, [0] * 4)

        prescription_medicines = PrescriptionMedicine.objects.filter(medicine=medicine)


        for i in range(4):
            fulfillments = PrescriptionFulfillment.objects.filter(
                prescription__prescriptionmedicine__in=prescription_medicines,
                fulfilled_at__range=(week_dates[i][0], week_dates[i][1]),
                atm=atm,
            )
            weekly_usages[medicine][i] += sum(
                [f.prescription.prescriptionmedicine_set.get(medicine=medicine).quantity for f in
                 fulfillments])
        updated_medicines.add(medicine)  # add the medicine to the set of updated medicines


     # Moving average forecast
    moving_averages = {}
    for medicine, quantities in weekly_usages.items():
        moving_average = sum(quantities) / 4
        moving_averages[medicine] = moving_average

    # Exponential smoothing forecast
    #alpha = 0.5  # Smoothing parameter
    #forecasted_usages = {}
    #for medicine, usages in weekly_usages.items():
         #    forecasted_usage = usages[0] + alpha * (usages[0] - usages[1])
        #forecasted_usages[medicine] = forecasted_usage
    #moving_averages = forecasted_usages

    # Add current stock levels to the context
    current_stock_levels = {}
    for atm_medicine in atm.atmmedicine_set.all():
        current_stock_levels[atm_medicine.medicine] = atm_medicine.stock_level

    # Determine which medicines need to be ordered
    medicines_to_order = {}
    for medicine, forecast in moving_averages.items():
        stock_level = current_stock_levels.get(medicine, 0)
        if forecast > stock_level:
            medicines_to_order[medicine] = {
                'order_amount':  math.ceil(forecast - stock_level),
                'forecast': forecast,
                'current_stock_level': current_stock_levels.get(medicine, 0),
            }

    context = {
        'atm': atm,
        'weekly_averages': weekly_usages,
        'moving_average_forecasts': moving_averages,
        'medicines_to_order': medicines_to_order,
    }
    return render(request, 'pharmacy/medicine_usages.html', context)



def medicine_sales(request, atm_id):
    atm = get_object_or_404(ATM, id=atm_id)
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        # Convert the date strings to datetime objects
        start_date = timezone.make_aware(
            datetime.combine(datetime.strptime(start_date, '%Y-%m-%d'), datetime.min.time()),
            timezone.get_current_timezone())
        end_date = timezone.make_aware(datetime.combine(datetime.strptime(end_date, '%Y-%m-%d'), datetime.max.time()),
                                       timezone.get_current_timezone())
        sales = PrescriptionFulfillment.objects.filter(atm=atm, fulfilled_at__range=[start_date, end_date])
        # Get a dictionary of medicine names and their total sold quantity
        medicine_sales = {}

        for sale in sales:
            prescription_medicines = PrescriptionMedicine.objects.filter(prescription=sale.prescription)
            for medicine in prescription_medicines:
                if medicine.medicine.name in medicine_sales:
                    medicine_sales[medicine.medicine.name]['quantity'] += medicine.quantity
                    medicine_sales[medicine.medicine.name]['price'] += medicine.quantity * medicine.price
                else:
                    medicine_sales[medicine.medicine.name] = {'quantity': medicine.quantity,
                                                              'price': medicine.quantity * medicine.price}
        return render(request, 'pharmacy/medicine_sales.html', {'sales_data': medicine_sales, 'atm': atm})
    else:
        return render(request, 'pharmacy/medicine_sales.html', {'atm': atm})




def add_medicine_to_atm(request, atm_id):
    atm = get_object_or_404(ATM, id=atm_id)
    if request.method == 'POST':
        form = ATMMedicineForm(request.POST)
        if form.is_valid():
            # Get the medicine details from the form
            medicine = form.cleaned_data['medicine']
            stock_count = form.cleaned_data['stock_level']
            # Check if the medicine already exists in the ATM
            try:
                atm_medicine = ATMMedicine.objects.get(atm=atm, medicine=medicine)
                # Update the stock count
                atm_medicine.stock_level += stock_count
                atm_medicine.save()
            except ATMMedicine.DoesNotExist:
                # Add a new entry for the medicine in the ATM
                atm_medicine = form.save(commit=False)
                atm_medicine.atm = atm
                atm_medicine.save()
            return redirect('atm_detail', pk=atm_id)
    else:
        form = ATMMedicineForm()
    return render(request, 'pharmacy/add_medicine_to_atm.html', {'form': form, 'atm': atm})



def create_atm(request):
    if request.method == 'POST':
        atm_form = ATMForm(request.POST)
        atm_medicine_form = ATMMedicineForm(request.POST)
        if atm_form.is_valid() and atm_medicine_form.is_valid():
            atm = atm_form.save()
            atm_medicine = atm_medicine_form.save(commit=False)
            atm_medicine.atm = atm
            atm_medicine.save()
            return redirect(reverse('atm_list'))
    else:
        atm_form = ATMForm()
        atm_medicine_form = ATMMedicineForm()
    return render(request, 'pharmacy/atm_create.html', {'atm_form': atm_form, 'atm_medicine_form': atm_medicine_form})


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
            return redirect(reverse('prescription_details', args=[prescription_id]))
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
            medicine = form.cleaned_data['medicine']
            prescription_medicine.price = medicine.price
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
            fulfillment = PrescriptionFulfillment(prescription=prescription, atm=atm, total_price=total_cost)
            fulfillment.save()
            # Change the status of the prescription to 'dispensed'
            prescription.status = 'dispensed'
            prescription.save()
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

            # Check if patient profile already exists
            patient_profile = prescription.patient
            try:
                patient = Patient.objects.get(user_profile=patient_profile, doctor=request.user.userprofile)
            except Patient.DoesNotExist:
                # If not, create patient profile for the prescribed person and set the doctor
                patient = Patient.objects.create(user_profile=patient_profile, doctor=request.user.userprofile)

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