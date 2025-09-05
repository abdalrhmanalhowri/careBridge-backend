from django.urls import path
from . import views

urlpatterns = [
    # تسجيل متطوع جديد
    path('register/', views.register_volunteer, name='register-volunteer'),

    #  تسجيل الدخول 
    path("login/", views.login_volunteer, name="login"),
    # كبار السن
    path('elders/', views.elder_list, name='elder-list'),
    path('elders/<int:pk>/', views.elder_detail, name='elder-detail'),

    # المتطوعين
    path('volunteers/', views.volunteer_list, name='volunteer-list'),
    path('volunteers/me/', views.volunteer_detail, name='volunteer-detail'),
    #  حذف المتطوع
    path("volunteers/<int:user_id>/delete/", views.delete_volunteer, name="delete-volunteer"),


    # الزيارات
    path('visits/', views.visit_list, name='visit-list'),
    path('visits/<int:pk>/', views.visit_detail, name='visit-detail'),
    path("visits/<int:visit_id>/accept/", views.accept_visit, name="accept-visit"),
    path('visits/<int:elder_id>/report/', views.visit_report, name='submit-visit-report'),

    # الادوية
    path('medications/', views.medication_list, name='medication-list'),
    path('medications/<int:pk>/', views.medication_detail, name='medication-detail'),

    # التحاليل
    path('analyses/', views.analysis_list, name='analysis-list'),
    path('analyses/<int:pk>/', views.analysis_detail, name='analysis-detail'),

    # الاشعارات
    path('notifications/', views.notification_list, name='notification-list'),
    # path('notifications/<int:pk>/', views.notification_detail, name='notification-detail'),
    path('notifications/<int:pk>/read/', views.mark_notification_as_read, name='notification-mark-read'),

    # الإحصائيات
    path('data/', views.get_data, name='get-data'),


    # الصورة الشخصية
    path('volunteer/avatar/', views.avatar_view, name='volunteer-avatar'),

    # انشاء ادمن 
    path('create-superuser/', views.create_superuser, name='create_superuser'),

    # ارسال بريد الكتروني
    path("contact/send/", views.send_contact_email, name="send_contact_email"),

]