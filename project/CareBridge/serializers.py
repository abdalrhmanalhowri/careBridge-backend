from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *

User = get_user_model()

class ElderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Elder
        fields = '__all__'
    
    def get_avatar_url(self, obj):
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
    class Meta:
        model = Analysis
        fields = '__all__'

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = '__all__'

class VisitReportSerializer(serializers.ModelSerializer):
    analyses = AnalysisSerializer(many=True, read_only=True, source='analysis_set')
    medications = MedicationSerializer(many=True, read_only=True, source='medication_set')

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
            'submitted_at',
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
    name = serializers.CharField(max_length=100)
    age = serializers.IntegerField()
    city = serializers.CharField(max_length=100)
    job_title = serializers.CharField(max_length=100)
    gender = serializers.ChoiceField(choices=[('ذكر', 'ذكر'), ('أنثى', 'أنثى')])
    marital_status = serializers.ChoiceField(choices=[('أعزب', 'أعزب'), ('متزوج', 'متزوج'), ('آخر', 'آخر')])
    resume = serializers.FileField()
    agreed_terms = serializers.BooleanField()
    commitment_statement = serializers.BooleanField()

    class Meta:
        model = User
        fields = [
            'email', 'password', 'name', 'age', 'city', 'job_title',
            'gender', 'marital_status', 'resume', 'agreed_terms',
            'commitment_statement'
        ]
        extra_kwargs = {
            'password': {'write_only': True},  # نخلي الباسورد للإنشاء فقط
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("هذا البريد مستخدم سابقًا.")
        return value

    def create(self, validated_data):
        volunteer_data = {
            key: validated_data.pop(key)
            for key in [
                'name', 'age', 'city', 'job_title', 'gender', 'marital_status',
                'resume', 'agreed_terms', 'commitment_statement'
            ]
        }

        userEmail = validated_data['email']
        u = User.objects.create_user(
            username=userEmail,
            email=userEmail,
            password=validated_data['password']
        )
        u.is_active = True
        u.save()
        Volunteer.objects.create(user=u, **volunteer_data)
        return u
