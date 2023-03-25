from django import forms
from .models import Prescription, Medicine, PrescriptionMedicine, ATM
from users.models import Patient

class PrescriptionForm(forms.ModelForm):

    class Meta:
        model = Prescription
        fields = ['patient']

class PrescriptionMedicineForm(forms.ModelForm):
    class Meta:
        model = PrescriptionMedicine
        fields = ['medicine', 'quantity', 'dosage_instructions']



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