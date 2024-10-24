# Generated by Django 5.1.2 on 2024-10-21 21:57

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "certifications",
            "0005_csvupload_samplecsv_remove_profile_certificates_and_more",
        ),
    ]

    operations = [
        migrations.RemoveField(
            model_name="issuer",
            name="url",
        ),
        migrations.RemoveField(
            model_name="student",
            name="qr_code",
        ),
        migrations.RemoveField(
            model_name="student",
            name="verification_status",
        ),
        migrations.AddField(
            model_name="certificatetemplate",
            name="body_font_size",
            field=models.IntegerField(default=18),
        ),
        migrations.AddField(
            model_name="certificatetemplate",
            name="font",
            field=models.CharField(default="Helvetica", max_length=50),
        ),
        migrations.AddField(
            model_name="certificatetemplate",
            name="text_color",
            field=models.CharField(default="#000000", max_length=7),
        ),
        migrations.AddField(
            model_name="certificatetemplate",
            name="title_font_size",
            field=models.IntegerField(default=24),
        ),
        migrations.AddField(
            model_name="csvupload",
            name="processed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="issuer",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="csvupload",
            name="file",
            field=models.FileField(upload_to="csv_uploads/"),
        ),
        migrations.AlterField(
            model_name="samplecsv",
            name="file",
            field=models.FileField(upload_to="sample_csv/"),
        ),
    ]