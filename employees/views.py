from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import (
    User, Department, Position, Employee,
    BankAccount, TaxInformation, Insurance, EmploymentHistory
)
from .serializers import (
    UserSerializer, DepartmentSerializer, PositionSerializer,
    EmployeeListSerializer, EmployeeDetailSerializer, EmployeeCreateSerializer,
    BankAccountSerializer, TaxInformationSerializer, InsuranceSerializer,
    EmploymentHistorySerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'date_joined']
    ordering = ['username']
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Obtener información del usuario actual
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Cambiar contraseña de usuario
        """
        user = self.get_object()
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response(
                {'error': 'Contraseña actual incorrecta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Contraseña actualizada correctamente'})


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar departamentos
    """
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """
        Listar empleados de un departamento
        """
        department = self.get_object()
        employees = department.employees.filter(status='active')
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data)


class PositionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar posiciones
    """
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'level']
    search_fields = ['title', 'code', 'description']
    ordering_fields = ['title', 'created_at']
    ordering = ['title']
    
    @action(detail=True, methods=['get'])
    def employees(self, request, pk=None):
        """
        Listar empleados de una posición
        """
        position = self.get_object()
        employees = position.employees.filter(status='active')
        serializer = EmployeeListSerializer(employees, many=True)
        return Response(serializer.data)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar empleados
    """
    queryset = Employee.objects.select_related(
        'user', 'department', 'position', 'manager'
    ).prefetch_related(
        'bank_accounts', 'insurances', 'employment_history'
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'position', 'status', 'employment_type']
    search_fields = [
        'employee_number', 'user__first_name', 'user__last_name',
        'user__email', 'identification_number'
    ]
    ordering_fields = ['employee_number', 'hire_date', 'created_at']
    ordering = ['employee_number']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeListSerializer
        elif self.action == 'create':
            return EmployeeCreateSerializer
        return EmployeeDetailSerializer
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Desactivar un empleado
        """
        employee = self.get_object()
        employee.status = 'inactive'
        employee.end_date = request.data.get('end_date')
        employee.save()
        
        employee.user.is_active = False
        employee.user.save()
        
        return Response({'message': 'Empleado desactivado correctamente'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activar un empleado
        """
        employee = self.get_object()
        employee.status = 'active'
        employee.end_date = None
        employee.save()
        
        employee.user.is_active = True
        employee.user.save()
        
        return Response({'message': 'Empleado activado correctamente'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Obtener estadísticas de empleados
        """
        total = self.queryset.count()
        active = self.queryset.filter(status='active').count()
        inactive = self.queryset.filter(status='inactive').count()
        by_department = {}
        
        for dept in Department.objects.all():
            by_department[dept.name] = dept.employees.filter(status='active').count()
        
        return Response({
            'total': total,
            'active': active,
            'inactive': inactive,
            'by_department': by_department
        })


class BankAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cuentas bancarias
    """
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'is_primary']


class TaxInformationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar información fiscal
    """
    queryset = TaxInformation.objects.all()
    serializer_class = TaxInformationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee']


class InsuranceViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar seguros
    """
    queryset = Insurance.objects.all()
    serializer_class = InsuranceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employee', 'insurance_type', 'is_active']
    ordering_fields = ['coverage_start_date']
    ordering = ['-coverage_start_date']


class EmploymentHistoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar historial laboral
    """
    queryset = EmploymentHistory.objects.all()
    serializer_class = EmploymentHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['employee', 'department', 'position']
    ordering_fields = ['start_date']
    ordering = ['-start_date']