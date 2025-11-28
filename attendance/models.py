from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from employees.models import Employee, Department
from datetime import datetime, timedelta


class WorkSchedule(models.Model):
    """
    Horario de trabajo
    """
    SCHEDULE_TYPE_CHOICES = (
        ('fixed', 'Fijo'),
        ('flexible', 'Flexible'),
        ('shift', 'Por turnos'),
    )
    
    DAY_CHOICES = (
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    )
    
    name = models.CharField(max_length=100)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES)
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='work_schedules',
        null=True,
        blank=True
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration = models.IntegerField(default=0, help_text='Duración del descanso en minutos')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Horario de Trabajo'
        verbose_name_plural = 'Horarios de Trabajo'
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.name} - {self.get_day_of_week_display()}: {self.start_time} - {self.end_time}"
    
    def get_total_hours(self):
        """Calcula las horas totales del horario"""
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        if end < start:
            end += timedelta(days=1)
        total_minutes = (end - start).total_seconds() / 60
        total_minutes -= self.break_duration
        return total_minutes / 60


class EmployeeSchedule(models.Model):
    """
    Asignación de horario a empleado
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='schedules')
    work_schedule = models.ForeignKey(WorkSchedule, on_delete=models.CASCADE)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Horario del Empleado'
        verbose_name_plural = 'Horarios de Empleados'
        ordering = ['-effective_from']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.work_schedule.name}"


class TimeSheet(models.Model):
    """
    Registro de asistencia diaria
    """
    STATUS_CHOICES = (
        ('present', 'Presente'),
        ('absent', 'Ausente'),
        ('late', 'Tarde'),
        ('half_day', 'Medio día'),
        ('on_leave', 'Con permiso'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='timesheets')
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    work_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    break_duration = models.IntegerField(default=0, help_text='Duración del descanso en minutos')
    notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, help_text='Ubicación GPS o nombre del lugar')
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_timesheets'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Registro de Asistencia'
        verbose_name_plural = 'Registros de Asistencia'
        unique_together = ['employee', 'date']
        ordering = ['-date', '-check_in']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.date}"
    
    def calculate_work_hours(self):
        """Calcula las horas trabajadas"""
        if self.check_in and self.check_out:
            total_time = self.check_out - self.check_in
            total_minutes = total_time.total_seconds() / 60
            total_minutes -= self.break_duration
            hours = total_minutes / 60
            
            # Obtener horario esperado del empleado
            try:
                employee_schedule = self.employee.schedules.filter(
                    effective_from__lte=self.date,
                    is_active=True
                ).filter(
                    models.Q(effective_to__gte=self.date) | models.Q(effective_to__isnull=True)
                ).first()
                
                if employee_schedule:
                    expected_hours = employee_schedule.work_schedule.get_total_hours()
                    if hours > expected_hours:
                        self.work_hours = expected_hours
                        self.overtime_hours = hours - expected_hours
                    else:
                        self.work_hours = hours
                        self.overtime_hours = 0
                else:
                    self.work_hours = hours
            except:
                self.work_hours = hours
            
            self.save()
    
    def save(self, *args, **kwargs):
        # Auto-calcular horas si hay check-in y check-out
        if self.check_in and self.check_out and self.work_hours == 0:
            self.calculate_work_hours()
        super().save(*args, **kwargs)


class Overtime(models.Model):
    """
    Registro de horas extras
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='overtimes')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    hours = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    multiplier = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=1.5,
        help_text='Multiplicador de pago (1.5 = 150%, 2.0 = 200%)'
    )
    approved_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_overtimes'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Hora Extra'
        verbose_name_plural = 'Horas Extras'
        ordering = ['-date', '-start_time']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.date} ({self.hours}h)"


class LeaveType(models.Model):
    """
    Tipos de permisos/ausencias
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    days_allowed_per_year = models.IntegerField(default=0, help_text='0 = ilimitado')
    requires_approval = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=True)
    carry_forward = models.BooleanField(
        default=False, 
        help_text='¿Se pueden acumular días no usados para el próximo año?'
    )
    max_consecutive_days = models.IntegerField(
        default=0, 
        help_text='Máximo de días consecutivos permitidos. 0 = sin límite'
    )
    notice_days_required = models.IntegerField(
        default=0, 
        help_text='Días de anticipación requeridos para solicitar'
    )
    attachments_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    color = models.CharField(max_length=7, default='#3B82F6', help_text='Color hexadecimal para el calendario')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Permiso'
        verbose_name_plural = 'Tipos de Permisos'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    """
    Balance de días de permiso por empleado
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    total_days = models.DecimalField(max_digits=5, decimal_places=2)
    used_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pending_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Balance de Permisos'
        verbose_name_plural = 'Balances de Permisos'
        unique_together = ['employee', 'leave_type', 'year']
        ordering = ['-year', 'leave_type']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.leave_type.name} ({self.year})"
    
    @property
    def available_days(self):
        return self.total_days - self.used_days - self.pending_days


class LeaveRequest(models.Model):
    """
    Solicitud de permiso/ausencia
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attachment = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    approved_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Solicitud de Permiso'
        verbose_name_plural = 'Solicitudes de Permisos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    def calculate_days(self):
        """Calcula los días de permiso (excluyendo fines de semana y festivos)"""
        from datetime import timedelta
        
        current_date = self.start_date
        total_days = 0
        
        while current_date <= self.end_date:
            # Verificar si es fin de semana (5=sábado, 6=domingo)
            if current_date.weekday() < 5:
                # Verificar si es festivo
                is_holiday = Holiday.objects.filter(
                    date=current_date,
                    is_active=True
                ).exists()
                
                if not is_holiday:
                    total_days += 1
            
            current_date += timedelta(days=1)
        
        self.days_requested = total_days
        return total_days
    
    def save(self, *args, **kwargs):
        # Auto-calcular días si no está definido
        if not self.days_requested or self.days_requested == 0:
            self.calculate_days()
        super().save(*args, **kwargs)


class Holiday(models.Model):
    """
    Días festivos de la empresa
    """
    name = models.CharField(max_length=100)
    date = models.DateField()
    is_recurring = models.BooleanField(
        default=False, 
        help_text='¿Se repite cada año en la misma fecha?'
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text='Dejar en blanco para aplicar a toda la empresa'
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Día Festivo'
        verbose_name_plural = 'Días Festivos'
        ordering = ['date']
    
    def __str__(self):
        return f"{self.name} - {self.date}"


class AttendanceReport(models.Model):
    """
    Reportes de asistencia generados
    """
    REPORT_TYPE_CHOICES = (
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('custom', 'Personalizado'),
    )
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    generated_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='attendance_reports/', null=True, blank=True)
    summary_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Reporte de Asistencia'
        verbose_name_plural = 'Reportes de Asistencia'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.start_date} to {self.end_date}"