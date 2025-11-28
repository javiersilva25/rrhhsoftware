from django.contrib import admin
from django.utils.html import format_html
from .models import (
    WorkSchedule, EmployeeSchedule, TimeSheet, Overtime,
    LeaveType, LeaveBalance, LeaveRequest, Holiday, AttendanceReport
)


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'schedule_type', 'department', 'day_of_week_display', 
                    'start_time', 'end_time', 'break_duration', 'is_active']
    list_filter = ['schedule_type', 'department', 'day_of_week', 'is_active']
    search_fields = ['name']
    ordering = ['day_of_week', 'start_time']
    
    def day_of_week_display(self, obj):
        return obj.get_day_of_week_display()
    day_of_week_display.short_description = 'Día'


@admin.register(EmployeeSchedule)
class EmployeeScheduleAdmin(admin.ModelAdmin):
    list_display = ['employee', 'work_schedule', 'effective_from', 'effective_to', 'is_active']
    list_filter = ['is_active', 'effective_from', 'work_schedule']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 
                     'employee__employee_number']
    date_hierarchy = 'effective_from'
    autocomplete_fields = ['employee', 'work_schedule']


@admin.register(TimeSheet)
class TimeSheetAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status_badge', 
                    'work_hours', 'overtime_hours', 'is_approved']
    list_filter = ['status', 'is_approved', 'date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 
                     'employee__employee_number']
    date_hierarchy = 'date'
    readonly_fields = ['work_hours', 'overtime_hours', 'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'approved_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'date', 'status')
        }),
        ('Registro de Tiempo', {
            'fields': ('check_in', 'check_out', 'break_duration', 'work_hours', 'overtime_hours')
        }),
        ('Ubicación', {
            'fields': ('ip_address', 'location')
        }),
        ('Aprobación', {
            'fields': ('is_approved', 'approved_by', 'approved_at')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'present': 'green',
            'absent': 'red',
            'late': 'orange',
            'half_day': 'blue',
            'on_leave': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    actions = ['approve_timesheets']
    
    def approve_timesheets(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            is_approved=True,
            approved_by=request.user.employee_profile,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} registros aprobados correctamente.')
    approve_timesheets.short_description = 'Aprobar registros seleccionados'


@admin.register(Overtime)
class OvertimeAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'hours', 'status_badge', 'multiplier', 
                    'approved_by', 'approved_at']
    list_filter = ['status', 'date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 
                     'employee__employee_number']
    date_hierarchy = 'date'
    readonly_fields = ['approved_at', 'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'approved_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'date', 'start_time', 'end_time', 'hours')
        }),
        ('Detalles', {
            'fields': ('reason', 'multiplier', 'status')
        }),
        ('Aprobación', {
            'fields': ('approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'days_allowed_per_year', 'is_paid', 
                    'requires_approval', 'color_preview', 'is_active']
    list_filter = ['is_paid', 'requires_approval', 'is_active']
    search_fields = ['name', 'code', 'description']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'code', 'description', 'color')
        }),
        ('Configuración', {
            'fields': ('days_allowed_per_year', 'is_paid', 'requires_approval', 
                      'carry_forward', 'attachments_required')
        }),
        ('Restricciones', {
            'fields': ('max_consecutive_days', 'notice_days_required')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 3px;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'total_days', 'used_days', 
                    'pending_days', 'available_days']
    list_filter = ['year', 'leave_type']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 
                     'employee__employee_number']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['employee', 'leave_type']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'leave_type', 'year')
        }),
        ('Balance', {
            'fields': ('total_days', 'used_days', 'pending_days', 'carried_forward')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 
                    'days_requested', 'status_badge', 'approved_by']
    list_filter = ['status', 'leave_type', 'start_date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 
                     'employee__employee_number']
    date_hierarchy = 'start_date'
    readonly_fields = ['days_requested', 'approved_at', 'cancelled_at', 
                      'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'leave_type', 'approved_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'leave_type', 'start_date', 'end_date', 'days_requested')
        }),
        ('Detalles', {
            'fields': ('reason', 'attachment', 'status')
        }),
        ('Aprobación', {
            'fields': ('approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Cancelación', {
            'fields': ('cancelled_at', 'cancellation_reason')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        from django.utils import timezone
        pending_requests = queryset.filter(status='pending')
        for leave_request in pending_requests:
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
        
        self.message_user(request, f'{pending_requests.count()} solicitudes aprobadas correctamente.')
    approve_requests.short_description = 'Aprobar solicitudes seleccionadas'
    
    def reject_requests(self, request, queryset):
        from django.utils import timezone
        pending_requests = queryset.filter(status='pending')
        for leave_request in pending_requests:
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
            leave_request.rejection_reason = 'Rechazado desde el panel de administración'
            leave_request.save()
        
        self.message_user(request, f'{pending_requests.count()} solicitudes rechazadas.')
    reject_requests.short_description = 'Rechazar solicitudes seleccionadas'


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'is_recurring', 'department', 'is_active']
    list_filter = ['is_recurring', 'is_active', 'department', 'date']
    search_fields = ['name', 'description']
    date_hierarchy = 'date'
    autocomplete_fields = ['department']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'date', 'description')
        }),
        ('Configuración', {
            'fields': ('is_recurring', 'department', 'is_active')
        }),
    )


@admin.register(AttendanceReport)
class AttendanceReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'start_date', 'end_date', 
                    'department', 'generated_by', 'created_at']
    list_filter = ['report_type', 'department', 'created_at']
    search_fields = ['name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    autocomplete_fields = ['department', 'generated_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'report_type', 'start_date', 'end_date')
        }),
        ('Filtros', {
            'fields': ('department',)
        }),
        ('Resultado', {
            'fields': ('file', 'summary_data')
        }),
        ('Metadata', {
            'fields': ('generated_by', 'created_at')
        }),
    )