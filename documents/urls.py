from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentCategoryViewSet, DocumentTypeViewSet, DocumentViewSet,
    DocumentTemplateViewSet, DocumentSignatureViewSet, DocumentShareViewSet,
    DocumentVersionViewSet, DocumentRequestViewSet, DocumentAccessLogViewSet,
    FolderViewSet, FolderDocumentViewSet, DocumentReminderViewSet,
    DocumentStatisticsViewSet
)

router = DefaultRouter()
router.register(r'categories', DocumentCategoryViewSet)
router.register(r'types', DocumentTypeViewSet)
router.register(r'documents', DocumentViewSet)
router.register(r'templates', DocumentTemplateViewSet)
router.register(r'signatures', DocumentSignatureViewSet)
router.register(r'shares', DocumentShareViewSet)
router.register(r'versions', DocumentVersionViewSet)
router.register(r'requests', DocumentRequestViewSet)
router.register(r'access-logs', DocumentAccessLogViewSet)
router.register(r'folders', FolderViewSet)
router.register(r'folder-documents', FolderDocumentViewSet)
router.register(r'reminders', DocumentReminderViewSet)
router.register(r'statistics', DocumentStatisticsViewSet, basename='document-statistics')

urlpatterns = [
    path('', include(router.urls)),
]