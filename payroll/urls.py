from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PayrollPeriodViewSet, SalaryComponentViewSet, EmployeeSalaryViewSet,
    EmployeeSalaryComponentViewSet, PayrollViewSet, PayrollItemViewSet,
    PayrollAdjustmentViewSet, PaymentMethodViewSet, PayrollPaymentViewSet
)

router = DefaultRouter()
router.register(r'periods', PayrollPeriodViewSet)
router.register(r'salary-components', SalaryComponentViewSet)
router.register(r'employee-salaries', EmployeeSalaryViewSet)
router.register(r'employee-salary-components', EmployeeSalaryComponentViewSet)
router.register(r'payrolls', PayrollViewSet)
router.register(r'payroll-items', PayrollItemViewSet)
router.register(r'adjustments', PayrollAdjustmentViewSet)
router.register(r'payment-methods', PaymentMethodViewSet)
router.register(r'payments', PayrollPaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]