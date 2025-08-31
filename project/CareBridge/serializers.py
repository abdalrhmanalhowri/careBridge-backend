from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *

class ElderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Elder
        fields = '__all__'

class VolunteerSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
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
    name = serializers.CharField(max_length=100)
    age = serializers.IntegerField()
    city = serializers.CharField(max_length=100)
    job_title = serializers.CharField(max_length=100)
    gender = serializers.ChoiceField(choices=[('ذكر', 'ذكر'), ('أنثى', 'أنثى')])
    marital_status = serializers.ChoiceField(choices=[('أعزب', 'أعزب'), ('متزوج', 'متزوج'), ('آخر', 'آخر')])
    resume = serializers.FileField()
    agreed_terms = serializers.BooleanField()
    commitment_statement = serializers.BooleanField()
    is_approved = serializers.BooleanField(default=False)
    is_admin = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'name', 'age', 'city', 'job_title',
                  'gender', 'marital_status', 'resume', 'agreed_terms',
                  'commitment_statement', 'is_approved', 'is_admin']

    def create(self, validated_data):
        volunteer_data = {
            key: validated_data.pop(key)
            for key in ['name', 'age', 'city', 'job_title', 'gender', 'marital_status',
                        'resume', 'agreed_terms', 'commitment_statement', 'is_approved', 'is_admin']
        }
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        Volunteer.objects.create(user=user, **volunteer_data)
        return user
    
    