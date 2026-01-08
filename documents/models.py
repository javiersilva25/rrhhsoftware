from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from employees.models import Employee, Department


class DocumentCategory(models.Model):
    """
    Categoría de documentos
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Nombre del icono')
    color = models.CharField(max_length=7, default='#3B82F6', help_text='Color hexadecimal')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Categoría de Documento'
        verbose_name_plural = 'Categorías de Documentos'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DocumentType(models.Model):
    """
    Tipo de documento
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.CASCADE,
        related_name='document_types'
    )
    description = models.TextField(blank=True)
    
    # Configuración
    requires_approval = models.BooleanField(default=False)
    requires_signature = models.BooleanField(default=False)
    is_confidential = models.BooleanField(default=False)
    expires = models.BooleanField(default=False, help_text='¿El documento tiene fecha de vencimiento?')
    default_expiry_days = models.IntegerField(
        null=True,
        blank=True,
        help_text='Días hasta el vencimiento por defecto'
    )
    
    # Permisos
    allowed_extensions = models.CharField(
        max_length=200,
        default='pdf,doc,docx,jpg,png',
        help_text='Extensiones permitidas separadas por coma'
    )
    max_file_size_mb = models.IntegerField(default=10, help_text='Tamaño máximo en MB')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documentos'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.category.name})"


class Document(models.Model):
    """
    Documento del empleado
    """
    STATUS_CHOICES = (
        ('draft', 'Borrador'),
        ('pending_approval', 'Pendiente de Aprobación'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('expired', 'Vencido'),
        ('archived', 'Archivado'),
    )
    
    VISIBILITY_CHOICES = (
        ('private', 'Privado'),
        ('employee', 'Empleado'),
        ('manager', 'Manager'),
        ('hr', 'RRHH'),
        ('public', 'Público'),
    )
    
    # Información básica
    title = models.CharField(max_length=200)
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, related_name='documents')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    
    # Archivo
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt', 'xls', 'xlsx'])]
    )
    file_size = models.BigIntegerField(help_text='Tamaño del archivo en bytes')
    file_extension = models.CharField(max_length=10)
    
    # Metadata
    description = models.TextField(blank=True)
    reference_number = models.CharField(max_length=100, blank=True, help_text='Número de referencia o folio')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    
    # Fechas
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Aprobación
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_documents'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Firma digital
    requires_signature = models.BooleanField(default=False)
    is_signed = models.BooleanField(default=False)
    
    # Versiones
    version = models.IntegerField(default=1)
    parent_document = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions'
    )
    
    # Tags para búsqueda
    tags = models.CharField(max_length=500, blank=True, help_text='Tags separados por coma')
    
    # Metadata
    uploaded_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.employee.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if self.file:
            # Obtener tamaño del archivo
            self.file_size = self.file.size
            # Obtener extensión
            self.file_extension = self.file.name.split('.')[-1].lower()
        super().save(*args, **kwargs)
    
    def check_expiry(self):
        """Verificar si el documento ha vencido"""
        if self.expiry_date and self.expiry_date < timezone.now().date():
            if self.status not in ['expired', 'archived']:
                self.status = 'expired'
                self.save()
                return True
        return False


class DocumentTemplate(models.Model):
    """
    Plantilla de documento
    """
    name = models.CharField(max_length=200)
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, related_name='templates')
    description = models.TextField(blank=True)
    
    # Archivo de plantilla
    template_file = models.FileField(
        upload_to='document_templates/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])]
    )
    
    # Campos dinámicos (JSON)
    fields_schema = models.JSONField(
        null=True,
        blank=True,
        help_text='Esquema de campos dinámicos en formato JSON'
    )
    
    # Estado
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plantilla de Documento'
        verbose_name_plural = 'Plantillas de Documentos'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DocumentSignature(models.Model):
    """
    Firma digital de documento
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('signed', 'Firmado'),
        ('rejected', 'Rechazado'),
    )
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signatures')
    signer = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='document_signatures')
    
    # Orden de firma
    signing_order = models.IntegerField(default=1, help_text='Orden en el que debe firmar')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Firma
    signature_data = models.TextField(blank=True, help_text='Datos de la firma (base64 o hash)')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Fechas
    signed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Firma de Documento'
        verbose_name_plural = 'Firmas de Documentos'
        unique_together = ['document', 'signer']
        ordering = ['signing_order', 'created_at']
    
    def __str__(self):
        return f"{self.document.title} - {self.signer.user.get_full_name()}"


class DocumentShare(models.Model):
    """
    Compartir documento con otros usuarios
    """
    PERMISSION_CHOICES = (
        ('view', 'Ver'),
        ('download', 'Descargar'),
        ('edit', 'Editar'),
    )
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='shares')
    shared_with = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='shared_documents'
    )
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    
    # Compartido por
    shared_by = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='documents_shared_by_me'
    )
    
    # Fechas
    expires_at = models.DateTimeField(null=True, blank=True)
    accessed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Documento Compartido'
        verbose_name_plural = 'Documentos Compartidos'
        unique_together = ['document', 'shared_with']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document.title} compartido con {self.shared_with.user.get_full_name()}"


class DocumentVersion(models.Model):
    """
    Historial de versiones de documentos
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='version_history')
    version_number = models.IntegerField()
    file = models.FileField(upload_to='document_versions/%Y/%m/')
    
    # Cambios
    change_summary = models.TextField(help_text='Resumen de cambios en esta versión')
    
    # Metadata
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Versión de Documento'
        verbose_name_plural = 'Versiones de Documentos'
        unique_together = ['document', 'version_number']
        ordering = ['-version_number']
    
    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"


class DocumentRequest(models.Model):
    """
    Solicitud de documento
    """
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('submitted', 'Enviado'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    )
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='document_requests')
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    
    # Detalles de la solicitud
    reason = models.TextField(help_text='Razón de la solicitud')
    due_date = models.DateField(null=True, blank=True)
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Documento enviado
    submitted_document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request'
    )
    
    # Aprobación
    reviewed_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_document_requests'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Metadata
    requested_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Solicitud de Documento'
        verbose_name_plural = 'Solicitudes de Documentos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document_type.name} - {self.employee.user.get_full_name()}"


class DocumentAccessLog(models.Model):
    """
    Log de acceso a documentos
    """
    ACTION_CHOICES = (
        ('view', 'Visualizar'),
        ('download', 'Descargar'),
        ('edit', 'Editar'),
        ('delete', 'Eliminar'),
        ('share', 'Compartir'),
    )
    
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Detalles técnicos
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Log de Acceso a Documento'
        verbose_name_plural = 'Logs de Acceso a Documentos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.user.get_full_name() if self.user else 'Unknown'} - {self.get_action_display()} - {self.document.title}"


class Folder(models.Model):
    """
    Carpeta para organizar documentos
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Estructura jerárquica
    parent_folder = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subfolders'
    )
    
    # Pertenencia
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='folders',
        help_text='Dejar en blanco para carpetas del sistema'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='folders',
        help_text='Carpeta departamental'
    )
    
    # Permisos
    is_public = models.BooleanField(default=False)
    
    # Metadata
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_folders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Carpeta'
        verbose_name_plural = 'Carpetas'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class FolderDocument(models.Model):
    """
    Relación entre carpetas y documentos
    """
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='folder_documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='folder_memberships')
    
    # Metadata
    added_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Documento en Carpeta'
        verbose_name_plural = 'Documentos en Carpetas'
        unique_together = ['folder', 'document']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.document.title} en {self.folder.name}"


class DocumentReminder(models.Model):
    """
    Recordatorio de documento (para renovaciones, vencimientos, etc.)
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='reminders')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='document_reminders')
    
    # Configuración
    reminder_date = models.DateField()
    message = models.TextField()
    
    # Estado
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Recordatorio de Documento'
        verbose_name_plural = 'Recordatorios de Documentos'
        ordering = ['reminder_date']
    
    def __str__(self):
        return f"Recordatorio: {self.document.title} - {self.reminder_date}"