from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes , parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import *
from .serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser 
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
import resend
from django.conf import settings
import random
from django.core.mail import send_mail
from django.db.models.functions import ExtractYear, ExtractMonth
from django.db.models import Count , Q
from rest_framework.pagination import PageNumberPagination
from .pagination import CustomPagination

User = get_user_model()
resend.api_key = settings.RESEND_API_KEY

# إرسال كود (للتسجيل أو إعادة تعيين كلمة المرور)
def send_verification_code(user, purpose="verify"):
    # اجعل كل الأكواد القديمة غير صالحة
    EmailVerificationCode.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    code = str(random.randint(100000, 999999))
    EmailVerificationCode.objects.create(user=user, code=code, purpose=purpose)

    # اسم المتطوع (fallback للبريد إذا ما في متطوع)
    volunteer = getattr(user, "volunteer", None)
    volunteer_name = volunteer.name if volunteer else user.email

    if purpose == "verify":
        subject = "رمز التحقق الخاص بك - CareBridge"
        greeting = f"مرحباً {volunteer_name}،"
        instruction = "رمز التحقق الخاص بك هو:"
    elif purpose == "reset":
        subject = "رمز إعادة تعيين كلمة المرور - CareBridge"
        greeting = f"مرحباً {volunteer_name}،"
        instruction = "رمز إعادة تعيين كلمة المرور الخاص بك هو:"
    else:
        subject = "رمز خاص بك - CareBridge"
        greeting = f"مرحباً {volunteer_name}،"
        instruction = "رمزك الخاص هو:"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; background-color: #f9f9f9;
        padding: 20px; border-radius: 10px; max-width: 500px; margin: auto; 
        text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <h2 style="color: #4A90E2;">{subject}</h2>
        <p style="font-size: 16px; color: #333;">{greeting}</p>
        <p style="font-size: 18px; margin: 20px 0;">{instruction}</p>
        <div style="font-size: 24px; font-weight: bold; color: #ffffff;
            background-color: #4A90E2; padding: 10px 20px; border-radius: 8px;
            display: inline-block;">
            {code}
        </div>
        <p style="margin-top: 20px; font-size: 14px; color: #666;">
            إذا لم تطلب هذا الرمز، يمكنك تجاهل الرسالة.
        </p>
    </div>
    """

    try:
        send_mail(
            subject=subject,
            message=f"{instruction} {code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )
    except Exception as e:
        # لا نرمي هنا 500 — فقط نسجل (يمكن إضافة logging)
        print("Error sending verification email:", e)
        # إذا أردت، ارجع False للإشارة لفشل الإرسال
        return False

    return True

@api_view(['POST'])
@permission_classes([AllowAny])
def register_volunteer(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        # serializer.create يجب أن تُعيد Volunteer وفق كودك الحالي
        volunteer = serializer.save()
        # تضمن وجود رابط user
        if volunteer and hasattr(volunteer, "user"):
            volunteer.is_verified = False
            volunteer.save()
            # نرسل كود التحقق، لكن إن فشل الإرسال لا نعيد 500
            send_verification_code(volunteer.user, purpose="verify")
            return Response(
                {"detail": "تم إنشاء الحساب بنجاح. الرجاء تأكيد البريد الإلكتروني قبل تسجيل الدخول."},
                status=status.HTTP_201_CREATED
            )
        else:
            # حالة نادرة: لم يُنشأ المتطوع بشكل سليم
            return Response({"detail": "خطأ في إنشاء المتطوع."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# تأكيد البريد الإلكتروني
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    serializer = VerifyCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']

    try:
        user = User.objects.get(email=email)
        verification = EmailVerificationCode.objects.filter(
            user=user, code=code, purpose="verify", is_used=False
        ).last()

        if verification and verification.is_valid():
            # تحديث حالة الكود
            verification.is_used = True
            verification.save()

            # تفعيل المتطوع
            volunteer = user.volunteer
            volunteer.is_verified = True
            volunteer.save()

            # توليد التوكنات
            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "تم تأكيد البريد بنجاح ✅",
                "user_id": user.id,
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            }, status=status.HTTP_200_OK)

        return Response({"detail": "رمز غير صالح أو منتهي"}, status=status.HTTP_400_BAD_REQUEST)

    except User.DoesNotExist:
        return Response({"detail": "المستخدم غير موجود"}, status=status.HTTP_404_NOT_FOUND)


# login 
@api_view(['POST'])
@permission_classes([AllowAny])
def login_volunteer(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"detail": "الرجاء إدخال الايميل وكلمة المرور."}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response({"detail": "الايميل أو كلمة المرور غير صحيحة."}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({"detail": "هذا الحساب غير مفعل."}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)

    if not hasattr(user, "volunteer") or not user.volunteer.is_verified:
        # أرسال كود جديد للتأكيد
        send_verification_code(user, purpose="verify")
        return Response(
            {"detail": "الرجاء تأكيد البريد الإلكتروني أولاً."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    return Response({
        "message": "تم تسجيل الدخول بنجاح",
        "user_id": user.id,
        "email": user.email,
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def elder_list(request):
    if request.method == 'GET':
        elders = Elder.objects.all()

        # 🔎 البحث بالاسم أو المدينة
        search = request.GET.get('search')
        if search:
            elders = elders.filter(
                Q(name__icontains=search) | Q(city__icontains=search)
            )

        # 🔎 التصفية حسب العمر
        min_age = request.GET.get('min_age')
        max_age = request.GET.get('max_age')
        if min_age:
            elders = elders.filter(age__gte=min_age)
        if max_age:
            elders = elders.filter(age__lte=max_age)

        # 🔎 التصفية حسب الحالة الصحية
        health_status = request.GET.get('health_status')
        if health_status:
            elders_ids = []
            for elder in elders:
                last_visit = Visit.objects.filter(elder=elder).order_by('-visit_date').first()
                if last_visit:
                    percent = last_visit.general_status_percent
                    if health_status == "good" and percent >= 80:
                        elders_ids.append(elder.id)
                    elif health_status == "medium" and 51 <= percent <= 79:
                        elders_ids.append(elder.id)
                    elif health_status == "critical" and percent <= 50:
                        elders_ids.append(elder.id)
            elders = elders.filter(id__in=elders_ids)

        # 🔎 الترتيب
        ordering = request.GET.get('ordering')
        if ordering == 'newest':
            elders = elders.order_by('-created_at')
        elif ordering == 'oldest':
            elders = elders.order_by('created_at')
        else:
            elders = elders.order_by('-created_at')

        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(elders, request)

        elders_data = []
        for elder in result_page:
            last_visit = Visit.objects.filter(elder=elder).order_by('-visit_date').first()
            health_percent = last_visit.general_status_percent if last_visit else None

            elders_data.append({
                'id': elder.id,
                'name': elder.name,
                'age': elder.age,
                'gender': elder.gender,
                'city': elder.city,
                'health_status': health_percent,
            })

        return paginator.get_paginated_response(elders_data)

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'يجب تسجيل الدخول لإضافة كبير السن.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        serializer = ElderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([AllowAny]) 
def elder_detail(request, pk):
    elder = get_object_or_404(Elder, pk=pk)

    if request.method == 'GET':
        serializer = ElderSerializer(elder)
        return Response(serializer.data)

    # باقي العمليات تحتاج تسجيل دخول
    if not request.user.is_authenticated:
        return Response(
            {"detail": "يجب تسجيل الدخول لإجراء هذا الطلب."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if request.method in ['PUT', 'PATCH']:
        partial = (request.method == 'PATCH')
        serializer = ElderSerializer(elder, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        elder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


#جدول المتطوعين
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def volunteer_list(request):
    volunteer = Volunteer.objects.filter(user=request.user).first()
    if volunteer:
        serializer = VolunteerSerializer(volunteer)
        return Response(serializer.data)
    else:
        return Response({
            'message': 'لا يوجد متطوع مرتبط بهذا المستخدم.',
            'volunteer': None
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def volunteer_detail(request):
    volunteer = Volunteer.objects.filter(user=request.user).first()
    if not volunteer:
        return Response({'message': 'لا يوجد متطوع مرتبط بهذا المستخدم.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = VolunteerSerializer(volunteer)
        return Response(serializer.data)

    elif request.method in ['PUT', 'PATCH']:
        partial = (request.method == 'PATCH')
        serializer = VolunteerSerializer(volunteer, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        volunteer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# حذف المتطوع 
@api_view(['DELETE'])
@permission_classes([IsAuthenticated]) 
def delete_volunteer(request, user_id):
    try:
        user = User.objects.get(id=user_id)

        # حذف المتطوع المرتبط
        Volunteer.objects.filter(user=user).delete()

        # حذف اليوزر نفسه
        user.delete()

        return Response({"detail": "تم حذف المستخدم والمتطوع بنجاح"}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({"detail": "المستخدم غير موجود"}, status=status.HTTP_404_NOT_FOUND)
    

#جدول الزيارات
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def visit_list(request):
    if request.method == 'GET':
        volunteer = Volunteer.objects.get(user=request.user)
        visits = Visit.objects.filter(volunteer=volunteer)
        serializer = VisitSerializer(visits, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = VisitSerializer(data=request.data)
        if serializer.is_valid():
                visit = serializer.save(volunteer=Volunteer.objects.get(user=request.user))
                # إنشاء إشعار تلقائي للمتطوع
                Notification.objects.create(
                    volunteer=visit.volunteer,
                    title="! لديك زيارة جديدة ",
                    message_text=f"تم تكليفك بزيارة جديدة للمسن {visit.elder.name} في {visit.elder.city} بتاريخ {visit.visit_date.strftime('%Y-%m-%d %H:%M')}"
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def visit_detail(request, pk):
    visit = get_object_or_404(Visit, pk=pk)
    if request.method == 'GET':
        serializer = VisitSerializer(visit)
        return Response(serializer.data)
    elif request.method in ['PUT', 'PATCH']:
        partial = (request.method == 'PATCH')
        serializer = VisitSerializer(visit, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        visit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_visit(request, visit_id):
    try:
        visit = Visit.objects.get(visit_id=visit_id)

        if visit.status != "missing":
            return Response(
                {"detail": "لا يمكن قبول هذه الزيارة، حالتها الحالية ليست (غير منجزة)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        visit.status = "pending"
        visit.save()

        return Response(
            {"detail": f"تم قبول الزيارة رقم {visit.visit_id} وهي الآن قيد التقدم."},
            status=status.HTTP_200_OK
        )

    except Visit.DoesNotExist:
        return Response({"detail": "الزيارة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)

# تقديم تقرير
@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])  # السماح المبدئي للجميع
@parser_classes([MultiPartParser, FormParser])
def visit_report(request, elder_id):
    visit = Visit.objects.filter(elder_id=elder_id).order_by('-created_at').first()
    if not visit:
        return Response({"detail": "لا توجد زيارات لهذا المسن"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = VisitReportSerializer(visit, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not request.user.is_authenticated:
            return Response(
                {"detail": "يجب تسجيل الدخول لتقديم التقرير."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = VisitReportSerializer(
            visit,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            visit.status = "done"
            visit.save()
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#جدول الادوية
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def medication_list(request):
    if request.method == 'GET':
        medications = Medication.objects.all()
        serializer = MedicationSerializer(medications, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = MedicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def medication_detail(request, pk):
    medication = get_object_or_404(Medication, pk=pk)
    if request.method == 'GET':
        serializer = MedicationSerializer(medication)
        return Response(serializer.data)
    elif request.method in ['PUT', 'PATCH']:
        partial = (request.method == 'PATCH')
        serializer = MedicationSerializer(medication, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        medication.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

#جدول التحاليل
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def analysis_list(request):
    if request.method == 'GET':
        analyses = Analysis.objects.all()
        serializer = AnalysisSerializer(analyses, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = AnalysisSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def analysis_detail(request, pk):
    analysis = get_object_or_404(Analysis, pk=pk)
    if request.method == 'GET':
        serializer = AnalysisSerializer(analysis)
        return Response(serializer.data)
    elif request.method in ['PUT', 'PATCH']:
        partial = (request.method == 'PATCH')
        serializer = AnalysisSerializer(analysis, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        analysis.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

#جدول الاشعارات
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    try:
        volunteer = Volunteer.objects.get(user=request.user)
    except Volunteer.DoesNotExist:
        return Response({'message': 'لا يوجد متطوع مرتبط بهذا المستخدم.'}, status=status.HTTP_404_NOT_FOUND)
    notifications = Notification.objects.filter(volunteer=volunteer)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def notification_detail(request, pk):
#     try:
#         volunteer = Volunteer.objects.get(user=request.user)
#     except Volunteer.DoesNotExist:
#         return Response({'message': 'لا يوجد متطوع مرتبط بهذا المستخدم.'}, status=status.HTTP_404_NOT_FOUND)
#     notification = get_object_or_404(Notification, pk=pk, volunteer=volunteer)
#     if not notification.is_read:
#         notification.is_read = True
#         notification.read_at = timezone.now()
#         notification.save()
#     serializer = NotificationSerializer(notification)
#     return Response(serializer.data)

# قراءة الاشعار 
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, pk):
    try:
        volunteer = Volunteer.objects.get(user=request.user)
    except Volunteer.DoesNotExist:
        return Response({'message': 'لا يوجد متطوع مرتبط بهذا المستخدم.'}, status=status.HTTP_404_NOT_FOUND)

    notification = get_object_or_404(Notification, pk=pk, volunteer=volunteer)

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

    return Response({'message': 'تم تحديد الإشعار كمقروء.', 'read_at': notification.read_at})
    

# الصورة الشخصية
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def avatar_view(request):
    volunteer = request.user.volunteer

    # جلب الصورة
    if request.method == 'GET':
        if not volunteer.image:
            return Response({"error": "No avatar found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"image": request.build_absolute_uri(volunteer.image.url)})

    # رفع/تحديث الصورة
    if request.method == 'POST':
        file_obj = request.data.get('image')
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        volunteer.image = file_obj  # CloudinaryField سيقوم بالرفع تلقائيًا
        volunteer.save()
        return Response({"message": "Avatar updated successfully", "image_url": volunteer.image.url})
    
@api_view(['GET'])
@permission_classes([AllowAny])
def create_superuser(request):
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='SuperStrongPassword123'
        )
        return Response({"message": "Superuser created successfully!"})
    return Response({"message": "Superuser already exists."})

#  تواصل معنا 
resend.api_key = settings.RESEND_API_KEY

@api_view(['POST'])
@permission_classes([AllowAny])  # أي شخص يقدر يرسل من الفورم
def send_contact_email(request):
    fullname = request.data.get("fullname")
    email = request.data.get("email")
    message = request.data.get("message")

    if not fullname or not email or not message:
        return Response({"error": "كل الحقول مطلوبة"}, status=400)

    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",  # لازم دومين مفعل في Resend
            "to": "carebridge.official0@gmail.com", 
            "subject": f"رسالة جديدة من {fullname}",
            "html": f"""
                <h3>تفاصيل الرسالة:</h3>
                <p><strong>الاسم:</strong> {fullname}</p>
                <p><strong>البريد:</strong> {email}</p>
                <p><strong>الرسالة:</strong> {message}</p>
            """,
        })

        return Response({"message": "تم إرسال الرسالة بنجاح ✅"})
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# طلب إعادة تعيين كلمة المرور
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get("email")
    try:
        user = User.objects.get(email=email)
        send_verification_code(user, purpose="reset")
        return Response({"detail": "تم إرسال رمز إعادة تعيين كلمة المرور إلى البريد"})
    except User.DoesNotExist:
        return Response({"detail": "المستخدم غير موجود"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data.get('new_password')  # ممكن يكون مش موجود

    try:
        user = User.objects.get(email=email)
        verification = EmailVerificationCode.objects.filter(
            user=user, code=code, purpose="reset", is_used=False
        ).last()

        if not verification or not verification.is_valid():
            return Response({"detail": "رمز غير صالح أو منتهي"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ إذا ما في new_password → معناها لسه عم نتحقق
        if not new_password:
            return Response({"detail": "تم التحقق من الرمز ✅ الرجاء إدخال كلمة المرور الجديدة"}, status=status.HTTP_200_OK)

        # ✅ إذا في new_password → معناها بدنا نغير الباسورد
        verification.is_used = True
        verification.save()
        user.set_password(new_password)
        user.save()
        return Response({"detail": "تم تغيير كلمة المرور بنجاح ✅"}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({"detail": "المستخدم غير موجود"}, status=status.HTTP_404_NOT_FOUND)

#  إعادة ارسال كود التاكيد
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_code(request):
    email = request.data.get("email")
    if not email:
        return Response({"detail": "الرجاء إدخال البريد الإلكتروني."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)

        # إذا تم التحقق مسبقاً لا نرسل الكود
        if hasattr(user, "volunteer") and user.volunteer.is_verified:
            return Response({"detail": "تم بالفعل تأكيد البريد الإلكتروني."}, status=status.HTTP_400_BAD_REQUEST)

        # استدعاء الدالة الأصلية لإرسال كود جديد
        send_verification_code(user, purpose="verify")

        return Response({"detail": "تم إرسال رمز التحقق بنجاح."}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({"detail": "المستخدم غير موجود."}, status=status.HTTP_404_NOT_FOUND)
    
#  admin dashboard

# تسجيل الدخول للادمنز 
@api_view(['POST'])
@permission_classes([AllowAny])
def login_admin(request):
    email = request.data.get("email")
    password = request.data.get("password")
    user = authenticate(request, username=email, password=password)
    
    if not user or not user.is_superuser:
        return Response({"detail": "غير مسموح"}, status=403)

    refresh = RefreshToken.for_user(user)
    return Response({
        "message": "تم تسجيل الدخول بنجاح كأدمن",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    })

#الاحصائيات
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data(request):
    elders_count_view = Elder.objects.count()
    volunteer_count_view = Volunteer.objects.count()
    visit_count_view = Visit.objects.count()
    report_count_view = Visit.objects.filter(status="done").count()

    count_data = {
        'elder_count': elders_count_view,
        'volunteer_count': volunteer_count_view,
        'visit_count': visit_count_view,
        'report_count': report_count_view,
    }
    serializer = CountDataSerializer(count_data)
    return Response(serializer.data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_visits_report(request):
    visits = (
        Visit.objects.filter(status="done")
        .annotate(year=ExtractYear('submitted_at'), month=ExtractMonth('submitted_at'))
        .values('year', 'month')
        .annotate(total_visit=Count('visit_id'))
        .order_by('year', 'month')
    )

    data = [
        {
            "year": v["year"],
            "month": v["month"],
            "total_visit": v["total_visit"],
        }
        for v in visits
    ]

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_overview(request):
    # المسنين شهريًا
    elders = (
        Elder.objects.annotate(year=ExtractYear('created_at'), month=ExtractMonth('created_at'))
        .values('year', 'month')
        .annotate(total_elders=Count('id'))
    )

    # المتطوعين شهريًا
    volunteers = (
        Volunteer.objects.annotate(year=ExtractYear('created_at'), month=ExtractMonth('created_at'))
        .values('year', 'month')
        .annotate(total_volunteers=Count('id'))
    )

    # الزيارات شهريًا
    visits = (
        Visit.objects.annotate(year=ExtractYear('created_at'), month=ExtractMonth('created_at'))
        .values('year', 'month')
        .annotate(total_visits=Count('visit_id'))  # 👈 عدلتها
    )

    # التقارير شهريًا (زيارات حالتها done)
    reports = (
        Visit.objects.filter(status='done')
        .annotate(year=ExtractYear('submitted_at'), month=ExtractMonth('submitted_at'))
        .values('year', 'month')
        .annotate(total_reports=Count('visit_id'))  # 👈 عدلتها
    )


    # تحويل الـ QuerySets لقواميس
    elders_dict = {(e['year'], e['month']): e['total_elders'] for e in elders}
    volunteers_dict = {(v['year'], v['month']): v['total_volunteers'] for v in volunteers}
    visits_dict = {(v['year'], v['month']): v['total_visits'] for v in visits}
    reports_dict = {(r['year'], r['month']): r['total_reports'] for r in reports}

    # نجمع كل الأشهر الموجودة بأي من الجداول
    months_years = set(list(elders_dict.keys()) + list(volunteers_dict.keys()) +
                       list(visits_dict.keys()) + list(reports_dict.keys()))

    # بناء البيانات النهائية
    data = []
    for year, month in sorted(months_years):
        data.append({
            "year": year,
            "month": month,
            "eldersCount": elders_dict.get((year, month), 0),
            "volunteersCount": volunteers_dict.get((year, month), 0),
            "visitsCount": visits_dict.get((year, month), 0),
            "reportsCount": reports_dict.get((year, month), 0),
        })

    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_volunteers(request):
    volunteers = Volunteer.objects.select_related("user").order_by('-created_at')[:8]

    data = []
    for v in volunteers:
        data.append({
            "id": v.id,
            "name": v.name,
            "email": v.user.email if v.user else None,
            "image": v.image.url if v.image else None,  
            "city": v.city,
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M"),
        })

    return Response(data)

#  حالات المسنين 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def elders_health_status_stats(request):
    elders = Elder.objects.all()
    total = elders.count() or 1 

    critical = elders.filter(health_status__lte=50).count()
    medium = elders.filter(health_status__gte=51, health_status__lte=79).count()
    good = elders.filter(health_status__gte=80).count()

    data = [
        {
            "status": "حالة جيدة",
            "percent": round((good / total) * 100, 2),
        },
        {
            "status": "حالة متوسطة",
            "percent": round((medium / total) * 100, 2),
        },
        {
            "status": "حالة حرجة",
            "percent": round((critical / total) * 100, 2),
        },
    ]

    return Response(data)