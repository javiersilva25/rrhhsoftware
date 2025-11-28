from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Department, Position, Employee, 
    BankAccount, TaxInformation, Insurance, EmploymentHistory
)


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo User
    """
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'profile_picture', 'password',
            'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Department
    """
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'description', 'manager', 
            'manager_name', 'employee_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_employee_count(self, obj):
        return obj.employees.filter(status='active').count()


class PositionSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Position
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    employee_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Position
        fields = [
            'id', 'title', 'code', 'department', 'department_name',
            'description', 'level', 'min_salary', 'max_salary',
            'employee_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_employee_count(self, obj):
        return obj.employees.filter(status='active').count()


class BankAccountSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo BankAccount
    """
    class Meta:
        model = BankAccount
        fields = [
            'id', 'employee', 'bank_name', 'account_number',
            'account_type', 'routing_number', 'swift_code',
            'is_primary', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TaxInformationSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo TaxInformation
    """
    class Meta:
        model = TaxInformation
        fields = [
            'id', 'employee', 'tax_id', 'tax_regime',
            'withholding_percentage', 'additional_withholding',
            'exemptions', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InsuranceSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Insurance
    """
    insurance_type_display = serializers.CharField(source='get_insurance_type_display', read_only=True)
    
    class Meta:
        model = Insurance
        fields = [
            'id', 'employee', 'insurance_type', 'insurance_type_display',
            'provider', 'policy_number', 'coverage_start_date',
            'coverage_end_date', 'premium_amount', 'employee_contribution',
            'employer_contribution', 'beneficiaries', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmploymentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo EmploymentHistory
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    
    class Meta:
        model = EmploymentHistory
        fields = [
            'id', 'employee', 'department', 'department_name',
            'position', 'position_title', 'start_date', 'end_date',
            'salary', 'change_reason', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de empleados
    """
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_number', 'full_name', 'email',
            'department_name', 'position_title', 'status',
            'hire_date', 'profile_picture'
        ]
    
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para empleados (incluye información relacionada)
    """
    user = UserSerializer()
    department_details = DepartmentSerializer(source='department', read_only=True)
    position_details = PositionSerializer(source='position', read_only=True)
    manager_name = serializers.CharField(source='manager.user.get_full_name', read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    tax_info = TaxInformationSerializer(read_only=True)
    insurances = InsuranceSerializer(many=True, read_only=True)
    employment_history = EmploymentHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'employee_number', 'date_of_birth', 'gender',
            'marital_status', 'nationality', 'identification_type',
            'identification_number', 'personal_email', 'mobile_phone',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'address_line1',
            'address_line2', 'city', 'state', 'postal_code', 'country',
            'department', 'department_details', 'position', 'position_details',
            'manager', 'manager_name', 'hire_date', 'end_date',
            'employment_type', 'status', 'bank_accounts', 'tax_info',
            'insurances', 'employment_history', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = User.objects.create(**user_data)
        if 'password' in user_data:
            user.set_password(user_data['password'])
            user.save()
        
        employee = Employee.objects.create(user=user, **validated_data)
        return employee
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        
        if user_data:
            user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class EmployeeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear empleados
    """
    user = UserSerializer()
    
    class Meta:
        model = Employee
        fields = [
            'user', 'employee_number', 'date_of_birth', 'gender',
            'marital_status', 'nationality', 'identification_type',
            'identification_number', 'personal_email', 'mobile_phone',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'address_line1',
            'address_line2', 'city', 'state', 'postal_code', 'country',
            'department', 'position', 'manager', 'hire_date',
            'employment_type', 'status'
        ]
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password = user_data.pop('password', None)
        
        user = User.objects.create(**user_data)
        if password:
            user.set_password(password)
            user.save()
        
        employee = Employee.objects.create(user=user, **validated_data)
        return employee