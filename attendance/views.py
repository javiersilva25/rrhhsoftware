from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from datetime import datetime, timedelta

from .models import (
    WorkSchedule, EmployeeSchedule, TimeSheet, Overtime,
    LeaveType, LeaveBalance, LeaveRequest, Holiday, AttendanceReport
)
from .serializers import (
    WorkScheduleSerializer, EmployeeScheduleSerializer,
    TimeSheetSerializer, TimeSheetCheckInSerializer, TimeSheetCheckOutSerializer,
    OvertimeSerializer, LeaveTypeSerializer, LeaveBalanceSerializer,
    LeaveRequestSerializer, HolidaySerializer, AttendanceReportSerializer,
    AttendanceSummarySerializer
)
from employees.models import Employee


class WorkScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar horarios de trabajo
    """
    queryset = WorkSchedule.objects.all()
    serializer_class = WorkScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['schedule_type', 'department', 'day_of_week', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'day_of_week', 'start_time']
    ordering = ['day_of_week', 'start_time']


class EmployeeScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar asignación de horarios a empleados
    """
    queryset = EmployeeSchedule.objects.select_related(
        'employee__user', 'work_schedule'
    ).all()
    serializer_class = EmployeeScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'work_schedule', 'is_active']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_number']
    ordering_fields = ['effective_from', 'created_at']
    ordering = ['-effective_from']
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Obtener horarios actuales activos
        """
        today = timezone.now().date()
        schedules = self.queryset.filter(
            effective_from__lte=today,
            is_active=True
        ).filter(
            Q(effective_to__gte=today) | Q(effective_to__isnull=True)
        )
        
        employee_id = request.query_params.get('employee')
        if employee_id:
            schedules = schedules.filter(employee_id=employee_id)
        
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data)


class TimeSheetViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar registros de asistencia
    """
    queryset = TimeSheet.objects.select_related(
        'employee__user', 'approved_by__user'
    ).all()
    serializer_class = TimeSheetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'status', 'is_approved', 'date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_number']
    ordering_fields = ['date', 'check_in', 'created_at']
    ordering = ['-date', '-check_in']
    
    @action(detail=False, methods=['post'])
    def check_in(self, request):
        """
        Registrar entrada (check-in)
        """
        serializer = TimeSheetCheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        employee = serializer.validated_data['employee']
        today = timezone.now().date()
        
        # Verificar si ya existe un registro para hoy
        timesheet, created = TimeSheet.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'check_in': serializer.validated_data.get('check_in', timezone.now()),
                'ip_address': serializer.validated_data.get('ip_address'),
                'location': serializer.validated_data.get('location', ''),
                'notes': serializer.validated_data.get('notes', ''),
                'status': 'present'
            }
        )
        
        if not created:
            if timesheet.check_in:
                return Response(
                    {'error': 'Ya existe un registro de entrada para hoy'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                timesheet.check_in = serializer.validated_data.get('check_in', timezone.now())
                timesheet.ip_address = serializer.validated_data.get('ip_address')
                timesheet.location = serializer.validated_data.get('location', '')
                timesheet.notes = serializer.validated_data.get('notes', '')
                timesheet.status = 'present'
                timesheet.save()
        
        response_serializer = TimeSheetSerializer(timesheet)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def check_out(self, request, pk=None):
        """
        Registrar salida (check-out)
        """
        timesheet = self.get_object()
        
        if timesheet.check_out:
            return Response(
                {'error': 'Ya existe un registro de salida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not timesheet.check_in:
            return Response(
                {'error': 'No existe registro de entrada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = TimeSheetCheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        timesheet.check_out = serializer.validated_data.get('check_out', timezone.now())
        timesheet.calculate_work_hours()
        timesheet.save()
        
        response_serializer = TimeSheetSerializer(timesheet)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar registro de asistencia
        """
        timesheet = self.get_object()
        
        if timesheet.is_approved:
            return Response(
                {'error': 'Este registro ya está aprobado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timesheet.is_approved = True
        timesheet.approved_by = request.user.employee_profile
        timesheet.approved_at = timezone.now()
        timesheet.save()
        
        serializer = self.get_serializer(timesheet)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Obtener resumen de asistencia
        """
        employee_id = request.query_params.get('employee')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not all([employee_id, start_date, end_date]):
            return Response(
                {'error': 'Se requieren los parámetros: employee, start_date, end_date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        timesheets = TimeSheet.objects.filter(
            employee_id=employee_id,
            date__range=[start_date, end_date]
        )
        
        total_days = (end_date - start_date).days + 1
        present_days = timesheets.filter(status='present').count()
        absent_days = timesheets.filter(status='absent').count()
        late_days = timesheets.filter(status='late').count()
        half_days = timesheets.filter(status='half_day').count()
        on_leave_days = timesheets.filter(status='on_leave').count()
        
        work_hours_sum = timesheets.aggregate(Sum('work_hours'))['work_hours__sum'] or 0
        overtime_hours_sum = timesheets.aggregate(Sum('overtime_hours'))['overtime_hours__sum'] or 0
        
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        summary_data = {
            'total_days': total_days,
            'present_days': present_days,
            'absent_days': absent_days,
            'late_days': late_days,
            'half_days': half_days,
            'on_leave_days': on_leave_days,
            'total_work_hours': work_hours_sum,
            'total_overtime_hours': overtime_hours_sum,
            'attendance_percentage': round(attendance_percentage, 2)
        }
        
        serializer = AttendanceSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """
        Obtener registros de asistencia del día actual
        """
        today = timezone.now().date()
        timesheets = self.queryset.filter(date=today)
        
        employee_id = request.query_params.get('employee')
        if employee_id:
            timesheets = timesheets.filter(employee_id=employee_id)
        
        serializer = self.get_serializer(timesheets, many=True)
        return Response(serializer.data)


class OvertimeViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar horas extras
    """
    queryset = Overtime.objects.select_related(
        'employee__user', 'approved_by__user'
    ).all()
    serializer_class = OvertimeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'status', 'date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_number']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar horas extras
        """
        overtime = self.get_object()
        
        if overtime.status != 'pending':
            return Response(
                {'error': 'Solo se pueden aprobar solicitudes pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        overtime.status = 'approved'
        overtime.approved_by = request.user.employee_profile
        overtime.approved_at = timezone.now()
        overtime.save()
        
        serializer = self.get_serializer(overtime)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Rechazar horas extras
        """
        overtime = self.get_object()
        
        if overtime.status != 'pending':
            return Response(
                {'error': 'Solo se pueden rechazar solicitudes pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'Se requiere una razón de rechazo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        overtime.status = 'rejected'
        overtime.approved_by = request.user.employee_profile
        overtime.approved_at = timezone.now()
        overtime.rejection_reason = rejection_reason
        overtime.save()
        
        serializer = self.get_serializer(overtime)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Obtener horas extras pendientes de aprobación
        """
        overtimes = self.queryset.filter(status='pending')
        serializer = self.get_serializer(overtimes, many=True)
        return Response(serializer.data)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar tipos de permisos
    """
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_paid', 'requires_approval', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar balances de permisos
    """
    queryset = LeaveBalance.objects.select_related(
        'employee__user', 'leave_type'
    ).all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employee', 'leave_type', 'year']
    ordering_fields = ['year', 'created_at']
    ordering = ['-year']
    
    @action(detail=False, methods=['get'])
    def current_year(self, request):
        """
        Obtener balances del año actual
        """
        current_year = timezone.now().year
        balances = self.queryset.filter(year=current_year)
        
        employee_id = request.query_params.get('employee')
        if employee_id:
            balances = balances.filter(employee_id=employee_id)
        
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def initialize_year(self, request):
        """
        Inicializar balances para un año
        """
        year = request.data.get('year')
        employee_id = request.data.get('employee')
        
        if not year:
            year = timezone.now().year
        
        # Obtener tipos de permisos activos
        leave_types = LeaveType.objects.filter(is_active=True)
        
        # Filtrar empleados
        if employee_id:
            employees = Employee.objects.filter(id=employee_id, status='active')
        else:
            employees = Employee.objects.filter(status='active')
        
        created_count = 0
        for employee in employees:
            for leave_type in leave_types:
                # Verificar si ya existe
                balance, created = LeaveBalance.objects.get_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    year=year,
                    defaults={
                        'total_days': leave_type.days_allowed_per_year,
                        'used_days': 0,
                        'pending_days': 0,
                        'carried_forward': 0
                    }
                )
                if created:
                    created_count += 1
        
        return Response({
            'message': f'Se crearon {created_count} balances de permisos',
            'year': year
        })


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar solicitudes de permisos
    """
    queryset = LeaveRequest.objects.select_related(
        'employee__user', 'leave_type', 'approved_by__user'
    ).all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'leave_type', 'status', 'start_date', 'end_date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_number']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar solicitud de permiso
        """
        leave_request = self.get_object()
        
        if leave_request.status != 'pending':
            return Response(
                {'error': 'Solo se pueden aprobar solicitudes pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar balance
        try:
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            
            balance.pending_days -= leave_request.days_requested
            balance.used_days += leave_request.days_requested
            balance.save()
        except LeaveBalance.DoesNotExist:
            pass
        
        leave_request.status = 'approved'
        leave_request.approved_by = request.user.employee_profile
        leave_request.approved_at = timezone.now()
        leave_request.save()
        
        # Crear registros de TimeSheet para los días de permiso
        current_date = leave_request.start_date
        while current_date <= leave_request.end_date:
            if current_date.weekday() < 5:  # Solo días laborables
                TimeSheet.objects.get_or_create(
                    employee=leave_request.employee,
                    date=current_date,
                    defaults={
                        'status': 'on_leave',
                        'notes': f'Permiso: {leave_request.leave_type.name}'
                    }
                )
            current_date += timedelta(days=1)
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Rechazar solicitud de permiso
        """
        leave_request = self.get_object()
        
        if leave_request.status != 'pending':
            return Response(
                {'error': 'Solo se pueden rechazar solicitudes pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        if not rejection_reason:
            return Response(
                {'error': 'Se requiere una razón de rechazo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar balance
        try:
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            
            balance.pending_days -= leave_request.days_requested
            balance.save()
        except LeaveBalance.DoesNotExist:
            pass
        
        leave_request.status = 'rejected'
        leave_request.approved_by = request.user.employee_profile
        leave_request.approved_at = timezone.now()
        leave_request.rejection_reason = rejection_reason
        leave_request.save()
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancelar solicitud de permiso
        """
        leave_request = self.get_object()
        
        if leave_request.status not in ['pending', 'approved']:
            return Response(
                {'error': 'Solo se pueden cancelar solicitudes pendientes o aprobadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cancellation_reason = request.data.get('cancellation_reason', '')
        
        # Actualizar balance
        try:
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            
            if leave_request.status == 'pending':
                balance.pending_days -= leave_request.days_requested
            elif leave_request.status == 'approved':
                balance.used_days -= leave_request.days_requested
            
            balance.save()
        except LeaveBalance.DoesNotExist:
            pass
        
        leave_request.status = 'cancelled'
        leave_request.cancelled_at = timezone.now()
        leave_request.cancellation_reason = cancellation_reason
        leave_request.save()
        
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Obtener solicitudes pendientes de aprobación
        """
        requests = self.queryset.filter(status='pending')
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """
        Crear solicitud de permiso y actualizar balance pendiente
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        leave_request = serializer.save()
        
        # Actualizar balance pendiente
        try:
            balance = LeaveBalance.objects.get(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                year=leave_request.start_date.year
            )
            
            balance.pending_days += leave_request.days_requested
            balance.save()
        except LeaveBalance.DoesNotExist:
            pass
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class HolidayViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar días festivos
    """
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'is_recurring', 'is_active', 'date']
    search_fields = ['name', 'description']
    ordering_fields = ['date', 'created_at']
    ordering = ['date']
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """
        Obtener próximos días festivos
        """
        today = timezone.now().date()
        holidays = self.queryset.filter(
            date__gte=today,
            is_active=True
        ).order_by('date')[:10]
        
        serializer = self.get_serializer(holidays, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def year(self, request):
        """
        Obtener días festivos de un año específico
        """
        year = request.query_params.get('year', timezone.now().year)
        
        holidays = self.queryset.filter(
            date__year=year,
            is_active=True
        )
        
        serializer = self.get_serializer(holidays, many=True)
        return Response(serializer.data)


class AttendanceReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar reportes de asistencia
    """
    queryset = AttendanceReport.objects.select_related(
        'department', 'generated_by__user'
    ).all()
    serializer_class = AttendanceReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['report_type', 'department']
    ordering_fields = ['created_at', 'start_date']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generar reporte de asistencia
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        report = serializer.save(generated_by=request.user.employee_profile)
        
        # TODO: Aquí iría la lógica para generar el archivo del reporte (CSV, Excel, PDF)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)