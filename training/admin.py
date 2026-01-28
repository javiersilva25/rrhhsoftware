from django.contrib import admin
from django.utils.html import format_html
from .models import (
    TrainingCategory, TrainingProvider, Course, TrainingSession,
    TrainingEnrollment, TrainingAttendance, TrainingAssessment,
    Certification, TrainingBudget, TrainingRequest, TrainingFeedback
)


@admin.register(TrainingCategory)
class TrainingCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'color_preview', 'is_active', 'courses_count']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'description']
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 30px; height: 20px; background-color: {}; border-radius: 3px;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    def courses_count(self, obj):
        return obj.courses.filter(is_active=True).count()
    courses_count.short_description = 'Cursos'


@admin.register(TrainingProvider)
class TrainingProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_type', 'contact_name', 'contact_email', 
                    'is_active', 'courses_count']
    list_filter = ['provider_type', 'is_active']
    search_fields = ['name', 'contact_name', 'contact_email']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'provider_type', 'description')
        }),
        ('Contacto', {
            'fields': ('contact_name', 'contact_email', 'contact_phone', 'website')
        }),
        ('Ubicación', {
            'fields': ('address',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )
    
    def courses_count(self, obj):
        return obj.courses.filter(is_active=True).count()
    courses_count.short_description = 'Cursos'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'category', 'provider', 'level', 
                    'duration_hours', 'cost_per_person', 'provides_certificate', 'is_active']
    list_filter = ['category', 'provider', 'level', 'delivery_method', 
                   'provides_certificate', 'is_active']
    search_fields = ['title', 'code', 'description']
    autocomplete_fields = ['category', 'provider', 'created_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'code', 'category', 'provider')
        }),
        ('Descripción', {
            'fields': ('description', 'objectives', 'prerequisites', 'syllabus')
        }),
        ('Configuración', {
            'fields': ('level', 'duration_hours', 'delivery_method', 'max_participants')
        }),
        ('Costos', {
            'fields': ('cost_per_person', 'currency')
        }),
        ('Materiales', {
            'fields': ('materials_url',)
        }),
        ('Certificación', {
            'fields': ('provides_certificate', 'certificate_validity_days')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


class TrainingEnrollmentInline(admin.TabularInline):
    model = TrainingEnrollment
    extra = 0
    readonly_fields = ['employee', 'status', 'enrolled_at']
    can_delete = False
    show_change_link = True


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'course', 'start_date', 'end_date', 
                    'status_badge', 'instructor_display', 'enrollment_status']
    list_filter = ['status', 'start_date', 'course__category']
    search_fields = ['session_name', 'course__title', 'location']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['course', 'instructor', 'created_by']
    inlines = [TrainingEnrollmentInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('course', 'session_name')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date', 'registration_deadline')
        }),
        ('Ubicación', {
            'fields': ('location', 'venue_details')
        }),
        ('Instructor', {
            'fields': ('instructor', 'external_instructor_name', 'external_instructor_bio')
        }),
        ('Capacidad', {
            'fields': ('max_participants', 'min_participants')
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Presupuesto', {
            'fields': ('total_cost', 'budget_code')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'scheduled': 'blue',
            'in_progress': 'orange',
            'completed': 'green',
            'cancelled': 'red',
            'postponed': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def instructor_display(self, obj):
        if obj.instructor:
            return obj.instructor.user.get_full_name()
        return obj.external_instructor_name or '-'
    instructor_display.short_description = 'Instructor'
    
    def enrollment_status(self, obj):
        enrolled = obj.enrollments.filter(status='enrolled').count()
        return f"{enrolled}/{obj.max_participants}"
    enrollment_status.short_description = 'Inscritos'
    
    actions = ['start_sessions', 'complete_sessions']
    
    def start_sessions(self, request, queryset):
        updated = queryset.filter(status='scheduled').update(status='in_progress')
        self.message_user(request, f'{updated} sesiones iniciadas.')
    start_sessions.short_description = 'Iniciar sesiones seleccionadas'
    
    def complete_sessions(self, request, queryset):
        updated = queryset.filter(status='in_progress').update(status='completed')
        self.message_user(request, f'{updated} sesiones completadas.')
    complete_sessions.short_description = 'Completar sesiones seleccionadas'


@admin.register(TrainingEnrollment)
class TrainingEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'session_name', 'status_badge', 'final_score',
                    'attendance_percentage', 'certificate_issued', 'enrolled_at']
    list_filter = ['status', 'certificate_issued', 'session__course__category', 'enrolled_at']
    search_fields = ['employee__user__first_name', 'employee__user__last_name',
                    'employee__employee_number', 'session__session_name']
    date_hierarchy = 'enrolled_at'
    readonly_fields = ['enrolled_at', 'completed_at', 'approved_at', 
                      'created_at', 'updated_at']
    autocomplete_fields = ['session', 'employee', 'approved_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('session', 'employee', 'status')
        }),
        ('Aprobación', {
            'fields': ('requires_manager_approval', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Asistencia', {
            'fields': ('attendance_percentage',)
        }),
        ('Evaluación', {
            'fields': ('pre_assessment_score', 'post_assessment_score', 
                      'final_score', 'passing_score')
        }),
        ('Retroalimentación', {
            'fields': ('participant_feedback', 'instructor_feedback')
        }),
        ('Certificación', {
            'fields': ('certificate_issued', 'certificate_issue_date', 
                      'certificate_expiry_date', 'certificate_file')
        }),
        ('Fechas', {
            'fields': ('enrolled_at', 'completed_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def session_name(self, obj):
        return obj.session.session_name
    session_name.short_description = 'Sesión'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'cyan',
            'rejected': 'red',
            'enrolled': 'blue',
            'completed': 'green',
            'failed': 'darkred',
            'cancelled': 'gray',
            'no_show': 'black'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    actions = ['approve_enrollments', 'issue_certificates']
    
    def approve_enrollments(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for enrollment in queryset.filter(status='pending'):
            enrollment.status = 'enrolled'
            enrollment.approved_by = request.user.employee_profile
            enrollment.approved_at = timezone.now()
            enrollment.save()
            updated += 1
        
        self.message_user(request, f'{updated} inscripciones aprobadas.')
    approve_enrollments.short_description = 'Aprobar inscripciones seleccionadas'
    
    def issue_certificates(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        updated = 0
        for enrollment in queryset.filter(status='completed', certificate_issued=False):
            if enrollment.session.course.provides_certificate:
                enrollment.certificate_issued = True
                enrollment.certificate_issue_date = timezone.now().date()
                if enrollment.session.course.certificate_validity_days:
                    enrollment.certificate_expiry_date = (
                        timezone.now().date() + 
                        timedelta(days=enrollment.session.course.certificate_validity_days)
                    )
                enrollment.save()
                
                # Crear certificación
                Certification.objects.get_or_create(
                    employee=enrollment.employee,
                    enrollment=enrollment,
                    defaults={
                        'certification_name': enrollment.session.course.title,
                        'issuing_organization': enrollment.session.course.provider.name,
                        'issue_date': enrollment.certificate_issue_date,
                        'expiry_date': enrollment.certificate_expiry_date,
                        'status': 'active'
                    }
                )
                updated += 1
        
        self.message_user(request, f'{updated} certificados emitidos.')
    issue_certificates.short_description = 'Emitir certificados'


@admin.register(TrainingAttendance)
class TrainingAttendanceAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'session_date', 'status_badge', 
                    'check_in_time', 'check_out_time', 'recorded_by']
    list_filter = ['status', 'session_date']
    search_fields = ['enrollment__employee__user__first_name',
                    'enrollment__employee__user__last_name', 'session_topic']
    date_hierarchy = 'session_date'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['enrollment', 'recorded_by']
    
    def status_badge(self, obj):
        colors = {
            'present': 'green',
            'absent': 'red',
            'late': 'orange',
            'excused': 'blue'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(TrainingAssessment)
class TrainingAssessmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'enrollment', 'assessment_type', 'obtained_score',
                    'max_score', 'has_passed_badge', 'submitted_date']
    list_filter = ['assessment_type', 'assigned_date', 'graded_date']
    search_fields = ['title', 'enrollment__employee__user__first_name',
                    'enrollment__employee__user__last_name']
    date_hierarchy = 'assigned_date'
    readonly_fields = ['created_at', 'updated_at', 'submitted_date', 'graded_date']
    autocomplete_fields = ['enrollment', 'graded_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('enrollment', 'assessment_type', 'title', 'description')
        }),
        ('Puntuación', {
            'fields': ('max_score', 'obtained_score', 'passing_score')
        }),
        ('Fechas', {
            'fields': ('assigned_date', 'due_date', 'submitted_date', 'graded_date')
        }),
        ('Archivos', {
            'fields': ('assessment_file', 'submission_file')
        }),
        ('Retroalimentación', {
            'fields': ('feedback', 'graded_by')
        }),
    )
    
    def has_passed_badge(self, obj):
        if obj.has_passed is None:
            return '-'
        
        if obj.has_passed:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; border-radius: 3px;">✓ Aprobado</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 3px 10px; border-radius: 3px;">✗ Reprobado</span>'
            )
    has_passed_badge.short_description = '¿Aprobado?'


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ['certification_name', 'employee', 'issuing_organization',
                    'issue_date', 'expiry_date', 'status_badge']
    list_filter = ['status', 'issuing_organization', 'issue_date', 'expiry_date']
    search_fields = ['certification_name', 'certification_number', 
                    'employee__user__first_name', 'employee__user__last_name']
    date_hierarchy = 'issue_date'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['employee', 'enrollment']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'enrollment', 'certification_name', 
                      'certification_number', 'issuing_organization')
        }),
        ('Fechas', {
            'fields': ('issue_date', 'expiry_date')
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Documentos', {
            'fields': ('certificate_file', 'verification_url')
        }),
        ('Información Adicional', {
            'fields': ('description', 'notes')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'expired': 'red',
            'revoked': 'darkred',
            'pending_renewal': 'orange'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(TrainingBudget)
class TrainingBudgetAdmin(admin.ModelAdmin):
    list_display = ['year', 'department', 'allocated_budget', 'spent_amount',
                    'remaining_budget_display', 'utilization_bar']
    list_filter = ['year', 'department']
    search_fields = ['notes']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['department', 'created_by']
    
    def remaining_budget_display(self, obj):
        return f"{obj.currency} {obj.remaining_budget:,.2f}"
    remaining_budget_display.short_description = 'Presupuesto Restante'
    
    def utilization_bar(self, obj):
        percentage = obj.utilization_percentage
        color = 'red' if percentage >= 90 else 'orange' if percentage >= 75 else 'green'
        return format_html(
            '<div style="width: 100px; background-color: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}px; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white;">{:.1f}%</div>'
            '</div>',
            min(percentage, 100), color, percentage
        )
    utilization_bar.short_description = 'Utilización'


@admin.register(TrainingRequest)
class TrainingRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'training_title', 'status_badge', 
                    'preferred_start_date', 'estimated_cost', 'created_at']
    list_filter = ['status', 'preferred_start_date', 'created_at']
    search_fields = ['training_title', 'justification', 'employee__user__first_name',
                    'employee__user__last_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['reviewed_at', 'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'course', 'reviewed_by', 'assigned_session']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'course', 'training_title')
        }),
        ('Detalles', {
            'fields': ('justification', 'expected_benefits')
        }),
        ('Fechas Preferidas', {
            'fields': ('preferred_start_date', 'preferred_end_date')
        }),
        ('Costos', {
            'fields': ('estimated_cost',)
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Revisión', {
            'fields': ('reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('Asignación', {
            'fields': ('assigned_session',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'scheduled': 'blue',
            'completed': 'darkgreen'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(TrainingFeedback)
class TrainingFeedbackAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'overall_satisfaction_stars', 'average_rating_display',
                    'would_recommend', 'submitted_at']
    list_filter = ['overall_satisfaction', 'would_recommend', 'submitted_at']
    search_fields = ['enrollment__employee__user__first_name',
                    'enrollment__employee__user__last_name']
    date_hierarchy = 'submitted_at'
    readonly_fields = ['submitted_at']
    autocomplete_fields = ['enrollment']
    
    fieldsets = (
        ('Inscripción', {
            'fields': ('enrollment',)
        }),
        ('Calificaciones', {
            'fields': ('content_quality', 'instructor_effectiveness', 
                      'materials_quality', 'relevance_to_job', 'overall_satisfaction')
        }),
        ('Comentarios', {
            'fields': ('strengths', 'improvements', 'additional_comments')
        }),
        ('Recomendación', {
            'fields': ('would_recommend',)
        }),
    )
    
    def overall_satisfaction_stars(self, obj):
        stars = '⭐' * obj.overall_satisfaction
        return format_html('<span>{}</span>', stars)
    overall_satisfaction_stars.short_description = 'Satisfacción'
    
    def average_rating_display(self, obj):
        avg = obj.average_rating
        return f"{avg:.2f}/5.0"
    average_rating_display.short_description = 'Promedio'