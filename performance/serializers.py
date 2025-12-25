from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import (
    PerformanceReviewCycle, CompetencyCategory, Competency, PerformanceReview,
    CompetencyRating, Goal, GoalCheckIn, Feedback, DevelopmentPlan,
    DevelopmentAction, PerformanceImprovementPlan, PIPCheckIn
)
from employees.models import Employee


class PerformanceReviewCycleSerializer(serializers.ModelSerializer):
    """
    Serializer para ciclos de evaluación
    """
    review_type_display = serializers.CharField(source='get_review_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    is_active = serializers.ReadOnlyField()
    reviews_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PerformanceReviewCycle
        fields = [
            'id', 'name', 'description', 'review_type', 'review_type_display',
            'start_date', 'end_date', 'self_review_deadline', 'manager_review_deadline',
            'department', 'department_name', 'status', 'status_display',
            'enable_self_review', 'enable_peer_review', 'enable_360_review',
            'is_active', 'reviews_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_reviews_count(self, obj):
        return obj.reviews.count()
    
    def validate(self, data):
        """
        Validar fechas
        """
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio"
                )
        
        if data.get('self_review_deadline'):
            if data['self_review_deadline'] < data.get('start_date'):
                raise serializers.ValidationError(
                    "La fecha límite de auto-evaluación no puede ser anterior al inicio"
                )
            if data['self_review_deadline'] > data.get('end_date'):
                raise serializers.ValidationError(
                    "La fecha límite de auto-evaluación no puede ser posterior al fin"
                )
        
        if data.get('manager_review_deadline'):
            if data['manager_review_deadline'] < data.get('start_date'):
                raise serializers.ValidationError(
                    "La fecha límite de evaluación del manager no puede ser anterior al inicio"
                )
            if data['manager_review_deadline'] > data.get('end_date'):
                raise serializers.ValidationError(
                    "La fecha límite de evaluación del manager no puede ser posterior al fin"
                )
        
        return data


class CompetencyCategorySerializer(serializers.ModelSerializer):
    """
    Serializer para categorías de competencias
    """
    competencies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CompetencyCategory
        fields = [
            'id', 'name', 'description', 'order', 'is_active',
            'competencies_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_competencies_count(self, obj):
        return obj.competencies.filter(is_active=True).count()


class CompetencySerializer(serializers.ModelSerializer):
    """
    Serializer para competencias
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Competency
        fields = [
            'id', 'name', 'category', 'category_name', 'description',
            'level_1_description', 'level_2_description', 'level_3_description',
            'level_4_description', 'level_5_description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompetencyRatingSerializer(serializers.ModelSerializer):
    """
    Serializer para calificaciones de competencias
    """
    competency_name = serializers.CharField(source='competency.name', read_only=True)
    competency_category = serializers.CharField(source='competency.category.name', read_only=True)
    rating_type_display = serializers.CharField(source='get_rating_type_display', read_only=True)
    rated_by_name = serializers.CharField(source='rated_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = CompetencyRating
        fields = [
            'id', 'performance_review', 'competency', 'competency_name',
            'competency_category', 'rating_type', 'rating_type_display',
            'rating', 'comments', 'rated_by', 'rated_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_rating(self, value):
        """
        Validar que la calificación esté entre 1 y 5
        """
        if value < 1 or value > 5:
            raise serializers.ValidationError("La calificación debe estar entre 1 y 5")
        return value


class PerformanceReviewListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de evaluaciones
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    cycle_name = serializers.CharField(source='review_cycle.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    overall_rating_display = serializers.CharField(source='get_overall_rating_display', read_only=True)
    
    class Meta:
        model = PerformanceReview
        fields = [
            'id', 'review_cycle', 'cycle_name', 'employee', 'employee_name',
            'employee_number', 'reviewer', 'reviewer_name', 'status', 'status_display',
            'overall_rating', 'overall_rating_display', 'self_rating', 'manager_rating',
            'created_at', 'updated_at'
        ]


class PerformanceReviewDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para evaluaciones
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    employee_department = serializers.CharField(source='employee.department.name', read_only=True)
    cycle_name = serializers.CharField(source='review_cycle.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    overall_rating_display = serializers.CharField(source='get_overall_rating_display', read_only=True)
    competency_ratings = CompetencyRatingSerializer(many=True, read_only=True)
    
    class Meta:
        model = PerformanceReview
        fields = [
            'id', 'review_cycle', 'cycle_name', 'employee', 'employee_name',
            'employee_number', 'employee_department', 'reviewer', 'reviewer_name',
            'status', 'status_display', 'overall_rating', 'overall_rating_display',
            'self_rating', 'manager_rating', 'self_review_comments', 'manager_comments',
            'strengths', 'areas_for_improvement', 'achievements',
            'self_review_completed_at', 'manager_review_completed_at', 'approved_at',
            'competency_ratings', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GoalSerializer(serializers.ModelSerializer):
    """
    Serializer para metas
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    goal_type_display = serializers.CharField(source='get_goal_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    manager_name = serializers.CharField(source='manager.user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = Goal
        fields = [
            'id', 'employee', 'employee_name', 'employee_number', 'title',
            'description', 'goal_type', 'goal_type_display', 'priority', 'priority_display',
            'start_date', 'target_date', 'completed_date', 'status', 'status_display',
            'progress_percentage', 'is_measurable', 'target_value', 'current_value',
            'unit_of_measure', 'manager', 'manager_name', 'approved_by',
            'approved_by_name', 'approved_at', 'performance_review',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'completed_date', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validar fechas y valores medibles
        """
        if data.get('target_date') and data.get('start_date'):
            if data['target_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "La fecha objetivo no puede ser anterior a la fecha de inicio"
                )
        
        if data.get('is_measurable'):
            if not data.get('target_value'):
                raise serializers.ValidationError(
                    "Se requiere un valor objetivo para metas medibles"
                )
            if not data.get('unit_of_measure'):
                raise serializers.ValidationError(
                    "Se requiere una unidad de medida para metas medibles"
                )
        
        return data


class GoalCheckInSerializer(serializers.ModelSerializer):
    """
    Serializer para check-ins de metas
    """
    goal_title = serializers.CharField(source='goal.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = GoalCheckIn
        fields = [
            'id', 'goal', 'goal_title', 'progress_percentage', 'current_value',
            'notes', 'challenges', 'support_needed', 'created_by', 'created_by_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer para retroalimentación
    """
    from_employee_name = serializers.CharField(source='from_employee.user.get_full_name', read_only=True)
    to_employee_name = serializers.CharField(source='to_employee.user.get_full_name', read_only=True)
    feedback_type_display = serializers.CharField(source='get_feedback_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'from_employee', 'from_employee_name', 'to_employee', 'to_employee_name',
            'feedback_type', 'feedback_type_display', 'subject', 'content',
            'is_anonymous', 'is_private', 'status', 'status_display',
            'acknowledged_at', 'performance_review', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'acknowledged_at', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """
        Ocultar from_employee si es anónimo
        """
        representation = super().to_representation(instance)
        
        if instance.is_anonymous:
            representation['from_employee'] = None
            representation['from_employee_name'] = 'Anónimo'
        
        return representation


class DevelopmentActionSerializer(serializers.ModelSerializer):
    """
    Serializer para acciones de desarrollo
    """
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DevelopmentAction
        fields = [
            'id', 'development_plan', 'title', 'description', 'action_type',
            'action_type_display', 'target_date', 'completed_date', 'status',
            'status_display', 'resources_needed', 'estimated_cost', 'outcome',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DevelopmentPlanSerializer(serializers.ModelSerializer):
    """
    Serializer para planes de desarrollo
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    manager_name = serializers.CharField(source='manager.user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    actions = DevelopmentActionSerializer(many=True, read_only=True)
    
    class Meta:
        model = DevelopmentPlan
        fields = [
            'id', 'employee', 'employee_name', 'employee_number', 'title',
            'description', 'start_date', 'end_date', 'status', 'status_display',
            'manager', 'manager_name', 'approved_by', 'approved_by_name',
            'approved_at', 'performance_review', 'actions', 'created_at', 'updated_at'
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
        
        return data


class PIPCheckInSerializer(serializers.ModelSerializer):
    """
    Serializer para check-ins de PIP
    """
    conducted_by_name = serializers.CharField(source='conducted_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = PIPCheckIn
        fields = [
            'id', 'improvement_plan', 'check_in_date', 'progress_summary',
            'areas_of_improvement', 'areas_of_concern', 'next_steps',
            'is_on_track', 'conducted_by', 'conducted_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PerformanceImprovementPlanSerializer(serializers.ModelSerializer):
    """
    Serializer para planes de mejora de desempeño
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    manager_name = serializers.CharField(source='manager.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    check_ins = PIPCheckInSerializer(many=True, read_only=True)
    
    class Meta:
        model = PerformanceImprovementPlan
        fields = [
            'id', 'employee', 'employee_name', 'employee_number', 'manager',
            'manager_name', 'title', 'performance_issues', 'expected_improvements',
            'support_provided', 'consequences', 'start_date', 'end_date',
            'review_frequency_days', 'status', 'status_display', 'final_outcome',
            'performance_review', 'check_ins', 'created_at', 'updated_at'
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
        
        return data


class SelfReviewSubmitSerializer(serializers.Serializer):
    """
    Serializer para enviar auto-evaluación
    """
    self_rating = serializers.IntegerField(min_value=1, max_value=5)
    self_review_comments = serializers.CharField()
    achievements = serializers.CharField(required=False, allow_blank=True)
    competency_ratings = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class ManagerReviewSubmitSerializer(serializers.Serializer):
    """
    Serializer para enviar evaluación del manager
    """
    manager_rating = serializers.IntegerField(min_value=1, max_value=5)
    manager_comments = serializers.CharField()
    strengths = serializers.CharField(required=False, allow_blank=True)
    areas_for_improvement = serializers.CharField(required=False, allow_blank=True)
    overall_rating = serializers.IntegerField(min_value=1, max_value=5)
    competency_ratings = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class GoalUpdateProgressSerializer(serializers.Serializer):
    """
    Serializer para actualizar progreso de meta
    """
    progress_percentage = serializers.IntegerField(min_value=0, max_value=100)
    current_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    notes = serializers.CharField()
    challenges = serializers.CharField(required=False, allow_blank=True)
    support_needed = serializers.CharField(required=False, allow_blank=True)


class PerformanceMetricsSerializer(serializers.Serializer):
    """
    Serializer para métricas de desempeño
    """
    total_reviews = serializers.IntegerField()
    completed_reviews = serializers.IntegerField()
    pending_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    ratings_distribution = serializers.DictField()
    total_goals = serializers.IntegerField()
    completed_goals = serializers.IntegerField()
    goals_by_status = serializers.DictField()
    average_goal_completion = serializers.FloatField()