from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, DepartmentViewSet, PositionViewSet,
    EmployeeViewSet, BankAccountViewSet, TaxInformationViewSet,
    InsuranceViewSet, EmploymentHistoryViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'positions', PositionViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'bank-accounts', BankAccountViewSet)
router.register(r'tax-information', TaxInformationViewSet)
router.register(r'insurances', InsuranceViewSet)
router.register(r'employment-history', EmploymentHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]