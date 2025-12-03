from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import (
    PayrollPeriod, SalaryComponent, EmployeeSalary, EmployeeSalaryComponent,
    Payroll, PayrollItem, PayrollAdjustment, PaymentMethod, PayrollPayment
)


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'period_type', 'start_date', 'end_date', 
                    'payment_date', 'status_badge', 'department', 'total_payrolls_count']
    list_filter = ['period_type', 'status', 'department', 'start_date']
    search_fields = ['name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    autocomplete_fields = ['department', 'created_by', 'approved_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'period_type', 'department')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date', 'payment_date')
        }),
        ('Estado', {
            'fields': ('status', 'notes')
        }),
        ('Aprobación', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'processing': 'blue',
            'approved': 'green',
            'paid': 'darkgreen',
            'closed': 'black'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def total_payrolls_count(self, obj):
        return obj.payrolls.count()
    total_payrolls_count.short_description = 'Total Nóminas'
    
    actions = ['approve_periods']
    
    def approve_periods(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for period in queryset.filter(status='processing'):
            period.status = 'approved'
            period.approved_by = request.user.employee_profile
            period.approved_at = timezone.now()
            period.save()
            updated += 1
        
        self.message_user(request, f'{updated} períodos aprobados correctamente.')
    approve_periods.short_description = 'Aprobar períodos seleccionados'


@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'component_type_badge', 'calculation_type',
                    'default_amount', 'is_taxable', 'is_mandatory', 'is_active']
    list_filter = ['component_type', 'calculation_type', 'is_taxable', 
                   'is_mandatory', 'is_active']
    search_fields = ['name', 'code', 'description']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'code', 'description')
        }),
        ('Configuración', {
            'fields': ('component_type', 'calculation_type', 'default_amount')
        }),
        ('Opciones', {
            'fields': ('is_taxable', 'is_mandatory', 'affects_net_pay', 'is_active')
        }),
    )
    
    def component_type_badge(self, obj):
        colors = {
            'earning': 'green',
            'deduction': 'red',
            'benefit': 'blue'
        }
        color = colors.get(obj.component_type, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_component_type_display()
        )
    component_type_badge.short_description = 'Tipo'


@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'base_salary', 'payment_frequency', 'currency',
                    'effective_from', 'effective_to', 'is_active']
    list_filter = ['payment_frequency', 'currency', 'is_active', 'effective_from']
    search_fields = ['employee__user__first_name', 'employee__user__last_name',
                     'employee__employee_number']
    date_hierarchy = 'effective_from'
    readonly_fields = ['hourly_rate', 'created_at', 'updated_at']
    autocomplete_fields = ['employee']
    
    fieldsets = (
        ('Empleado', {
            'fields': ('employee',)
        }),
        ('Salario', {
            'fields': ('base_salary', 'payment_frequency', 'currency', 'hourly_rate')
        }),
        ('Vigencia', {
            'fields': ('effective_from', 'effective_to', 'is_active')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmployeeSalaryComponent)
class EmployeeSalaryComponentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'salary_component', 'amount', 'is_recurring',
                    'effective_from', 'effective_to', 'is_active']
    list_filter = ['salary_component', 'is_recurring', 'is_active', 'effective_from']
    search_fields = ['employee__user__first_name', 'employee__user__last_name',
                     'employee__employee_number']
    date_hierarchy = 'effective_from'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['employee', 'salary_component']
    
    fieldsets = (
        ('Empleado', {
            'fields': ('employee', 'salary_component')
        }),
        ('Configuración', {
            'fields': ('amount', 'is_recurring')
        }),
        ('Vigencia', {
            'fields': ('effective_from', 'effective_to', 'is_active')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
    )


class PayrollItemInline(admin.TabularInline):
    model = PayrollItem
    extra = 0
    readonly_fields = ['salary_component', 'amount', 'description', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class PayrollAdjustmentInline(admin.TabularInline):
    model = PayrollAdjustment
    extra = 1
    autocomplete_fields = ['approved_by']


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'payroll_period', 'base_salary', 'gross_pay',
                    'net_pay', 'status_badge', 'payment_date']
    list_filter = ['status', 'payroll_period', 'payment_date']
    search_fields = ['employee__user__first_name', 'employee__user__last_name',
                     'employee__employee_number']
    date_hierarchy = 'payment_date'
    readonly_fields = ['base_salary', 'hourly_rate', 'regular_hours', 'overtime_hours',
                      'gross_pay', 'total_earnings', 'total_deductions', 'total_benefits',
                      'tax_amount', 'net_pay', 'created_at', 'updated_at', 'approved_at', 'paid_at']
    autocomplete_fields = ['employee', 'payroll_period', 'approved_by']
    inlines = [PayrollItemInline, PayrollAdjustmentInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('payroll_period', 'employee', 'status')
        }),
        ('Salario Base', {
            'fields': ('base_salary', 'hourly_rate')
        }),
        ('Horas Trabajadas', {
            'fields': ('regular_hours', 'overtime_hours')
        }),
        ('Cálculos', {
            'fields': ('gross_pay', 'total_earnings', 'total_deductions', 
                      'total_benefits', 'tax_amount', 'net_pay'),
            'classes': ('collapse',)
        }),
        ('Pago', {
            'fields': ('payment_date', 'paid_at')
        }),
        ('Aprobación', {
            'fields': ('approved_by', 'approved_at')
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
            'draft': 'gray',
            'calculated': 'blue',
            'approved': 'green',
            'paid': 'darkgreen',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    actions = ['calculate_payrolls', 'approve_payrolls']
    
    def calculate_payrolls(self, request, queryset):
        calculated = 0
        errors = []
        for payroll in queryset.filter(status__in=['draft', 'calculated']):
            try:
                payroll.calculate_payroll()
                calculated += 1
            except Exception as e:
                errors.append(f"{payroll.employee.user.get_full_name()}: {str(e)}")
        
        message = f'{calculated} nóminas calculadas correctamente.'
        if errors:
            message += f' Errores: {", ".join(errors)}'
        
        self.message_user(request, message)
    calculate_payrolls.short_description = 'Calcular nóminas seleccionadas'
    
    def approve_payrolls(self, request, queryset):
        from django.utils import timezone
        approved = 0
        for payroll in queryset.filter(status='calculated'):
            payroll.status = 'approved'
            payroll.approved_by = request.user.employee_profile
            payroll.approved_at = timezone.now()
            payroll.save()
            approved += 1
        
        self.message_user(request, f'{approved} nóminas aprobadas correctamente.')
    approve_payrolls.short_description = 'Aprobar nóminas seleccionadas'


@admin.register(PayrollItem)
class PayrollItemAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'salary_component', 'amount', 'created_at']
    list_filter = ['salary_component', 'created_at']
    search_fields = ['payroll__employee__user__first_name', 
                     'payroll__employee__user__last_name']
    readonly_fields = ['created_at']
    autocomplete_fields = ['payroll', 'salary_component']


@admin.register(PayrollAdjustment)
class PayrollAdjustmentAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'adjustment_type', 'amount', 'is_taxable',
                    'approved_by', 'approved_at']
    list_filter = ['adjustment_type', 'is_taxable', 'created_at']
    search_fields = ['payroll__employee__user__first_name',
                     'payroll__employee__user__last_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    autocomplete_fields = ['payroll', 'approved_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('payroll', 'adjustment_type', 'amount')
        }),
        ('Detalles', {
            'fields': ('description', 'is_taxable')
        }),
        ('Aprobación', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'method_type', 'is_active', 'created_at']
    list_filter = ['method_type', 'is_active']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'method_type')
        }),
        ('Detalles', {
            'fields': ('description', 'is_active')
        }),
    )


@admin.register(PayrollPayment)
class PayrollPaymentAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'payment_method', 'amount', 'payment_date',
                    'status_badge', 'reference_number', 'processed_by']
    list_filter = ['status', 'payment_method', 'payment_date']
    search_fields = ['payroll__employee__user__first_name',
                     'payroll__employee__user__last_name', 'reference_number']
    date_hierarchy = 'payment_date'
    readonly_fields = ['created_at', 'updated_at', 'processed_at']
    autocomplete_fields = ['payroll', 'payment_method', 'processed_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('payroll', 'payment_method', 'amount')
        }),
        ('Detalles del Pago', {
            'fields': ('payment_date', 'reference_number', 'status')
        }),
        ('Procesamiento', {
            'fields': ('processed_by', 'processed_at')
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
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    actions = ['mark_as_completed']
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for payment in queryset.filter(status__in=['pending', 'processing']):
            payment.status = 'completed'
            payment.processed_by = request.user.employee_profile
            payment.processed_at = timezone.now()
            payment.save()
            
            # Actualizar nómina
            payment.payroll.status = 'paid'
            payment.payroll.paid_at = timezone.now()
            payment.payroll.save()
            
            updated += 1
        
        self.message_user(request, f'{updated} pagos marcados como completados.')
    mark_as_completed.short_description = 'Marcar como completado'