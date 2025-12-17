from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from employees.models import Employee, Department


class PerformanceReviewCycle(models.Model):
    """
    Ciclo de evaluación de desempeño
    """
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    )
    
    REVIEW_TYPE_CHOICES = (
        ('annual', 'Anual'),
        ('semi_annual', 'Semestral'),
        ('quarterly', 'Trimestral'),
        ('probation', 'Período de Prueba'),
        ('project_based', 'Basado en Proyecto'),
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES)
    
    # Fechas
    start_date = models.DateField()
    end_date = models.DateField()
    self_review_deadline = models.DateField(null=True, blank=True)
    manager_review_deadline = models.DateField(null=True, blank=True)
    
    # Alcance
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Dejar en blanco para aplicar a toda la empresa'
    )
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Configuración
    enable_self_review = models.BooleanField(default=True)
    enable_peer_review = models.BooleanField(default=False)
    enable_360_review = models.BooleanField(default=False)
    
    # Metadata
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_review_cycles'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ciclo de Evaluación'
        verbose_name_plural = 'Ciclos de Evaluación'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    @property
    def is_active(self):
        today = timezone.now().date()
        return self.status == 'active' and self.start_date <= today <= self.end_date


class CompetencyCategory(models.Model):
    """
    Categoría de competencias
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Categoría de Competencia'
        verbose_name_plural = 'Categorías de Competencias'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Competency(models.Model):
    """
    Competencia o habilidad a evaluar
    """
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        CompetencyCategory,
        on_delete=models.CASCADE,
        related_name='competencies'
    )
    description = models.TextField()
    
    # Niveles de competencia
    level_1_description = models.TextField(help_text='Nivel Básico')
    level_2_description = models.TextField(help_text='Nivel Intermedio')
    level_3_description = models.TextField(help_text='Nivel Avanzado')
    level_4_description = models.TextField(help_text='Nivel Experto')
    level_5_description = models.TextField(help_text='Nivel Maestro')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Competencia'
        verbose_name_plural = 'Competencias'
        ordering = ['category__order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category.name})"


class PerformanceReview(models.Model):
    """
    Evaluación de desempeño individual
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('self_review', 'Auto-Evaluación en Progreso'),
        ('manager_review', 'Evaluación del Manager en Progreso'),
        ('peer_review', 'Evaluación de Pares en Progreso'),
        ('completed', 'Completada'),
        ('approved', 'Aprobada'),
    )
    
    OVERALL_RATING_CHOICES = (
        (1, 'Necesita Mejora'),
        (2, 'Por Debajo de las Expectativas'),
        (3, 'Cumple las Expectativas'),
        (4, 'Supera las Expectativas'),
        (5, 'Excepcional'),
    )
    
    review_cycle = models.ForeignKey(
        PerformanceReviewCycle,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='performance_reviews'
    )
    reviewer = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews_conducted'
    )
    
    # Estado
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    # Calificaciones generales
    overall_rating = models.IntegerField(
        choices=OVERALL_RATING_CHOICES,
        null=True,
        blank=True
    )
    self_rating = models.IntegerField(
        choices=OVERALL_RATING_CHOICES,
        null=True,
        blank=True
    )
    manager_rating = models.IntegerField(
        choices=OVERALL_RATING_CHOICES,
        null=True,
        blank=True
    )
    
    # Comentarios
    self_review_comments = models.TextField(blank=True)
    manager_comments = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    
    # Fechas
    self_review_completed_at = models.DateTimeField(null=True, blank=True)
    manager_review_completed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Evaluación de Desempeño'
        verbose_name_plural = 'Evaluaciones de Desempeño'
        unique_together = ['review_cycle', 'employee']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.review_cycle.name}"


class CompetencyRating(models.Model):
    """
    Calificación de competencia en una evaluación
    """
    RATING_TYPE_CHOICES = (
        ('self', 'Auto-Evaluación'),
        ('manager', 'Evaluación del Manager'),
        ('peer', 'Evaluación de Par'),
    )
    
    performance_review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.CASCADE,
        related_name='competency_ratings'
    )
    competency = models.ForeignKey(Competency, on_delete=models.PROTECT)
    rating_type = models.CharField(max_length=20, choices=RATING_TYPE_CHOICES)
    
    # Calificación (1-5)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Comentarios
    comments = models.TextField(blank=True)
    
    # Evaluador (para peer reviews)
    rated_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competency_ratings_given'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Calificación de Competencia'
        verbose_name_plural = 'Calificaciones de Competencias'
        ordering = ['competency__category__order', 'competency__name']
    
    def __str__(self):
        return f"{self.competency.name} - {self.rating}/5"


class Goal(models.Model):
    """
    Meta u objetivo del empleado
    """
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
        ('overdue', 'Vencido'),
    )
    
    GOAL_TYPE_CHOICES = (
        ('individual', 'Individual'),
        ('team', 'Equipo'),
        ('company', 'Empresa'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    )
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='goals'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Fechas
    start_date = models.DateField()
    target_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    
    # Progreso
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Métricas
    is_measurable = models.BooleanField(default=False)
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Valor objetivo (si es medible)'
    )
    current_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Valor actual (si es medible)'
    )
    unit_of_measure = models.CharField(
        max_length=50,
        blank=True,
        help_text='Unidad de medida (ej: ventas, %, puntos)'
    )
    
    # Aprobación
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinate_goals'
    )
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_goals'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Relación con evaluación
    performance_review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='goals'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Meta'
        verbose_name_plural = 'Metas'
        ordering = ['-priority', '-target_date']
    
    def __str__(self):
        return f"{self.title} - {self.employee.user.get_full_name()}"
    
    def update_status(self):
        """Actualizar estado basado en fechas y progreso"""
        today = timezone.now().date()
        
        if self.progress_percentage == 100:
            self.status = 'completed'
            if not self.completed_date:
                self.completed_date = today
        elif self.target_date < today and self.status != 'completed':
            self.status = 'overdue'
        elif self.status == 'draft':
            pass
        else:
            self.status = 'active'
        
        self.save()


class GoalCheckIn(models.Model):
    """
    Check-in o actualización de progreso de meta
    """
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='check_ins')
    progress_percentage = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    current_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    notes = models.TextField()
    challenges = models.TextField(blank=True)
    support_needed = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Check-In de Meta'
        verbose_name_plural = 'Check-Ins de Metas'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.goal.title} - {self.progress_percentage}% ({self.created_at.date()})"


class Feedback(models.Model):
    """
    Retroalimentación entre empleados
    """
    FEEDBACK_TYPE_CHOICES = (
        ('positive', 'Positiva'),
        ('constructive', 'Constructiva'),
        ('recognition', 'Reconocimiento'),
        ('coaching', 'Coaching'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('submitted', 'Enviada'),
        ('acknowledged', 'Reconocida'),
    )
    
    from_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='feedback_given'
    )
    to_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='feedback_received'
    )
    
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    
    # Privacidad
    is_anonymous = models.BooleanField(default=False)
    is_private = models.BooleanField(
        default=True,
        help_text='Si es privado, solo el destinatario puede verlo'
    )
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Relación con evaluación
    performance_review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback_items'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Retroalimentación'
        verbose_name_plural = 'Retroalimentaciones'
        ordering = ['-created_at']
    
    def __str__(self):
        from_name = 'Anónimo' if self.is_anonymous else self.from_employee.user.get_full_name()
        return f"{from_name} → {self.to_employee.user.get_full_name()}: {self.subject}"


class DevelopmentPlan(models.Model):
    """
    Plan de desarrollo individual (IDP)
    """
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('active', 'Activo'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    )
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='development_plans'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Fechas
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Aprobación
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='subordinate_development_plans'
    )
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_development_plans'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Relación con evaluación
    performance_review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='development_plans'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plan de Desarrollo'
        verbose_name_plural = 'Planes de Desarrollo'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.employee.user.get_full_name()}"


class DevelopmentAction(models.Model):
    """
    Acción o actividad dentro de un plan de desarrollo
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    )
    
    ACTION_TYPE_CHOICES = (
        ('training', 'Capacitación'),
        ('mentoring', 'Mentoría'),
        ('job_shadowing', 'Job Shadowing'),
        ('stretch_assignment', 'Asignación Desafiante'),
        ('certification', 'Certificación'),
        ('reading', 'Lectura/Estudio'),
        ('conference', 'Conferencia/Evento'),
        ('other', 'Otro'),
    )
    
    development_plan = models.ForeignKey(
        DevelopmentPlan,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    action_type = models.CharField(max_length=30, choices=ACTION_TYPE_CHOICES)
    
    # Fechas
    target_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Recursos
    resources_needed = models.TextField(blank=True)
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Resultado
    outcome = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Acción de Desarrollo'
        verbose_name_plural = 'Acciones de Desarrollo'
        ordering = ['target_date']
    
    def __str__(self):
        return f"{self.title} - {self.development_plan.employee.user.get_full_name()}"


class PerformanceImprovementPlan(models.Model):
    """
    Plan de mejora de desempeño (PIP)
    """
    STATUS_CHOICES = (
        ('active', 'Activo'),
        ('successful', 'Exitoso'),
        ('unsuccessful', 'No Exitoso'),
        ('cancelled', 'Cancelado'),
    )
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='improvement_plans'
    )
    manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_improvement_plans'
    )
    
    # Detalles
    title = models.CharField(max_length=200)
    performance_issues = models.TextField(help_text='Problemas de desempeño identificados')
    expected_improvements = models.TextField(help_text='Mejoras esperadas')
    support_provided = models.TextField(help_text='Apoyo que se proporcionará')
    consequences = models.TextField(help_text='Consecuencias si no se cumplen las expectativas')
    
    # Fechas
    start_date = models.DateField()
    end_date = models.DateField()
    review_frequency_days = models.IntegerField(
        default=30,
        help_text='Frecuencia de revisiones en días'
    )
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    final_outcome = models.TextField(blank=True)
    
    # Relación con evaluación
    performance_review = models.ForeignKey(
        PerformanceReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='improvement_plans'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plan de Mejora de Desempeño'
        verbose_name_plural = 'Planes de Mejora de Desempeño'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PIP - {self.employee.user.get_full_name()} ({self.start_date})"


class PIPCheckIn(models.Model):
    """
    Check-in de progreso en PIP
    """
    improvement_plan = models.ForeignKey(
        PerformanceImprovementPlan,
        on_delete=models.CASCADE,
        related_name='check_ins'
    )
    check_in_date = models.DateField()
    progress_summary = models.TextField()
    areas_of_improvement = models.TextField()
    areas_of_concern = models.TextField(blank=True)
    next_steps = models.TextField()
    
    # Evaluación
    is_on_track = models.BooleanField(default=True)
    
    # Metadata
    conducted_by = models.ForeignKey(Employee, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Check-In de PIP'
        verbose_name_plural = 'Check-Ins de PIP'
        ordering = ['-check_in_date']
    
    def __str__(self):
        return f"PIP Check-In - {self.improvement_plan.employee.user.get_full_name()} ({self.check_in_date})"