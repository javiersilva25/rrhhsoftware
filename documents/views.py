from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta

from .models import (
    DocumentCategory, DocumentType, Document, DocumentTemplate,
    DocumentSignature, DocumentShare, DocumentVersion, DocumentRequest,
    DocumentAccessLog, Folder, FolderDocument, DocumentReminder
)
from .serializers import (
    DocumentCategorySerializer, DocumentTypeSerializer, DocumentListSerializer,
    DocumentDetailSerializer, DocumentUploadSerializer, DocumentTemplateSerializer,
    DocumentSignatureSerializer, DocumentShareSerializer, DocumentVersionSerializer,
    DocumentRequestSerializer, DocumentAccessLogSerializer, FolderSerializer,
    FolderDocumentSerializer, DocumentReminderSerializer, DocumentApprovalSerializer,
    DocumentSignSerializer, DocumentShareCreateSerializer, BulkDocumentActionSerializer,
    DocumentStatisticsSerializer
)
from employees.models import Employee


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de documentos
    """
    queryset = DocumentCategory.objects.prefetch_related('document_types').all()
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class DocumentTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar tipos de documentos
    """
    queryset = DocumentType.objects.select_related('category').all()
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'requires_approval', 'requires_signature', 
                       'is_confidential', 'expires', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['category', 'name']


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar documentos
    """
    queryset = Document.objects.select_related(
        'employee__user', 'document_type__category', 'approved_by__user',
        'uploaded_by__user'
    ).prefetch_related('signatures', 'shares').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'document_type', 'status', 'visibility', 
                       'requires_approval', 'requires_signature', 'is_signed']
    search_fields = ['title', 'description', 'reference_number', 'tags',
                    'employee__user__first_name', 'employee__user__last_name']
    ordering_fields = ['created_at', 'title', 'expiry_date']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentListSerializer
        elif self.action == 'create' or self.action == 'upload':
            return DocumentUploadSerializer
        return DocumentDetailSerializer
    
    def perform_create(self, serializer):
        document = serializer.save()
        
        # Crear log de acceso
        DocumentAccessLog.objects.create(
            document=document,
            user=self.request.user.employee_profile,
            action='view',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Subir documento
        """
        serializer = DocumentUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        
        response_serializer = DocumentDetailSerializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Aprobar documento
        """
        document = self.get_object()
        
        if not document.requires_approval:
            return Response(
                {'error': 'Este documento no requiere aprobación'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if document.status != 'pending_approval':
            return Response(
                {'error': 'Solo se pueden aprobar documentos pendientes de aprobación'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DocumentApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data['action'] == 'approve':
            document.status = 'approved'
            document.approved_by = request.user.employee_profile
            document.approved_at = timezone.now()
        else:
            document.status = 'rejected'
            document.rejection_reason = serializer.validated_data.get('notes', '')
        
        document.save()
        
        # Crear log de acceso
        DocumentAccessLog.objects.create(
            document=document,
            user=request.user.employee_profile,
            action='edit',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        response_serializer = DocumentDetailSerializer(document)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """
        Firmar documento
        """
        document = self.get_object()
        
        if not document.requires_signature:
            return Response(
                {'error': 'Este documento no requiere firma'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DocumentSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Buscar firma pendiente del usuario
        try:
            signature = DocumentSignature.objects.get(
                document=document,
                signer=request.user.employee_profile,
                status='pending'
            )
        except DocumentSignature.DoesNotExist:
            return Response(
                {'error': 'No tiene una firma pendiente para este documento'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        signature.status = 'signed'
        signature.signature_data = serializer.validated_data['signature_data']
        signature.ip_address = request.META.get('REMOTE_ADDR')
        signature.signed_at = timezone.now()
        signature.save()
        
        # Verificar si todas las firmas están completadas
        pending_signatures = document.signatures.filter(status='pending').count()
        if pending_signatures == 0:
            document.is_signed = True
            document.save()
        
        # Crear log de acceso
        DocumentAccessLog.objects.create(
            document=document,
            user=request.user.employee_profile,
            action='edit',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        response_serializer = DocumentDetailSerializer(document)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """
        Compartir documento con otros usuarios
        """
        document = self.get_object()
        
        serializer = DocumentShareCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        shared_with_list = serializer.validated_data['shared_with']
        permission = serializer.validated_data['permission']
        expires_at = serializer.validated_data.get('expires_at')
        notes = serializer.validated_data.get('notes', '')
        
        created_shares = []
        for employee in shared_with_list:
            share, created = DocumentShare.objects.get_or_create(
                document=document,
                shared_with=employee,
                defaults={
                    'shared_by': request.user.employee_profile,
                    'permission': permission,
                    'expires_at': expires_at,
                    'notes': notes
                }
            )
            
            if not created:
                # Actualizar si ya existía
                share.permission = permission
                share.expires_at = expires_at
                share.notes = notes
                share.save()
            
            created_shares.append(share)
        
        # Crear log de acceso
        DocumentAccessLog.objects.create(
            document=document,
            user=request.user.employee_profile,
            action='share',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        response_serializer = DocumentShareSerializer(created_shares, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """
        Crear nueva versión del documento
        """
        document = self.get_object()
        
        new_file = request.FILES.get('file')
        change_summary = request.data.get('change_summary', '')
        
        if not new_file:
            return Response(
                {'error': 'Se requiere un archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not change_summary:
            return Response(
                {'error': 'Se requiere un resumen de cambios'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear versión anterior
        DocumentVersion.objects.create(
            document=document,
            version_number=document.version,
            file=document.file,
            change_summary=f"Versión {document.version}",
            created_by=request.user.employee_profile
        )
        
        # Actualizar documento
        document.file = new_file
        document.version += 1
        document.save()
        
        # Crear versión nueva
        DocumentVersion.objects.create(
            document=document,
            version_number=document.version,
            file=new_file,
            change_summary=change_summary,
            created_by=request.user.employee_profile
        )
        
        # Crear log de acceso
        DocumentAccessLog.objects.create(
            document=document,
            user=request.user.employee_profile,
            action='edit',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        response_serializer = DocumentDetailSerializer(document)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """
        Registrar descarga de documento
        """
        document = self.get_object()
        
        # Crear log de acceso
        DocumentAccessLog.objects.create(
            document=document,
            user=request.user.employee_profile,
            action='download',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({'message': 'Descarga registrada', 'file_url': document.file.url})
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archivar documento
        """
        document = self.get_object()
        document.status = 'archived'
        document.save()
        
        serializer = DocumentDetailSerializer(document)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """
        Ejecutar acción en lote sobre documentos
        """
        serializer = BulkDocumentActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        document_ids = serializer.validated_data['document_ids']
        action = serializer.validated_data['action']
        
        documents = Document.objects.filter(id__in=document_ids)
        
        if action == 'archive':
            documents.update(status='archived')
            message = f'{documents.count()} documentos archivados'
        
        elif action == 'delete':
            count = documents.count()
            documents.delete()
            message = f'{count} documentos eliminados'
        
        elif action == 'approve':
            documents.filter(status='pending_approval').update(
                status='approved',
                approved_by=request.user.employee_profile,
                approved_at=timezone.now()
            )
            message = f'{documents.count()} documentos aprobados'
        
        elif action == 'move_to_folder':
            folder_id = serializer.validated_data.get('folder_id')
            if not folder_id:
                return Response(
                    {'error': 'Se requiere folder_id para esta acción'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                folder = Folder.objects.get(id=folder_id)
                for document in documents:
                    FolderDocument.objects.get_or_create(
                        folder=folder,
                        document=document,
                        defaults={'added_by': request.user.employee_profile}
                    )
                message = f'{documents.count()} documentos movidos a la carpeta'
            except Folder.DoesNotExist:
                return Response(
                    {'error': 'Carpeta no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {'error': 'Acción no válida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'message': message})
    
    @action(detail=False, methods=['get'])
    def my_documents(self, request):
        """
        Obtener documentos del usuario actual
        """
        employee = request.user.employee_profile
        documents = self.queryset.filter(employee=employee)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            documents = documents.filter(status=status_filter)
        
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def shared_with_me(self, request):
        """
        Obtener documentos compartidos con el usuario
        """
        employee = request.user.employee_profile
        shares = DocumentShare.objects.filter(
            shared_with=employee
        ).select_related('document')
        
        documents = [share.document for share in shares]
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_approval(self, request):
        """
        Obtener documentos pendientes de aprobación
        """
        documents = self.queryset.filter(status='pending_approval')
        
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_signature(self, request):
        """
        Obtener documentos pendientes de firma del usuario
        """
        employee = request.user.employee_profile
        signatures = DocumentSignature.objects.filter(
            signer=employee,
            status='pending'
        ).select_related('document')
        
        documents = [signature.document for signature in signatures]
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Obtener documentos próximos a vencer
        """
        days = int(request.query_params.get('days', 30))
        today = timezone.now().date()
        future_date = today + timedelta(days=days)
        
        documents = self.queryset.filter(
            expiry_date__range=[today, future_date],
            status='approved'
        )
        
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Obtener documentos vencidos
        """
        today = timezone.now().date()
        documents = self.queryset.filter(
            expiry_date__lt=today,
            status__in=['approved', 'expired']
        )
        
        # Actualizar estado
        documents.update(status='expired')
        
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)


class DocumentTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar plantillas de documentos
    """
    queryset = DocumentTemplate.objects.select_related(
        'document_type', 'created_by__user'
    ).all()
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['document_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)


class DocumentSignatureViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar firmas de documentos
    """
    queryset = DocumentSignature.objects.select_related(
        'document', 'signer__user'
    ).all()
    serializer_class = DocumentSignatureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'signer', 'status']
    ordering_fields = ['signing_order', 'created_at']
    ordering = ['signing_order']
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Rechazar firma de documento
        """
        signature = self.get_object()
        
        if signature.status != 'pending':
            return Response(
                {'error': 'Solo se pueden rechazar firmas pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rejection_reason = request.data.get('rejection_reason', '')
        
        signature.status = 'rejected'
        signature.rejected_at = timezone.now()
        signature.rejection_reason = rejection_reason
        signature.save()
        
        serializer = self.get_serializer(signature)
        return Response(serializer.data)


class DocumentShareViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar documentos compartidos
    """
    queryset = DocumentShare.objects.select_related(
        'document', 'shared_with__user', 'shared_by__user'
    ).all()
    serializer_class = DocumentShareSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'shared_with', 'shared_by', 'permission']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Revocar acceso compartido
        """
        share = self.get_object()
        share.delete()
        
        return Response({'message': 'Acceso revocado correctamente'})


class DocumentVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver versiones de documentos
    """
    queryset = DocumentVersion.objects.select_related(
        'document', 'created_by__user'
    ).all()
    serializer_class = DocumentVersionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document']
    ordering_fields = ['version_number', 'created_at']
    ordering = ['-version_number']


class DocumentRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar solicitudes de documentos
    """
    queryset = DocumentRequest.objects.select_related(
        'employee__user', 'document_type', 'submitted_document',
        'reviewed_by__user', 'requested_by__user'
    ).all()
    serializer_class = DocumentRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'document_type', 'status']
    search_fields = ['reason', 'employee__user__first_name', 'employee__user__last_name']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """
        Enviar documento solicitado
        """
        doc_request = self.get_object()
        
        if doc_request.status != 'pending':
            return Response(
                {'error': 'Solo se pueden enviar documentos para solicitudes pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document_id = request.data.get('document_id')
        
        if not document_id:
            return Response(
                {'error': 'Se requiere document_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            document = Document.objects.get(id=document_id)
            doc_request.submitted_document = document
            doc_request.status = 'submitted'
            doc_request.save()
            
            serializer = self.get_serializer(doc_request)
            return Response(serializer.data)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Documento no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """
        Revisar solicitud de documento
        """
        doc_request = self.get_object()
        
        if doc_request.status != 'submitted':
            return Response(
                {'error': 'Solo se pueden revisar solicitudes enviadas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        action = request.data.get('action')  # 'approve' or 'reject'
        review_notes = request.data.get('review_notes', '')
        
        if action == 'approve':
            doc_request.status = 'approved'
        elif action == 'reject':
            doc_request.status = 'rejected'
        else:
            return Response(
                {'error': 'Acción no válida. Use "approve" o "reject"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        doc_request.reviewed_by = request.user.employee_profile
        doc_request.reviewed_at = timezone.now()
        doc_request.review_notes = review_notes
        doc_request.save()
        
        serializer = self.get_serializer(doc_request)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Obtener solicitudes pendientes
        """
        requests = self.queryset.filter(status='pending')
        serializer = self.get_serializer(requests, many=True)
        return Response(serializer.data)


class DocumentAccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para ver logs de acceso a documentos
    """
    queryset = DocumentAccessLog.objects.select_related(
        'document', 'user__user'
    ).all()
    serializer_class = DocumentAccessLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'user', 'action']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class FolderViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar carpetas
    """
    queryset = Folder.objects.select_related(
        'employee__user', 'department', 'created_by__user', 'parent_folder'
    ).prefetch_related('folder_documents').all()
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['employee', 'department', 'parent_folder', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.employee_profile)
    
    @action(detail=True, methods=['post'])
    def add_document(self, request, pk=None):
        """
        Agregar documento a carpeta
        """
        folder = self.get_object()
        document_id = request.data.get('document_id')
        
        if not document_id:
            return Response(
                {'error': 'Se requiere document_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            document = Document.objects.get(id=document_id)
            folder_doc, created = FolderDocument.objects.get_or_create(
                folder=folder,
                document=document,
                defaults={'added_by': request.user.employee_profile}
            )
            
            if not created:
                return Response(
                    {'message': 'El documento ya está en esta carpeta'},
                    status=status.HTTP_200_OK
                )
            
            serializer = FolderDocumentSerializer(folder_doc)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Documento no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_document(self, request, pk=None):
        """
        Remover documento de carpeta
        """
        folder = self.get_object()
        document_id = request.data.get('document_id')
        
        if not document_id:
            return Response(
                {'error': 'Se requiere document_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            folder_doc = FolderDocument.objects.get(folder=folder, document_id=document_id)
            folder_doc.delete()
            return Response({'message': 'Documento removido de la carpeta'})
        except FolderDocument.DoesNotExist:
            return Response(
                {'error': 'El documento no está en esta carpeta'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """
        Obtener documentos de una carpeta
        """
        folder = self.get_object()
        folder_documents = folder.folder_documents.select_related('document').all()
        
        documents = [fd.document for fd in folder_documents]
        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)


class FolderDocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar documentos en carpetas
    """
    queryset = FolderDocument.objects.select_related(
        'folder', 'document', 'added_by__user'
    ).all()
    serializer_class = FolderDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['folder', 'document']


class DocumentReminderViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar recordatorios de documentos
    """
    queryset = DocumentReminder.objects.select_related(
        'document', 'employee__user'
    ).all()
    serializer_class = DocumentReminderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'employee', 'is_sent']
    ordering_fields = ['reminder_date', 'created_at']
    ordering = ['reminder_date']


class DocumentStatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet para estadísticas de documentos
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Obtener resumen general de estadísticas de documentos
        """
        employee_id = request.query_params.get('employee')
        department_id = request.query_params.get('department')
        
        # Filtrar documentos
        documents = Document.objects.all()
        
        if employee_id:
            documents = documents.filter(employee_id=employee_id)
        
        if department_id:
            documents = documents.filter(employee__department_id=department_id)
        
        total_documents = documents.count()
        
        # Por estado
        by_status = {}
        for status_choice in Document.STATUS_CHOICES:
            count = documents.filter(status=status_choice[0]).count()
            if count > 0:
                by_status[status_choice[1]] = count
        
        # Por categoría
        by_category = {}
        categories = DocumentCategory.objects.all()
        for category in categories:
            count = documents.filter(document_type__category=category).count()
            if count > 0:
                by_category[category.name] = count
        
        # Por tipo
        by_type = {}
        types = DocumentType.objects.all()
        for doc_type in types:
            count = documents.filter(document_type=doc_type).count()
            if count > 0:
                by_type[doc_type.name] = count
        
        # Pendientes de aprobación
        pending_approval = documents.filter(status='pending_approval').count()
        
        # Próximos a vencer (30 días)
        today = timezone.now().date()
        future_date = today + timedelta(days=30)
        expiring_soon = documents.filter(
            expiry_date__range=[today, future_date],
            status='approved'
            ).count()
        
        # Vencidos
        expired = documents.filter(
            expiry_date__lt=today,
            status__in=['approved', 'expired']
        ).count()
        
        # Pendientes de firma
        pending_signatures = DocumentSignature.objects.filter(
            document__in=documents,
            status='pending'
        ).count()
        
        # Almacenamiento total
        total_storage_bytes = documents.aggregate(Sum('file_size'))['file_size__sum'] or 0
        total_storage_mb = round(total_storage_bytes / (1024 * 1024), 2)
        
        statistics_data = {
            'total_documents': total_documents,
            'by_status': by_status,
            'by_category': by_category,
            'by_type': by_type,
            'pending_approval': pending_approval,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'pending_signatures': pending_signatures,
            'total_storage_mb': total_storage_mb
        }
        
        serializer = DocumentStatisticsSerializer(statistics_data)
        return Response(serializer.data)