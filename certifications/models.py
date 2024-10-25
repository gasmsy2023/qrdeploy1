from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
import uuid

class Issuer(models.Model):
    name_en = models.CharField('Issuer Name In English', max_length=100)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    signature = models.ImageField(upload_to='signatures', blank=True)

    def __str__(self):
        return self.name_en

    def get_verify_url(self):
        return settings.BASE_URL + reverse('certifications:verify_issuer', args=[str(self.uuid)])

class CertificateTemplate(models.Model):
    name = models.CharField(max_length=100)
    background_image = models.ImageField(upload_to='certificate_templates', blank=True, null=True)
    font = models.CharField(max_length=50, default='Helvetica')
    title_font_size = models.IntegerField(default=24)
    body_font_size = models.IntegerField(default=18)
    text_color = models.CharField(max_length=7, default='#000000')
    qr_code_position = models.CharField(max_length=20, choices=[
        ('top_left', 'Top Left'),
        ('top_right', 'Top Right'),
        ('bottom_left', 'Bottom Left'),
        ('bottom_right', 'Bottom Right'),
    ], default='bottom_right')

    def __str__(self):
        return self.name

class Student(models.Model):
    student_name = models.CharField('Name of Student', max_length=100)
    student_id = models.IntegerField('Student Identification Number', unique=True)
    programm = models.CharField('Programme studied', max_length=100)
    degree_obtained = models.CharField('Degree Obtained', max_length=100)
    issuer = models.ForeignKey(Issuer, on_delete=models.CASCADE)
    issue_date = models.DateTimeField('Certification Issued Date', blank=True, null=True, auto_now_add=True)
    template = models.ForeignKey(CertificateTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    qr_code_link = models.URLField('QR Code Link', max_length=255, unique=True, blank=True, null=True)

    class Meta:
        unique_together = ['student_name', 'student_id', 'programm', 'degree_obtained', 'issuer']

    def __str__(self):
        return f"{self.student_name} | {self.student_id}"

class QRCodeCustomization(models.Model):
    logo = models.ImageField(upload_to='qr_logos', blank=True, null=True)
    foreground_color = models.CharField(max_length=7, default='#000000')
    background_color = models.CharField(max_length=7, default='#FFFFFF')

    def __str__(self):
        return f"QR Code Customization {self.id}"

class SampleCSV(models.Model):
    file = models.FileField(upload_to='sample_csv/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sample CSV {self.id} - {self.created_at}"

class CSVUpload(models.Model):
    file = models.FileField(upload_to='uploads/csv/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    total_records = models.IntegerField(default=0)
    successful_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)

    def __str__(self):
        return f"CSV Upload {self.id} - {self.uploaded_at}"

    class Meta:
        ordering = ['-uploaded_at']
