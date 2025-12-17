from django.contrib import admin
from django.utils.html import format_html
from .models import (
    JobPosting, Candidate, Application, RecruitmentStage, Interview,
    Assessment, JobOffer, OnboardingTask, RecruitmentReport
)


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['title', 'job_code', 'department', 'position', 
                    'employment_type', 'status_badge', 'posted_date', 
                    'application_deadline', 'applications_count']
    list_filter = ['status', 'employment_type', 'experience_level', 
                   'department', 'remote_option', 'posted_date']
    search_fields = ['title', 'job_code', 'description']
    date_hierarchy = 'posted_date'
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    autocomplete_fields = ['department', 'position', 'hiring_manager', 'created_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'job_code', 'department', 'position')
        }),
        ('Detalles del Trabajo', {
            'fields': ('employment_type', 'experience_level', 'location', 'remote_option')
        }),
        ('Descripción', {
            'fields': ('description', 'responsibilities', 'requirements', 
                      'preferred_qualifications', 'benefits')
        }),
        ('Salario', {
            'fields': ('min_salary', 'max_salary', 'salary_currency', 'show_salary')
        }),
        ('Vacantes y Fechas', {
            'fields': ('number_of_positions', 'posted_date', 'application_deadline')
        }),
        ('Estado', {
            'fields': ('status', 'hiring_manager')
        }),
        ('Metadata', {
            'fields': ('views_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'active': 'green',
            'paused': 'orange',
            'closed': 'red',
            'filled': 'blue'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def applications_count(self, obj):
        return obj.applications_count
    applications_count.short_description = 'Solicitudes'
    
    actions = ['publish_postings', 'close_postings']
    
    def publish_postings(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for posting in queryset.filter(status='draft'):
            posting.status = 'active'
            posting.posted_date = timezone.now().date()
            posting.save()
            updated += 1
        
        self.message_user(request, f'{updated} vacantes publicadas correctamente.')
    publish_postings.short_description = 'Publicar vacantes seleccionadas'
    
    def close_postings(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} vacantes cerradas correctamente.')
    close_postings.short_description = 'Cerrar vacantes seleccionadas'


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'email', 'phone', 'current_position', 
                    'years_of_experience', 'source', 'created_at']
    list_filter = ['source', 'education_level', 'country', 'city', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'skills', 
                    'current_position', 'current_company']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['referred_by']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Dirección', {
            'fields': ('address', 'city', 'country')
        }),
        ('Información Profesional', {
            'fields': ('current_position', 'current_company', 'years_of_experience', 
                      'education_level')
        }),
        ('Documentos', {
            'fields': ('resume', 'cover_letter', 'portfolio_url', 'linkedin_url')
        }),
        ('Compensación', {
            'fields': ('expected_salary', 'salary_currency')
        }),
        ('Disponibilidad', {
            'fields': ('available_from', 'notice_period_days')
        }),
        ('Origen', {
            'fields': ('source', 'referred_by')
        }),
        ('Habilidades', {
            'fields': ('skills',)
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Nombre Completo'


class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 0
    readonly_fields = ['scheduled_date', 'scheduled_time', 'status', 'result']
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False


class AssessmentInline(admin.TabularInline):
    model = Assessment
    extra = 0
    readonly_fields = ['title', 'status', 'obtained_score', 'max_score']
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['candidate_name', 'job_title', 'status_badge', 'rating_stars',
                    'assigned_recruiter', 'applied_date']
    list_filter = ['status', 'job_posting__department', 'assigned_recruiter', 
                   'rating', 'applied_date']
    search_fields = ['candidate__first_name', 'candidate__last_name', 
                    'candidate__email', 'job_posting__title']
    date_hierarchy = 'applied_date'
    readonly_fields = ['applied_date', 'status_changed_at', 'created_at', 'updated_at']
    autocomplete_fields = ['candidate', 'job_posting', 'current_stage', 'assigned_recruiter']
    inlines = [InterviewInline, AssessmentInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('candidate', 'job_posting', 'status', 'current_stage')
        }),
        ('Calificación', {
            'fields': ('rating',)
        }),
        ('Asignación', {
            'fields': ('assigned_recruiter',)
        }),
        ('Notas', {
            'fields': ('notes', 'rejection_reason')
        }),
        ('Fechas', {
            'fields': ('applied_date', 'status_changed_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def candidate_name(self, obj):
        return obj.candidate.get_full_name()
    candidate_name.short_description = 'Candidato'
    
    def job_title(self, obj):
        return obj.job_posting.title
    job_title.short_description = 'Vacante'
    
    def status_badge(self, obj):
        colors = {
            'applied': 'gray',
            'screening': 'blue',
            'shortlisted': 'cyan',
            'interviewing': 'purple',
            'assessment': 'orange',
            'offer': 'yellow',
            'hired': 'green',
            'rejected': 'red',
            'withdrawn': 'darkgray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def rating_stars(self, obj):
        if obj.rating:
            stars = '⭐' * obj.rating
            return format_html('<span>{}</span>', stars)
        return '-'
    rating_stars.short_description = 'Calificación'
    
    actions = ['move_to_screening', 'move_to_shortlisted', 'reject_applications']
    
    def move_to_screening(self, request, queryset):
        updated = queryset.update(status='screening')
        self.message_user(request, f'{updated} solicitudes movidas a revisión.')
    move_to_screening.short_description = 'Mover a revisión'
    
    def move_to_shortlisted(self, request, queryset):
        updated = queryset.update(status='shortlisted')
        self.message_user(request, f'{updated} solicitudes preseleccionadas.')
    move_to_shortlisted.short_description = 'Preseleccionar'
    
    def reject_applications(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} solicitudes rechazadas.')
    reject_applications.short_description = 'Rechazar solicitudes'


@admin.register(RecruitmentStage)
class RecruitmentStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'job_posting', 'order', 'duration_days', 'is_active']
    list_filter = ['is_active', 'job_posting']
    search_fields = ['name', 'description']
    ordering = ['order']
    autocomplete_fields = ['job_posting']


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['candidate_name', 'job_title', 'interview_type', 
                    'scheduled_date', 'scheduled_time', 'status_badge', 'result_badge']
    list_filter = ['interview_type', 'status', 'result', 'scheduled_date']
    search_fields = ['application__candidate__first_name', 
                    'application__candidate__last_name']
    date_hierarchy = 'scheduled_date'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['application', 'interviewers']
    filter_horizontal = ['interviewers']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('application', 'interview_type')
        }),
        ('Programación', {
            'fields': ('scheduled_date', 'scheduled_time', 'duration_minutes')
        }),
        ('Ubicación/Enlace', {
            'fields': ('location', 'meeting_link')
        }),
        ('Entrevistadores', {
            'fields': ('interviewers',)
        }),
        ('Estado y Resultado', {
            'fields': ('status', 'result')
        }),
        ('Feedback', {
            'fields': ('notes', 'candidate_strengths', 'candidate_weaknesses', 
                      'overall_rating', 'recommendation')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def candidate_name(self, obj):
        return obj.application.candidate.get_full_name()
    candidate_name.short_description = 'Candidato'
    
    def job_title(self, obj):
        return obj.application.job_posting.title
    job_title.short_description = 'Vacante'
    
    def status_badge(self, obj):
        colors = {
            'scheduled': 'blue',
            'completed': 'green',
            'cancelled': 'red',
            'rescheduled': 'orange',
            'no_show': 'darkred'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def result_badge(self, obj):
        colors = {
            'pass': 'green',
            'fail': 'red',
            'pending': 'gray'
        }
        color = colors.get(obj.result, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_result_display()
        )
    result_badge.short_description = 'Resultado'


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'candidate_name', 'assessment_type', 'status_badge',
                    'obtained_score', 'max_score', 'is_passed_badge']
    list_filter = ['assessment_type', 'status', 'sent_date']
    search_fields = ['title', 'application__candidate__first_name',
                    'application__candidate__last_name']
    date_hierarchy = 'sent_date'
    readonly_fields = ['sent_date', 'submitted_date', 'created_at', 'updated_at']
    autocomplete_fields = ['application', 'evaluator']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('application', 'title', 'description', 'assessment_type')
        }),
        ('Archivos y Enlaces', {
            'fields': ('assessment_file', 'submission_file', 'assessment_url')
        }),
        ('Fechas', {
            'fields': ('sent_date', 'due_date', 'submitted_date')
        }),
        ('Calificación', {
            'fields': ('max_score', 'obtained_score', 'passing_score')
        }),
        ('Estado', {
            'fields': ('status', 'evaluator')
        }),
        ('Feedback', {
            'fields': ('feedback',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def candidate_name(self, obj):
        return obj.application.candidate.get_full_name()
    candidate_name.short_description = 'Candidato'
    
    def status_badge(self, obj):
        colors = {
            'sent': 'blue',
            'in_progress': 'orange',
            'submitted': 'cyan',
            'graded': 'green',
            'expired': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def is_passed_badge(self, obj):
        if obj.is_passed is None:
            return '-'
        
        if obj.is_passed:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; border-radius: 3px;">✓ Aprobado</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 3px 10px; border-radius: 3px;">✗ Reprobado</span>'
            )
    is_passed_badge.short_description = '¿Aprobado?'


@admin.register(JobOffer)
class JobOfferAdmin(admin.ModelAdmin):
    list_display = ['candidate_name', 'position_title', 'salary', 
                    'offer_date', 'expiry_date', 'status_badge']
    list_filter = ['status', 'department', 'offer_date']
    search_fields = ['application__candidate__first_name',
                    'application__candidate__last_name', 'position_title']
    date_hierarchy = 'offer_date'
    readonly_fields = ['candidate_response_date', 'approved_at', 'created_at', 'updated_at']
    autocomplete_fields = ['application', 'department', 'approved_by', 'created_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('application', 'position_title', 'department')
        }),
        ('Compensación', {
            'fields': ('salary', 'salary_currency', 'bonus')
        }),
        ('Fechas', {
            'fields': ('offer_date', 'expiry_date', 'proposed_start_date')
        }),
        ('Documentos', {
            'fields': ('offer_letter',)
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Respuesta del Candidato', {
            'fields': ('candidate_response_date', 'candidate_notes')
        }),
        ('Aprobación', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def candidate_name(self, obj):
        return obj.application.candidate.get_full_name()
    candidate_name.short_description = 'Candidato'
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'sent': 'blue',
            'accepted': 'green',
            'rejected': 'red',
            'expired': 'orange',
            'withdrawn': 'darkgray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'candidate_name', 'category', 'order', 
                    'status_badge', 'due_date', 'assigned_to']
    list_filter = ['status', 'category', 'due_date']
    search_fields = ['title', 'description']
    ordering = ['order', 'due_date']
    readonly_fields = ['completed_date', 'created_at', 'updated_at']
    autocomplete_fields = ['job_offer', 'assigned_to']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'description', 'category', 'order')
        }),
        ('Asignación', {
            'fields': ('job_offer', 'assigned_to')
        }),
        ('Estado', {
            'fields': ('status', 'due_date', 'completed_date')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
    )
    
    def candidate_name(self, obj):
        if obj.job_offer:
            return obj.job_offer.application.candidate.get_full_name()
        return '-'
    candidate_name.short_description = 'Candidato'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'in_progress': 'blue',
            'completed': 'green',
            'skipped': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(RecruitmentReport)
class RecruitmentReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'start_date', 'end_date', 
                    'department', 'generated_by', 'created_at']
    list_filter = ['report_type', 'department', 'created_at']
    search_fields = ['name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    autocomplete_fields = ['department', 'job_posting', 'generated_by']