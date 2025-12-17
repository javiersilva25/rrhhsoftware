from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobPostingViewSet, CandidateViewSet, ApplicationViewSet,
    RecruitmentStageViewSet, InterviewViewSet, AssessmentViewSet,
    JobOfferViewSet, OnboardingTaskViewSet, RecruitmentReportViewSet
)

router = DefaultRouter()
router.register(r'job-postings', JobPostingViewSet)
router.register(r'candidates', CandidateViewSet)
router.register(r'applications', ApplicationViewSet)
router.register(r'stages', RecruitmentStageViewSet)
router.register(r'interviews', InterviewViewSet)
router.register(r'assessments', AssessmentViewSet)
router.register(r'job-offers', JobOfferViewSet)
router.register(r'onboarding-tasks', OnboardingTaskViewSet)
router.register(r'reports', RecruitmentReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]