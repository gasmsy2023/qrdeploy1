import io
import csv
import qrcode
import zipfile
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.db import transaction, IntegrityError
from django.contrib import messages
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import default_storage
from certifications.models import Student, QRCodeCustomization, Issuer, CertificateTemplate, CSVUpload, SampleCSV
from certifications.forms import CertificateTemplateForm, IssuerForm, StudentForm, CSVUploadForm
from PIL import Image

def home(request):
    return render(request, 'home.html')

def index(request):
    students_list = Student.objects.all().order_by('-id')  # Order by most recently added
    paginator = Paginator(students_list, 10)  # Show 10 students per page

    page = request.GET.get('page')
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        students = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        students = paginator.page(paginator.num_pages)

    return render(request, 'index.html', {'students': students})

def verify(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    context = {'student': student}
    return render(request, 'student_verification.html', context)

def student_qr_info(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    context = {
        'student': student,
    }
    return render(request, 'student_qr_info.html', context)

def generate_qr_code(student_id, customization):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(f"{settings.BASE_URL}/certificate/student-qr-info/{student_id}/")
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color=customization.foreground_color, back_color=customization.background_color)

    if customization.logo:
        logo = Image.open(customization.logo.path)
        logo_size = (qr_img.size[0] // 4, qr_img.size[1] // 4)
        logo = logo.resize(logo_size, Image.LANCZOS)
        pos = ((qr_img.size[0] - logo.size[0]) // 2, (qr_img.size[1] - logo.size[1]) // 2)
        qr_img.paste(logo, pos, logo)

    return qr_img

def generate_qr_codes(request):
    students = Student.objects.all()
    qr_customization = QRCodeCustomization.objects.first()
    if not qr_customization:
        qr_customization = QRCodeCustomization.objects.create()

    for student in students:
        qr_img = generate_qr_code(student.id, qr_customization)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        # Save QR code image to media storage
        qr_code_path = f'qr_codes/student_{student.id}.png'
        default_storage.save(qr_code_path, ContentFile(qr_buffer.getvalue()))
        
        # Store QR code link in the database with fully qualified domain
        qr_code_url = f"{settings.BASE_URL}{settings.MEDIA_URL}{qr_code_path}"
        student.qr_code_link = qr_code_url
        student.save()

    messages.success(request, f'Generated QR codes for {len(students)} students.')
    return redirect('certifications:index')

def download_qr_codes(request):
    students = Student.objects.all()
    
    # Create a CSV file with student data and QR code links
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(['Student Name', 'Student ID', 'Program', 'Degree Obtained', 'Issuer', 'Issue Date', 'QR Code Link'])
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for student in students:
            # Write student data to CSV
            csv_writer.writerow([
                student.student_name,
                student.student_id,
                student.programm,
                student.degree_obtained,
                student.issuer.name_en,
                student.issue_date,
                student.qr_code_link
            ])
            
            # Add QR code image to zip file
            qr_code_path = f'qr_codes/student_{student.id}.png'
            if default_storage.exists(qr_code_path):
                with default_storage.open(qr_code_path, 'rb') as qr_file:
                    zip_file.writestr(f'qr_codes/student_{student.id}.png', qr_file.read())
        
        # Add CSV file to zip
        zip_file.writestr('student_data.csv', csv_buffer.getvalue())
    
    zip_buffer.seek(0)
    response = FileResponse(zip_buffer, as_attachment=True, filename='student_qr_codes_and_data.zip')
    return response


def upload_csv(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            csv_upload = CSVUpload.objects.create(file=csv_file)
            
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            success_count = 0
            error_count = 0
            error_messages = []

            try:
                with transaction.atomic():
                    for row in reader:
                        try:
                            issuer = Issuer.objects.get(name_en=row['issuer_name_en'])
                            student = Student(
                                student_name=row['student_name'],
                                student_id=row['student_id'],
                                programm=row['programm'],
                                degree_obtained=row['degree_obtained'],
                                issuer=issuer,
                                issue_date=row['issue_date'],
                            )
                            student.save()
                            success_count += 1
                        except Issuer.DoesNotExist:
                            error_count += 1
                            error_messages.append(f"Issuer '{row['issuer_name_en']}' does not exist for student {row['student_name']}")
                        except IntegrityError:
                            error_count += 1
                            error_messages.append(f"Duplicate record or QR code link for student {row['student_name']}")
                        except KeyError as e:
                            error_count += 1
                            error_messages.append(f"Missing column {str(e)} for student {row['student_name']}")
                        except Exception as e:
                            error_count += 1
                            error_messages.append(f"Error creating student record for {row['student_name']}: {str(e)}")

            except Exception as e:
                messages.error(request, f"An error occurred while processing the CSV file: {str(e)}")
                return redirect('certifications:index')

            if success_count > 0:
                messages.success(request, f'Successfully created {success_count} student records.')
            if error_count > 0:
                messages.warning(request, f'Failed to create {error_count} student records. Check the error log for details.')
                for error in error_messages:
                    messages.error(request, error)

            return redirect('certifications:index')
    else:
        form = CSVUploadForm()

    return render(request, 'upload_csv.html', {'form': form})


def download_sample_csv(request):
    sample_csv = SampleCSV.objects.first()
    if not sample_csv:
        # Create a sample CSV if it doesn't exist
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['student_name', 'student_id', 'programm', 'degree_obtained', 'issuer_name_en', 'issue_date'])
        writer.writerow(['John Doe', '12345', 'Computer Science', 'Bachelor of Science', 'Example University', '2023-05-15'])
        writer.writerow(['Jane Smith', '67890', 'Data Science', 'Master of Science', 'Example Institute', '2023-05-16'])
        
        content = ContentFile(buffer.getvalue().encode('utf-8'), name='sample_students.csv')
        sample_csv = SampleCSV.objects.create(file=content)

    response = HttpResponse(sample_csv.file, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_students.csv"'
    return response

def manage_templates(request):
    templates = CertificateTemplate.objects.all()
    return render(request, 'manage_templates.html', {'templates': templates})

def create_template(request):
    if request.method == 'POST':
        form = CertificateTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certificate template created successfully.')
            return redirect('certifications:manage_templates')
    else:
        form = CertificateTemplateForm()
    return render(request, 'template_form.html', {'form': form, 'action': 'Create'})

def edit_template(request, template_id):
    template = get_object_or_404(CertificateTemplate, id=template_id)
    if request.method == 'POST':
        form = CertificateTemplateForm(request.POST, request.FILES, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certificate template updated successfully.')
            return redirect('certifications:manage_templates')
    else:
        form = CertificateTemplateForm(instance=template)
    return render(request, 'template_form.html', {'form': form, 'action': 'Edit'})

def delete_template(request, template_id):
    template = get_object_or_404(CertificateTemplate, id=template_id)
    template.delete()
    messages.success(request, 'Certificate template deleted successfully.')
    return redirect('certifications:manage_templates')

def create_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            try:
                student = form.save(commit=False)
                student.save()
                messages.success(request, f'Student record created for {student.student_name}')
                return redirect('certifications:index')
            except IntegrityError:
                messages.error(request, 'Error: This student record already exists or has a duplicate QR code link.')
    else:
        form = StudentForm()
    return render(request, 'student_form.html', {'form': form, 'action': 'Create'})

def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'Student record updated for {student.student_name}')
                return redirect('certifications:index')
            except IntegrityError:
                messages.error(request, 'Error: This update would result in a duplicate record or QR code link.')
    else:
        form = StudentForm(instance=student)
    return render(request, 'student_form.html', {'form': form, 'action': 'Edit'})

def create_issuer(request):
    if request.method == 'POST':
        form = IssuerForm(request.POST, request.FILES)
        if form.is_valid():
            issuer = form.save()
            messages.success(request, f'Issuer {issuer.name_en} created successfully.')
            return redirect('certifications:index')
    else:
        form = IssuerForm()
    return render(request, 'issuer_form.html', {'form': form, 'action': 'Create'})

def edit_issuer(request, issuer_id):
    issuer = get_object_or_404(Issuer, id=issuer_id)
    if request.method == 'POST':
        form = IssuerForm(request.POST, request.FILES, instance=issuer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Issuer {issuer.name_en} updated successfully.')
            return redirect('certifications:index')
    else:
        form = IssuerForm(instance=issuer)
    return render(request, 'issuer_form.html', {'form': form, 'action': 'Edit'})

def list_issuers(request):
    issuers = Issuer.objects.all()
    return render(request, 'issuer_list.html', {'issuers': issuers})

def verify_issuer(request, uuid):
    issuer = get_object_or_404(Issuer, uuid=uuid)
    students = issuer.student_set.all()
    context = {
        'issuer': issuer,
        'students': students,
    }
    return render(request, 'verify_issuer.html', context)

def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.delete()
        messages.success(request, f'Student record deleted for {student.student_name}')
        return redirect('certifications:index')
    return render(request, 'student_confirm_delete.html', {'student': student})
