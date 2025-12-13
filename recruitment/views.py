from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta

from .models import (
    JobPosting, Candidate, Application, RecruitmentStage, Interview,
    Assessment, JobOffer, OnboardingTask, RecruitmentReport
)
from .serializers import (
    JobPostingListSerializer, JobPostingDetailSerializer, CandidateSerializer,
    ApplicationListSerializer, ApplicationDetailSerializer, ApplicationCreateSerializer,
    RecruitmentStageSerializer, InterviewSerializer, AssessmentSerializer,
    JobOfferSerializer, OnboardingTaskSerializer, RecruitmentReportSerializer,
    ApplicationStatusUpdateSerializer, ApplicationRatingSerializer,
    InterviewScheduleSerializer, InterviewFeedbackSerializer, AssessmentGradeSerializer,
    JobOfferAcceptSerializer, JobOfferRejectSerializer, RecruitmentMetricsSerializer
)
from employees.models import Employee


class JobPostingViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar publicaciones de trabajo
    """
    queryset = JobPosting.objects.select_related(
        'department', 'position', 'hiring_manager__user', 'created_by__user'
    ).prefetch_related('applications').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'position', 'employment_type', 'experience_level', 
                       'status', 'remote_option']
    search_fields = ['title', 'job_code', 'description', 'location']
    ordering_fields = ['posted_date', 'application_deadline', 'created_at', 'views_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return JobPostingListSerializer
        return JobPostingDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """
        Publicar vacante
        """
        job_posting = self.get_object()
        
        if job_posting.status != 'draft':
            return Response(
                {'error': 'Solo se pueden publicar vacantes en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job_posting.status = 'active'
        job_posting.posted_date = timezone.now().date()
        job_posting.save()
        
        serializer = self.get_serializer(job_posting)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """
        Pausar vacante
        """
        job_posting = self.get_object()
        
        if job_posting.status != 'active':
            return Response(
                {'error': 'Solo se pueden pausar vacantes activas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job_posting.status = 'paused'
        job_posting.save()
        
        serializer = self.get_serializer(job_posting)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        Cerrar vacante
        """
        job_posting = self.get_object()
        
        job_posting.status = 'closed'
        job_posting.save()
        
        serializer = self.get_serializer(job_posting)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_filled(self, request, pk=None):
        """
        Marcar vacante como ocupada
        """
        job_posting = self.get_object()
        
        job_posting.status = 'filled'
        job_posting.save()
        
        serializer = self.get_serializer(job_posting)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """
        Obtener solicitudes de una vacante
        """
        job_posting = self.get_object()
        applications = job_posting.applications.all()
        
        # Filtros adicionales
        status_filter = request.query_params.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        
        serializer = ApplicationListSerializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Obtener estadísticas de una vacante
        """
        job_posting = self.get_object()
        applications = job_posting.applications.all()
        
        total_applications = applications.count()
        applications_by_status = {}
        
        for status_choice in Application.STATUS_CHOICES:
            count = applications.filter(status=status_choice[0]).count()
            if count > 0:
                applications_by_status[status_choice[1]] = count
        
        applications_by_source = {}
        candidates = Candidate.objects.filter(applications__job_posting=job_posting).distinct()
        
        for source_choice in Candidate.SOURCE_CHOICES:
            count = candidates.filter(source=source_choice[0]).count()
            if count > 0:
                applications_by_source[source_choice[1]] = count
        
        average_rating = applications.exclude(rating__isnull=True).aggregate(
            Avg('rating')
        )['rating__avg']
        
        return Response({
            'total_applications': total_applications,
            'applications_by_status': applications_by_status,
            'applications_by_source': applications_by_source,
            'average_rating': round(average_rating, 2) if average_rating else None,
            'views_count': job_posting.views_count
        })
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Obtener vacantes activas
        """
        active_postings = self.queryset.filter(status='active')
        serializer = self.get_serializer(active_postings, many=True)
        return Response(serializer.data)


class CandidateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar candidatos
    """
    queryset = Candidate.objects.select_related('referred_by__user').all()
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source', 'education_level', 'country', 'city']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'skills', 
                    'current_position', 'current_company']
    ordering_fields = ['created_at', 'years_of_experience', 'expected_salary']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """
        Obtener solicitudes de un candidato
        """
        candidate = self.get_object()
        applications = candidate.applications.all()
        serializer = ApplicationListSerializer(applications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search_skills(self, request):
        """
        Buscar candidatos por habilidades
        """
        skills = request.query_params.get('skills', '')
        
        if not skills:
            return Response(
                {'error': 'Se requiere el parámetro skills'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        skill_list = [s.strip().lower() for s in skills.split(',')]
        candidates = self.queryset
        
        for skill in skill_list:
            candidates = candidates.filter(skills__icontains=skill)
        
        serializer = self.get_serializer(candidates, many=True)
        return Response(serializer.data)


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar solicitudes
    """
    queryset = Application.objects.select_related(
        'candidate', 'job_posting__department', 'job_posting__position',
        'current_stage', 'assigned_recruiter__user'
    ).prefetch_related('interviews', 'assessments', 'offers').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['candidate', 'job_posting', 'status', 'assigned_recruiter', 'rating']
    search_fields = ['candidate__first_name', 'candidate__last_name', 'candidate__email']
    ordering_fields = ['applied_date', 'status_changed_at', 'rating']
    ordering = ['-applied_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ApplicationListSerializer
        elif self.action == 'create':
            return ApplicationCreateSerializer
        return ApplicationDetailSerializer
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Actualizar estado de solicitud
        """
        application = self.get_object()
        serializer = ApplicationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        application.status = serializer.validated_data['status']
        
        if serializer.validated_data.get('notes'):
            application.notes = serializer.validated_data['notes']
        
        if serializer.validated_data.get('rejection_reason'):
            application.rejection_reason = serializer.validated_data['rejection_reason']
        
        application.status_changed_at = timezone.now()
        application.save()
        
        response_serializer = ApplicationDetailSerializer(application)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """
        Calificar solicitud
        """
        application = self.get_object()
        serializer = ApplicationRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        application.rating = serializer.validated_data['rating']
        
        if serializer.validated_data.get('notes'):
            application.notes = serializer.validated_data['notes']
        
        application.save()
        
        response_serializer = ApplicationDetailSerializer(application)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_recruiter(self, request, pk=None):
        """
        Asignar reclutador a solicitud
        """
        application = self.get_object()
        recruiter_id = request.data.get('recruiter_id')
        
        if not recruiter_id:
            return Response(
                {'error': 'Se requiere recruiter_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            recruiter = Employee.objects.get(id=recruiter_id)
            application.assigned_recruiter = recruiter
            application.save()
            
            serializer = ApplicationDetailSerializer(application)
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Reclutador no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def move_to_stage(self, request, pk=None):
        """
        Mover solicitud a otra etapa
        """
        application = self.get_object()
        stage_id = request.data.get('stage_id')
        
        if not stage_id:
            return Response(
                {'error': 'Se requiere stage_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stage = RecruitmentStage.objects.get(id=stage_id)
            application.current_stage = stage
            application.save()
            
            serializer = ApplicationDetailSerializer(application)
            return Response(serializer.data)
        except RecruitmentStage.DoesNotExist:
            return Response(
                {'error': 'Etapa no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def pipeline(self, request):
        """
        Obtener pipeline de reclutamiento (solicitudes por etapa)
        """
        job_posting_id = request.query_params.get('job_posting')
        
        queryset = self.queryset
        if job_posting_id:
            queryset = queryset.filter(job_posting_id=job_posting_id)
        
        pipeline = {}
        for status_choice in Application.STATUS_CHOICES:
            count = queryset.filter(status=status_choice[0]).count()
            if count > 0:
                pipeline[status_choice[1]] = count
        
        return Response(pipeline)
    
    @action(detail=False, methods=['get'])
    def shortlisted(self, request):
        """
        Obtener solicitudes preseleccionadas
        """
        applications = self.queryset.filter(status='shortlisted')
        serializer = ApplicationListSerializer(applications, many=True)
        return Response(serializer.data)


class RecruitmentStageViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar etapas de reclutamiento
    """
    queryset = RecruitmentStage.objects.select_related('job_posting').all()
    serializer_class = RecruitmentStageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['job_posting', 'is_active']
    ordering_fields = ['order', 'created_at']
    ordering = ['order']


class InterviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar entrevistas
    """
    queryset = Interview.objects.select_related(
        'application__candidate', 'application__job_posting'
    ).prefetch_related('interviewers__user').all()
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['application', 'interview_type', 'status', 'result', 'scheduled_date']
    ordering_fields = ['scheduled_date', 'scheduled_time', 'created_at']
    ordering = ['-scheduled_date', '-scheduled_time']
    
    @action(detail=False, methods=['post'])
    def schedule(self, request):
        """
        Programar entrevista
        """
        application_id = request.data.get('application_id')
        
        if not application_id:
            return Response(
                {'error': 'Se requiere application_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            application = Application.objects.get(id=application_id)
        except Application.DoesNotExist:
            return Response(
                {'error': 'Solicitud no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = InterviewScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        interview = Interview.objects.create(
            application=application,
            interview_type=serializer.validated_data['interview_type'],
            scheduled_date=serializer.validated_data['scheduled_date'],
            scheduled_time=serializer.validated_data['scheduled_time'],
            duration_minutes=serializer.validated_data.get('duration_minutes', 60),
            location=serializer.validated_data.get('location', ''),
            meeting_link=serializer.validated_data.get('meeting_link', ''),
            notes=serializer.validated_data.get('notes', '')
        )
        
        if serializer.validated_data.get('interviewers'):
            interview.interviewers.set(serializer.validated_data['interviewers'])
        
        response_serializer = InterviewSerializer(interview)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def add_feedback(self, request, pk=None):
        """
        Agregar feedback a entrevista
        """
        interview = self.get_object()
        serializer = InterviewFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        interview.status = serializer.validated_data['status']
        interview.result = serializer.validated_data['result']
        
        if serializer.validated_data.get('notes'):
            interview.notes = serializer.validated_data['notes']
        
        if serializer.validated_data.get('candidate_strengths'):
            interview.candidate_strengths = serializer.validated_data['candidate_strengths']
        
        if serializer.validated_data.get('candidate_weaknesses'):
            interview.candidate_weaknesses = serializer.validated_data['candidate_weaknesses']
        
        if serializer.validated_data.get('overall_rating'):
            interview.overall_rating = serializer.validated_data['overall_rating']
        
        if serializer.validated_data.get('recommendation'):
            interview.recommendation = serializer.validated_data['recommendation']
        
        interview.save()
        
        response_serializer = InterviewSerializer(interview)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancelar entrevista
        """
        interview = self.get_object()
        
        interview.status = 'cancelled'
        interview.notes = request.data.get('notes', '')
        interview.save()
        
        serializer = self.get_serializer(interview)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Obtener entrevistas próximas
        """
        today = timezone.now().date()
        interviews = self.queryset.filter(
            scheduled_date__gte=today,
            status='scheduled'
        ).order_by('scheduled_date', 'scheduled_time')[:20]
        
        serializer = self.get_serializer(interviews, many=True)
        return Response(serializer.data)


class AssessmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar evaluaciones
    """
    queryset = Assessment.objects.select_related(
        'application__candidate', 'application__job_posting', 'evaluator__user'
    ).all()
    serializer_class = AssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['application', 'assessment_type', 'status']
    ordering_fields = ['sent_date', 'due_date', 'submitted_date']
    ordering = ['-sent_date']
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Enviar evaluación (candidato)
        """
        assessment = self.get_object()
        
        if assessment.status != 'sent':
            return Response(
                {'error': 'Esta evaluación ya ha sido enviada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission_file = request.FILES.get('submission_file')
        
        if not submission_file:
            return Response(
                {'error': 'Se requiere el archivo de entrega'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assessment.submission_file = submission_file
        assessment.submitted_date = timezone.now()
        assessment.status = 'submitted'
        assessment.save()
        
        serializer = self.get_serializer(assessment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        """
        Calificar evaluación
        """
        assessment = self.get_object()
        
        if assessment.status not in ['submitted', 'in_progress']:
            return Response(
                {'error': 'Solo se pueden calificar evaluaciones entregadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AssessmentGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        assessment.obtained_score = serializer.validated_data['obtained_score']
        assessment.feedback = serializer.validated_data.get('feedback', '')
        assessment.status = 'graded'
        assessment.evaluator = request.user.employee_profile
        assessment.save()
        
        response_serializer = AssessmentSerializer(assessment)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Obtener evaluaciones pendientes de calificar
        """
        assessments = self.queryset.filter(status='submitted')
        serializer = self.get_serializer(assessments, many=True)
        return Response(serializer.data)


class JobOfferViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar ofertas de trabajo
    """
    queryset = JobOffer.objects.select_related(
        'application__candidate', 'application__job_posting',
        'department', 'approved_by__user', 'created_by__user'
    ).all()
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['application', 'department', 'status']
    ordering_fields = ['offer_date', 'expiry_date', 'created_at']
    ordering = ['-offer_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar oferta
        """
        offer = self.get_object()
        
        if offer.status != 'draft':
            return Response(
                {'error': 'Solo se pueden aprobar ofertas en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        offer.status = 'sent'
        offer.approved_by = request.user.employee_profile
        offer.approved_at = timezone.now()
        offer.save()
        
        serializer = self.get_serializer(offer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """
        Aceptar oferta (candidato)
        """
        offer = self.get_object()
        
        if offer.status != 'sent':
            return Response(
                {'error': 'Solo se pueden aceptar ofertas enviadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = JobOfferAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        offer.status = 'accepted'
        offer.candidate_response_date = timezone.now()
        offer.candidate_notes = serializer.validated_data.get('notes', '')
        offer.save()
        
        # Actualizar estado de la solicitud
        offer.application.status = 'hired'
        offer.application.save()
        
        response_serializer = JobOfferSerializer(offer)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Rechazar oferta (candidato)
        """
        offer = self.get_object()
        
        if offer.status != 'sent':
            return Response(
                {'error': 'Solo se pueden rechazar ofertas enviadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = JobOfferRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        offer.status = 'rejected'
        offer.candidate_response_date = timezone.now()
        offer.candidate_notes = serializer.validated_data['reason']
        offer.save()
        
        response_serializer = JobOfferSerializer(offer)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """
        Retirar oferta
        """
        offer = self.get_object()
        
        if offer.status in ['accepted', 'rejected']:
            return Response(
                {'error': 'No se pueden retirar ofertas aceptadas o rechazadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        offer.status = 'withdrawn'
        offer.save()
        
        serializer = self.get_serializer(offer)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_response(self, request):
        """
        Obtener ofertas pendientes de respuesta
        """
        offers = self.queryset.filter(status='sent')
        serializer = self.get_serializer(offers, many=True)
        return Response(serializer.data)


class OnboardingTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar tareas de onboarding
    """
    queryset = OnboardingTask.objects.select_related(
        'job_offer__application__candidate', 'assigned_to__user'
    ).all()
    serializer_class = OnboardingTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['job_offer', 'assigned_to', 'status', 'category']
    ordering_fields = ['order', 'due_date', 'created_at']
    ordering = ['order']
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Marcar tarea como completada
        """
        task = self.get_object()
        
        task.status = 'completed'
        task.completed_date = timezone.now()
        task.save()
        
        serializer = self.get_serializer(task)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Obtener tareas pendientes
        """
        tasks = self.queryset.filter(status='pending')
        
        job_offer_id = request.query_params.get('job_offer')
        if job_offer_id:
            tasks = tasks.filter(job_offer_id=job_offer_id)
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


class RecruitmentReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar reportes de reclutamiento
    """
    queryset = RecruitmentReport.objects.select_related(
        'department', 'job_posting', 'generated_by__user'
    ).all()
    serializer_class = RecruitmentReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['report_type', 'department', 'job_posting']
    ordering_fields = ['created_at', 'start_date']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def metrics(self, request):
        """
        Obtener métricas generales de reclutamiento
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            # Último mes por defecto
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Vacantes
        postings = JobPosting.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        total_postings = postings.count()
        active_postings = postings.filter(status='active').count()
        
        # Solicitudes
        applications = Application.objects.filter(
            applied_date__date__range=[start_date, end_date]
        )
        total_applications = applications.count()
        
        applications_by_status = {}
        for status_choice in Application.STATUS_CHOICES:
            count = applications.filter(status=status_choice[0]).count()
            if count > 0:
                applications_by_status[status_choice[1]] = count
        
        # Tiempo promedio de contratación
        hired_applications = applications.filter(status='hired')
        if hired_applications.exists():
            total_days = sum([
                (app.status_changed_at.date() - app.applied_date.date()).days
                for app in hired_applications
            ])
            average_time_to_hire = total_days / hired_applications.count()
        else:
            average_time_to_hire = 0
        
        # Solicitudes por fuente
        candidates = Candidate.objects.filter(
            applications__applied_date__date__range=[start_date, end_date]
        ).distinct()
        
        applications_by_source = {}
        for source_choice in Candidate.SOURCE_CHOICES:
            count = candidates.filter(source=source_choice[0]).count()
            if count > 0:
                applications_by_source[source_choice[1]] = count
        
        # Tasas de conversión
        conversion_rates = {}
        for i, status_choice in enumerate(Application.STATUS_CHOICES[:-1]):
            current_count = applications.filter(status=status_choice[0]).count()
            next_status = Application.STATUS_CHOICES[i + 1][0]
            next_count = applications.filter(status=next_status).count()
            
            if current_count > 0:
                rate = (next_count / current_count) * 100
                conversion_rates[f"{status_