from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

class User(AbstractUser):
    """
    Usuario extendido para el sistema RRHH
    """
    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('hr', 'Recursos Humanos'),
        ('manager', 'Manager'),
        ('employee', 'Empleado'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"


class Department(models.Model):
    """
    Departamento de la empresa
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_departments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Position(models.Model):
    """
    Cargo o posición laboral
    """
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    description = models.TextField(blank=True)
    level = models.CharField(max_length=50, blank=True)  # Junior, Senior, etc.
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Posición'
        verbose_name_plural = 'Posiciones'
        ordering = ['title']
    
    def __str__(self):
        return f"{self.title} - {self.department.name}"


class Employee(models.Model):
    """
    Información del empleado
    """
    GENDER_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    )
    
    MARITAL_STATUS_CHOICES = (
        ('single', 'Soltero/a'),
        ('married', 'Casado/a'),
        ('divorced', 'Divorciado/a'),
        ('widowed', 'Viudo/a'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('suspended', 'Suspendido'),
        ('terminated', 'Terminado'),
    )
    
    # Relación con usuario
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    
    # Información personal
    employee_number = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    nationality = models.CharField(max_length=50)
    
    # Documentos de identidad
    identification_type = models.CharField(max_length=50)  # DNI, Pasaporte, etc.
    identification_number = models.CharField(max_length=50, unique=True)
    
    # Contacto
    personal_email = models.EmailField(blank=True)
    mobile_phone = models.CharField(max_length=20)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    emergency_contact_relationship = models.CharField(max_length=50)
    
    # Dirección
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Información laboral
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name='employees')
    manager = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='subordinates'
    )
    hire_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=50)  # Full-time, Part-time, Contract
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['employee_number']
    
    def __str__(self):
        return f"{self.employee_number} - {self.user.get_full_name()}"


class BankAccount(models.Model):
    """
    Información bancaria del empleado
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    account_type = models.CharField(max_length=50)  # Checking, Savings
    routing_number = models.CharField(max_length=50, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cuenta Bancaria'
        verbose_name_plural = 'Cuentas Bancarias'
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.bank_name}"


class TaxInformation(models.Model):
    """
    Información fiscal del empleado
    """
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='tax_info')
    tax_id = models.CharField(max_length=50, unique=True)  # RUT, RFC, etc.
    tax_regime = models.CharField(max_length=100)
    withholding_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    additional_withholding = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    exemptions = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Información Fiscal'
        verbose_name_plural = 'Información Fiscal'
    
    def __str__(self):
        return f"Tax Info - {self.employee.user.get_full_name()}"


class Insurance(models.Model):
    """
    Seguros del empleado
    """
    INSURANCE_TYPE_CHOICES = (
        ('health', 'Salud'),
        ('life', 'Vida'),
        ('dental', 'Dental'),
        ('vision', 'Visión'),
        ('disability', 'Discapacidad'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='insurances')
    insurance_type = models.CharField(max_length=50, choices=INSURANCE_TYPE_CHOICES)
    provider = models.CharField(max_length=100)
    policy_number = models.CharField(max_length=50)
    coverage_start_date = models.DateField()
    coverage_end_date = models.DateField(null=True, blank=True)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    employee_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    employer_contribution = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    beneficiaries = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Seguro'
        verbose_name_plural = 'Seguros'
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.get_insurance_type_display()}"


class EmploymentHistory(models.Model):
    """
    Historial laboral dentro de la empresa
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employment_history')
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    position = models.ForeignKey(Position, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    change_reason = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Historial Laboral'
        verbose_name_plural = 'Historiales Laborales'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.position.title} ({self.start_date})"