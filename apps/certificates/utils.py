def generate_certificate(student, course):
    import qrcode, io, uuid
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from django.core.files.base import ContentFile
    from apps.certificates.models import Certificate

    cert = Certificate.objects.create(student=student, course=course, verification_code=uuid.uuid4())
    qr_url = f"https://lms.uz/verify/{cert.verification_code}/"
    qr_img = qrcode.make(qr_url)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, 'PNG')
    cert.qr_code.save(f'qr_{cert.id}.png', ContentFile(qr_buffer.getvalue()))

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))
    w, h = landscape(A4)
    c.setFillColorRGB(0.11, 0.62, 0.46)
    c.rect(0, 0, w, h, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont('Helvetica-Bold', 48)
    c.drawCentredString(w/2, h-150, 'SERTIFIKAT')
    c.setFont('Helvetica', 24)
    c.drawCentredString(w/2, h-220, f'{student.get_full_name()} muvaffaqiyatli tugatdi:')
    c.setFont('Helvetica-Bold', 30)
    c.drawCentredString(w/2, h-280, course.title)
    c.drawInlineImage(cert.qr_code.path, w-140, 40, 100, 100)
    c.setFont('Helvetica', 10)
    c.drawString(40, 40, f'Tasdiqlash kodi: {cert.verification_code}')
    c.save()
    cert.pdf_file.save(f'cert_{cert.id}.pdf', ContentFile(pdf_buffer.getvalue()))
    cert.save()
    return cert
