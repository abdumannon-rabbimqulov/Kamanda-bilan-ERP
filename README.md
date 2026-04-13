# Kamanda Bilan ERP - Zamonaviy Ta'lim Markazi Boshqaruv Tizimi

Ushbu loyiha o'quv markazlari va ta'lim muassasalari uchun mo'ljallangan keng qamrovli ERP (Enterprise Resource Planning) va LMS (Learning Management System) tizimidir. Tizim o'quv jarayonlarini avtomatlashtirish, moliya va xodimlar boshqaruvini osonlashtirish uchun ishlab chiqilgan.

## 🚀 Asosiy Imkoniyatlar

- **Ko'p darajali rollar tizimi**: Admin, O'qituvchi, Assistent va Talaba rollari uchun alohida dashboardlar.
- **Kurslar boshqaruvi**: Kurslarni yaratish, guruhlarga bo'lish va dars jadvallarini shakllantirish.
- **Davomat va Vazifalar**: Talabalarning darsga qatnashishi va uy vazifalarini topshirilishini onlayn nazorat qilish.
- **Real-vaqtda Chat**: O'qituvchilar va talabalar o'rtasida muloqot qilish uchun WebSockets (Django Channels) asosidagi messenjer.
- **Sertifikatlar**: QR-kod orqali tasdiqlanadigan avtomatik sertifikat generatsiyasi.
- **Moliya moduli**: Talabalar to'lovlari (Payments) va o'qituvchilar ish haqlarini (Salary) hisoblash tizimi.
- **Imtihonlar**: Onlayn testlar va natijalarni hisoblash moduli.
- **Bildirishnomalar**: Muhim yangiliklar va eslatmalar uchun ichki bildirishnomalar tizimi.
- **Shikoyat va Takliflar**: Markaz sifatini oshirish uchun foydalanuvchilar bilan qayta aloqa.

## 🛠 Texnologiyalar

- **Python & Django**: Loyihaning asosiy asosi (Backend).
- **Django Channels & Redis**: Real-vaqt rejimida ishlash (Chat va Notifications).
- **Daphne**: ASGI server sifatida real-time ulanishlar uchun.
- **PostgreSQL / SQLite**: Ma'lumotlarni ishonchli saqlash.
- **ReportLab**: PDF formatda sertifikatlar va hisobotlar tayyorlash.
- **Pillow & openpyxl**: Media fayllar va Excel eksportlar bilan ishlash.

## 📦 O'rnatish va Ishga tushirish

### 1. Loyihani yuklab olish
```bash
git clone https://github.com/Abbos-Akromov/Kamanda-bilan-ERP.git
cd Kamanda-bilan-ERP
```

### 2. Virtual muhitni sozlash
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows uchun: .venv\Scripts\activate
```

### 3. Kerakli kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. .env faylini sozlash
Loyihaning asosiy papkasida `.env` faylini yarating va email sozlamalarini (OTP kodlari uchun) kiriting:
```env
EMAIL_HOST_USER=example@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### 5. Bazani migratsiya qilish
```bash
python manage.py migrate
```

### 6. Superuser yaratish (Admin panel uchun)
```bash
python manage.py createsuperuser
```

### 7. Loyihani ishga tushirish
```bash
python manage.py runserver
# yoki async rejimi uchun:
daphne -p 8000 config.asgi:application
```

## 📂 Loyiha Tuzilishi

- `apps/`: Tizimning barcha kichik modullari (accounts, courses, homework, payments, etc.)
- `config/`: Django loyihasining asosiy sozlamalari.
- `static/` & `templates/`: Front-end qismi (CSS, JS va HTML shablonlar).
- `media/`: Yuklangan rasmlar va hujjatlar.

---
© 2024 Kamanda Bilan ERP. Barcha huquqlar himoyalangan.
