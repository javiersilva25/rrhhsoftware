from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import (
    PayrollPeriod, SalaryComponent, EmployeeSalary, EmployeeSalaryComponent,
    Payroll, PayrollItem, PayrollAdjustment, PaymentMethod, PayrollPayment
)
from employees.models import Employee


class PayrollPeriodSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo PayrollPeriod
    """
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    total_payrolls = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = PayrollPeriod
        fields = [
            'id', 'name', 'period_type', 'period_type_display',
            'start_date', 'end_date', 'payment_date', 'status', 'status_display',
            'department', 'department_name', 'notes', 'created_by', 'created_by_name',
            'approved_by', 'approved_by_name', 'approved_at',
            'total_payrolls', 'total_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_payrolls(self, obj):
        return obj.payrolls.count()
    
    def get_total_amount(self, obj):
        total = sum([p.net_pay for p in obj.payrolls.all()])
        return float(total)
    
    def validate(self, data):
        """
        Validar que las fechas sean coherentes
        """
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio"
                )
        
        if data.get('payment_date') and data.get('end_date'):
            if data['payment_date'] < data['end_date']:
                raise serializers.ValidationError(
                    "La fecha de pago no puede ser anterior a la fecha de fin del período"
                )
        
        return data


class SalaryComponentSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo SalaryComponent
    """
    component_type_display = serializers.CharField(source='get_component_type_display', read_only=True)
    calculation_type_display = serializers.CharField(source='get_calculation_type_display', read_only=True)
    
    class Meta:
        model = SalaryComponent
        fields = [
            'id', 'name', 'code', 'component_type', 'component_type_display',
            'calculation_type', 'calculation_type_display', 'default_amount',
            'is_taxable', 'is_mandatory', 'affects_net_pay', 'description',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSalarySerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo EmployeeSalary
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    payment_frequency_display = serializers.CharField(source='get_payment_frequency_display', read_only=True)
    
    class Meta:
        model = EmployeeSalary
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'base_salary', 'payment_frequency', 'payment_frequency_display',
            'currency', 'effective_from', 'effective_to', 'hourly_rate',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'hourly_rate', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validar que las fechas sean coherentes
        """
        if data.get('effective_to') and data.get('effective_from'):
            if data['effective_to'] < data['effective_from']:
                raise serializers.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio"
                )
        
        # Validar que no haya solapamiento de salarios activos
        employee = data.get('employee')
        effective_from = data.get('effective_from')
        effective_to = data.get('effective_to')
        
        if employee and effective_from:
            instance_id = self.instance.id if self.instance else None
            
            existing = EmployeeSalary.objects.filter(
                employee=employee,
                is_active=True,
                effective_from__lte=effective_from
            )
            
            if effective_to:
                existing = existing.filter(
                    models.Q(effective_to__gte=effective_from) | 
                    models.Q(effective_to__isnull=True)
                )
            
            if instance_id:
                existing = existing.exclude(id=instance_id)
            
            if existing.exists():
                raise serializers.ValidationError(
                    "Ya existe un salario activo que se solapa con este período"
                )
        
        return data


class EmployeeSalaryComponentSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo EmployeeSalaryComponent
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    component_name = serializers.CharField(source='salary_component.name', read_only=True)
    component_type = serializers.CharField(source='salary_component.component_type', read_only=True)
    component_type_display = serializers.CharField(source='salary_component.get_component_type_display', read_only=True)
    
    class Meta:
        model = EmployeeSalaryComponent
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'salary_component', 'component_name', 'component_type', 'component_type_display',
            'amount', 'is_recurring', 'effective_from', 'effective_to',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validar que las fechas sean coherentes
        """
        if data.get('effective_to') and data.get('effective_from'):
            if data['effective_to'] < data['effective_from']:
                raise serializers.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio"
                )
        
        return data


class PayrollItemSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo PayrollItem
    """
    component_name = serializers.CharField(source='salary_component.name', read_only=True)
    component_code = serializers.CharField(source='salary_component.code', read_only=True)
    component_type = serializers.CharField(source='salary_component.component_type', read_only=True)
    component_type_display = serializers.CharField(source='salary_component.get_component_type_display', read_only=True)
    
    class Meta:
        model = PayrollItem
        fields = [
            'id', 'payroll', 'salary_component', 'component_name',
            'component_code', 'component_type', 'component_type_display',
            'amount', 'description', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PayrollAdjustmentSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo PayrollAdjustment
    """
    adjustment_type_display = serializers.CharField(source='get_adjustment_type_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = PayrollAdjustment
        fields = [
            'id', 'payroll', 'adjustment_type', 'adjustment_type_display',
            'amount', 'description', 'is_taxable', 'approved_by',
            'approved_by_name', 'approved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de nóminas
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    period_name = serializers.CharField(source='payroll_period.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'payroll_period', 'period_name', 'base_salary',
            'gross_pay', 'net_pay', 'status', 'status_display',
            'payment_date', 'created_at'
        ]


class PayrollDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para nóminas
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    employee_department = serializers.CharField(source='employee.department.name', read_only=True)
    period_name = serializers.CharField(source='payroll_period.name', read_only=True)
    period_start = serializers.DateField(source='payroll_period.start_date', read_only=True)
    period_end = serializers.DateField(source='payroll_period.end_date', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    payroll_items = PayrollItemSerializer(many=True, read_only=True)
    adjustments = PayrollAdjustmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'payroll_period', 'period_name', 'period_start', 'period_end',
            'employee', 'employee_name', 'employee_number', 'employee_department',
            'base_salary', 'hourly_rate', 'regular_hours', 'overtime_hours',
            'gross_pay', 'total_earnings', 'total_deductions', 'total_benefits',
            'tax_amount', 'net_pay', 'status', 'status_display',
            'payment_date', 'paid_at', 'notes', 'approved_by', 'approved_by_name',
            'approved_at', 'payroll_items', 'adjustments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'base_salary', 'hourly_rate', 'regular_hours', 'overtime_hours',
            'gross_pay', 'total_earnings', 'total_deductions', 'total_benefits',
            'tax_amount', 'net_pay', 'created_at', 'updated_at'
        ]


class PayrollCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear nóminas
    """
    class Meta:
        model = Payroll
        fields = [
            'payroll_period', 'employee', 'notes'
        ]
    
    def validate(self, data):
        """
        Validar que no exista ya una nómina para este empleado en este período
        """
        payroll_period = data.get('payroll_period')
        employee = data.get('employee')
        
        if Payroll.objects.filter(payroll_period=payroll_period, employee=employee).exists():
            raise serializers.ValidationError(
                "Ya existe una nómina para este empleado en este período"
            )
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Crear la nómina y calcularla automáticamente
        """
        payroll = Payroll.objects.create(**validated_data)
        
        try:
            payroll.calculate_payroll()
        except Exception as e:
            raise serializers.ValidationError(f"Error al calcular la nómina: {str(e)}")
        
        return payroll


class PayrollCalculateSerializer(serializers.Serializer):
    """
    Serializer para recalcular nóminas
    """
    recalculate = serializers.BooleanField(default=True)


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo PaymentMethod
    """
    method_type_display = serializers.CharField(source='get_method_type_display', read_only=True)
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'name', 'method_type', 'method_type_display',
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollPaymentSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo PayrollPayment
    """
    employee_name = serializers.CharField(source='payroll.employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='payroll.employee.employee_number', read_only=True)
    period_name = serializers.CharField(source='payroll.payroll_period.name', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = PayrollPayment
        fields = [
            'id', 'payroll', 'employee_name', 'employee_number', 'period_name',
            'payment_method', 'payment_method_name', 'amount', 'payment_date',
            'reference_number', 'status', 'status_display', 'notes',
            'processed_by', 'processed_by_name', 'processed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollSummarySerializer(serializers.Serializer):
    """
    Serializer para resúmenes de nómina
    """
    total_employees = serializers.IntegerField()
    total_gross_pay = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_net_pay = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_deductions = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_taxes = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_department = serializers.DictField()
    by_status = serializers.DictField()


class BulkPayrollCreateSerializer(serializers.Serializer):
    """
    Serializer para crear nóminas en lote
    """
    payroll_period = serializers.PrimaryKeyRelatedField(queryset=PayrollPeriod.objects.all())
    department = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        required=False,
        allow_null=True
    )
    employee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='Lista de IDs de empleados. Si está vacío, se crearán para todos los empleados activos'
    )


class PayrollApproveSerializer(serializers.Serializer):
    """
    Serializer para aprobar nóminas
    """
    notes = serializers.CharField(required=False, allow_blank=True)


class PayrollPaySerializer(serializers.Serializer):
    """
    Serializer para marcar nóminas como pagadas
    """
    payment_method = serializers.PrimaryKeyRelatedField(queryset=PaymentMethod.objects.all())
    payment_date = serializers.DateField()
    reference_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)