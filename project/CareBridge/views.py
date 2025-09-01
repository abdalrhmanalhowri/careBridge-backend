from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.contrib.auth.models import User
from .models import *
from .serializers import *

@api_view(['POST'])
@permission_classes([AllowAny])
def register_volunteer(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save() 
        return Response({'message': 'تم إنشاء الحساب بنجاح', 'user_id': user.id}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#جدول كبار السن
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def elder_list(request):
    if request.method == 'GET':
        elders_data = []
        elders = Elder.objects.all()
        for elder in elders:
            # الحصول على آخر زيارة لكبير السن
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
        visits = Visit.objects.all()
        serializer = VisitSerializer(visits, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = VisitSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_detail(request, pk):
    try:
        volunteer = Volunteer.objects.get(user=request.user)
    except Volunteer.DoesNotExist:
        return Response({'message': 'لا يوجد متطوع مرتبط بهذا المستخدم.'}, status=status.HTTP_404_NOT_FOUND)
    notification = get_object_or_404(Notification, pk=pk, volunteer=volunteer)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
    serializer = NotificationSerializer(notification)
    return Response(serializer.data)

#الاحصائيات
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data(request):
    elders_count_view= Elder.objects.all().count()
    volunteer_count_viwe= Elder.objects.all().count()
    Visit_count_view= Elder.objects.all().count()

    count_data={'elder_count':elders_count_view,
                'volunteer_count':volunteer_count_viwe,
                'visit_count':Visit_count_view,
                }
    serializer = CountDataSerializer(count_data)
    return Response(serializer.data)
    


    
