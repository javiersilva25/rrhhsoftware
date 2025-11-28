from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkScheduleViewSet, EmployeeScheduleViewSet, TimeSheetViewSet,
    OvertimeViewSet, LeaveTypeViewSet, LeaveBalanceViewSet,
    LeaveRequestViewSet, HolidayViewSet, AttendanceReportViewSet
)

router = DefaultRouter()
router.register(r'work-schedules', WorkScheduleViewSet)
router.register(r'employee-schedules', EmployeeScheduleViewSet)
router.register(r'timesheets', TimeSheetViewSet)
router.register(r'overtime', OvertimeViewSet)
router.register(r'leave-types', LeaveTypeViewSet)
router.register(r'leave-balances', LeaveBalanceViewSet)
router.register(r'leave-requests', LeaveRequestViewSet)
router.register(r'holidays', HolidayViewSet)
router.register(r'reports', AttendanceReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]