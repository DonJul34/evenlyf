from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import (
    User, PersonalityTestResult, OnboardingProgress, 
    UserInterests, Reservation, EventGroup, GroupMembership, FriendInvitation
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'email_verified', 'invited_by_display', 'created_at']
    list_filter = ['is_active', 'email_verified', 'is_staff', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['last_login', 'date_joined', 'created_at', 'updated_at', 'invited_by_display']
    
    def invited_by_display(self, obj):
        """Affiche qui a invité cet utilisateur"""
        try:
            # Chercher une invitation acceptée pour cet utilisateur
            invitation = FriendInvitation.objects.filter(
                invited_user=obj,
                status='ACCEPTED'
            ).select_related('inviter').first()
            
            if invitation:
                return format_html(
                    '✉️ Invité par <strong>{}</strong>',
                    invitation.inviter.email
                )
            return "❌ Non invité"
        except:
            return "❌ Erreur"
    
    invited_by_display.short_description = "Invité par"


@admin.register(FriendInvitation)
class FriendInvitationAdmin(admin.ModelAdmin):
    list_display = ['inviter_email', 'invited_email', 'activity_name', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['inviter__email', 'invited_email', 'reservation__activity_name']
    readonly_fields = ['invitation_token', 'created_at', 'accepted_at', 'used_at']
    
    fieldsets = (
        ('Invitation', {
            'fields': ('inviter', 'invited_email', 'invited_user', 'invitation_token')
        }),
        ('Activité', {
            'fields': ('reservation', 'message')
        }),
        ('Statut', {
            'fields': ('status', 'created_at', 'expires_at', 'accepted_at', 'used_at')
        }),
    )
    
    def inviter_email(self, obj):
        return obj.inviter.email
    inviter_email.short_description = "Inviteur"
    
    def activity_name(self, obj):
        return obj.reservation.activity_name
    activity_name.short_description = "Activité"





class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0
    readonly_fields = ['joined_at']


@admin.register(EventGroup)
class EventGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'event_date', 'activity_name', 'participants_count_display', 'max_participants', 'is_confirmed', 'created_at']
    list_filter = ['event_date', 'activity_name', 'is_confirmed', 'created_at']
    search_fields = ['name', 'activity_name', 'meeting_point_name']
    readonly_fields = ['participants_count', 'created_at', 'updated_at']
    inlines = [GroupMembershipInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'event_date', 'activity_name', 'max_participants', 'is_confirmed')
        }),
        ('Point de rendez-vous', {
            'fields': ('meeting_point_name', 'meeting_point_address', 'meeting_time', 'location_reveal_time')
        }),
        ('Statistiques', {
            'fields': ('participants_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def participants_count_display(self, obj):
        count = obj.participants_count
        max_count = obj.max_participants
        color = 'green' if count == max_count else 'orange' if count > 0 else 'red'
        return format_html(
            '<span style="color: {};">{}/{}</span>',
            color, count, max_count
        )
    participants_count_display.short_description = 'Participants'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'activity_name', 'reservation_date', 'status', 'group_display', 'price_amount', 'is_paid', 'created_at']
    list_filter = ['status', 'reservation_date', 'activity_name', 'created_at']
    search_fields = ['user__email', 'activity_name', 'venue_name']
    readonly_fields = ['stripe_payment_intent_id', 'paid_at', 'cancellation_deadline', 'created_at', 'updated_at', 'has_group']
    
    fieldsets = (
        ('Utilisateur et activité', {
            'fields': ('user', 'activity_name', 'activity_description')
        }),
        ('Date et lieu', {
            'fields': ('reservation_date', 'reservation_time', 'venue_name', 'venue_address')
        }),
        ('Tarification', {
            'fields': ('price_plan', 'price_amount', 'currency')
        }),
        ('Statut et paiement', {
            'fields': ('status', 'stripe_payment_intent_id', 'paid_at')
        }),
        ('Autres informations', {
            'fields': ('participants_count', 'special_requests', 'cancellation_deadline'),
            'classes': ('collapse',)
        }),
        ('Groupe', {
            'fields': ('has_group',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['create_groups_for_selected', 'confirm_reservations']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email utilisateur'
    
    def group_display(self, obj):
        if obj.has_group:
            group = obj.group
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:users_eventgroup_change', args=[group.id]),
                group.name
            )
        return format_html('<span style="color: red;">Aucun groupe</span>')
    group_display.short_description = 'Groupe'
    
    def is_paid(self, obj):
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if obj.paid_at else 'red',
            'Payé' if obj.paid_at else 'Non payé'
        )
    is_paid.short_description = 'Paiement'
    
    def create_groups_for_selected(self, request, queryset):
        """Action pour créer automatiquement des groupes pour les réservations sélectionnées"""
        
        # Grouper les réservations par date et activité
        grouped_reservations = {}
        for reservation in queryset.filter(status='CONFIRMED'):
            if reservation.has_group:
                continue  # Ignorer les réservations déjà assignées
                
            key = (reservation.reservation_date, reservation.activity_name)
            if key not in grouped_reservations:
                grouped_reservations[key] = []
            grouped_reservations[key].append(reservation)
        
        groups_created = 0
        for (date, activity), reservations in grouped_reservations.items():
            # Créer des groupes de 6 maximum
            for i in range(0, len(reservations), 6):
                group_reservations = reservations[i:i+6]
                
                # Créer le groupe
                group = EventGroup.objects.create(
                    name=f"Groupe {activity} - {date.strftime('%d/%m')} #{i//6 + 1}",
                    event_date=date,
                    activity_name=activity,
                    max_participants=6,
                    is_confirmed=True
                )
                
                # Assigner les réservations au groupe
                for reservation in group_reservations:
                    GroupMembership.objects.create(
                        reservation=reservation,
                        group=group
                    )
                
                groups_created += 1
        
        self.message_user(
            request,
            f"{groups_created} groupe(s) créé(s) avec succès.",
            messages.SUCCESS
        )
    
    create_groups_for_selected.short_description = "Créer des groupes automatiquement"
    
    def confirm_reservations(self, request, queryset):
        """Action pour confirmer les réservations sélectionnées"""
        updated = queryset.update(status='CONFIRMED')
        self.message_user(
            request,
            f"{updated} réservation(s) confirmée(s).",
            messages.SUCCESS
        )
    
    confirm_reservations.short_description = "Confirmer les réservations"


@admin.register(PersonalityTestResult)
class PersonalityTestResultAdmin(admin.ModelAdmin):
    """Admin pour les résultats de tests de personnalité"""
    
    list_display = ['user', 'mbti_result', 'disc_result', 'test_duration_minutes', 'completed_at']
    list_filter = ['mbti_result', 'disc_result', 'completed_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering = ['-completed_at']
    
    readonly_fields = ['completed_at']
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Scores MBTI', {
            'fields': ('extraversion_score', 'intuition_score', 'thinking_score', 'judging_score')
        }),
        ('Scores DISC', {
            'fields': ('dominance_score', 'influence_score', 'steadiness_score', 'conscientiousness_score')
        }),
        ('Résultats', {
            'fields': ('mbti_result', 'disc_result')
        }),
        ('Métadonnées', {
            'fields': ('test_duration_seconds', 'completed_at')
        }),
    )
    
    def test_duration_minutes(self, obj):
        """Afficher la durée en minutes"""
        if obj.test_duration_seconds:
            return f"{obj.test_duration_seconds // 60}m {obj.test_duration_seconds % 60}s"
        return '-'
    test_duration_minutes.short_description = 'Durée du test'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')





@admin.register(UserInterests)
class UserInterestsAdmin(admin.ModelAdmin):
    list_display = ['user', 'interests_count', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(OnboardingProgress)
class OnboardingProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_step', 'started_at']
    list_filter = ['current_step', 'started_at']
    search_fields = ['user__email']


# Configuration du site admin
admin.site.site_header = "Evenlyf Administration"
admin.site.site_title = "Evenlyf Admin"
admin.site.index_title = "Tableau de bord"
