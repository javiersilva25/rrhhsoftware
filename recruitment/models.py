from django.db import models
from django.core.validators import EmailValidator, URLValidator
from django.utils import timezone
from employees.models import Employee, Department, Position


class JobPosting(models.Model):
    """
    Publicación de vacante laboral
    """
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('paused', 'Pausada'),
        ('closed', 'Cerrada'),
        ('filled', 'Ocupada'),
    )
    
    EMPLOYMENT_TYPE_CHOICES = (
        ('full_time', 'Tiempo Completo'),
        ('part_time', 'Medio Tiempo'),
        ('contract', 'Contrato'),
        ('temporary', 'Temporal'),
        ('internship', 'Pasantía'),
    )
    
    EXPERIENCE_LEVEL_CHOICES = (
        ('entry', 'Nivel de Entrada'),
        ('junior', 'Junior'),
        ('mid', 'Semi-Senior'),
        ('senior', 'Senior'),
        ('lead', 'Líder'),
        ('executive', 'Ejecutivo'),
    )
    
    title = models.CharField(max_length=200)
    job_code = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='job_postings')
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name='job_postings')
    
    # Detalles del trabajo
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL_CHOICES)
    location = models.CharField(max_length=200)
    remote_option = models.BooleanField(default=False)
    
    # Descripción
    description = models.TextField()
    responsibilities = models.TextField()
    requirements = models.TextField()
    preferred_qualifications = models.TextField(blank=True)
    benefits = models.TextField(blank=True)
    
    # Salario
    min_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='USD')
    show_salary = models.BooleanField(default=False, help_text='Mostrar salario en la publicación')
    
    # Vacantes
    number_of_positions = models.IntegerField(default=1)
    
    # Fechas
    posted_date = models.DateField(null=True, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Responsable
    hiring_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_job_postings'
    )
    
    # Metadata
    views_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_job_postings'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Publicación de Trabajo'
        verbose_name_plural = 'Publicaciones de Trabajo'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.job_code}"
    
    @property
    def is_active(self):
        if self.status != 'active':
            return False
        if self.application_deadline and self.application_deadline < timezone.now().date():
            return False
        return True
    
    @property
    def applications_count(self):
        return self.applications.count()


class Candidate(models.Model):
    """
    Candidato para una posición
    """
    SOURCE_CHOICES = (
        ('website', 'Sitio Web'),
        ('linkedin', 'LinkedIn'),
        ('referral', 'Referido'),
        ('job_board', 'Portal de Empleo'),
        ('recruiter', 'Reclutador'),
        ('social_media', 'Redes Sociales'),
        ('career_fair', 'Feria de Empleo'),
        ('other', 'Otro'),
    )
    
    # Información personal
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    phone = models.CharField(max_length=20)
    
    # Dirección
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Información profesional
    current_position = models.CharField(max_length=200, blank=True)
    current_company = models.CharField(max_length=200, blank=True)
    years_of_experience = models.IntegerField(null=True, blank=True)
    education_level = models.CharField(max_length=100, blank=True)
    
    # Documentos
    resume = models.FileField(upload_to='candidates/resumes/', null=True, blank=True)
    cover_letter = models.FileField(upload_to='candidates/cover_letters/', null=True, blank=True)
    portfolio_url = models.URLField(blank=True, validators=[URLValidator()])
    linkedin_url = models.URLField(blank=True, validators=[URLValidator()])
    
    # Salario esperado
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='USD')
    
    # Disponibilidad
    available_from = models.DateField(null=True, blank=True)
    notice_period_days = models.IntegerField(null=True, blank=True, help_text='Días de preaviso en trabajo actual')
    
    # Origen
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    referred_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_candidates'
    )
    
    # Notas
    notes = models.TextField(blank=True)
    
    # Tags para búsqueda
    skills = models.TextField(blank=True, help_text='Habilidades separadas por comas')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Candidato'
        verbose_name_plural = 'Candidatos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


class Application(models.Model):
    """
    Solicitud de empleo
    """
    STATUS_CHOICES = (
        ('applied', 'Aplicado'),
        ('screening', 'En Revisión'),
        ('shortlisted', 'Preseleccionado'),
        ('interviewing', 'En Entrevista'),
        ('assessment', 'En Evaluación'),
        ('offer', 'Oferta Extendida'),
        ('hired', 'Contratado'),
        ('rejected', 'Rechazado'),
        ('withdrawn', 'Retirado'),
    )
    
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    current_stage = models.ForeignKey(
        'RecruitmentStage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Calificación
    rating = models.IntegerField(null=True, blank=True, help_text='Calificación de 1 a 5')
    
    # Fechas
    applied_date = models.DateTimeField(auto_now_add=True)
    status_changed_at = models.DateTimeField(auto_now=True)
    
    # Asignación
    assigned_recruiter = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_applications'
    )
    
    # Notas y comentarios
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Solicitud'
        verbose_name_plural = 'Solicitudes'
        unique_together = ['candidate', 'job_posting']
        ordering = ['-applied_date']
    
    def __str__(self):
        return f"{self.candidate.get_full_name()} - {self.job_posting.title}"


class RecruitmentStage(models.Model):
    """
    Etapa del proceso de reclutamiento
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text='Orden en el proceso')
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name='stages',
        null=True,
        blank=True,
        help_text='Dejar en blanco para etapa global'
    )
    duration_days = models.IntegerField(default=7, help_text='Duración estimada en días')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Etapa de Reclutamiento'
        verbose_name_plural = 'Etapas de Reclutamiento'
        ordering = ['order']
    
    def __str__(self):
        return self.name


class Interview(models.Model):
    """
    Entrevista con candidato
    """
    INTERVIEW_TYPE_CHOICES = (
        ('phone', 'Teléfono'),
        ('video', 'Video'),
        ('in_person', 'Presencial'),
        ('technical', 'Técnica'),
        ('panel', 'Panel'),
    )
    
    STATUS_CHOICES = (
        ('scheduled', 'Programada'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
        ('rescheduled', 'Reprogramada'),
        ('no_show', 'No Asistió'),
    )
    
    RESULT_CHOICES = (
        ('pass', 'Aprobado'),
        ('fail', 'Rechazado'),
        ('pending', 'Pendiente'),
    )
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPE_CHOICES)
    
    # Fecha y hora
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    duration_minutes = models.IntegerField(default=60)
    
    # Ubicación/Link
    location = models.CharField(max_length=255, blank=True)
    meeting_link = models.URLField(blank=True, validators=[URLValidator()])
    
    # Entrevistadores
    interviewers = models.ManyToManyField(Employee, related_name='interviews')
    
    # Estado y resultado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='pending')
    
    # Feedback
    notes = models.TextField(blank=True)
    candidate_strengths = models.TextField(blank=True)
    candidate_weaknesses = models.TextField(blank=True)
    overall_rating = models.IntegerField(null=True, blank=True, help_text='Calificación de 1 a 5')
    recommendation = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Entrevista'
        verbose_name_plural = 'Entrevistas'
        ordering = ['-scheduled_date', '-scheduled_time']
    
    def __str__(self):
        return f"{self.application.candidate.get_full_name()} - {self.get_interview_type_display()} ({self.scheduled_date})"


class Assessment(models.Model):
    """
    Evaluación o prueba técnica
    """
    STATUS_CHOICES = (
        ('sent', 'Enviada'),
        ('in_progress', 'En Progreso'),
        ('submitted', 'Entregada'),
        ('graded', 'Calificada'),
        ('expired', 'Expirada'),
    )
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='assessments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assessment_type = models.CharField(max_length=100, help_text='Tipo de evaluación (técnica, personalidad, etc.)')
    
    # Archivos
    assessment_file = models.FileField(upload_to='assessments/', null=True, blank=True)
    submission_file = models.FileField(upload_to='assessments/submissions/', null=True, blank=True)
    
    # Enlaces
    assessment_url = models.URLField(blank=True, validators=[URLValidator()])
    
    # Fechas
    sent_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    submitted_date = models.DateTimeField(null=True, blank=True)
    
    # Calificación
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    obtained_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    
    # Evaluador
    evaluator = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluated_assessments'
    )
    
    # Feedback
    feedback = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Evaluación'
        verbose_name_plural = 'Evaluaciones'
        ordering = ['-sent_date']
    
    def __str__(self):
        return f"{self.title} - {self.application.candidate.get_full_name()}"
    
    @property
    def is_passed(self):
        if self.obtained_score is None:
            return None
        return self.obtained_score >= self.passing_score


class JobOffer(models.Model):
    """
    Oferta de trabajo
    """
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('sent', 'Enviada'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
        ('expired', 'Expirada'),
        ('withdrawn', 'Retirada'),
    )
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='offers')
    
    # Detalles de la oferta
    position_title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    
    # Compensación
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    salary_currency = models.CharField(max_length=3, default='USD')
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Fechas
    offer_date = models.DateField()
    expiry_date = models.DateField()
    proposed_start_date = models.DateField()
    
    # Documentos
    offer_letter = models.FileField(upload_to='job_offers/', null=True, blank=True)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Respuesta del candidato
    candidate_response_date = models.DateTimeField(null=True, blank=True)
    candidate_notes = models.TextField(blank=True)
    
    # Aprobación
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_offers'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_offers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Oferta de Trabajo'
        verbose_name_plural = 'Ofertas de Trabajo'
        ordering = ['-offer_date']
    
    def __str__(self):
        return f"Oferta para {self.application.candidate.get_full_name()} - {self.position_title}"


class OnboardingTask(models.Model):
    """
    Tareas de onboarding para nuevos empleados
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('skipped', 'Omitida'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    order = models.IntegerField(default=0)
    
    # Asignación
    job_offer = models.ForeignKey(
        JobOffer,
        on_delete=models.CASCADE,
        related_name='onboarding_tasks',
        null=True,
        blank=True
    )
    assigned_to = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_onboarding_tasks'
    )
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Fechas
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Notas
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tarea de Onboarding'
        verbose_name_plural = 'Tareas de Onboarding'
        ordering = ['order', 'due_date']
    
    def __str__(self):
        return self.title


class RecruitmentReport(models.Model):
    """
    Reportes de reclutamiento
    """
    REPORT_TYPE_CHOICES = (
        ('applications', 'Solicitudes'),
        ('time_to_hire', 'Tiempo de Contratación'),
        ('source_effectiveness', 'Efectividad de Fuentes'),
        ('pipeline', 'Pipeline de Reclutamiento'),
        ('custom', 'Personalizado'),
    )
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Filtros
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    job_posting = models.ForeignKey(
        JobPosting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Resultado
    file = models.FileField(upload_to='recruitment_reports/', null=True, blank=True)
    summary_data = models.JSONField(null=True, blank=True)
    
    # Generación
    generated_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Reporte de Reclutamiento'
        verbose_name_plural = 'Reportes de Reclutamiento'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.start_date} to {self.end_date}"