from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from employees.models import Employee, Department
from attendance.models import TimeSheet, Overtime
from decimal import Decimal


class PayrollPeriod(models.Model):
    """
    Período de nómina (mensual, quincenal, semanal)
    """
    PERIOD_TYPE_CHOICES = (
        ('weekly', 'Semanal'),
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual'),
        ('custom', 'Personalizado'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('processing', 'Procesando'),
        ('approved', 'Aprobado'),
        ('paid', 'Pagado'),
        ('closed', 'Cerrado'),
    )
    
    name = models.CharField(max_length=100)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    payment_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Dejar en blanco para aplicar a todos los departamentos'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_payroll_periods'
    )
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payroll_periods'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Período de Nómina'
        verbose_name_plural = 'Períodos de Nómina'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"


class SalaryComponent(models.Model):
    """
    Componentes del salario (conceptos de pago y deducciones)
    """
    COMPONENT_TYPE_CHOICES = (
        ('earning', 'Ingreso'),
        ('deduction', 'Deducción'),
        ('benefit', 'Beneficio'),
    )
    
    CALCULATION_TYPE_CHOICES = (
        ('fixed', 'Monto Fijo'),
        ('percentage', 'Porcentaje del Salario Base'),
        ('hourly', 'Por Hora'),
        ('daily', 'Por Día'),
    )
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPE_CHOICES)
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPE_CHOICES)
    default_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text='Monto fijo o porcentaje según el tipo de cálculo'
    )
    is_taxable = models.BooleanField(default=True, help_text='¿Está sujeto a impuestos?')
    is_mandatory = models.BooleanField(default=False, help_text='¿Es obligatorio para todos los empleados?')
    affects_net_pay = models.BooleanField(default=True, help_text='¿Afecta el salario neto?')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Componente Salarial'
        verbose_name_plural = 'Componentes Salariales'
        ordering = ['component_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"


class EmployeeSalary(models.Model):
    """
    Salario del empleado
    """
    PAYMENT_FREQUENCY_CHOICES = (
        ('weekly', 'Semanal'),
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salaries')
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_frequency = models.CharField(max_length=20, choices=PAYMENT_FREQUENCY_CHOICES)
    currency = models.CharField(max_length=3, default='USD')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    hourly_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text='Tasa por hora (calculada automáticamente si no se especifica)'
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Salario del Empleado'
        verbose_name_plural = 'Salarios de Empleados'
        ordering = ['-effective_from']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.base_salary} {self.currency}"
    
    def calculate_hourly_rate(self):
        """Calcula la tasa por hora basada en el salario base"""
        if self.payment_frequency == 'monthly':
            # Asumiendo 160 horas al mes (4 semanas * 40 horas)
            return self.base_salary / 160
        elif self.payment_frequency == 'biweekly':
            # Asumiendo 80 horas quincenales (2 semanas * 40 horas)
            return self.base_salary / 80
        elif self.payment_frequency == 'weekly':
            # Asumiendo 40 horas semanales
            return self.base_salary / 40
        return Decimal('0.00')
    
    def save(self, *args, **kwargs):
        if not self.hourly_rate:
            self.hourly_rate = self.calculate_hourly_rate()
        super().save(*args, **kwargs)


class EmployeeSalaryComponent(models.Model):
    """
    Componentes salariales específicos del empleado
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_components')
    salary_component = models.ForeignKey(SalaryComponent, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_recurring = models.BooleanField(default=True, help_text='¿Se aplica automáticamente cada período?')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Componente Salarial del Empleado'
        verbose_name_plural = 'Componentes Salariales de Empleados'
        ordering = ['employee', 'salary_component']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.salary_component.name}"


class Payroll(models.Model):
    """
    Nómina individual de un empleado
    """
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('approved', 'Aprobado'),
        ('paid', 'Pagado'),
        ('cancelled', 'Cancelado'),
    )
    
    payroll_period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name='payrolls')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='payrolls')
    
    # Información del salario
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Horas trabajadas
    regular_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    
    # Totales
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_benefits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Impuestos
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Fechas
    payment_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payrolls'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Nómina'
        verbose_name_plural = 'Nóminas'
        unique_together = ['payroll_period', 'employee']
        ordering = ['-payroll_period__start_date', 'employee__employee_number']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.payroll_period.name}"
    
    def calculate_payroll(self):
        """Calcula todos los componentes de la nómina"""
        # Obtener el salario actual del empleado
        try:
            employee_salary = EmployeeSalary.objects.filter(
                employee=self.employee,
                effective_from__lte=self.payroll_period.end_date,
                is_active=True
            ).filter(
                models.Q(effective_to__gte=self.payroll_period.start_date) | 
                models.Q(effective_to__isnull=True)
            ).first()
            
            if not employee_salary:
                raise ValueError(f"No hay salario activo para {self.employee.user.get_full_name()}")
            
            self.base_salary = employee_salary.base_salary
            self.hourly_rate = employee_salary.hourly_rate or employee_salary.calculate_hourly_rate()
            
        except Exception as e:
            raise ValueError(f"Error al obtener salario: {str(e)}")
        
        # Calcular horas trabajadas desde TimeSheet
        timesheets = TimeSheet.objects.filter(
            employee=self.employee,
            date__range=[self.payroll_period.start_date, self.payroll_period.end_date],
            is_approved=True
        )
        
        self.regular_hours = sum([ts.work_hours for ts in timesheets])
        self.overtime_hours = sum([ts.overtime_hours for ts in timesheets])
        
        # Calcular salario bruto
        if employee_salary.payment_frequency == 'monthly':
            self.gross_pay = self.base_salary
        else:
            # Para frecuencias no mensuales, calcular basado en horas
            self.gross_pay = (self.regular_hours * self.hourly_rate)
        
        # Agregar horas extras
        overtime_records = Overtime.objects.filter(
            employee=self.employee,
            date__range=[self.payroll_period.start_date, self.payroll_period.end_date],
            status='approved'
        )
        
        overtime_pay = sum([
            ot.hours * self.hourly_rate * ot.multiplier 
            for ot in overtime_records
        ])
        
        self.gross_pay += Decimal(str(overtime_pay))
        
        # Inicializar totales
        self.total_earnings = self.gross_pay
        self.total_deductions = Decimal('0.00')
        self.total_benefits = Decimal('0.00')
        
        # Calcular componentes adicionales
        self._calculate_components()
        
        # Calcular impuestos
        self._calculate_taxes()
        
        # Calcular salario neto
        self.net_pay = self.gross_pay + self.total_earnings - self.total_deductions - self.tax_amount
        
        self.status = 'calculated'
        self.save()
    
    def _calculate_components(self):
        """Calcula los componentes salariales adicionales"""
        # Obtener componentes del empleado
        employee_components = EmployeeSalaryComponent.objects.filter(
            employee=self.employee,
            effective_from__lte=self.payroll_period.end_date,
            is_active=True,
            is_recurring=True
        ).filter(
            models.Q(effective_to__gte=self.payroll_period.start_date) | 
            models.Q(effective_to__isnull=True)
        ).select_related('salary_component')
        
        # Borrar componentes existentes
        self.payroll_items.all().delete()
        
        for emp_component in employee_components:
            component = emp_component.salary_component
            
            # Calcular monto
            if component.calculation_type == 'fixed':
                amount = emp_component.amount
            elif component.calculation_type == 'percentage':
                amount = self.base_salary * (emp_component.amount / 100)
            elif component.calculation_type == 'hourly':
                amount = self.regular_hours * emp_component.amount
            elif component.calculation_type == 'daily':
                working_days = (self.payroll_period.end_date - self.payroll_period.start_date).days + 1
                amount = working_days * emp_component.amount
            else:
                amount = emp_component.amount
            
            # Crear item de nómina
            PayrollItem.objects.create(
                payroll=self,
                salary_component=component,
                amount=amount,
                description=component.description
            )
            
            # Actualizar totales
            if component.component_type == 'earning':
                self.total_earnings += amount
            elif component.component_type == 'deduction':
                self.total_deductions += amount
            elif component.component_type == 'benefit':
                self.total_benefits += amount
    
    def _calculate_taxes(self):
        """Calcula los impuestos"""
        # Obtener información fiscal del empleado
        try:
            tax_info = self.employee.tax_info
            taxable_income = self.gross_pay + self.total_earnings
            
            # Aplicar porcentaje de retención
            self.tax_amount = taxable_income * (tax_info.withholding_percentage / 100)
            
            # Agregar retención adicional
            self.tax_amount += tax_info.additional_withholding
            
        except Exception:
            # Si no hay información fiscal, aplicar tasa por defecto
            self.tax_amount = Decimal('0.00')


class PayrollItem(models.Model):
    """
    Items individuales de la nómina (ingresos, deducciones, beneficios)
    """
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='payroll_items')
    salary_component = models.ForeignKey(SalaryComponent, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Item de Nómina'
        verbose_name_plural = 'Items de Nómina'
        ordering = ['salary_component__component_type', 'salary_component__name']
    
    def __str__(self):
        return f"{self.payroll.employee.user.get_full_name()} - {self.salary_component.name}: {self.amount}"


class PayrollAdjustment(models.Model):
    """
    Ajustes manuales a la nómina (bonos, deducciones especiales, etc.)
    """
    ADJUSTMENT_TYPE_CHOICES = (
        ('bonus', 'Bono'),
        ('commission', 'Comisión'),
        ('allowance', 'Asignación'),
        ('reimbursement', 'Reembolso'),
        ('deduction', 'Deducción'),
        ('correction', 'Corrección'),
        ('other', 'Otro'),
    )
    
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    is_taxable = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_adjustments'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ajuste de Nómina'
        verbose_name_plural = 'Ajustes de Nómina'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.payroll.employee.user.get_full_name()} - {self.get_adjustment_type_display()}: {self.amount}"


class PaymentMethod(models.Model):
    """
    Métodos de pago
    """
    METHOD_TYPE_CHOICES = (
        ('bank_transfer', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('cash', 'Efectivo'),
        ('paypal', 'PayPal'),
        ('other', 'Otro'),
    )
    
    name = models.CharField(max_length=100)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Método de Pago'
        verbose_name_plural = 'Métodos de Pago'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PayrollPayment(models.Model):
    """
    Registro de pagos de nómina
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    )
    
    payroll = models.OneToOneField(Payroll, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    reference_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_payments'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pago de Nómina'
        verbose_name_plural = 'Pagos de Nómina'
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payroll.employee.user.get_full_name()} - {self.amount} ({self.payment_date})"