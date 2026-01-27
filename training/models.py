from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from employees.models import Employee, Department


class TrainingCategory(models.Model):
    """
    Categoría de capacitación
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, default='#3B82F6')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Categoría de Capacitación'
        verbose_name_plural = 'Categorías de Capacitación'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TrainingProvider(models.Model):
    """
    Proveedor de capacitación
    """
    PROVIDER_TYPE_CHOICES = (
        ('internal', 'Interno'),
        ('external', 'Externo'),
        ('online', 'En Línea'),
    )
    
    name = models.CharField(max_length=200)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPE_CHOICES)
    contact_name = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Proveedor de Capacitación'
        verbose_name_plural = 'Proveedores de Capacitación'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Course(models.Model):
    """
    Curso o programa de capacitación
    """
    LEVEL_CHOICES = (
        ('beginner', 'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
        ('expert', 'Experto'),
    )
    
    DELIVERY_METHOD_CHOICES = (
        ('in_person', 'Presencial'),
        ('online', 'En Línea'),
        ('hybrid', 'Híbrido'),
        ('self_paced', 'Auto-Dirigido'),
    )
    
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(TrainingCategory, on_delete=models.PROTECT, related_name='courses')
    provider = models.ForeignKey(TrainingProvider, on_delete=models.PROTECT, related_name='courses')
    
    # Descripción
    description = models.TextField()
    objectives = models.TextField(help_text='Objetivos de aprendizaje')
    prerequisites = models.TextField(blank=True, help_text='Requisitos previos')
    
    # Nivel y duración
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    duration_hours = models.DecimalField(max_digits=6, decimal_places=2, help_text='Duración en horas')
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES)
    
    # Costos
    cost_per_person = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Capacidad
    max_participants = models.IntegerField(null=True, blank=True, help_text='Máximo de participantes por sesión')
    
    # Contenido
    syllabus = models.TextField(blank=True, help_text='Programa o temario del curso')
    materials_url = models.URLField(blank=True, help_text='Enlace a materiales del curso')
    
    # Certificación
    provides_certificate = models.BooleanField(default=False)
    certificate_validity_days = models.IntegerField(
        null=True,
        blank=True,
        help_text='Días de validez del certificado (dejar en blanco para indefinido)'
    )
    
    # Estado
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_courses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['title']
    
    def __str__(self):
        return f"{self.title} ({self.code})"


class TrainingSession(models.Model):
    """
    Sesión de capacitación (instancia específica de un curso)
    """
    STATUS_CHOICES = (
        ('scheduled', 'Programada'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ('postponed', 'Pospuesta'),
    )
    
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='sessions')
    session_name = models.CharField(max_length=200, help_text='Nombre identificador de la sesión')
    
    # Fechas
    start_date = models.DateField()
    end_date = models.DateField()
    registration_deadline = models.DateField(null=True, blank=True)
    
    # Ubicación
    location = models.CharField(max_length=200, blank=True, help_text='Ubicación física o enlace virtual')
    venue_details = models.TextField(blank=True)
    
    # Instructor
    instructor = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instructed_sessions'
    )
    external_instructor_name = models.CharField(max_length=200, blank=True)
    external_instructor_bio = models.TextField(blank=True)
    
    # Capacidad
    max_participants = models.IntegerField(help_text='Máximo de participantes')
    min_participants = models.IntegerField(default=1, help_text='Mínimo de participantes')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Costos
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    budget_code = models.CharField(max_length=50, blank=True)
    
    # Notas
    notes = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sessions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Sesión de Capacitación'
        verbose_name_plural = 'Sesiones de Capacitación'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.session_name} - {self.start_date}"
    
    @property
    def available_spots(self):
        enrolled_count = self.enrollments.filter(status='enrolled').count()
        return self.max_participants - enrolled_count
    
    @property
    def is_full(self):
        return self.available_spots <= 0


class TrainingEnrollment(models.Model):
    """
    Inscripción de empleado a sesión de capacitación
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('enrolled', 'Inscrito'),
        ('completed', 'Completado'),
        ('failed', 'Reprobado'),
        ('cancelled', 'Cancelado'),
        ('no_show', 'No Asistió'),
    )
    
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name='enrollments')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_enrollments')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Aprobación
    requires_manager_approval = models.BooleanField(default=True)
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_enrollments'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Asistencia
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Evaluación
    pre_assessment_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Puntuación pre-capacitación'
    )
    post_assessment_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Puntuación post-capacitación'
    )
    final_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Calificación final'
    )
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    
    # Feedback
    participant_feedback = models.TextField(blank=True)
    instructor_feedback = models.TextField(blank=True)
    
    # Certificación
    certificate_issued = models.BooleanField(default=False)
    certificate_issue_date = models.DateField(null=True, blank=True)
    certificate_expiry_date = models.DateField(null=True, blank=True)
    certificate_file = models.FileField(upload_to='training_certificates/', null=True, blank=True)
    
    # Metadata
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Inscripción a Capacitación'
        verbose_name_plural = 'Inscripciones a Capacitaciones'
        unique_together = ['session', 'employee']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.session.session_name}"
    
    @property
    def has_passed(self):
        if self.final_score is None:
            return None
        return self.final_score >= self.passing_score


class TrainingAttendance(models.Model):
    """
    Asistencia a sesiones de capacitación
    """
    STATUS_CHOICES = (
        ('present', 'Presente'),
        ('absent', 'Ausente'),
        ('late', 'Tarde'),
        ('excused', 'Justificado'),
    )
    
    enrollment = models.ForeignKey(TrainingEnrollment, on_delete=models.CASCADE, related_name='attendance_records')
    session_date = models.DateField()
    session_topic = models.CharField(max_length=200, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Metadata
    recorded_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_attendances'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Asistencia a Capacitación'
        verbose_name_plural = 'Asistencias a Capacitaciones'
        unique_together = ['enrollment', 'session_date']
        ordering = ['-session_date']
    
    def __str__(self):
        return f"{self.enrollment.employee.user.get_full_name()} - {self.session_date} ({self.get_status_display()})"


class TrainingAssessment(models.Model):
    """
    Evaluación de capacitación
    """
    ASSESSMENT_TYPE_CHOICES = (
        ('pre', 'Pre-Evaluación'),
        ('post', 'Post-Evaluación'),
        ('quiz', 'Quiz'),
        ('exam', 'Examen'),
        ('practical', 'Práctica'),
    )
    
    enrollment = models.ForeignKey(TrainingEnrollment, on_delete=models.CASCADE, related_name='assessments')
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPE_CHOICES)
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Puntuación
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    obtained_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    
    # Fechas
    assigned_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    submitted_date = models.DateTimeField(null=True, blank=True)
    graded_date = models.DateTimeField(null=True, blank=True)
    
    # Archivos
    assessment_file = models.FileField(upload_to='training_assessments/', null=True, blank=True)
    submission_file = models.FileField(upload_to='training_submissions/', null=True, blank=True)
    
    # Feedback
    feedback = models.TextField(blank=True)
    
    # Evaluador
    graded_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_assessments'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Evaluación de Capacitación'
        verbose_name_plural = 'Evaluaciones de Capacitaciones'
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.title} - {self.enrollment.employee.user.get_full_name()}"
    
    @property
    def has_passed(self):
        if self.obtained_score is None:
            return None
        return self.obtained_score >= self.passing_score


class Certification(models.Model):
    """
    Certificación profesional
    """
    STATUS_CHOICES = (
        ('active', 'Activa'),
        ('expired', 'Vencida'),
        ('revoked', 'Revocada'),
        ('pending_renewal', 'Pendiente de Renovación'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='certifications')
    enrollment = models.ForeignKey(
        TrainingEnrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certifications'
    )
    
    # Información de la certificación
    certification_name = models.CharField(max_length=200)
    certification_number = models.CharField(max_length=100, blank=True)
    issuing_organization = models.CharField(max_length=200)
    
    # Fechas
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Documentos
    certificate_file = models.FileField(upload_to='certifications/', null=True, blank=True)
    verification_url = models.URLField(blank=True, help_text='URL para verificar la certificación')
    
    # Metadata
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Certificación'
        verbose_name_plural = 'Certificaciones'
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.certification_name} - {self.employee.user.get_full_name()}"
    
    def check_expiry(self):
        """Verificar si la certificación ha vencido"""
        if self.expiry_date and self.expiry_date < timezone.now().date():
            if self.status == 'active':
                self.status = 'expired'
                self.save()
                return True
        return False


class TrainingBudget(models.Model):
    """
    Presupuesto de capacitación
    """
    year = models.IntegerField()
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='training_budgets'
    )
    
    # Presupuesto
    allocated_budget = models.DecimalField(max_digits=12, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # Metadata
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_budgets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Presupuesto de Capacitación'
        verbose_name_plural = 'Presupuestos de Capacitación'
        unique_together = ['year', 'department']
        ordering = ['-year']
    
    def __str__(self):
        dept_name = self.department.name if self.department else 'General'
        return f"Presupuesto {self.year} - {dept_name}"
    
    @property
    def remaining_budget(self):
        return self.allocated_budget - self.spent_amount
    
    @property
    def utilization_percentage(self):
        if self.allocated_budget > 0:
            return (self.spent_amount / self.allocated_budget) * 100
        return 0


class TrainingRequest(models.Model):
    """
    Solicitud de capacitación
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('scheduled', 'Programado'),
        ('completed', 'Completado'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='training_requests')
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requests'
    )
    
    # Detalles de la solicitud
    training_title = models.CharField(max_length=200, help_text='Título de la capacitación solicitada')
    justification = models.TextField(help_text='Justificación de la solicitud')
    expected_benefits = models.TextField(help_text='Beneficios esperados')
    
    # Fechas preferidas
    preferred_start_date = models.DateField(null=True, blank=True)
    preferred_end_date = models.DateField(null=True, blank=True)
    
    # Costos estimados
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Aprobación
    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_training_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Sesión asignada
    assigned_session = models.ForeignKey(
        TrainingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requests'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Solicitud de Capacitación'
        verbose_name_plural = 'Solicitudes de Capacitación'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.training_title} - {self.employee.user.get_full_name()}"


class TrainingFeedback(models.Model):
    """
    Retroalimentación de capacitación
    """
    enrollment = models.OneToOneField(
        TrainingEnrollment,
        on_delete=models.CASCADE,
        related_name='detailed_feedback'
    )
    
    # Calificaciones (1-5)
    content_quality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Calidad del contenido'
    )
    instructor_effectiveness = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Efectividad del instructor'
    )
    materials_quality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Calidad de los materiales'
    )
    relevance_to_job = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Relevancia para el trabajo'
    )
    overall_satisfaction = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='Satisfacción general'
    )
    
    # Comentarios
    strengths = models.TextField(blank=True, help_text='Fortalezas de la capacitación')
    improvements = models.TextField(blank=True, help_text='Áreas de mejora')
    additional_comments = models.TextField(blank=True)
    
    # Recomendación
    would_recommend = models.BooleanField(default=True)
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Retroalimentación de Capacitación'
        verbose_name_plural = 'Retroalimentaciones de Capacitaciones'
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Feedback - {self.enrollment.employee.user.get_full_name()}"
    
    @property
    def average_rating(self):
        return (
            self.content_quality +
            self.instructor_effectiveness +
            self.materials_quality +
            self.relevance_to_job +
            self.overall_satisfaction
        ) / 5