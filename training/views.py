from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from datetime import datetime, timedelta

from .models import (
    TrainingCategory, TrainingProvider, Course, TrainingSession,
    TrainingEnrollment, TrainingAttendance, TrainingAssessment,
    Certification, TrainingBudget, TrainingRequest, TrainingFeedback
)
from .serializers import (
    TrainingCategorySerializer, TrainingProviderSerializer, CourseListSerializer,
    CourseDetailSerializer, TrainingSessionListSerializer, TrainingSessionDetailSerializer,
    TrainingEnrollmentSerializer, TrainingAttendanceSerializer, TrainingAssessmentSerializer,
    CertificationSerializer, TrainingBudgetSerializer, TrainingRequestSerializer,
    TrainingFeedbackSerializer, EnrollmentApprovalSerializer, EnrollmentCompleteSerializer,
    BulkEnrollmentSerializer, TrainingStatisticsSerializer, SessionEnrollSerializer
)
from employees.models import Employee


class TrainingCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de capacitación
    """
    queryset = TrainingCategory.objects.prefetch_related('courses').all()
    serializer_class = TrainingCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class TrainingProviderViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar proveedores de capacitación
    """
    queryset = TrainingProvider.objects.all()
    serializer_class = TrainingProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['provider_type', 'is_active']
    search_fields = ['name', 'contact_name', 'contact_email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cursos
    """
    queryset = Course.objects.select_related(
        'category', 'provider', 'created_by__user'
    ).prefetch_related('sessions').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'provider', 'level', 'delivery_method', 
                       'provides_certificate', 'is_active']
    search_fields = ['title', 'code', 'description', 'objectives']
    ordering_fields = ['title', 'duration_hours', 'cost_per_person', 'created_at']
    ordering = ['title']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """
        Obtener sesiones de un curso
        """
        course = self.get_object()
        sessions = course.sessions.all()
        
        status_filter = request.query_params.get('status')
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        
        serializer = TrainingSessionListSerializer(sessions, many=True)
        return Response(serializer.data)


class TrainingSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar sesiones de capacitación
    """
    queryset = TrainingSession.objects.select_related(
        'course__category', 'course__provider', 'instructor__user',
        'created_by__user'
    ).prefetch_related('enrollments').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['course', 'status', 'instructor', 'start_date', 'end_date']
    search_fields = ['session_name', 'location', 'course__title']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return TrainingSessionListSerializer
        return TrainingSessionDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """
        Inscribir empleado a sesión
        """
        session = self.get_object()
        
        serializer = SessionEnrollSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        employee = serializer.validated_data['employee']
        
        # Verificar disponibilidad
        if session.is_full:
            return Response(
                {'error': 'Esta sesión ya está llena'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar fecha límite de registro
        if session.registration_deadline and timezone.now().date() > session.registration_deadline:
            return Response(
                {'error': 'La fecha límite de registro ha pasado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar si ya está inscrito
        if TrainingEnrollment.objects.filter(session=session, employee=employee).exists():
            return Response(
                {'error': 'El empleado ya está inscrito en esta sesión'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear inscripción
        enrollment = TrainingEnrollment.objects.create(
            session=session,
            employee=employee,
            status='pending' if session.course.cost_per_person > 0 else 'enrolled'
        )
        
        response_serializer = TrainingEnrollmentSerializer(enrollment)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def bulk_enroll(self, request, pk=None):
        """
        Inscribir múltiples empleados a sesión
        """
        session = self.get_object()
        
        serializer = BulkEnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        employee_ids = serializer.validated_data['employee_ids']
        employees = Employee.objects.filter(id__in=employee_ids, status='active')
        
        created_count = 0
        errors = []
        
        for employee in employees:
            # Verificar si ya está inscrito
            if TrainingEnrollment.objects.filter(session=session, employee=employee).exists():
                errors.append({
                    'employee': employee.user.get_full_name(),
                    'error': 'Ya está inscrito'
                })
                continue
            
            # Verificar disponibilidad
            if session.is_full:
                errors.append({
                    'employee': employee.user.get_full_name(),
                    'error': 'Sesión llena'
                })
                continue
            
            try:
                TrainingEnrollment.objects.create(
                    session=session,
                    employee=employee,
                    status='pending' if session.course.cost_per_person > 0 else 'enrolled'
                )
                created_count += 1
            except Exception as e:
                errors.append({
                    'employee': employee.user.get_full_name(),
                    'error': str(e)
                })
        
        return Response({
            'message': f'Se inscribieron {created_count} empleados',
            'created': created_count,
            'errors': errors
        })
    
    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        """
        Obtener inscripciones de una sesión
        """
        session = self.get_object()
        enrollments = session.enrollments.all()
        
        status_filter = request.query_params.get('status')
        if status_filter:
            enrollments = enrollments.filter(status=status_filter)
        
        serializer = TrainingEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Iniciar sesión
        """
        session = self.get_object()
        
        if session.status != 'scheduled':
            return Response(
                {'error': 'Solo se pueden iniciar sesiones programadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'in_progress'
        session.save()
        
        serializer = TrainingSessionDetailSerializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Completar sesión
        """
        session = self.get_object()
        
        if session.status != 'in_progress':
            return Response(
                {'error': 'Solo se pueden completar sesiones en progreso'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'completed'
        session.save()
        
        serializer = TrainingSessionDetailSerializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancelar sesión
        """
        session = self.get_object()
        
        if session.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'Esta sesión no puede ser cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'cancelled'
        session.save()
        
        # Cancelar todas las inscripciones
        session.enrollments.filter(status__in=['pending', 'approved', 'enrolled']).update(
            status='cancelled'
        )
        
        serializer = TrainingSessionDetailSerializer(session)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Obtener sesiones próximas
        """
        today = timezone.now().date()
        sessions = self.queryset.filter(
            start_date__gte=today,
            status='scheduled'
        ).order_by('start_date')[:20]
        
        serializer = TrainingSessionListSerializer(sessions, many=True)
        return Response(serializer.data)


class TrainingEnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar inscripciones
    """
    queryset = TrainingEnrollment.objects.select_related(
        'session__course', 'employee__user', 'approved_by__user'
    ).all()
    serializer_class = TrainingEnrollmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['session', 'employee', 'status', 'certificate_issued']
    search_fields = ['employee__user__first_name', 'employee__user__last_name',
                    'employee__employee_number', 'session__session_name']
    ordering_fields = ['enrolled_at', 'final_score', 'attendance_percentage']
    ordering = ['-enrolled_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar inscripción
        """
        enrollment = self.get_object()
        
        if enrollment.status != 'pending':
            return Response(
                {'error': 'Solo se pueden aprobar inscripciones pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = EnrollmentApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data['action'] == 'approve':
            enrollment.status = 'enrolled'
            enrollment.approved_by = request.user.employee_profile
            enrollment.approved_at = timezone.now()
        else:
            enrollment.status = 'rejected'
            enrollment.rejection_reason = serializer.validated_data.get('notes', '')
        
        enrollment.save()
        
        response_serializer = TrainingEnrollmentSerializer(enrollment)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Completar inscripción
        """
        enrollment = self.get_object()
        
        if enrollment.status != 'enrolled':
            return Response(
                {'error': 'Solo se pueden completar inscripciones activas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = EnrollmentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        enrollment.final_score = serializer.validated_data['final_score']
        enrollment.instructor_feedback = serializer.validated_data.get('instructor_feedback', '')
        enrollment.completed_at = timezone.now()
        
        # Determinar si pasó o reprobó
        if enrollment.has_passed:
            enrollment.status = 'completed'
            
            # Emitir certificado si aplica
            if serializer.validated_data.get('issue_certificate') and enrollment.session.course.provides_certificate:
                enrollment.certificate_issued = True
                enrollment.certificate_issue_date = timezone.now().date()
                
                # Calcular fecha de vencimiento del certificado
                if enrollment.session.course.certificate_validity_days:
                    enrollment.certificate_expiry_date = (
                        timezone.now().date() + 
                        timedelta(days=enrollment.session.course.certificate_validity_days)
                    )
        else:
            enrollment.status = 'failed'
        
        enrollment.save()
        
        response_serializer = TrainingEnrollmentSerializer(enrollment)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancelar inscripción
        """
        enrollment = self.get_object()
        
        if enrollment.status in ['completed', 'failed', 'cancelled']:
            return Response(
                {'error': 'Esta inscripción no puede ser cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        enrollment.status = 'cancelled'
        enrollment.save()
        
        serializer = TrainingEnrollmentSerializer(enrollment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def issue_certificate(self, request, pk=None):
        """
        Emitir certificado
        """
        enrollment = self.get_object()
        
        if enrollment.status != 'completed':
            return Response(
                {'error': 'Solo se pueden emitir certificados para inscripciones completadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not enrollment.session.course.provides_certificate:
            return Response(
                {'error': 'Este curso no otorga certificado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        enrollment.certificate_issued = True
        enrollment.certificate_issue_date = timezone.now().date()
        
        # Calcular fecha de vencimiento
        if enrollment.session.course.certificate_validity_days:
            enrollment.certificate_expiry_date = (
                timezone.now().date() + 
                timedelta(days=enrollment.session.course.certificate_validity_days)
            )
        
        enrollment.save()
        
        # Crear certificación
        Certification.objects.create(
            employee=enrollment.employee,
            enrollment=enrollment,
            certification_name=enrollment.session.course.title,
            issuing_organization=enrollment.session.course.provider.name,
            issue_date=enrollment.certificate_issue_date,
            expiry_date=enrollment.certificate_expiry_date,
            status='active'
        )
        
        serializer = TrainingEnrollmentSerializer(enrollment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_enrollments(self, request):
        """
        Obtener inscripciones del usuario actual
        """
        employee = request.user.employee_profile
        enrollments = self.queryset.filter(employee=employee)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            enrollments = enrollments.filter(status=status_filter)
        
        serializer = TrainingEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """
        Obtener inscripciones pendientes de aprobación
        """
        enrollments = self.queryset.filter(status='pending')
        
        serializer = TrainingEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)


class TrainingAttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar asistencia a capacitación
    """
    queryset = TrainingAttendance.objects.select_related(
        'enrollment__employee__user', 'enrollment__session',
        'recorded_by__user'
    ).all()
    serializer_class = TrainingAttendanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enrollment', 'status', 'session_date']
    ordering_fields = ['session_date', 'created_at']
    ordering = ['-session_date']
    
    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user.employee_profile)


class TrainingAssessmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar evaluaciones de capacitación
    """
    queryset = TrainingAssessment.objects.select_related(
        'enrollment__employee__user', 'enrollment__session',
        'graded_by__user'
    ).all()
    serializer_class = TrainingAssessmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enrollment', 'assessment_type']
    ordering_fields = ['assigned_date', 'due_date', 'submitted_date']
    ordering = ['-assigned_date']
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Enviar evaluación
        """
        assessment = self.get_object()
        
        submission_file = request.FILES.get('submission_file')
        
        if not submission_file:
            return Response(
                {'error': 'Se requiere el archivo de entrega'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assessment.submission_file = submission_file
        assessment.submitted_date = timezone.now()
        assessment.save()
        
        serializer = TrainingAssessmentSerializer(assessment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        """
        Calificar evaluación
        """
        assessment = self.get_object()
        
        obtained_score = request.data.get('obtained_score')
        feedback = request.data.get('feedback', '')
        
        if not obtained_score:
            return Response(
                {'error': 'Se requiere obtained_score'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        assessment.obtained_score = obtained_score
        assessment.feedback = feedback
        assessment.graded_by = request.user.employee_profile
        assessment.graded_date = timezone.now()
        assessment.save()
        
        serializer = TrainingAssessmentSerializer(assessment)
        return Response(serializer.data)


class CertificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar certificaciones
    """
    queryset = Certification.objects.select_related(
        'employee__user', 'enrollment__session__course'
    ).all()
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'status']
    search_fields = ['certification_name', 'certification_number', 'issuing_organization']
    ordering_fields = ['issue_date', 'expiry_date', 'created_at']
    ordering = ['-issue_date']
    
    @action(detail=False, methods=['get'])
    def my_certifications(self, request):
        """
        Obtener certificaciones del usuario actual
        """
        employee = request.user.employee_profile
        certifications = self.queryset.filter(employee=employee)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            certifications = certifications.filter(status=status_filter)
        
        serializer = CertificationSerializer(certifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Obtener certificaciones próximas a vencer
        """
        days = int(request.query_params.get('days', 30))
        today = timezone.now().date()
        future_date = today + timedelta(days=days)
        
        certifications = self.queryset.filter(
            expiry_date__range=[today, future_date],
            status='active'
        )
        
        serializer = CertificationSerializer(certifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Obtener certificaciones vencidas
        """
        today = timezone.now().date()
        certifications = self.queryset.filter(
            expiry_date__lt=today,
            status__in=['active', 'expired']
        )
        
        # Actualizar estado
        certifications.update(status='expired')
        
        serializer = CertificationSerializer(certifications, many=True)
        return Response(serializer.data)


class TrainingBudgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar presupuestos de capacitación
    """
    queryset = TrainingBudget.objects.select_related(
        'department', 'created_by__user'
    ).all()
    serializer_class = TrainingBudgetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['year', 'department']
    ordering_fields = ['year', 'allocated_budget']
    ordering = ['-year']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)


class TrainingRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar solicitudes de capacitación
    """
    queryset = TrainingRequest.objects.select_related(
        'employee__user', 'course', 'reviewed_by__user', 'assigned_session'
    ).all()
    serializer_class = TrainingRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'course', 'status']
    search_fields = ['training_title', 'justification', 'employee__user__first_name',
                    'employee__user__last_name']
    ordering_fields = ['created_at', 'preferred_start_date']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """
        Revisar solicitud de capacitación
        """
        training_request = self.get_object()
        
        if training_request.status != 'pending':
            return Response(
                {'error': 'Solo se pueden revisar solicitudes pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        action = request.data.get('action')  # 'approve' or 'reject'
        review_notes = request.data.get('review_notes', '')
        
        if action == 'approve':
            training_request.status = 'approved'
        elif action == 'reject':
            training_request.status = 'rejected'
        else:
            return Response(
                {'error': 'Acción no válida. Use "approve" o "reject"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        training_request.reviewed_by = request.user.employee_profile
        training_request.reviewed_at = timezone.now()
        training_request.review_notes = review_notes
        training_request.save()
        
        serializer = TrainingRequestSerializer(training_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_session(self, request, pk=None):
        """
        Asignar sesión a solicitud
        """
        training_request = self.get_object()
        
        if training_request.status != 'approved':
            return Response(
                {'error': 'Solo se pueden asignar sesiones a solicitudes aprobadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response(
                {'error': 'Se requiere session_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = TrainingSession.objects.get(id=session_id)
            training_request.assigned_session = session
            training_request.status = 'scheduled'
            training_request.save()
            
            # Crear inscripción automáticamente
            TrainingEnrollment.objects.get_or_create(
                session=session,
                employee=training_request.employee,
                defaults={'status': 'enrolled'}
            )
            
            serializer = TrainingRequestSerializer(training_request)
            return Response(serializer.data)
        except TrainingSession.DoesNotExist:
            return Response(
                {'error': 'Sesión no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def my_requests(self, request):
        """
        Obtener solicitudes del usuario actual
        """
        employee = request.user.employee_profile
        requests = self.queryset.filter(employee=employee)
        
        serializer = TrainingRequestSerializer(requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Obtener solicitudes pendientes
        """
        requests = self.queryset.filter(status='pending')
        
        serializer = TrainingRequestSerializer(requests, many=True)
        return Response(serializer.data)


class TrainingFeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar retroalimentación de capacitación
    """
    queryset = TrainingFeedback.objects.select_related(
        'enrollment__employee__user', 'enrollment__session'
    ).all()
    serializer_class = TrainingFeedbackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enrollment', 'would_recommend']
    ordering_fields = ['submitted_at', 'overall_satisfaction']
    ordering = ['-submitted_at']


class TrainingStatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet para estadísticas de capacitación
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Obtener resumen general de estadísticas de capacitación
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
        
        # Cursos
        total_courses = Course.objects.filter(is_active=True).count()
        
        # Sesiones activas
        active_sessions = TrainingSession.objects.filter(
            status='in_progress'
        ).count()
        
        # Inscripciones
        enrollments = TrainingEnrollment.objects.filter(
            enrolled_at__date__range=[start_date, end_date]
        )
        
        if department_id:
            enrollments = enrollments.filter(employee__department_id=department_id)
        
        total_enrollments = enrollments.count()
        completed_enrollments = enrollments.filter(status='completed').count()
        
        # Tasa de finalización
        average_completion_rate = (
            (completed_enrollments / total_enrollments * 100) 
            if total_enrollments > 0 else 0
        )
        
        # Satisfacción promedio
        feedbacks = TrainingFeedback.objects.filter(
            enrollment__in=enrollments
        )
        average_satisfaction = feedbacks.aggregate(
            Avg('overall_satisfaction')
        )['overall_satisfaction__avg'] or 0
        
        # Horas de capacitación
        completed_enroll = enrollments.filter(status='completed')
        total_training_hours = sum([
            e.session.course.duration_hours 
            for e in completed_enroll
        ])
        
        # Certificaciones emitidas
        certifications_issued = Certification.objects.filter(
            issue_date__range=[start_date, end_date]
        ).count()
        
        # Por categoría
        by_category = {}
        categories = TrainingCategory.objects.all()
        for category in categories:
            count = enrollments.filter(session__course__category=category).count()
            if count > 0:
                by_category[category.name] = count

        # Por departamento
        by_department = {}
        if not department_id:
            from employees.models import Department
            departments = Department.objects.all()
            for dept in departments:
                count = enrollments.filter(employee__department=dept).count()
                if count > 0:
                    by_department[dept.name] = count
        
        # Utilización de presupuesto
        budget_utilization = {}
        year = end_date.year
        budgets = TrainingBudget.objects.filter(year=year)
        
        for budget in budgets:
            dept_name = budget.department.name if budget.department else 'General'
            budget_utilization[dept_name] = {
                'allocated': float(budget.allocated_budget),
                'spent': float(budget.spent_amount),
                'remaining': float(budget.remaining_budget),
                'utilization_percentage': float(budget.utilization_percentage)
            }
        
        statistics_data = {
            'total_courses': total_courses,
            'active_sessions': active_sessions,
            'total_enrollments': total_enrollments,
            'completed_enrollments': completed_enrollments,
            'average_completion_rate': round(average_completion_rate, 2),
            'average_satisfaction': round(average_satisfaction, 2),
            'total_training_hours': float(total_training_hours),
            'certifications_issued': certifications_issued,
            'by_category': by_category,
            'by_department': by_department,
            'budget_utilization': budget_utilization
        }
        
        serializer = TrainingStatisticsSerializer(statistics_data)
        return Response(serializer.data)