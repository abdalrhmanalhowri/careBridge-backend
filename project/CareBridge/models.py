from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('volunteer', 'Volunteer'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='volunteer')
    email = models.EmailField(unique=True)

# جدول كبار السن
class Elder(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    health_status = models.CharField(max_length=10, blank=True, null=True)
    children_count = models.PositiveIntegerField()
    financial_status = models.CharField(max_length=30)
    special_needs = models.TextField()
    phone = models.CharField(max_length=20)
    image = models.ImageField(upload_to='images/', null=True, blank=True)

    def __str__(self):
        return f"{self.id} – {self.name}"


# جدول المتطوعين (مرتبط بـ User)
class Volunteer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    city = models.CharField(max_length=100)
    job_title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='images/', null=True, blank=True)

    gender = models.CharField(
        max_length=10,
        choices=[
            ('ذكر', 'ذكر'),
            ('أنثى', 'أنثى'),
        ]
    )
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ('أعزب', 'أعزب'),
            ('متزوج', 'متزوج'),
            ('آخر', 'آخر'),
        ]
    )
    resume = models.FileField(upload_to='volunteer_resumes/')
    agreed_terms = models.BooleanField(default=False)
    commitment_statement = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} – User: {self.user.username}"

# جدول الزيارات
class Visit(models.Model):
    visit_id = models.AutoField(primary_key=True)
    elder = models.ForeignKey(Elder, on_delete=models.CASCADE)
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE)
    visit_date = models.DateTimeField()
    status = models.CharField(max_length=20)
    duration_minutes = models.PositiveIntegerField()
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    heart_rate = models.PositiveIntegerField()
    blood_pressure = models.CharField(max_length=20)
    oxygen_level = models.PositiveIntegerField()
    blood_sugar = models.PositiveIntegerField()
    general_health_status = models.CharField(
        max_length=20,
        choices=[
            ('جيد', 'جيد'),
            ('متوسط', 'متوسط'),
            ('يحتاج متابعة', 'يحتاج متابعة'),
            ('حرج', 'حرج'),
        ]
    )
    health_notes = models.TextField(blank=True)
    medical_need = models.CharField(
        max_length=30,
        choices=[
            ('فحص دوري', 'فحص دوري'),
            ('دواء', 'دواء'),
            ('مرافقة لطبيب', 'مرافقة لطبيب'),
        ]
    )
    psych_status = models.CharField(
        max_length=20,
        choices=[
            ('مستقر', 'مستقر'),
            ('مكتئب', 'مكتئب'),
            ('وحيد', 'وحيد'),
            ('متحسن', 'متحسن'),
        ]
    )
    social_status = models.CharField(
        max_length=50,
        choices=[
            ('يتواصل مع الجيران', 'يتواصل مع الجيران'),
            ('لديه زيارات متقطعة', 'لديه زيارات متقطعة'),
            ('لا يوجد دعم عائلي', 'لا يوجد دعم عائلي'),
        ]
    )
    additional_notes = models.TextField(blank=True)
    living_need = models.CharField(
        max_length=30,
        choices=[
            ('غذاء', 'غذاء'),
            ('أدوات منزلية', 'أدوات منزلية'),
            ('أدوية', 'أدوية'),
        ]
    )
    support_need = models.CharField(
        max_length=30,
        choices=[
            ('زيارة إضافية', 'زيارة إضافية'),
            ('جلسة استماع', 'جلسة استماع'),
            ('نشاط جماعي', 'نشاط جماعي'),
        ]
    )
    general_status_percent = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"زيارة رقم {self.visit_id} لكبير السن {self.elder.name}"

    def save(self, *args, **kwargs):
        if self.is_submitted and not self.submitted_at:
            from django.utils import timezone
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)

        if self.general_status_percent:
            elder = self.elder
            elder.health_status = str(self.general_status_percent) 
            elder.save(update_fields=['health_status'])


# جدول التحاليل
class Analysis(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    pdf_file = models.FileField(upload_to='pdf_analysis/')

    def __str__(self):
        return f"تحليل زيارة {self.visit.visit_id}"


# جدول الأدوية
class Medication(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    medication_name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    duration = models.CharField(max_length=100)

    def __str__(self):
        return self.medication_name


# جدول الإشعارات
class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE)
    message_text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at'] 

    def __str__(self):
        return f"إشعار للمتطوع {self.volunteer.name}"
    

# class count_data:
#     elder_count =0 
#     volunteer_count=0
#     visit_count=0