from django import forms
from .models import Prescription, Medicine, PrescriptionMedicine, ATM, ATMMedicine


class ATMForm(forms.ModelForm):
    class Meta:
        model = ATM
        fields = ['city', 'county', 'owner_email' , 'total_cash']

class ATMMedicineForm(forms.ModelForm):
    class Meta:
        model = ATMMedicine
        fields = ['medicine', 'stock_level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['medicine'].queryset = Medicine.objects.all()


class PrescriptionForm(forms.ModelForm):

    class Meta:
        model = Prescription
        fields = ['patient']

class PrescriptionMedicineForm(forms.ModelForm):
    class Meta:
        model = PrescriptionMedicine
        fields = ['medicine', 'quantity', 'dosage_instructions']
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.price = instance.medicine.price
        if commit:
            instance.save()
        return instance

class SelectATMForm(forms.Form):
    atm = forms.ModelChoiceField(queryset=ATM.objects.all(), empty_label=None, label='Select an ATM')


class AddMedicineToPrescriptionForm(forms.ModelForm):
    class Meta:
        model = PrescriptionMedicine
        fields = ['medicine', 'quantity', 'dosage_instructions']

class AddMedicineToExistingPrescriptionForm(forms.Form):
    prescription_id = forms.IntegerField()
    medicine = forms.ModelChoiceField(queryset=Medicine.objects.all())
    quantity = forms.IntegerField()

    def clean_prescription_id(self):
        prescription_id = self.cleaned_data.get('prescription_id')
        try:
            prescription = Prescription.objects.get(id=prescription_id)
        except Prescription.DoesNotExist:
            raise forms.ValidationError("Prescription does not exist.")
        return prescription