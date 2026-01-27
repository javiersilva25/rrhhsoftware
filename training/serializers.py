from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import (
    TrainingCategory, TrainingProvider, Course, TrainingSession,
    TrainingEnrollment, TrainingAttendance, TrainingAssessment,
    Certification, TrainingBudget, TrainingRequest, TrainingFeedback
)
from employees.models import Employee


class TrainingCategorySerializer(serializers.ModelSerializer):
    """
    Serializer para categorías de capacitación
    """
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingCategory
        fields = [
            'id', 'name', 'code', 'description', 'icon', 'color',
            'is_active', 'courses_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_courses_count(self, obj):
        return obj.courses.filter(is_active=True).count()


class TrainingProviderSerializer(serializers.ModelSerializer):
    """
    Serializer para proveedores de capacitación
    """
    provider_type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingProvider
        fields = [
            'id', 'name', 'provider_type', 'provider_type_display',
            'contact_name', 'contact_email', 'contact_phone', 'website',
            'address', 'description', 'is_active', 'courses_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_courses_count(self, obj):
        return obj.courses.filter(is_active=True).count()


class CourseListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de cursos
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    delivery_method_display = serializers.CharField(source='get_delivery_method_display', read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'code', 'category', 'category_name',
            'provider', 'provider_name', 'level', 'level_display',
            'duration_hours', 'delivery_method', 'delivery_method_display',
            'cost_per_person', 'currency', 'provides_certificate',
            'is_active', 'created_at'
        ]


class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para cursos
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    provider_details = TrainingProviderSerializer(source='provider', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    delivery_method_display = serializers.CharField(source='get_delivery_method_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    sessions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'code', 'category', 'category_name',
            'provider', 'provider_details', 'description', 'objectives',
            'prerequisites', 'level', 'level_display', 'duration_hours',
            'delivery_method', 'delivery_method_display', 'cost_per_person',
            'currency', 'max_participants', 'syllabus', 'materials_url',
            'provides_certificate', 'certificate_validity_days', 'is_active',
            'sessions_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_sessions_count(self, obj):
        return obj.sessions.count()


class TrainingSessionListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de sesiones
    """
    course_title = serializers.CharField(source='course.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    instructor_name = serializers.CharField(source='instructor.user.get_full_name', read_only=True)
    available_spots = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    enrollments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingSession
        fields = [
            'id', 'course', 'course_title', 'session_name', 'start_date',
            'end_date', 'registration_deadline', 'location', 'instructor',
            'instructor_name', 'external_instructor_name', 'max_participants',
            'available_spots', 'is_full', 'enrollments_count', 'status',
            'status_display', 'created_at'
        ]
    
    def get_enrollments_count(self, obj):
        return obj.enrollments.filter(status='enrolled').count()


class TrainingSessionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para sesiones
    """
    course_details = CourseListSerializer(source='course', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    instructor_name = serializers.CharField(source='instructor.user.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    available_spots = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    
    class Meta:
        model = TrainingSession
        fields = [
            'id', 'course', 'course_details', 'session_name', 'start_date',
            'end_date', 'registration_deadline', 'location', 'venue_details',
            'instructor', 'instructor_name', 'external_instructor_name',
            'external_instructor_bio', 'max_participants', 'min_participants',
            'available_spots', 'is_full', 'status', 'status_display',
            'total_cost', 'budget_code', 'notes', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validar fechas
        """
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio"
                )
        
        if data.get('registration_deadline') and data.get('start_date'):
            if data['registration_deadline'] > data['start_date']:
                raise serializers.ValidationError(
                    "La fecha límite de registro debe ser antes del inicio de la sesión"
                )
        
        if data.get('max_participants') and data.get('min_participants'):
            if data['max_participants'] < data['min_participants']:
                raise serializers.ValidationError(
                    "El máximo de participantes no puede ser menor al mínimo"
                )
        
        return data


class TrainingEnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializer para inscripciones a capacitación
    """
    session_name = serializers.CharField(source='session.session_name', read_only=True)
    course_title = serializers.CharField(source='session.course.title', read_only=True)
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    has_passed = serializers.ReadOnlyField()
    
    class Meta:
        model = TrainingEnrollment
        fields = [
            'id', 'session', 'session_name', 'course_title', 'employee',
            'employee_name', 'employee_number', 'status', 'status_display',
            'requires_manager_approval', 'approved_by', 'approved_by_name',
            'approved_at', 'rejection_reason', 'attendance_percentage',
            'pre_assessment_score', 'post_assessment_score', 'final_score',
            'passing_score', 'has_passed', 'participant_feedback',
            'instructor_feedback', 'certificate_issued', 'certificate_issue_date',
            'certificate_expiry_date', 'certificate_file', 'enrolled_at',
            'completed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrolled_at', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validar inscripción
        """
        session = data.get('session')
        employee = data.get('employee')
        
        # Verificar si ya existe inscripción
        instance_id = self.instance.id if self.instance else None
        existing = TrainingEnrollment.objects.filter(session=session, employee=employee)
        
        if instance_id:
            existing = existing.exclude(id=instance_id)
        
        if existing.exists():
            raise serializers.ValidationError(
                "El empleado ya está inscrito en esta sesión"
            )
        
        # Verificar disponibilidad
        if not self.instance and session.is_full:
            raise serializers.ValidationError(
                "Esta sesión ya está llena"
            )
        
        # Verificar fecha límite de registro
        if session.registration_deadline and timezone.now().date() > session.registration_deadline:
            raise serializers.ValidationError(
                "La fecha límite de registro ha pasado"
            )
        
        return data


class TrainingAttendanceSerializer(serializers.ModelSerializer):
    """
    Serializer para asistencia a capacitación
    """
    employee_name = serializers.CharField(source='enrollment.employee.user.get_full_name', read_only=True)
    session_name = serializers.CharField(source='enrollment.session.session_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = TrainingAttendance
        fields = [
            'id', 'enrollment', 'employee_name', 'session_name', 'session_date',
            'session_topic', 'status', 'status_display', 'check_in_time',
            'check_out_time', 'notes', 'recorded_by', 'recorded_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingAssessmentSerializer(serializers.ModelSerializer):
    """
    Serializer para evaluaciones de capacitación
    """
    employee_name = serializers.CharField(source='enrollment.employee.user.get_full_name', read_only=True)
    session_name = serializers.CharField(source='enrollment.session.session_name', read_only=True)
    assessment_type_display = serializers.CharField(source='get_assessment_type_display', read_only=True)
    graded_by_name = serializers.CharField(source='graded_by.user.get_full_name', read_only=True)
    has_passed = serializers.ReadOnlyField()
    
    class Meta:
        model = TrainingAssessment
        fields = [
            'id', 'enrollment', 'employee_name', 'session_name',
            'assessment_type', 'assessment_type_display', 'title',
            'description', 'max_score', 'obtained_score', 'passing_score',
            'has_passed', 'assigned_date', 'due_date', 'submitted_date',
            'graded_date', 'assessment_file', 'submission_file', 'feedback',
            'graded_by', 'graded_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CertificationSerializer(serializers.ModelSerializer):
    """
    Serializer para certificaciones
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    course_title = serializers.CharField(source='enrollment.session.course.title', read_only=True)
    
    class Meta:
        model = Certification
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'enrollment', 'course_title', 'certification_name',
            'certification_number', 'issuing_organization', 'issue_date',
            'expiry_date', 'status', 'status_display', 'certificate_file',
            'verification_url', 'description', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingBudgetSerializer(serializers.ModelSerializer):
    """
    Serializer para presupuestos de capacitación
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    remaining_budget = serializers.ReadOnlyField()
    utilization_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = TrainingBudget
        fields = [
            'id', 'year', 'department', 'department_name', 'allocated_budget',
            'spent_amount', 'remaining_budget', 'utilization_percentage',
            'currency', 'notes', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingRequestSerializer(serializers.ModelSerializer):
    """
    Serializer para solicitudes de capacitación
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.user.get_full_name', read_only=True)
    assigned_session_name = serializers.CharField(source='assigned_session.session_name', read_only=True)
    
    class Meta:
        model = TrainingRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'course', 'course_title', 'training_title', 'justification',
            'expected_benefits', 'preferred_start_date', 'preferred_end_date',
            'estimated_cost', 'status', 'status_display', 'reviewed_by',
            'reviewed_by_name', 'reviewed_at', 'review_notes',
            'assigned_session', 'assigned_session_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer para retroalimentación de capacitación
    """
    employee_name = serializers.CharField(source='enrollment.employee.user.get_full_name', read_only=True)
    session_name = serializers.CharField(source='enrollment.session.session_name', read_only=True)
    average_rating = serializers.ReadOnlyField()
    
    class Meta:
        model = TrainingFeedback
        fields = [
            'id', 'enrollment', 'employee_name', 'session_name',
            'content_quality', 'instructor_effectiveness', 'materials_quality',
            'relevance_to_job', 'overall_satisfaction', 'average_rating',
            'strengths', 'improvements', 'additional_comments',
            'would_recommend', 'submitted_at'
        ]
        read_only_fields = ['id', 'submitted_at']
    
    def validate(self, data):
        """
        Validar calificaciones
        """
        for field in ['content_quality', 'instructor_effectiveness', 'materials_quality',
                     'relevance_to_job', 'overall_satisfaction']:
            value = data.get(field)
            if value and (value < 1 or value > 5):
                raise serializers.ValidationError(
                    f"{field} debe estar entre 1 y 5"
                )
        
        return data


class EnrollmentApprovalSerializer(serializers.Serializer):
    """
    Serializer para aprobar/rechazar inscripciones
    """
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)


class EnrollmentCompleteSerializer(serializers.Serializer):
    """
    Serializer para completar inscripción
    """
    final_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    instructor_feedback = serializers.CharField(required=False, allow_blank=True)
    issue_certificate = serializers.BooleanField(default=False)


class BulkEnrollmentSerializer(serializers.Serializer):
    """
    Serializer para inscripciones en lote
    """
    session = serializers.PrimaryKeyRelatedField(queryset=TrainingSession.objects.all())
    employee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='Lista de IDs de empleados'
    )


class TrainingStatisticsSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de capacitación
    """
    total_courses = serializers.IntegerField()
    active_sessions = serializers.IntegerField()
    total_enrollments = serializers.IntegerField()
    completed_enrollments = serializers.IntegerField()
    average_completion_rate = serializers.FloatField()
    average_satisfaction = serializers.FloatField()
    total_training_hours = serializers.FloatField()
    certifications_issued = serializers.IntegerField()
    by_category = serializers.DictField()
    by_department = serializers.DictField()
    budget_utilization = serializers.DictField()


class SessionEnrollSerializer(serializers.Serializer):
    """
    Serializer para inscribirse a una sesión
    """
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    notes = serializers.CharField(required=False, allow_blank=True)