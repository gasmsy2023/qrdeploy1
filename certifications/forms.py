from django import forms
from django.core.exceptions import ValidationError
from .models import CertificateTemplate, Student, Issuer

class CertificateTemplateForm(forms.ModelForm):
    class Meta:
        model = CertificateTemplate
        fields = ['name', 'background_image', 'qr_code_position']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['student_name', 'student_id', 'programm', 'degree_obtained', 'issuer', 'template']
        widgets = {
            'student_name': forms.TextInput(attrs={'class': 'form-control'}),
            'student_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'programm': forms.TextInput(attrs={'class': 'form-control'}),
            'degree_obtained': forms.TextInput(attrs={'class': 'form-control'}),
            'issuer': forms.Select(attrs={'class': 'form-control'}),
            'template': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id')
        if Student.objects.filter(student_id=student_id).exists():
            if self.instance and self.instance.student_id == student_id:
                return student_id
            raise ValidationError("A student with this ID already exists.")
        return student_id

    def clean(self):
        cleaned_data = super().clean()
        student_name = cleaned_data.get('student_name')
        student_id = cleaned_data.get('student_id')
        programm = cleaned_data.get('programm')
        degree_obtained = cleaned_data.get('degree_obtained')
        issuer = cleaned_data.get('issuer')

        if student_name and student_id and programm and degree_obtained and issuer:
            if Student.objects.filter(
                student_name=student_name,
                student_id=student_id,
                programm=programm,
                degree_obtained=degree_obtained,
                issuer=issuer
            ).exists():
                if not (self.instance and self.instance.id):
                    raise ValidationError("A student with these exact details already exists.")
        return cleaned_data

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='Select a CSV file',
        help_text='Max. 5 megabytes',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'})
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if csv_file:
            if csv_file.size > 5 * 1024 * 1024:  # 5 MB limit
                raise forms.ValidationError("File size must be under 5 MB.")
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError("File must be a CSV.")
        return csv_file

class IssuerForm(forms.ModelForm):
    class Meta:
        model = Issuer
        fields = ['name_ar', 'name_en', 'signature']
        widgets = {
            'name_ar': forms.TextInput(attrs={'class': 'form-control'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control'}),
            'signature': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }
