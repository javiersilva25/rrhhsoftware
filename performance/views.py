from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta

from .models import (
    PerformanceReviewCycle, CompetencyCategory, Competency, PerformanceReview,
    CompetencyRating, Goal, GoalCheckIn, Feedback, DevelopmentPlan,
    DevelopmentAction, PerformanceImprovementPlan, PIPCheckIn
)
from .serializers import (
    PerformanceReviewCycleSerializer, CompetencyCategorySerializer, CompetencySerializer,
    PerformanceReviewListSerializer, PerformanceReviewDetailSerializer,
    CompetencyRatingSerializer, GoalSerializer, GoalCheckInSerializer,
    FeedbackSerializer, DevelopmentPlanSerializer, DevelopmentActionSerializer,
    PerformanceImprovementPlanSerializer, PIPCheckInSerializer,
    SelfReviewSubmitSerializer, ManagerReviewSubmitSerializer,
    GoalUpdateProgressSerializer, PerformanceMetricsSerializer
)
from employees.models import Employee


class PerformanceReviewCycleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar ciclos de evaluación
    """
    queryset = PerformanceReviewCycle.objects.select_related(
        'department', 'created_by__user'
    ).prefetch_related('reviews').all()
    serializer_class = PerformanceReviewCycleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['review_type', 'status', 'department']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activar ciclo de evaluación
        """
        cycle = self.get_object()
        
        if cycle.status != 'draft':
            return Response(
                {'error': 'Solo se pueden activar ciclos en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cycle.status = 'active'
        cycle.save()
        
        serializer = self.get_serializer(cycle)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Completar ciclo de evaluación
        """
        cycle = self.get_object()
        
        if cycle.status != 'active':
            return Response(
                {'error': 'Solo se pueden completar ciclos activos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que todas las evaluaciones estén completadas
        pending_reviews = cycle.reviews.exclude(status='completed').count()
        if pending_reviews > 0:
            return Response(
                {'error': f'Hay {pending_reviews} evaluaciones pendientes de completar'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cycle.status = 'completed'
        cycle.save()
        
        serializer = self.get_serializer(cycle)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def generate_reviews(self, request, pk=None):
        """
        Generar evaluaciones para todos los empleados elegibles
        """
        cycle = self.get_object()
        
        if cycle.status != 'active':
            return Response(
                {'error': 'Solo se pueden generar evaluaciones en ciclos activos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Filtrar empleados
        employees = Employee.objects.filter(status='active')
        
        if cycle.department:
            employees = employees.filter(department=cycle.department)
        
        created_count = 0
        errors = []
        
        for employee in employees:
            # Verificar si ya existe una evaluación
            if PerformanceReview.objects.filter(
                review_cycle=cycle,
                employee=employee
            ).exists():
                continue
            
            try:
                # Crear evaluación
                PerformanceReview.objects.create(
                    review_cycle=cycle,
                    employee=employee,
                    reviewer=employee.manager,
                    status='pending'
                )
                created_count += 1
            except Exception as e:
                errors.append({
                    'employee': employee.user.get_full_name(),
                    'error': str(e)
                })
        
        return Response({
            'message': f'Se crearon {created_count} evaluaciones',
            'created': created_count,
            'errors': errors
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Obtener estadísticas del ciclo
        """
        cycle = self.get_object()
        reviews = cycle.reviews.all()
        
        total_reviews = reviews.count()
        completed_reviews = reviews.filter(status='completed').count()
        pending_reviews = reviews.filter(status='pending').count()
        
        reviews_by_status = {}
        for status_choice in PerformanceReview.STATUS_CHOICES:
            count = reviews.filter(status=status_choice[0]).count()
            if count > 0:
                reviews_by_status[status_choice[1]] = count
        
        average_rating = reviews.filter(
            overall_rating__isnull=False
        ).aggregate(Avg('overall_rating'))['overall_rating__avg']
        
        return Response({
            'total_reviews': total_reviews,
            'completed_reviews': completed_reviews,
            'pending_reviews': pending_reviews,
            'reviews_by_status': reviews_by_status,
            'average_rating': round(average_rating, 2) if average_rating else None,
            'completion_rate': round((completed_reviews / total_reviews * 100), 2) if total_reviews > 0 else 0
        })
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Obtener ciclos activos
        """
        cycles = self.queryset.filter(status='active')
        serializer = self.get_serializer(cycles, many=True)
        return Response(serializer.data)


class CompetencyCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de competencias
    """
    queryset = CompetencyCategory.objects.prefetch_related('competencies').all()
    serializer_class = CompetencyCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    ordering = ['order']


class CompetencyViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar competencias
    """
    queryset = Competency.objects.select_related('category').all()
    serializer_class = CompetencySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['category__order', 'name', 'created_at']
    ordering = ['category__order', 'name']


class PerformanceReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar evaluaciones de desempeño
    """
    queryset = PerformanceReview.objects.select_related(
        'employee__user', 'employee__department', 'review_cycle',
        'reviewer__user'
    ).prefetch_related('competency_ratings__competency').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'review_cycle', 'reviewer', 'status', 'overall_rating']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_number']
    ordering_fields = ['created_at', 'overall_rating']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PerformanceReviewListSerializer
        return PerformanceReviewDetailSerializer
    
    @action(detail=True, methods=['post'])
    def submit_self_review(self, request, pk=None):
        """
        Enviar auto-evaluación
        """
        review = self.get_object()
        
        if review.status not in ['pending', 'self_review']:
            return Response(
                {'error': 'Esta evaluación no está disponible para auto-evaluación'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SelfReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        review.self_rating = serializer.validated_data['self_rating']
        review.self_review_comments = serializer.validated_data['self_review_comments']
        review.achievements = serializer.validated_data.get('achievements', '')
        review.self_review_completed_at = timezone.now()
        review.status = 'manager_review'
        review.save()
        
        # Guardar calificaciones de competencias
        competency_ratings = serializer.validated_data.get('competency_ratings', [])
        for rating_data in competency_ratings:
            CompetencyRating.objects.create(
                performance_review=review,
                competency_id=rating_data['competency_id'],
                rating_type='self',
                rating=rating_data['rating'],
                comments=rating_data.get('comments', ''),
                rated_by=request.user.employee_profile
            )
        
        response_serializer = PerformanceReviewDetailSerializer(review)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit_manager_review(self, request, pk=None):
        """
        Enviar evaluación del manager
        """
        review = self.get_object()
        
        if review.status not in ['manager_review', 'peer_review']:
            return Response(
                {'error': 'Esta evaluación no está disponible para evaluación del manager'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ManagerReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        review.manager_rating = serializer.validated_data['manager_rating']
        review.manager_comments = serializer.validated_data['manager_comments']
        review.strengths = serializer.validated_data.get('strengths', '')
        review.areas_for_improvement = serializer.validated_data.get('areas_for_improvement', '')
        review.overall_rating = serializer.validated_data['overall_rating']
        review.manager_review_completed_at = timezone.now()
        review.status = 'completed'
        review.save()
        
        # Guardar calificaciones de competencias
        competency_ratings = serializer.validated_data.get('competency_ratings', [])
        for rating_data in competency_ratings:
            CompetencyRating.objects.create(
                performance_review=review,
                competency_id=rating_data['competency_id'],
                rating_type='manager',
                rating=rating_data['rating'],
                comments=rating_data.get('comments', ''),
                rated_by=request.user.employee_profile
            )
        
        response_serializer = PerformanceReviewDetailSerializer(review)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar evaluación
        """
        review = self.get_object()
        
        if review.status != 'completed':
            return Response(
                {'error': 'Solo se pueden aprobar evaluaciones completadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        review.status = 'approved'
        review.approved_at = timezone.now()
        review.save()
        
        serializer = PerformanceReviewDetailSerializer(review)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """
        Obtener evaluaciones del usuario actual
        """
        employee = request.user.employee_profile
        reviews = self.queryset.filter(employee=employee)
        
        serializer = PerformanceReviewListSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_reviews(self, request):
        """
        Obtener evaluaciones pendientes (como evaluador)
        """
        employee = request.user.employee_profile
        reviews = self.queryset.filter(
            reviewer=employee,
            status__in=['manager_review', 'peer_review']
        )
        
        serializer = PerformanceReviewListSerializer(reviews, many=True)
        return Response(serializer.data)


class CompetencyRatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar calificaciones de competencias
    """
    queryset = CompetencyRating.objects.select_related(
        'performance_review__employee__user', 'competency__category',
        'rated_by__user'
    ).all()
    serializer_class = CompetencyRatingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['performance_review', 'competency', 'rating_type', 'rating']


class GoalViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar metas
    """
    queryset = Goal.objects.select_related(
        'employee__user', 'manager__user', 'approved_by__user',
        'performance_review'
    ).prefetch_related('check_ins').all()
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'goal_type', 'priority', 'status', 'manager']
    search_fields = ['title', 'description']
    ordering_fields = ['priority', 'target_date', 'progress_percentage', 'created_at']
    ordering = ['-priority', 'target_date']
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """
        Actualizar progreso de meta
        """
        goal = self.get_object()
        
        serializer = GoalUpdateProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Crear check-in
        check_in = GoalCheckIn.objects.create(
            goal=goal,
            progress_percentage=serializer.validated_data['progress_percentage'],
            current_value=serializer.validated_data.get('current_value'),
            notes=serializer.validated_data['notes'],
            challenges=serializer.validated_data.get('challenges', ''),
            support_needed=serializer.validated_data.get('support_needed', ''),
            created_by=request.user.employee_profile
        )
        
        # Actualizar meta
        goal.progress_percentage = serializer.validated_data['progress_percentage']
        if serializer.validated_data.get('current_value'):
            goal.current_value = serializer.validated_data['current_value']
        goal.update_status()
        
        response_serializer = GoalSerializer(goal)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar meta
        """
        goal = self.get_object()
        
        if goal.status != 'draft':
            return Response(
                {'error': 'Solo se pueden aprobar metas en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        goal.status = 'active'
        goal.approved_by = request.user.employee_profile
        goal.approved_at = timezone.now()
        goal.save()
        
        serializer = self.get_serializer(goal)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Completar meta
        """
        goal = self.get_object()
        
        goal.progress_percentage = 100
        goal.completed_date = timezone.now().date()
        goal.update_status()
        
        serializer = self.get_serializer(goal)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_goals(self, request):
        """
        Obtener metas del usuario actual
        """
        employee = request.user.employee_profile
        goals = self.queryset.filter(employee=employee)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            goals = goals.filter(status=status_filter)
        
        serializer = self.get_serializer(goals, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def team_goals(self, request):
        """
        Obtener metas del equipo (subordinados)
        """
        employee = request.user.employee_profile
        goals = self.queryset.filter(manager=employee)
        
        serializer = self.get_serializer(goals, many=True)
        return Response(serializer.data)


class GoalCheckInViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar check-ins de metas
    """
    queryset = GoalCheckIn.objects.select_related(
        'goal__employee__user', 'created_by__user'
    ).all()
    serializer_class = GoalCheckInSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['goal', 'created_by']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)


class FeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar retroalimentación
    """
    queryset = Feedback.objects.select_related(
        'from_employee__user', 'to_employee__user', 'performance_review'
    ).all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['from_employee', 'to_employee', 'feedback_type', 'status', 'is_anonymous']
    search_fields = ['subject', 'content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(from_employee=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """
        Reconocer retroalimentación recibida
        """
        feedback = self.get_object()
        
        if feedback.to_employee != request.user.employee_profile:
            return Response(
                {'error': 'Solo el destinatario puede reconocer esta retroalimentación'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        feedback.status = 'acknowledged'
        feedback.acknowledged_at = timezone.now()
        feedback.save()
        
        serializer = self.get_serializer(feedback)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def received(self, request):
        """
        Obtener retroalimentación recibida
        """
        employee = request.user.employee_profile
        feedback = self.queryset.filter(to_employee=employee)
        
        serializer = self.get_serializer(feedback, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def given(self, request):
        """
        Obtener retroalimentación dada
        """
        employee = request.user.employee_profile
        feedback = self.queryset.filter(from_employee=employee)
        
        serializer = self.get_serializer(feedback, many=True)
        return Response(serializer.data)


class DevelopmentPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar planes de desarrollo
    """
    queryset = DevelopmentPlan.objects.select_related(
        'employee__user', 'manager__user', 'approved_by__user',
        'performance_review'
    ).prefetch_related('actions').all()
    serializer_class = DevelopmentPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'manager', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar plan de desarrollo
        """
        plan = self.get_object()
        
        if plan.status != 'draft':
            return Response(
                {'error': 'Solo se pueden aprobar planes en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan.status = 'active'
        plan.approved_by = request.user.employee_profile
        plan.approved_at = timezone.now()
        plan.save()
        
        serializer = self.get_serializer(plan)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Completar plan de desarrollo
        """
        plan = self.get_object()
        
        plan.status = 'completed'
        plan.save()
        
        serializer = self.get_serializer(plan)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_plans(self, request):
        """
        Obtener planes del usuario actual
        """
        employee = request.user.employee_profile
        plans = self.queryset.filter(employee=employee)
        
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)


class DevelopmentActionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar acciones de desarrollo
    """
    queryset = DevelopmentAction.objects.select_related(
        'development_plan__employee__user'
    ).all()
    serializer_class = DevelopmentActionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['development_plan', 'action_type', 'status']
    ordering_fields = ['target_date', 'created_at']
    ordering = ['target_date']
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Completar acción
        """
        action = self.get_object()
        
        outcome = request.data.get('outcome', '')
        
        action.status = 'completed'
        action.completed_date = timezone.now().date()
        action.outcome = outcome
        action.save()
        
        serializer = self.get_serializer(action)
        return Response(serializer.data)


class PerformanceImprovementPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar planes de mejora de desempeño
    """
    queryset = PerformanceImprovementPlan.objects.select_related(
        'employee__user', 'manager__user', 'performance_review'
    ).prefetch_related('check_ins').all()
    serializer_class = PerformanceImprovementPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employee', 'manager', 'status']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def mark_successful(self, request, pk=None):
        """
        Marcar PIP como exitoso
        """
        pip = self.get_object()
        
        if pip.status != 'active':
            return Response(
                {'error': 'Solo se pueden completar PIPs activos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        final_outcome = request.data.get('final_outcome', '')
        
        pip.status = 'successful'
        pip.final_outcome = final_outcome
        pip.save()
        
        serializer = self.get_serializer(pip)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_unsuccessful(self, request, pk=None):
        """
        Marcar PIP como no exitoso
        """
        pip = self.get_object()
        
        if pip.status != 'active':
            return Response(
                {'error': 'Solo se pueden completar PIPs activos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        final_outcome = request.data.get('final_outcome', '')
        
        pip.status = 'unsuccessful'
        pip.final_outcome = final_outcome
        pip.save()
        
        serializer = self.get_serializer(pip)
        return Response(serializer.data)


class PIPCheckInViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar check-ins de PIP
    """
    queryset = PIPCheckIn.objects.select_related(
        'improvement_plan__employee__user', 'conducted_by__user'
    ).all()
    serializer_class = PIPCheckInSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['improvement_plan', 'is_on_track']
    ordering_fields = ['check_in_date', 'created_at']
    ordering = ['-check_in_date']
    
    def perform_create(self, serializer):
        serializer.save(conducted_by=self.request.user.employee_profile)


class PerformanceMetricsViewSet(viewsets.ViewSet):
    """
    ViewSet para métricas de desempeño
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Obtener resumen general de métricas de desempeño
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        department_id = request.query_params.get('department')
        
        # Filtros de fecha por defecto (último año)
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=365)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Filtrar evaluaciones
        reviews = PerformanceReview.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        if department_id:
            reviews = reviews.filter(employee__department_id=department_id)
        
        total_reviews = reviews.count()
        completed_reviews = reviews.filter(status='completed').count()
        pending_reviews = reviews.filter(status='pending').count()
        
        average_rating = reviews.filter(
            overall_rating__isnull=False
        ).aggregate(Avg('overall_rating'))['overall_rating__avg']
        
        # Distribución de calificaciones
        ratings_distribution = {}
        for rating_choice in PerformanceReview.OVERALL_RATING_CHOICES:
            count = reviews.filter(overall_rating=rating_choice[0]).count()
            ratings_distribution[rating_choice[1]] = count
        
        # Metas
        goals = Goal.objects.filter(
            start_date__range=[start_date, end_date]
        )
        
        if department_id:
            goals = goals.filter(employee__department_id=department_id)
        
        total_goals = goals.count()
        completed_goals = goals.filter(status='completed').count()
        
        goals_by_status = {}
        for status_choice in Goal.STATUS_CHOICES:
            count = goals.filter(status=status_choice[0]).count()
            if count > 0:
                goals_by_status[status_choice[1]] = count
        
        average_goal_completion = goals.aggregate(
            Avg('progress_percentage')
        )['progress_percentage__avg'] or 0
        
        metrics_data = {
            'total_reviews': total_reviews,
            'completed_reviews': completed_reviews,
            'pending_reviews': pending_reviews,
            'average_rating': round(average_rating, 2) if average_rating else None,
            'ratings_distribution': ratings_distribution,
            'total_goals': total_goals,
            'completed_goals': completed_goals,
            'goals_by_status': goals_by_status,
            'average_goal_completion': round(average_goal_completion, 2)
        }
        
        serializer = PerformanceMetricsSerializer(metrics_data)
        return Response(serializer.data)