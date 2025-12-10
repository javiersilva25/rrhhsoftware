from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import (
    JobPosting, Candidate, Application, RecruitmentStage, Interview,
    Assessment, JobOffer, OnboardingTask, RecruitmentReport
)
from employees.models import Employee, Department, Position


class JobPostingListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de vacantes
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    applications_count = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = JobPosting
        fields = [
            'id', 'title', 'job_code', 'department', 'department_name',
            'position', 'position_title', 'employment_type', 'employment_type_display',
            'location', 'remote_option', 'status', 'status_display',
            'posted_date', 'application_deadline', 'number_of_positions',
            'applications_count', 'is_active', 'created_at'
        ]


class JobPostingDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para vacantes
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    position_title = serializers.CharField(source='position.title', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    experience_level_display = serializers.CharField(source='get_experience_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    hiring_manager_name = serializers.CharField(source='hiring_manager.user.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    applications_count = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = JobPosting
        fields = [
            'id', 'title', 'job_code', 'department', 'department_name',
            'position', 'position_title', 'employment_type', 'employment_type_display',
            'experience_level', 'experience_level_display', 'location', 'remote_option',
            'description', 'responsibilities', 'requirements', 'preferred_qualifications',
            'benefits', 'min_salary', 'max_salary', 'salary_currency', 'show_salary',
            'number_of_positions', 'posted_date', 'application_deadline',
            'status', 'status_display', 'hiring_manager', 'hiring_manager_name',
            'views_count', 'applications_count', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'views_count', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validar fechas y salarios
        """
        if data.get('application_deadline') and data.get('posted_date'):
            if data['application_deadline'] < data['posted_date']:
                raise serializers.ValidationError(
                    "La fecha límite no puede ser anterior a la fecha de publicación"
                )
        
        if data.get('max_salary') and data.get('min_salary'):
            if data['max_salary'] < data['min_salary']:
                raise serializers.ValidationError(
                    "El salario máximo no puede ser menor al salario mínimo"
                )
        
        return data


class CandidateSerializer(serializers.ModelSerializer):
    """
    Serializer para candidatos
    """
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    referred_by_name = serializers.CharField(source='referred_by.user.get_full_name', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'address', 'city', 'country', 'current_position', 'current_company',
            'years_of_experience', 'education_level', 'resume', 'cover_letter',
            'portfolio_url', 'linkedin_url', 'expected_salary', 'salary_currency',
            'available_from', 'notice_period_days', 'source', 'source_display',
            'referred_by', 'referred_by_name', 'notes', 'skills',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_email(self, value):
        """
        Validar que el email sea único (excepto para actualización)
        """
        instance_id = self.instance.id if self.instance else None
        
        existing = Candidate.objects.filter(email=value)
        if instance_id:
            existing = existing.exclude(id=instance_id)
        
        if existing.exists():
            raise serializers.ValidationError(
                "Ya existe un candidato con este email"
            )
        
        return value


class RecruitmentStageSerializer(serializers.ModelSerializer):
    """
    Serializer para etapas de reclutamiento
    """
    job_posting_title = serializers.CharField(source='job_posting.title', read_only=True)
    
    class Meta:
        model = RecruitmentStage
        fields = [
            'id', 'name', 'description', 'order', 'job_posting',
            'job_posting_title', 'duration_days', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApplicationListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de solicitudes
    """
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    job_title = serializers.CharField(source='job_posting.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_stage_name = serializers.CharField(source='current_stage.name', read_only=True)
    assigned_recruiter_name = serializers.CharField(source='assigned_recruiter.user.get_full_name', read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'candidate', 'candidate_name', 'candidate_email',
            'job_posting', 'job_title', 'status', 'status_display',
            'current_stage', 'current_stage_name', 'rating',
            'assigned_recruiter', 'assigned_recruiter_name',
            'applied_date', 'status_changed_at'
        ]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para solicitudes
    """
    candidate_details = CandidateSerializer(source='candidate', read_only=True)
    job_posting_details = JobPostingListSerializer(source='job_posting', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_stage_details = RecruitmentStageSerializer(source='current_stage', read_only=True)
    assigned_recruiter_name = serializers.CharField(source='assigned_recruiter.user.get_full_name', read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'candidate', 'candidate_details', 'job_posting', 'job_posting_details',
            'status', 'status_display', 'current_stage', 'current_stage_details',
            'rating', 'applied_date', 'status_changed_at',
            'assigned_recruiter', 'assigned_recruiter_name', 'notes',
            'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'applied_date', 'status_changed_at', 'created_at', 'updated_at']


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear solicitudes
    """
    class Meta:
        model = Application
        fields = ['candidate', 'job_posting', 'assigned_recruiter', 'notes']
    
    def validate(self, data):
        """
        Validar que no exista ya una solicitud del mismo candidato para la misma vacante
        """
        candidate = data.get('candidate')
        job_posting = data.get('job_posting')
        
        if Application.objects.filter(candidate=candidate, job_posting=job_posting).exists():
            raise serializers.ValidationError(
                "Este candidato ya ha aplicado para esta vacante"
            )
        
        return data


class InterviewSerializer(serializers.ModelSerializer):
    """
    Serializer para entrevistas
    """
    candidate_name = serializers.CharField(source='application.candidate.get_full_name', read_only=True)
    job_title = serializers.CharField(source='application.job_posting.title', read_only=True)
    interview_type_display = serializers.CharField(source='get_interview_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    interviewers_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Interview
        fields = [
            'id', 'application', 'candidate_name', 'job_title',
            'interview_type', 'interview_type_display', 'scheduled_date',
            'scheduled_time', 'duration_minutes', 'location', 'meeting_link',
            'interviewers', 'interviewers_names', 'status', 'status_display',
            'result', 'result_display', 'notes', 'candidate_strengths',
            'candidate_weaknesses', 'overall_rating', 'recommendation',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_interviewers_names(self, obj):
        return [interviewer.user.get_full_name() for interviewer in obj.interviewers.all()]


class AssessmentSerializer(serializers.ModelSerializer):
    """
    Serializer para evaluaciones
    """
    candidate_name = serializers.CharField(source='application.candidate.get_full_name', read_only=True)
    job_title = serializers.CharField(source='application.job_posting.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    evaluator_name = serializers.CharField(source='evaluator.user.get_full_name', read_only=True)
    is_passed = serializers.ReadOnlyField()
    
    class Meta:
        model = Assessment
        fields = [
            'id', 'application', 'candidate_name', 'job_title',
            'title', 'description', 'assessment_type', 'assessment_file',
            'submission_file', 'assessment_url', 'sent_date', 'due_date',
            'submitted_date', 'max_score', 'obtained_score', 'passing_score',
            'status', 'status_display', 'evaluator', 'evaluator_name',
            'feedback', 'is_passed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sent_date', 'created_at', 'updated_at']


class JobOfferSerializer(serializers.ModelSerializer):
    """
    Serializer para ofertas de trabajo
    """
    candidate_name = serializers.CharField(source='application.candidate.get_full_name', read_only=True)
    job_title = serializers.CharField(source='application.job_posting.title', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = JobOffer
        fields = [
            'id', 'application', 'candidate_name', 'job_title',
            'position_title', 'department', 'department_name',
            'salary', 'salary_currency', 'bonus', 'offer_date',
            'expiry_date', 'proposed_start_date', 'offer_letter',
            'status', 'status_display', 'candidate_response_date',
            'candidate_notes', 'approved_by', 'approved_by_name',
            'approved_at', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validar fechas
        """
        if data.get('expiry_date') and data.get('offer_date'):
            if data['expiry_date'] < data['offer_date']:
                raise serializers.ValidationError(
                    "La fecha de expiración no puede ser anterior a la fecha de oferta"
                )
        
        if data.get('proposed_start_date') and data.get('offer_date'):
            if data['proposed_start_date'] < data['offer_date']:
                raise serializers.ValidationError(
                    "La fecha de inicio propuesta no puede ser anterior a la fecha de oferta"
                )
        
        return data


class OnboardingTaskSerializer(serializers.ModelSerializer):
    """
    Serializer para tareas de onboarding
    """
    candidate_name = serializers.CharField(source='job_offer.application.candidate.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = OnboardingTask
        fields = [
            'id', 'title', 'description', 'category', 'order',
            'job_offer', 'candidate_name', 'assigned_to', 'assigned_to_name',
            'status', 'status_display', 'due_date', 'completed_date',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentReportSerializer(serializers.ModelSerializer):
    """
    Serializer para reportes de reclutamiento
    """
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    job_posting_title = serializers.CharField(source='job_posting.title', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = RecruitmentReport
        fields = [
            'id', 'name', 'report_type', 'report_type_display',
            'start_date', 'end_date', 'department', 'department_name',
            'job_posting', 'job_posting_title', 'file', 'summary_data',
            'generated_by', 'generated_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ApplicationStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar estado de solicitud
    """
    status = serializers.ChoiceField(choices=Application.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class ApplicationRatingSerializer(serializers.Serializer):
    """
    Serializer para calificar solicitud
    """
    rating = serializers.IntegerField(min_value=1, max_value=5)
    notes = serializers.CharField(required=False, allow_blank=True)


class InterviewScheduleSerializer(serializers.Serializer):
    """
    Serializer para programar entrevista
    """
    interview_type = serializers.ChoiceField(choices=Interview.INTERVIEW_TYPE_CHOICES)
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField()
    duration_minutes = serializers.IntegerField(default=60)
    location = serializers.CharField(required=False, allow_blank=True)
    meeting_link = serializers.URLField(required=False, allow_blank=True)
    interviewers = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all()),
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class InterviewFeedbackSerializer(serializers.Serializer):
    """
    Serializer para feedback de entrevista
    """
    status = serializers.ChoiceField(choices=Interview.STATUS_CHOICES)
    result = serializers.ChoiceField(choices=Interview.RESULT_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    candidate_strengths = serializers.CharField(required=False, allow_blank=True)
    candidate_weaknesses = serializers.CharField(required=False, allow_blank=True)
    overall_rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    recommendation = serializers.CharField(required=False, allow_blank=True)


class AssessmentGradeSerializer(serializers.Serializer):
    """
    Serializer para calificar evaluación
    """
    obtained_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)


class JobOfferAcceptSerializer(serializers.Serializer):
    """
    Serializer para aceptar oferta
    """
    notes = serializers.CharField(required=False, allow_blank=True)


class JobOfferRejectSerializer(serializers.Serializer):
    """
    Serializer para rechazar oferta
    """
    reason = serializers.CharField(required=True)


class RecruitmentMetricsSerializer(serializers.Serializer):
    """
    Serializer para métricas de reclutamiento
    """
    total_postings = serializers.IntegerField()
    active_postings = serializers.IntegerField()
    total_applications = serializers.IntegerField()
    applications_by_status = serializers.DictField()
    average_time_to_hire = serializers.FloatField()
    applications_by_source = serializers.DictField()
    conversion_rates = serializers.DictField()