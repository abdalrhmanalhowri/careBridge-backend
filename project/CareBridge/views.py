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

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def register_volunteer(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    refresh = RefreshToken.for_user(user)
    
    if serializer.is_valid():
        return Response({
            "message": "تم إنشاء الحساب بنجاح",
            "user_id": user.id,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

    return Response({
        "message": "تم تسجيل الدخول بنجاح",
        "user_id": user.id,
        "email": user.email,
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }, status=status.HTTP_200_OK)


#جدول كبار السن
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def elder_list(request):
    if request.method == 'GET':
        elders_data = []
        elders = Elder.objects.all()
        for elder in elders:
            last_visit = Visit.objects.filter(elder=elder).order_by('-visit_date').first()
            health_percent = last_visit.general_status_percent if last_visit else None

            elders_data.append({
                'id': elder.id,
                'name': elder.name,
                'age': elder.age,
                'gender': elder.gender,
                'city': elder.city,
                'health_status':health_percent,
            })
        return Response(elders_data)

    elif request.method == 'POST':
        # 🔹 خلي الإدخال فقط للـ authenticated users
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

    elif request.method == 'POST':
        serializer = ElderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def elder_detail(request, pk):
    elder = get_object_or_404(Elder, pk=pk)
    if request.method == 'GET':
        serializer = ElderSerializer(elder)
        return Response(serializer.data)
    elif request.method in ['PUT', 'PATCH']:
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
        visit = Visit.objects.get(id=visit_id)

        if visit.status != "missing":
            return Response(
                {"detail": "لا يمكن قبول هذه الزيارة، حالتها الحالية ليست (غير منجزة)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        visit.status = "pending"
        visit.save()

        return Response(
            {"detail": f"تم قبول الزيارة رقم {visit.id} وهي الآن قيد التقدم."},
            status=status.HTTP_200_OK
        )

    except Visit.DoesNotExist:
        return Response({"detail": "الزيارة غير موجودة"}, status=status.HTTP_404_NOT_FOUND)

# تقديم تقرير 
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def visit_report(request, elder_id):
    # جلب آخر زيارة للمسن
    visit = Visit.objects.filter(elder_id=elder_id).order_by('-created_at').first()
    if not visit:
        return Response({"detail": "لا توجد زيارات لهذا المسن"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = VisitReportSerializer(visit)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = VisitReportSerializer(visit, data=request.data, partial=True)
        if serializer.is_valid():
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


#الاحصائيات
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data(request):
    elders_count_view= Elder.objects.count()
    volunteer_count_viwe= Volunteer.objects.count()
    Visit_count_view= Visit.objects.count()

    count_data={'elder_count':elders_count_view,
                'volunteer_count':volunteer_count_viwe,
                'visit_count':Visit_count_view,
                }
    serializer = CountDataSerializer(count_data)
    return Response(serializer.data)
    

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