from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Department, Position, Employee,
    BankAccount, TaxInformation, Insurance, EmploymentHistory
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('role', 'phone', 'profile_picture')}),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'manager', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'department', 'level', 'min_salary', 'max_salary']
    search_fields = ['title', 'code']
    list_filter = ['department', 'level']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_number', 'get_full_name', 'department', 'position', 'status', 'hire_date']
    search_fields = ['employee_number', 'user__first_name', 'user__last_name', 'identification_number']
    list_filter = ['status', 'department', 'employment_type']
    date_hierarchy = 'hire_date'
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Nombre Completo'


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['employee', 'bank_name', 'account_type', 'is_primary']
    list_filter = ['bank_name', 'account_type', 'is_primary']


@admin.register(TaxInformation)
class TaxInformationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'tax_id', 'tax_regime']
    search_fields = ['tax_id']


@admin.register(Insurance)
class InsuranceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'insurance_type', 'provider', 'coverage_start_date', 'is_active']
    list_filter = ['insurance_type', 'is_active', 'provider']


@admin.register(EmploymentHistory)
class EmploymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'department', 'position', 'start_date', 'end_date', 'salary']
    list_filter = ['department', 'start_date']
    date_hierarchy = 'start_date'