from django.contrib import admin
from django.utils.html import format_html
from .models import (
    PerformanceReviewCycle, CompetencyCategory, Competency, PerformanceReview,
    CompetencyRating, Goal, GoalCheckIn, Feedback, DevelopmentPlan,
    DevelopmentAction, PerformanceImprovementPlan, PIPCheckIn
)


@admin.register(PerformanceReviewCycle)
class PerformanceReviewCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'review_type', 'start_date', 'end_date', 
                    'status_badge', 'department', 'is_active', 'reviews_count']
    list_filter = ['review_type', 'status', 'department', 'start_date']
    search_fields = ['name', 'description']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['department', 'created_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'review_type')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date', 'self_review_deadline', 'manager_review_deadline')
        }),
        ('Alcance', {
            'fields': ('department',)
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Configuración', {
            'fields': ('enable_self_review', 'enable_peer_review', 'enable_360_review')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'active': 'green',
            'completed': 'blue',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def reviews_count(self, obj):
        return obj.reviews.count()
    reviews_count.short_description = 'Evaluaciones'
    
    actions = ['activate_cycles', 'complete_cycles']
    
    def activate_cycles(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='active')
        self.message_user(request, f'{updated} ciclos activados correctamente.')
    activate_cycles.short_description = 'Activar ciclos seleccionados'
    
    def complete_cycles(self, request, queryset):
        updated = queryset.filter(status='active').update(status='completed')
        self.message_user(request, f'{updated} ciclos completados correctamente.')
    complete_cycles.short_description = 'Completar ciclos seleccionados'


@admin.register(CompetencyCategory)
class CompetencyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active', 'competencies_count']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    
    def competencies_count(self, obj):
        return obj.competencies.filter(is_active=True).count()
    competencies_count.short_description = 'Competencias'


@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']
    autocomplete_fields = ['category']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'category', 'description')
        }),
        ('Niveles de Competencia', {
            'fields': ('level_1_description', 'level_2_description', 'level_3_description',
                      'level_4_description', 'level_5_description')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )


class CompetencyRatingInline(admin.TabularInline):
    model = CompetencyRating
    extra = 0
    readonly_fields = ['competency', 'rating_type', 'rating', 'comments', 'rated_by']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ['employee', 'review_cycle', 'reviewer', 'status_badge',
                    'overall_rating_stars', 'self_rating_stars', 'manager_rating_stars']
    list_filter = ['status', 'review_cycle', 'overall_rating', 'self_rating', 'manager_rating']
    search_fields = ['employee__user__first_name', 'employee__user__last_name',
                     'employee__employee_number']
    date_hierarchy = 'created_at'
    readonly_fields = ['self_review_completed_at', 'manager_review_completed_at',
                      'approved_at', 'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'review_cycle', 'reviewer']
    inlines = [CompetencyRatingInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('review_cycle', 'employee', 'reviewer', 'status')
        }),
        ('Calificaciones Generales', {
            'fields': ('overall_rating', 'self_rating', 'manager_rating')
        }),
        ('Auto-Evaluación', {
            'fields': ('self_review_comments', 'achievements', 'self_review_completed_at')
        }),
        ('Evaluación del Manager', {
            'fields': ('manager_comments', 'strengths', 'areas_for_improvement', 'manager_review_completed_at')
        }),
        ('Aprobación', {
            'fields': ('approved_at',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'self_review': 'blue',
            'manager_review': 'orange',
            'peer_review': 'cyan',
            'completed': 'green',
            'approved': 'darkgreen'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def overall_rating_stars(self, obj):
        if obj.overall_rating:
            stars = '⭐' * obj.overall_rating
            return format_html('<span>{}</span>', stars)
        return '-'
    overall_rating_stars.short_description = 'Calif. General'
    
    def self_rating_stars(self, obj):
        if obj.self_rating:
            stars = '⭐' * obj.self_rating
            return format_html('<span>{}</span>', stars)
        return '-'
    self_rating_stars.short_description = 'Auto-Calif.'
    
    def manager_rating_stars(self, obj):
        if obj.manager_rating:
            stars = '⭐' * obj.manager_rating
            return format_html('<span>{}</span>', stars)
        return '-'
    manager_rating_stars.short_description = 'Calif. Manager'


@admin.register(CompetencyRating)
class CompetencyRatingAdmin(admin.ModelAdmin):
    list_display = ['performance_review', 'competency', 'rating_type', 'rating_stars', 'rated_by']
    list_filter = ['rating_type', 'rating', 'competency__category']
    search_fields = ['performance_review__employee__user__first_name',
                     'performance_review__employee__user__last_name']
    autocomplete_fields = ['performance_review', 'competency', 'rated_by']
    
    def rating_stars(self, obj):
        stars = '⭐' * obj.rating
        return format_html('<span>{}</span>', stars)
    rating_stars.short_description = 'Calificación'


class GoalCheckInInline(admin.TabularInline):
    model = GoalCheckIn
    extra = 0
    readonly_fields = ['progress_percentage', 'notes', 'created_by', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['title', 'employee', 'goal_type', 'priority_badge', 
                    'status_badge', 'progress_bar', 'target_date']
    list_filter = ['goal_type', 'priority', 'status', 'start_date', 'target_date']
    search_fields = ['title', 'description', 'employee__user__first_name',
                     'employee__user__last_name']
    date_hierarchy = 'target_date'
    readonly_fields = ['completed_date', 'approved_at', 'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'manager', 'approved_by', 'performance_review']
    inlines = [GoalCheckInInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'title', 'description')
        }),
        ('Clasificación', {
            'fields': ('goal_type', 'priority')
        }),
        ('Fechas', {
            'fields': ('start_date', 'target_date', 'completed_date')
        }),
        ('Progreso', {
            'fields': ('status', 'progress_percentage')
        }),
        ('Métricas', {
            'fields': ('is_measurable', 'target_value', 'current_value', 'unit_of_measure')
        }),
        ('Aprobación', {
            'fields': ('manager', 'approved_by', 'approved_at')
        }),
        ('Relación', {
            'fields': ('performance_review',)
        }),
    )
    
    def priority_badge(self, obj):
        colors = {
            'low': 'green',
            'medium': 'blue',
            'high': 'orange',
            'critical': 'red'
        }
        color = colors.get(obj.priority, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Prioridad'
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'active': 'blue',
            'completed': 'green',
            'cancelled': 'red',
            'overdue': 'darkred'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def progress_bar(self, obj):
        percentage = obj.progress_percentage
        color = 'green' if percentage >= 75 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background-color: #e0e0e0; border-radius: 3px;">'
            '<div style="width: {}px; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white;">{} %</div>'
            '</div>',
            percentage, color, percentage
        )
    progress_bar.short_description = 'Progreso'
    
    actions = ['mark_as_completed']
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        for goal in queryset:
            goal.progress_percentage = 100
            goal.completed_date = timezone.now().date()
            goal.update_status()
        
        count = queryset.count()
        self.message_user(request, f'{count} metas marcadas como completadas.')
    mark_as_completed.short_description = 'Marcar como completadas'


@admin.register(GoalCheckIn)
class GoalCheckInAdmin(admin.ModelAdmin):
    list_display = ['goal', 'progress_percentage', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['goal__title', 'notes']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    autocomplete_fields = ['goal', 'created_by']


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['subject', 'from_employee_display', 'to_employee', 
                    'feedback_type_badge', 'status_badge', 'created_at']
    list_filter = ['feedback_type', 'status', 'is_anonymous', 'is_private', 'created_at']
    search_fields = ['subject', 'content', 'to_employee__user__first_name',
                     'to_employee__user__last_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['acknowledged_at', 'created_at', 'updated_at']
    autocomplete_fields = ['from_employee', 'to_employee', 'performance_review']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('from_employee', 'to_employee', 'feedback_type')
        }),
        ('Contenido', {
            'fields': ('subject', 'content')
        }),
        ('Privacidad', {
            'fields': ('is_anonymous', 'is_private')
        }),
        ('Estado', {
            'fields': ('status', 'acknowledged_at')
        }),
        ('Relación', {
            'fields': ('performance_review',)
        }),
    )
    
    def from_employee_display(self, obj):
        if obj.is_anonymous:
            return 'Anónimo'
        return obj.from_employee.user.get_full_name()
    from_employee_display.short_description = 'De'
    
    def feedback_type_badge(self, obj):
        colors = {
            'positive': 'green',
            'constructive': 'orange',
            'recognition': 'blue',
            'coaching': 'purple'
        }
        color = colors.get(obj.feedback_type, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_feedback_type_display()
        )
    feedback_type_badge.short_description = 'Tipo'
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'submitted': 'blue',
            'acknowledged': 'green'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


class DevelopmentActionInline(admin.TabularInline):
    model = DevelopmentAction
    extra = 1
    fields = ['title', 'action_type', 'target_date', 'status']


@admin.register(DevelopmentPlan)
class DevelopmentPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'employee', 'start_date', 'end_date', 
                    'status_badge', 'manager']
    list_filter = ['status', 'start_date']
    search_fields = ['title', 'description', 'employee__user__first_name',
                     'employee__user__last_name']
    date_hierarchy = 'start_date'
    readonly_fields = ['approved_at', 'created_at', 'updated_at']
    autocomplete_fields = ['employee', 'manager', 'approved_by', 'performance_review']
    inlines = [DevelopmentActionInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'title', 'description')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date')
        }),
        ('Estado', {
            'fields': ('status',)
        }),
        ('Aprobación', {
            'fields': ('manager', 'approved_by', 'approved_at')
        }),
        ('Relación', {
            'fields': ('performance_review',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'active': 'green',
            'completed': 'blue',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(DevelopmentAction)
class DevelopmentActionAdmin(admin.ModelAdmin):
    list_display = ['title', 'development_plan', 'action_type', 'target_date', 
                    'status_badge', 'completed_date']
    list_filter = ['action_type', 'status', 'target_date']
    search_fields = ['title', 'description']
    date_hierarchy = 'target_date'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['development_plan']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'in_progress': 'blue',
            'completed': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


class PIPCheckInInline(admin.TabularInline):
    model = PIPCheckIn
    extra = 0
    readonly_fields = ['check_in_date', 'is_on_track', 'conducted_by', 'created_at']
    can_delete = False


@admin.register(PerformanceImprovementPlan)
class PerformanceImprovementPlanAdmin(admin.ModelAdmin):
    list_display = ['employee', 'title', 'start_date', 'end_date', 
                    'status_badge', 'manager']
    list_filter = ['status', 'start_date']
    search_fields = ['title', 'employee__user__first_name',
                     'employee__user__last_name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['employee', 'manager', 'performance_review']
    inlines = [PIPCheckInInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'manager', 'title')
        }),
        ('Detalles del Plan', {
            'fields': ('performance_issues', 'expected_improvements', 
                      'support_provided', 'consequences')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date', 'review_frequency_days')
        }),
        ('Estado', {
            'fields': ('status', 'final_outcome')
        }),
        ('Relación', {
            'fields': ('performance_review',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'active': 'blue',
            'successful': 'green',
            'unsuccessful': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Estado'


@admin.register(PIPCheckIn)
class PIPCheckInAdmin(admin.ModelAdmin):
    list_display = ['improvement_plan', 'check_in_date', 'is_on_track_badge', 'conducted_by']
    list_filter = ['is_on_track', 'check_in_date']
    search_fields = ['improvement_plan__employee__user__first_name',
                     'improvement_plan__employee__user__last_name']
    date_hierarchy = 'check_in_date'
    readonly_fields = ['created_at']
    autocomplete_fields = ['improvement_plan', 'conducted_by']
    
    def is_on_track_badge(self, obj):
        if obj.is_on_track:
            return format_html(
                '<span style="background-color: green; color: white; padding: 3px 10px; border-radius: 3px;">✓ En Progreso</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 3px 10px; border-radius: 3px;">✗ Preocupante</span>'
            )
    is_on_track_badge.short_description = 'En Progreso'