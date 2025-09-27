import os
from celery import Celery

# اضبط الإعدادات الافتراضية لـ Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

# إنشاء تطبيق Celery. (يمكنك تسميته باسم مشروعك)
app = Celery('project')

# استخدام إعدادات Django. مفتاح الإعدادات هو CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# اكتشاف المهام تلقائياً في جميع ملفات tasks.py
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')