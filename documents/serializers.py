from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import (
    DocumentCategory, DocumentType, Document, DocumentTemplate,
    DocumentSignature, DocumentShare, DocumentVersion, DocumentRequest,
    DocumentAccessLog, Folder, FolderDocument, DocumentReminder
)
from employees.models import Employee


class DocumentCategorySerializer(serializers.ModelSerializer):
    """
    Serializer para categorías de documentos
    """
    document_types_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentCategory
        fields = [
            'id', 'name', 'code', 'description', 'icon', 'color',
            'is_active', 'document_types_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_document_types_count(self, obj):
        return obj.document_types.filter(is_active=True).count()


class DocumentTypeSerializer(serializers.ModelSerializer):
    """
    Serializer para tipos de documentos
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    documents_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentType
        fields = [
            'id', 'name', 'code', 'category', 'category_name', 'description',
            'requires_approval', 'requires_signature', 'is_confidential',
            'expires', 'default_expiry_days', 'allowed_extensions',
            'max_file_size_mb', 'is_active', 'documents_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_documents_count(self, obj):
        return obj.documents.count()


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de documentos
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    document_type_name = serializers.CharField(source='document_type.name', read_only=True)
    category_name = serializers.CharField(source='document_type.category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'document_type', 'document_type_name',
            'category_name', 'employee', 'employee_name', 'employee_number',
            'file', 'file_extension', 'file_size_mb', 'status', 'status_display',
            'visibility', 'visibility_display', 'issue_date', 'expiry_date',
            'is_signed', 'version', 'created_at'
        ]
    
    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0


class DocumentDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para documentos
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_number = serializers.CharField(source='employee.employee_number', read_only=True)
    document_type_details = DocumentTypeSerializer(source='document_type', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.user.get_full_name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.user.get_full_name', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    signatures_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'document_type', 'document_type_details',
            'employee', 'employee_name', 'employee_number', 'file',
            'file_size', 'file_size_mb', 'file_extension', 'description',
            'reference_number', 'status', 'status_display', 'visibility',
            'visibility_display', 'issue_date', 'expiry_date',
            'requires_approval', 'approved_by', 'approved_by_name',
            'approved_at', 'rejection_reason', 'requires_signature',
            'is_signed', 'signatures_count', 'version', 'parent_document',
            'tags', 'uploaded_by', 'uploaded_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'file_size', 'file_extension', 'created_at', 'updated_at']
    
    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_signatures_count(self, obj):
        return obj.signatures.filter(status='signed').count()


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer para subir documentos
    """
    class Meta:
        model = Document
        fields = [
            'title', 'document_type', 'employee', 'file', 'description',
            'reference_number', 'visibility', 'issue_date', 'expiry_date', 'tags'
        ]
    
    def validate_file(self, value):
        """
        Validar archivo
        """
        # Obtener tipo de documento del contexto
        document_type_id = self.initial_data.get('document_type')
        
        if document_type_id:
            try:
                document_type = DocumentType.objects.get(id=document_type_id)
                
                # Validar extensión
                file_extension = value.name.split('.')[-1].lower()
                allowed_extensions = [ext.strip() for ext in document_type.allowed_extensions.split(',')]
                
                if file_extension not in allowed_extensions:
                    raise serializers.ValidationError(
                        f"Extensión no permitida. Extensiones permitidas: {', '.join(allowed_extensions)}"
                    )
                
                # Validar tamaño
                max_size_bytes = document_type.max_file_size_mb * 1024 * 1024
                if value.size > max_size_bytes:
                    raise serializers.ValidationError(
                        f"El archivo es demasiado grande. Tamaño máximo: {document_type.max_file_size_mb}MB"
                    )
            
            except DocumentType.DoesNotExist:
                pass
        
        return value
    
    def create(self, validated_data):
        """
        Crear documento y configurar campos automáticos
        """
        document_type = validated_data['document_type']
        
        # Configurar campos basados en el tipo de documento
        validated_data['requires_approval'] = document_type.requires_approval
        validated_data['requires_signature'] = document_type.requires_signature
        
        # Si requiere aprobación, establecer estado como pendiente
        if document_type.requires_approval:
            validated_data['status'] = 'pending_approval'
        else:
            validated_data['status'] = 'approved'
        
        # Establecer fecha de vencimiento por defecto si aplica
        if document_type.expires and document_type.default_expiry_days and not validated_data.get('expiry_date'):
            validated_data['expiry_date'] = timezone.now().date() + timezone.timedelta(
                days=document_type.default_expiry_days
            )
        
        # Establecer uploaded_by
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['uploaded_by'] = request.user.employee_profile
        
        return super().create(validated_data)


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer para plantillas de documentos
    """
    document_type_name = serializers.CharField(source='document_type.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentTemplate
        fields = [
            'id', 'name', 'document_type', 'document_type_name',
            'description', 'template_file', 'fields_schema', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSignatureSerializer(serializers.ModelSerializer):
    """
    Serializer para firmas de documentos
    """
    document_title = serializers.CharField(source='document.title', read_only=True)
    signer_name = serializers.CharField(source='signer.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DocumentSignature
        fields = [
            'id', 'document', 'document_title', 'signer', 'signer_name',
            'signing_order', 'status', 'status_display', 'signature_data',
            'ip_address', 'signed_at', 'rejected_at', 'rejection_reason',
            'created_at'
        ]
        read_only_fields = ['id', 'signature_data', 'ip_address', 'signed_at', 
                           'rejected_at', 'created_at']


class DocumentShareSerializer(serializers.ModelSerializer):
    """
    Serializer para documentos compartidos
    """
    document_title = serializers.CharField(source='document.title', read_only=True)
    shared_with_name = serializers.CharField(source='shared_with.user.get_full_name', read_only=True)
    shared_by_name = serializers.CharField(source='shared_by.user.get_full_name', read_only=True)
    permission_display = serializers.CharField(source='get_permission_display', read_only=True)
    
    class Meta:
        model = DocumentShare
        fields = [
            'id', 'document', 'document_title', 'shared_with', 'shared_with_name',
            'permission', 'permission_display', 'shared_by', 'shared_by_name',
            'expires_at', 'accessed_at', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'accessed_at', 'created_at']


class DocumentVersionSerializer(serializers.ModelSerializer):
    """
    Serializer para versiones de documentos
    """
    document_title = serializers.CharField(source='document.title', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'document', 'document_title', 'version_number',
            'file', 'change_summary', 'created_by', 'created_by_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentRequestSerializer(serializers.ModelSerializer):
    """
    Serializer para solicitudes de documentos
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    document_type_name = serializers.CharField(source='document_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.user.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentRequest
        fields = [
            'id', 'employee', 'employee_name', 'document_type', 'document_type_name',
            'reason', 'due_date', 'status', 'status_display', 'submitted_document',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_notes',
            'requested_by', 'requested_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reviewed_at', 'created_at', 'updated_at']


class DocumentAccessLogSerializer(serializers.ModelSerializer):
    """
    Serializer para logs de acceso a documentos
    """
    document_title = serializers.CharField(source='document.title', read_only=True)
    user_name = serializers.CharField(source='user.user.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = DocumentAccessLog
        fields = [
            'id', 'document', 'document_title', 'user', 'user_name',
            'action', 'action_display', 'ip_address', 'user_agent',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FolderSerializer(serializers.ModelSerializer):
    """
    Serializer para carpetas
    """
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.user.get_full_name', read_only=True)
    documents_count = serializers.SerializerMethodField()
    subfolders_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'description', 'parent_folder', 'employee',
            'employee_name', 'department', 'department_name', 'is_public',
            'documents_count', 'subfolders_count', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_documents_count(self, obj):
        return obj.folder_documents.count()
    
    def get_subfolders_count(self, obj):
        return obj.subfolders.count()


class FolderDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer para documentos en carpetas
    """
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    document_details = DocumentListSerializer(source='document', read_only=True)
    added_by_name = serializers.CharField(source='added_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = FolderDocument
        fields = [
            'id', 'folder', 'folder_name', 'document', 'document_details',
            'added_by', 'added_by_name', 'added_at'
        ]
        read_only_fields = ['id', 'added_at']


class DocumentReminderSerializer(serializers.ModelSerializer):
    """
    Serializer para recordatorios de documentos
    """
    document_title = serializers.CharField(source='document.title', read_only=True)
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentReminder
        fields = [
            'id', 'document', 'document_title', 'employee', 'employee_name',
            'reminder_date', 'message', 'is_sent', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'is_sent', 'sent_at', 'created_at']


class DocumentApprovalSerializer(serializers.Serializer):
    """
    Serializer para aprobar/rechazar documentos
    """
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)


class DocumentSignSerializer(serializers.Serializer):
    """
    Serializer para firmar documentos
    """
    signature_data = serializers.CharField(help_text='Datos de la firma en base64')


class DocumentShareCreateSerializer(serializers.Serializer):
    """
    Serializer para compartir documentos
    """
    shared_with = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        many=True
    )
    permission = serializers.ChoiceField(choices=DocumentShare.PERMISSION_CHOICES)
    expires_at = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class BulkDocumentActionSerializer(serializers.Serializer):
    """
    Serializer para acciones en lote sobre documentos
    """
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='Lista de IDs de documentos'
    )
    action = serializers.ChoiceField(choices=['archive', 'delete', 'approve', 'move_to_folder'])
    folder_id = serializers.IntegerField(required=False, help_text='ID de carpeta destino (para move_to_folder)')


class DocumentStatisticsSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de documentos
    """
    total_documents = serializers.IntegerField()
    by_status = serializers.DictField()
    by_category = serializers.DictField()
    by_type = serializers.DictField()
    pending_approval = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()
    expired = serializers.IntegerField()
    pending_signatures = serializers.IntegerField()
    total_storage_mb = serializers.FloatField()