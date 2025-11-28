from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    WorkSchedule, EmployeeSchedule, TimeSheet, Overtime,
    LeaveType, LeaveBalance, LeaveRequest, Holiday, AttendanceReport
)
from employees.models import Employee


class WorkScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo WorkSchedule
    """
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    schedule_type_display = serializers.CharField(source='get_schedule_type_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    total_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkSchedule
        fields = [
            'id', 'name', 'schedule_type', 'schedule_type_display',
            'department', 'department_name', 'day_of_week', 'day_of_week_display',
            'start_time', 'end_time', 'break_duration', 'total_hours',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_hours(self, obj):
        return round(obj.get_total_hours(), 2)


class EmployeeScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo EmployeeSchedule
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    work_schedule_details = WorkScheduleSerializer(source='work_schedule', read_only=True)
    
    class Meta:
        model = EmployeeSchedule
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'work_schedule', 'work_schedule_details', 'effective_from',
            'effective_to', 'is_active', 'notes', 'created_at', 'updated_at'
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


class TimeSheetSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo TimeSheet
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = TimeSheet
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'date', 'check_in', 'check_out', 'status', 'status_display',
            'work_hours', 'overtime_hours', 'break_duration',
            'notes', 'ip_address', 'location', 'is_approved',
            'approved_by', 'approved_by_name', 'approved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'work_hours', 'overtime_hours', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validaciones de TimeSheet
        """
        if data.get('check_out') and data.get('check_in'):
            if data['check_out'] <= data['check_in']:
                raise serializers.ValidationError(
                    "La hora de salida debe ser posterior a la hora de entrada"
                )
        
        # Validar que no exista otro registro para el mismo empleado y fecha
        employee = data.get('employee')
        date = data.get('date')
        instance_id = self.instance.id if self.instance else None
        
        existing = TimeSheet.objects.filter(employee=employee, date=date)
        if instance_id:
            existing = existing.exclude(id=instance_id)
        
        if existing.exists():
            raise serializers.ValidationError(
                "Ya existe un registro de asistencia para este empleado en esta fecha"
            )
        
        return data


class TimeSheetCheckInSerializer(serializers.Serializer):
    """
    Serializer para check-in rápido
    """
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    check_in = serializers.DateTimeField(default=timezone.now)
    ip_address = serializers.IPAddressField(required=False)
    location = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class TimeSheetCheckOutSerializer(serializers.Serializer):
    """
    Serializer para check-out rápido
    """
    check_out = serializers.DateTimeField(default=timezone.now)


class OvertimeSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Overtime
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = Overtime
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'date', 'start_time', 'end_time', 'hours', 'reason',
            'status', 'status_display', 'multiplier',
            'approved_by', 'approved_by_name', 'approved_at',
            'rejection_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validaciones de Overtime
        """
        if data.get('end_time') and data.get('start_time'):
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError(
                    "La hora de fin debe ser posterior a la hora de inicio"
                )
        
        return data


class LeaveTypeSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo LeaveType
    """
    class Meta:
        model = LeaveType
        fields = [
            'id', 'name', 'code', 'description', 'days_allowed_per_year',
            'requires_approval', 'is_paid', 'carry_forward',
            'max_consecutive_days', 'notice_days_required',
            'attachments_required', 'is_active', 'color',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo LeaveBalance
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    available_days = serializers.ReadOnlyField()
    
    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'leave_type', 'leave_type_name', 'leave_type_code',
            'year', 'total_days', 'used_days', 'pending_days',
            'carried_forward', 'available_days', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'available_days', 'created_at', 'updated_at']


class LeaveRequestSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo LeaveRequest
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)
    leave_type_code = serializers.CharField(source='leave_type.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_number',
            'leave_type', 'leave_type_name', 'leave_type_code',
            'start_date', 'end_date', 'days_requested', 'reason',
            'status', 'status_display', 'attachment',
            'approved_by', 'approved_by_name', 'approved_at',
            'rejection_reason', 'cancelled_at', 'cancellation_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'days_requested', 'created_at', 'updated_at']
    
    def validate(self, data):
        """
        Validaciones de LeaveRequest
        """
        # Validar fechas
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "La fecha de fin no puede ser anterior a la fecha de inicio"
                )
        
        # Validar días de anticipación requeridos
        leave_type = data.get('leave_type')
        start_date = data.get('start_date')
        
        if leave_type and start_date:
            days_difference = (start_date - timezone.now().date()).days
            if days_difference < leave_type.notice_days_required:
                raise serializers.ValidationError(
                    f"Este tipo de permiso requiere {leave_type.notice_days_required} días de anticipación"
                )
            
            # Validar días consecutivos máximos
            if leave_type.max_consecutive_days > 0:
                instance = LeaveRequest()
                instance.start_date = data['start_date']
                instance.end_date = data['end_date']
                days = instance.calculate_days()
                
                if days > leave_type.max_consecutive_days:
                    raise serializers.ValidationError(
                        f"Este tipo de permiso permite máximo {leave_type.max_consecutive_days} días consecutivos"
                    )
        
        # Validar balance disponible
        employee = data.get('employee')
        if employee and leave_type and start_date:
            year = start_date.year
            try:
                balance = LeaveBalance.objects.get(
                    employee=employee,
                    leave_type=leave_type,
                    year=year
                )
                
                instance = LeaveRequest()
                instance.start_date = data['start_date']
                instance.end_date = data['end_date']
                days_requested = instance.calculate_days()
                
                if balance.available_days < days_requested:
                    raise serializers.ValidationError(
                        f"Balance insuficiente. Disponible: {balance.available_days} días, Solicitado: {days_requested} días"
                    )
            except LeaveBalance.DoesNotExist:
                if leave_type.days_allowed_per_year > 0:
                    raise serializers.ValidationError(
                        "No existe balance de permisos para este año"
                    )
        
        return data


class HolidaySerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Holiday
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Holiday
        fields = [
            'id', 'name', 'date', 'is_recurring', 'department',
            'department_name', 'description', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AttendanceReportSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo AttendanceReport
    """
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = AttendanceReport
        fields = [
            'id', 'name', 'report_type', 'report_type_display',
            'start_date', 'end_date', 'department', 'department_name',
            'generated_by', 'generated_by_name', 'file',
            'summary_data', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AttendanceSummarySerializer(serializers.Serializer):
    """
    Serializer para resúmenes de asistencia
    """
    total_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    half_days = serializers.IntegerField()
    on_leave_days = serializers.IntegerField()
    total_work_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_overtime_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    attendance_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)