from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *
import json

User = get_user_model()

class ElderSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Elder
        fields = '__all__'

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class VolunteerSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    image_url = serializers.SerializerMethodField()
    cv_url = serializers.SerializerMethodField()

    class Meta:
        model = Volunteer
        fields = '__all__'  # جميع الحقول
        extra_fields = ['email']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_cv_url(self, obj):
        if obj.resume:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.resume.url) if request else obj.resume.url
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['email'] = instance.user.email
        return representation


class VisitSerializer(serializers.ModelSerializer):
    elder_name = serializers.CharField(source='elder.name', read_only=True)
    elder_city = serializers.CharField(source='elder.city', read_only=True)
    elder = serializers.PrimaryKeyRelatedField(queryset=Elder.objects.all()) 
    volunteer = serializers.PrimaryKeyRelatedField(queryset=Volunteer.objects.all()) 

    class Meta:
        model = Visit
        fields = [
            'visit_id',
            'elder',
            'elder_name',
            'elder_city',
            'volunteer',
            'visit_date',
            'status',
            'created_at',
        ]

class AnalysisSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Analysis
        fields = '__all__'
    
    def get_pdf_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.pdf_file.url) if request else obj.pdf_file.url
        return None

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = '__all__'

class VisitReportSerializer(serializers.ModelSerializer):
    analyses = AnalysisSerializer(many=True, read_only=True)
    medications = MedicationSerializer(many=True, read_only=True)

    class Meta:
        model = Visit
        fields = [
            'visit_id',
            'heart_rate',
            'blood_pressure',
            'oxygen_level',
            'blood_sugar',
            'general_health_status',
            'health_notes',
            'medical_need',
            'psych_status',
            'social_status',
            'additional_notes',
            'living_need',
            'support_need',
            'general_status_percent',
            'analyses',
            'medications',
            'status',
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['is_read', 'read_at', 'created_at']

class CountDataSerializer(serializers.Serializer):
    elder_count = serializers.IntegerField()
    volunteer_count = serializers.IntegerField()
    visit_count = serializers.IntegerField()

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Volunteer
        fields = [
            'email', 'password', 'name', 'age', 'city', 'job_title',
            'gender', 'marital_status', 'resume',
            'agreed_terms', 'commitment_statement'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("هذا البريد مستخدم سابقًا.")
        return value

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # إنشاء المستخدم
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            role="volunteer"
        )
        user.is_active = True
        user.save()

        # إنشاء المتطوع وربطه بالمستخدم
        volunteer = Volunteer.objects.create(user=user, **validated_data)
        return volunteer


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)