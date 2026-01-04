from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PerformanceReviewCycleViewSet, CompetencyCategoryViewSet, CompetencyViewSet,
    PerformanceReviewViewSet, CompetencyRatingViewSet, GoalViewSet,
    GoalCheckInViewSet, FeedbackViewSet, DevelopmentPlanViewSet,
    DevelopmentActionViewSet, PerformanceImprovementPlanViewSet,
    PIPCheckInViewSet, PerformanceMetricsViewSet
)

router = DefaultRouter()
router.register(r'review-cycles', PerformanceReviewCycleViewSet)
router.register(r'competency-categories', CompetencyCategoryViewSet)
router.register(r'competencies', CompetencyViewSet)
router.register(r'reviews', PerformanceReviewViewSet)
router.register(r'competency-ratings', CompetencyRatingViewSet)
router.register(r'goals', GoalViewSet)
router.register(r'goal-check-ins', GoalCheckInViewSet)
router.register(r'feedback', FeedbackViewSet)
router.register(r'development-plans', DevelopmentPlanViewSet)
router.register(r'development-actions', DevelopmentActionViewSet)
router.register(r'improvement-plans', PerformanceImprovementPlanViewSet)
router.register(r'pip-check-ins', PIPCheckInViewSet)
router.register(r'metrics', PerformanceMetricsViewSet, basename='performance-metrics')

urlpatterns = [
    path('', include(router.urls)),
]