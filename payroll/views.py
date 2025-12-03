from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from django.db import transaction
from decimal import Decimal

from .models import (
    PayrollPeriod, SalaryComponent, EmployeeSalary, EmployeeSalaryComponent,
    Payroll, PayrollItem, PayrollAdjustment, PaymentMethod, PayrollPayment
)
from .serializers import (
    PayrollPeriodSerializer, SalaryComponentSerializer, EmployeeSalarySerializer,
    EmployeeSalaryComponentSerializer, PayrollListSerializer, PayrollDetailSerializer,
    PayrollCreateSerializer, PayrollCalculateSerializer, PayrollItemSerializer,
    PayrollAdjustmentSerializer, PaymentMethodSerializer, PayrollPaymentSerializer,
    PayrollSummarySerializer, BulkPayrollCreateSerializer, PayrollApproveSerializer,
    PayrollPaySerializer
)
from employees.models import Employee, Department


class PayrollPeriodViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar períodos de nómina
    """
    queryset = PayrollPeriod.objects.select_related(
        'department', 'created_by__user', 'approved_by__user'
    ).prefetch_related('payrolls').all()
    serializer_class = PayrollPeriodSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['period_type', 'status', 'department', 'start_date', 'end_date']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'payment_date', 'created_at']
    ordering = ['-start_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar período de nómina
        """
        period = self.get_object()
        
        if period.status != 'processing':
            return Response(
                {'error': 'Solo se pueden aprobar períodos en estado "Procesando"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que todas las nóminas del período estén calculadas
        pending_payrolls = period.payrolls.filter(status='draft').count()
        if pending_payrolls > 0:
            return Response(
                {'error': f'Hay {pending_payrolls} nóminas sin calcular'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        period.status = 'approved'
        period.approved_by = request.user.employee_profile
        period.approved_at = timezone.now()
        period.save()
        
        serializer = self.get_serializer(period)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        Cerrar período de nómina
        """
        period = self.get_object()
        
        if period.status != 'paid':
            return Response(
                {'error': 'Solo se pueden cerrar períodos en estado "Pagado"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        period.status = 'closed'
        period.save()
        
        serializer = self.get_serializer(period)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Obtener resumen del período de nómina
        """
        period = self.get_object()
        payrolls = period.payrolls.all()
        
        total_employees = payrolls.count()
        total_gross_pay = payrolls.aggregate(Sum('gross_pay'))['gross_pay__sum'] or Decimal('0.00')
        total_net_pay = payrolls.aggregate(Sum('net_pay'))['net_pay__sum'] or Decimal('0.00')
        total_deductions = payrolls.aggregate(Sum('total_deductions'))['total_deductions__sum'] or Decimal('0.00')
        total_taxes = payrolls.aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
        average_salary = payrolls.aggregate(Avg('net_pay'))['net_pay__avg'] or Decimal('0.00')
        
        # Por departamento
        by_department = {}
        for dept in Department.objects.all():
            dept_payrolls = payrolls.filter(employee__department=dept)
            if dept_payrolls.exists():
                by_department[dept.name] = {
                    'count': dept_payrolls.count(),
                    'total': float(dept_payrolls.aggregate(Sum('net_pay'))['net_pay__sum'] or 0)
                }
        
        # Por estado
        by_status = {}
        for status_choice in Payroll.STATUS_CHOICES:
            count = payrolls.filter(status=status_choice[0]).count()
            if count > 0:
                by_status[status_choice[1]] = count
        
        summary_data = {
            'total_employees': total_employees,
            'total_gross_pay': total_gross_pay,
            'total_net_pay': total_net_pay,
            'total_deductions': total_deductions,
            'total_taxes': total_taxes,
            'average_salary': average_salary,
            'by_department': by_department,
            'by_status': by_status
        }
        
        serializer = PayrollSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def generate_payrolls(self, request, pk=None):
        """
        Generar nóminas para todos los empleados activos del período
        """
        period = self.get_object()
        
        if period.status not in ['draft', 'processing']:
            return Response(
                {'error': 'Solo se pueden generar nóminas en períodos en borrador o procesando'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BulkPayrollCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        department = serializer.validated_data.get('department')
        employee_ids = serializer.validated_data.get('employee_ids', [])
        
        # Filtrar empleados
        employees = Employee.objects.filter(status='active')
        
        if department:
            employees = employees.filter(department=department)
        
        if employee_ids:
            employees = employees.filter(id__in=employee_ids)
        
        created_count = 0
        errors = []
        
        with transaction.atomic():
            for employee in employees:
                # Verificar si ya existe
                if Payroll.objects.filter(payroll_period=period, employee=employee).exists():
                    continue
                
                try:
                    payroll = Payroll.objects.create(
                        payroll_period=period,
                        employee=employee
                    )
                    payroll.calculate_payroll()
                    created_count += 1
                except Exception as e:
                    errors.append({
                        'employee': employee.user.get_full_name(),
                        'error': str(e)
                    })
        
        period.status = 'processing'
        period.save()
        
        return Response({
            'message': f'Se crearon {created_count} nóminas',
            'created': created_count,
            'errors': errors
        })


class SalaryComponentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar componentes salariales
    """
    queryset = SalaryComponent.objects.all()
    serializer_class = SalaryComponentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['component_type', 'calculation_type', 'is_taxable', 'is_mandatory', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['component_type', 'name']


class EmployeeSalaryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar salarios de empleados
    """
    queryset = EmployeeSalary.objects.select_related('employee__user').all()
    serializer_class = EmployeeSalarySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'payment_frequency', 'is_active']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_number']
    ordering_fields = ['effective_from', 'base_salary', 'created_at']
    ordering = ['-effective_from']
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Obtener salarios actuales activos
        """
        today = timezone.now().date()
        salaries = self.queryset.filter(
            effective_from__lte=today,
            is_active=True
        ).filter(
            Q(effective_to__gte=today) | Q(effective_to__isnull=True)
        )
        
        employee_id = request.query_params.get('employee')
        if employee_id:
            salaries = salaries.filter(employee_id=employee_id)
        
        serializer = self.get_serializer(salaries, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Obtener historial de salarios de un empleado
        """
        employee_id = request.query_params.get('employee')
        
        if not employee_id:
            return Response(
                {'error': 'Se requiere el parámetro employee'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        salaries = self.queryset.filter(employee_id=employee_id).order_by('-effective_from')
        serializer = self.get_serializer(salaries, many=True)
        return Response(serializer.data)


class EmployeeSalaryComponentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar componentes salariales de empleados
    """
    queryset = EmployeeSalaryComponent.objects.select_related(
        'employee__user', 'salary_component'
    ).all()
    serializer_class = EmployeeSalaryComponentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employee', 'salary_component', 'is_recurring', 'is_active']
    ordering_fields = ['effective_from', 'created_at']
    ordering = ['-effective_from']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Obtener componentes activos de un empleado
        """
        employee_id = request.query_params.get('employee')
        
        if not employee_id:
            return Response(
                {'error': 'Se requiere el parámetro employee'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        today = timezone.now().date()
        components = self.queryset.filter(
            employee_id=employee_id,
            effective_from__lte=today,
            is_active=True
        ).filter(
            Q(effective_to__gte=today) | Q(effective_to__isnull=True)
        )
        
        serializer = self.get_serializer(components, many=True)
        return Response(serializer.data)


class PayrollViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar nóminas
    """
    queryset = Payroll.objects.select_related(
        'employee__user', 'employee__department', 'payroll_period',
        'approved_by__user'
    ).prefetch_related('payroll_items', 'adjustments').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'payroll_period', 'status', 'payment_date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_number']
    ordering_fields = ['payment_date', 'net_pay', 'created_at']
    ordering = ['-payroll_period__start_date', 'employee__employee_number']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PayrollListSerializer
        elif self.action == 'create':
            return PayrollCreateSerializer
        return PayrollDetailSerializer
    
    @action(detail=True, methods=['post'])
    def calculate(self, request, pk=None):
        """
        Calcular o recalcular nómina
        """
        payroll = self.get_object()
        
        if payroll.status not in ['draft', 'calculated']:
            return Response(
                {'error': 'Solo se pueden calcular nóminas en borrador o ya calculadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            payroll.calculate_payroll()
            serializer = PayrollDetailSerializer(payroll)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': f'Error al calcular la nómina: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar nómina
        """
        payroll = self.get_object()
        
        if payroll.status != 'calculated':
            return Response(
                {'error': 'Solo se pueden aprobar nóminas calculadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = PayrollApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payroll.status = 'approved'
        payroll.approved_by = request.user.employee_profile
        payroll.approved_at = timezone.now()
        if serializer.validated_data.get('notes'):
            payroll.notes = serializer.validated_data['notes']
        payroll.save()
        
        response_serializer = PayrollDetailSerializer(payroll)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """
        Marcar nómina como pagada y crear registro de pago
        """
        payroll = self.get_object()
        
        if payroll.status != 'approved':
            return Response(
                {'error': 'Solo se pueden pagar nóminas aprobadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = PayrollPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Crear registro de pago
            payment = PayrollPayment.objects.create(
                payroll=payroll,
                payment_method=serializer.validated_data['payment_method'],
                amount=payroll.net_pay,
                payment_date=serializer.validated_data['payment_date'],
                reference_number=serializer.validated_data.get('reference_number', ''),
                notes=serializer.validated_data.get('notes', ''),
                status='completed',
                processed_by=request.user.employee_profile,
                processed_at=timezone.now()
            )
            
            # Actualizar nómina
            payroll.status = 'paid'
            payroll.paid_at = timezone.now()
            payroll.payment_date = serializer.validated_data['payment_date']
            payroll.save()
        
        response_serializer = PayrollDetailSerializer(payroll)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancelar nómina
        """
        payroll = self.get_object()
        
        if payroll.status == 'paid':
            return Response(
                {'error': 'No se pueden cancelar nóminas pagadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payroll.status = 'cancelled'
        payroll.save()
        
        serializer = PayrollDetailSerializer(payroll)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Obtener resumen de nóminas
        """
        payroll_period_id = request.query_params.get('payroll_period')
        employee_id = request.query_params.get('employee')
        department_id = request.query_params.get('department')
        
        queryset = self.queryset
        
        if payroll_period_id:
            queryset = queryset.filter(payroll_period_id=payroll_period_id)
        
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        
        if department_id:
            queryset = queryset.filter(employee__department_id=department_id)
        
        total_employees = queryset.values('employee').distinct().count()
        total_gross_pay = queryset.aggregate(Sum('gross_pay'))['gross_pay__sum'] or Decimal('0.00')
        total_net_pay = queryset.aggregate(Sum('net_pay'))['net_pay__sum'] or Decimal('0.00')
        total_deductions = queryset.aggregate(Sum('total_deductions'))['total_deductions__sum'] or Decimal('0.00')
        total_taxes = queryset.aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
        average_salary = queryset.aggregate(Avg('net_pay'))['net_pay__avg'] or Decimal('0.00')
        
        # Por departamento
        by_department = {}
        for dept in Department.objects.all():
            dept_payrolls = queryset.filter(employee__department=dept)
            if dept_payrolls.exists():
                by_department[dept.name] = {
                    'count': dept_payrolls.count(),
                    'total': float(dept_payrolls.aggregate(Sum('net_pay'))['net_pay__sum'] or 0)
                }
        
        # Por estado
        by_status = {}
        for status_choice in Payroll.STATUS_CHOICES:
            count = queryset.filter(status=status_choice[0]).count()
            if count > 0:
                by_status[status_choice[1]] = count
        
        summary_data = {
            'total_employees': total_employees,
            'total_gross_pay': total_gross_pay,
            'total_net_pay': total_net_pay,
            'total_deductions': total_deductions,
            'total_taxes': total_taxes,
            'average_salary': average_salary,
            'by_department': by_department,
            'by_status': by_status
        }
        
        serializer = PayrollSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """
        Aprobar múltiples nóminas
        """
        payroll_ids = request.data.get('payroll_ids', [])
        
        if not payroll_ids:
            return Response(
                {'error': 'Se requiere una lista de IDs de nóminas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payrolls = self.queryset.filter(id__in=payroll_ids, status='calculated')
        
        updated = payrolls.update(
            status='approved',
            approved_by=request.user.employee_profile,
            approved_at=timezone.now()
        )
        
        return Response({
            'message': f'Se aprobaron {updated} nóminas',
            'approved_count': updated
        })


class PayrollItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar items de nómina
    """
    queryset = PayrollItem.objects.select_related('payroll', 'salary_component').all()
    serializer_class = PayrollItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['payroll', 'salary_component']


class PayrollAdjustmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar ajustes de nómina
    """
    queryset = PayrollAdjustment.objects.select_related(
        'payroll__employee__user', 'approved_by__user'
    ).all()
    serializer_class = PayrollAdjustmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['payroll', 'adjustment_type', 'is_taxable']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar ajuste
        """
        adjustment = self.get_object()
        
        if adjustment.approved_at:
            return Response(
                {'error': 'Este ajuste ya está aprobado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        adjustment.approved_by = request.user.employee_profile
        adjustment.approved_at = timezone.now()
        adjustment.save()
        
        # Recalcular la nómina si está en borrador o calculada
        if adjustment.payroll.status in ['draft', 'calculated']:
            adjustment.payroll.calculate_payroll()
        
        serializer = self.get_serializer(adjustment)
        return Response(serializer.data)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar métodos de pago
    """
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['method_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class PayrollPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar pagos de nómina
    """
    queryset = PayrollPayment.objects.select_related(
        'payroll__employee__user', 'payroll__payroll_period',
        'payment_method', 'processed_by__user'
    ).all()
    serializer_class = PayrollPaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['payroll', 'payment_method', 'status', 'payment_date']
    search_fields = [
        'payroll__employee__user__first_name',
        'payroll__employee__user__last_name',
        'reference_number'
    ]
    ordering_fields = ['payment_date', 'created_at']
    ordering = ['-payment_date']
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """
        Marcar pago como completado
        """
        payment = self.get_object()
        
        if payment.status == 'completed':
            return Response(
                {'error': 'Este pago ya está completado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = 'completed'
        payment.processed_by = request.user.employee_profile
        payment.processed_at = timezone.now()
        payment.save()
        
        # Actualizar estado de la nómina
        payment.payroll.status = 'paid'
        payment.payroll.paid_at = timezone.now()
        payment.payroll.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_failed(self, request, pk=None):
        """
        Marcar pago como fallido
        """
        payment = self.get_object()
        
        notes = request.data.get('notes', '')
        
        payment.status = 'failed'
        payment.notes = notes
        payment.processed_by = request.user.employee_profile
        payment.processed_at = timezone.now()
        payment.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)