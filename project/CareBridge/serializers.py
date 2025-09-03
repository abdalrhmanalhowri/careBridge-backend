from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *

class ElderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Elder
        fields = '__all__'

class VolunteerSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Volunteer
        fields = '__all__'

class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = '__all__'

class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = '__all__'

class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['is_read', 'read_at']

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

        email = validated_data['email']
        u = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password']
        )
        u.is_active = True
        u.save()
        Volunteer.objects.create(user=u, **volunteer_data)
        return u
