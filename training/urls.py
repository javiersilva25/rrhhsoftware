from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TrainingCategoryViewSet, TrainingProviderViewSet, CourseViewSet,
    TrainingSessionViewSet, TrainingEnrollmentViewSet, TrainingAttendanceViewSet,
    TrainingAssessmentViewSet, CertificationViewSet, TrainingBudgetViewSet,
    TrainingRequestViewSet, TrainingFeedbackViewSet, TrainingStatisticsViewSet
)

router = DefaultRouter()
router.register(r'categories', TrainingCategoryViewSet)
router.register(r'providers', TrainingProviderViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'sessions', TrainingSessionViewSet)
router.register(r'enrollments', TrainingEnrollmentViewSet)
router.register(r'attendance', TrainingAttendanceViewSet)
router.register(r'assessments', TrainingAssessmentViewSet)
router.register(r'certifications', CertificationViewSet)
router.register(r'budgets', TrainingBudgetViewSet)
router.register(r'requests', TrainingRequestViewSet)
router.register(r'feedback', TrainingFeedbackViewSet)
router.register(r'statistics', TrainingStatisticsViewSet, basename='training-statistics')

urlpatterns = [
    path('', include(router.urls)),
]