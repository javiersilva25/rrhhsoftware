from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DocumentCategory, DocumentType, Document, DocumentTemplate,
    DocumentSignature, DocumentShare, DocumentVersion, DocumentRequest,
    DocumentAccessLog, Folder, FolderDocument, DocumentReminder
)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color_preview', 'is_active', 'document_types_count']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border-radius: 3px;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    def document_types_count(self, obj):
        return obj.document_types.filter(is_active=True).count()
    document_types_count.short_description = 'Tipos de Documentos'


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'requires_approval', 
                    'requires_signature', 'is_confidential', 'expires', 'is_active']
    list_filter = ['category', 'requires_approval', 'requires_signature', 
                   'is_confidential', 'expires', 'is_active']
    search_fields = ['name', 'code', 'description']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'code', 'category', 'description')
        }),
        ('Configuración', {
            'fields': ('requires_approval', 'requires_signature', 'is_confidential')
        }),
        ('Vencimiento', {
            'fields': ('expires', 'default_expiry_days')
        }),
        ('Restricciones de Archivo', {
            'fields': ('allowed_extensions', 'max_file_size_mb')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )


class DocumentSignatureInline(admin.TabularInline):
    model = DocumentSignature
    extra = 0
    readonly_fields = ['signer', 'status', 'signed_at']
    can_delete = False


class DocumentShareInline(admin.TabularInline):
    model = DocumentShare
    extra = 0
    readonly_fields = ['shared_with', 'permission', 'shared_by', 'created_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'employee', 'document_type', 'status_badge', 
                    'visibility_badge', 'file_size_display', 'expiry_date', 
                    'is_signed', 'version']
    list_filter = ['status', 'visibility', 'document_type__category', 
                   'requires_approval', 'requires_signature', 'is_signed', 'created_at']
    search_fields = ['title', 'description', 'reference_number', 'tags',
                    'employee__user__first_name', 'employee__user__last_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['file_size', 'file_extension', 'approved_at', 
                      'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'document_type', 'approved_by', 'uploaded_by']
    inlines = [DocumentSignatureInline, DocumentShareInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'document_type', 'employee', 'description')
        }),
        ('Archivo', {
            'fields': ('file', 'file_size', 'file_extension')
        }),
        ('Metadata', {
            'fields': ('reference_number', 'tags', 'visibility')
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Fechas', {
            'fields': ('issue_date', 'expiry_date')
        }),
        ('Aprobación', {
            'fields': ('requires_approval', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Firma Digital', {
            'fields': ('requires_signature', 'is_signed')
        }),
        ('Versiones', {
            'fields': ('version', 'parent_document')
        }),
        ('Metadata del Sistema', {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'pending_approval': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'expired': 'darkred',
            'archived': 'blue'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def visibility_badge(self, obj):
        colors = {
            'private': 'red',
            'employee': 'orange',
            'manager': 'blue',
            'hr': 'purple',
            'public': 'green'
        }
        color = colors.get(obj.visibility, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_visibility_display()
        )
    visibility_badge.short_description = 'Visibilidad'
    
    def file_size_display(self, obj):
        if obj.file_size:
            mb = obj.file_size / (1024 * 1024)
            if mb < 1:
                kb = obj.file_size / 1024
                return f"{kb:.2f} KB"
            return f"{mb:.2f} MB"
        return '-'
    file_size_display.short_description = 'Tamaño'
    
    actions = ['approve_documents', 'archive_documents']
    
    def approve_documents(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for document in queryset.filter(status='pending_approval'):
            document.status = 'approved'
            document.approved_by = request.user.employee_profile
            document.approved_at = timezone.now()
            document.save()
            updated += 1
        
        self.message_user(request, f'{updated} documentos aprobados correctamente.')
    approve_documents.short_description = 'Aprobar documentos seleccionados'
    
    def archive_documents(self, request, queryset):
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} documentos archivados correctamente.')
    archive_documents.short_description = 'Archivar documentos seleccionados'


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'document_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['document_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['document_type', 'created_by']


@admin.register(DocumentSignature)
class DocumentSignatureAdmin(admin.ModelAdmin):
    list_display = ['document', 'signer', 'signing_order', 'status_badge', 
                    'signed_at', 'rejected_at']
    list_filter = ['status', 'signed_at', 'rejected_at']
    search_fields = ['document__title', 'signer__user__first_name', 
                    'signer__user__last_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['signature_data', 'ip_address', 'signed_at', 
                      'rejected_at', 'created_at']
    autocomplete_fields = ['document', 'signer']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'signed': 'green',
            'rejected': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = ['document', 'shared_with', 'permission_badge', 'shared_by', 
                    'expires_at', 'accessed_at']
    list_filter = ['permission', 'created_at', 'expires_at']
    search_fields = ['document__title', 'shared_with__user__first_name',
                    'shared_with__user__last_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['accessed_at', 'created_at']
    autocomplete_fields = ['document', 'shared_with', 'shared_by']
    
    def permission_badge(self, obj):
        colors = {
            'view': 'blue',
            'download': 'green',
            'edit': 'orange'
        }
        color = colors.get(obj.permission, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_permission_display()
        )
    permission_badge.short_description = 'Permiso'


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['document__title', 'change_summary']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    autocomplete_fields = ['document', 'created_by']


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'document_type', 'status_badge', 'due_date', 
                    'requested_by', 'created_at']
    list_filter = ['status', 'document_type', 'due_date', 'created_at']
    search_fields = ['reason', 'employee__user__first_name',
                    'employee__user__last_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['reviewed_at', 'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'document_type', 'submitted_document',
                          'reviewed_by', 'requested_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'document_type', 'reason', 'due_date')
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Documento Enviado', {
            'fields': ('submitted_document',)
        }),
        ('Revisión', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('Metadata', {
            'fields': ('requested_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'submitted': 'blue',
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


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'action_badge', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['document__title', 'user__user__first_name',
                    'user__user__last_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    autocomplete_fields = ['document', 'user']
    
    def action_badge(self, obj):
        colors = {
            'view': 'blue',
            'download': 'green',
            'edit': 'orange',
            'delete': 'red',
            'share': 'purple'
        }
        color = colors.get(obj.action, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = 'Acción'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


class FolderDocumentInline(admin.TabularInline):
    model = FolderDocument
    extra = 0
    readonly_fields = ['document', 'added_by', 'added_at']


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_folder', 'employee', 'department', 
                    'is_public', 'documents_count', 'subfolders_count']
    list_filter = ['is_public', 'department', 'created_at']
    search_fields = ['name', 'description']
    autocomplete_fields = ['parent_folder', 'employee', 'department', 'created_by']
    inlines = [FolderDocumentInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'parent_folder')
        }),
        ('Pertenencia', {
            'fields': ('employee', 'department')
        }),
        ('Permisos', {
            'fields': ('is_public',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def documents_count(self, obj):
        return obj.folder_documents.count()
    documents_count.short_description = 'Documentos'
    
    def subfolders_count(self, obj):
        return obj.subfolders.count()
    subfolders_count.short_description = 'Subcarpetas'


@admin.register(FolderDocument)
class FolderDocumentAdmin(admin.ModelAdmin):
    list_display = ['folder', 'document', 'added_by', 'added_at']
    list_filter = ['added_at']
    search_fields = ['folder__name', 'document__title']
    date_hierarchy = 'added_at'
    readonly_fields = ['added_at']
    autocomplete_fields = ['folder', 'document', 'added_by']


@admin.register(DocumentReminder)
class DocumentReminderAdmin(admin.ModelAdmin):
    list_display = ['document', 'employee', 'reminder_date', 'is_sent', 'sent_at']
    list_filter = ['is_sent', 'reminder_date', 'created_at']
    search_fields = ['document__title', 'message', 'employee__user__first_name',
                    'employee__user__last_name']
    date_hierarchy = 'reminder_date'
    readonly_fields = ['is_sent', 'sent_at', 'created_at']
    autocomplete_fields = ['document', 'employee']