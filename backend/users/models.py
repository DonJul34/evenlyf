from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import json


class User(AbstractUser):
    """Modèle utilisateur personnalisé"""
    
    GENDER_CHOICES = [
        ('M', 'Homme'),
        ('F', 'Femme'),
        ('O', 'Autre'),
        ('N', 'Ne souhaite pas préciser'),
    ]
    
    PERSONALITY_TYPE_CHOICES = [
        # MBTI Types
        ('INTJ', 'INTJ - Architecte'),
        ('INTP', 'INTP - Penseur'),
        ('ENTJ', 'ENTJ - Commandant'),
        ('ENTP', 'ENTP - Innovateur'),
        ('INFJ', 'INFJ - Avocat'),
        ('INFP', 'INFP - Médiateur'),
        ('ENFJ', 'ENFJ - Protagoniste'),
        ('ENFP', 'ENFP - Inspirateur'),
        ('ISTJ', 'ISTJ - Logisticien'),
        ('ISFJ', 'ISFJ - Protecteur'),
        ('ESTJ', 'ESTJ - Directeur'),
        ('ESFJ', 'ESFJ - Consul'),
        ('ISTP', 'ISTP - Virtuose'),
        ('ISFP', 'ISFP - Aventurier'),
        ('ESTP', 'ESTP - Entrepreneur'),
        ('ESFP', 'ESFP - Amuseur'),
    ]
    
    DISC_TYPE_CHOICES = [
        ('D', 'Dominant'),
        ('I', 'Influent'),
        ('S', 'Stable'),
        ('C', 'Consciencieux'),
    ]
    
    # Champs personnalisés
    email = models.EmailField('Adresse email', unique=True)
    phone = models.CharField('Téléphone', max_length=15, blank=True)
    birth_date = models.DateField('Date de naissance', null=True, blank=True)
    gender = models.CharField('Genre', max_length=1, choices=GENDER_CHOICES, blank=True)
    
    # Profil
    profile_picture = models.ImageField('Photo de profil', upload_to='profiles/', blank=True, null=True)
    bio = models.TextField('Biographie', max_length=500, blank=True)
    location = models.CharField('Localisation', max_length=100, blank=True)
    
    # Tests de personnalité
    personality_type = models.CharField('Type MBTI', max_length=4, choices=PERSONALITY_TYPE_CHOICES, blank=True)
    disc_type = models.CharField('Type DISC', max_length=1, choices=DISC_TYPE_CHOICES, blank=True)
    personality_test_completed = models.BooleanField('Test de personnalité complété', default=False)
    personality_test_date = models.DateTimeField('Date du test', null=True, blank=True)
    
    # Statut et dates
    email_verified = models.BooleanField('Email vérifié', default=False)
    onboarding_completed = models.BooleanField('Onboarding complété', default=False)
    is_premium = models.BooleanField('Compte premium', default=False)
    premium_until = models.DateTimeField('Premium jusqu\'à', null=True, blank=True)
    
    # Type de compte et abonnement
    ACCOUNT_TYPE_CHOICES = [
        ('FREE', 'Gratuit'),
        ('TICKET', 'Ticket'),
        ('SUBSCRIPTION', 'Abonnement'),
    ]
    account_type = models.CharField('Type de compte', max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='FREE')
    has_active_subscription = models.BooleanField('Abonnement actif', default=False)
    
    # Invitation et jumelage
    is_invited_user = models.BooleanField('Utilisateur invité', default=False)
    invitation_used = models.ForeignKey('FriendInvitation', on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_user_profile')
    
    # Méta-données
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    last_login_at = models.DateTimeField('Dernière connexion', null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def age(self):
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None
    
    @property
    def is_premium_active(self):
        if self.is_premium and self.premium_until:
            return self.premium_until > timezone.now()
        return False
    
    @property
    def active_subscription(self):
        """Retourne l'abonnement actif de l'utilisateur s'il existe"""
        return UserSubscription.get_active_subscription(self)
    
    @property
    def can_skip_payment(self):
        """Vérifie si l'utilisateur peut sauter l'étape de paiement"""
        # Les abonnés actifs peuvent sauter le paiement
        if self.has_active_subscription and self.active_subscription:
            return self.active_subscription.can_make_reservation
        return False
    
    @property
    def available_tickets(self):
        """Retourne les tickets disponibles de l'utilisateur"""
        return self.tickets.filter(status='ACTIVE', expires_at__gt=timezone.now())
    
    @property
    def has_available_tickets(self):
        """Vérifie si l'utilisateur a des tickets disponibles"""
        return self.available_tickets.exists()
    
    def update_subscription_status(self):
        """Met à jour le statut d'abonnement de l'utilisateur"""
        active_sub = self.active_subscription
        if active_sub:
            self.has_active_subscription = True
            self.account_type = 'SUBSCRIPTION'
            self.is_premium = True
            self.premium_until = active_sub.end_date
        else:
            self.has_active_subscription = False
            if self.has_available_tickets:
                self.account_type = 'TICKET'
            else:
                self.account_type = 'FREE'
            self.is_premium = False
            self.premium_until = None
        self.save()
        return self.account_type


class OnboardingProgress(models.Model):
    """Modèle pour suivre le progrès de l'onboarding"""
    
    STEP_CHOICES = [
        ('PERSONAL_INFO', 'Informations personnelles'),
        ('PERSONALITY_TEST', 'Test de personnalité'),
        ('PASSION_SELECTION', 'Sélection des passions'),
        ('COMPLETED', 'Terminé'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='onboarding_progress')
    current_step = models.CharField('Étape actuelle', max_length=20, choices=STEP_CHOICES, default='PERSONAL_INFO')
    completed_steps = models.JSONField('Étapes complétées', default=list)
    
    # Données temporaires de l'onboarding
    temp_data = models.JSONField('Données temporaires', default=dict, blank=True)
    
    # Timestamps
    started_at = models.DateTimeField('Commencé le', auto_now_add=True)
    last_updated = models.DateTimeField('Dernière mise à jour', auto_now=True)
    completed_at = models.DateTimeField('Terminé le', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Progrès onboarding'
        verbose_name_plural = 'Progrès onboarding'
    
    def __str__(self):
        return f"{self.user.email} - {self.get_current_step_display()}"
    
    def mark_step_completed(self, step_name):
        """Marquer une étape comme complétée"""
        if step_name not in self.completed_steps:
            self.completed_steps.append(step_name)
            self.save()
    
    def save_temp_data(self, data):
        """Sauvegarder des données temporaires"""
        self.temp_data.update(data)
        self.save()
    
    def complete_onboarding(self):
        """Marque l'onboarding comme complètement terminé"""
        self.current_step = 'COMPLETED'
        self.completed_at = timezone.now()
        self.mark_step_completed('PASSION_SELECTION')
        self.save()
        return self
    
    def get_completion_status(self):
        """Retourne l'état de completion de toutes les étapes"""
        completed_steps = self.completed_steps or []
        
        # Vérifier aussi si l'utilisateur a des résultats de test de personnalité
        try:
            has_personality_results = self.user.personality_result is not None
        except PersonalityTestResult.DoesNotExist:
            has_personality_results = False
        
        # Vérifier si l'utilisateur a des centres d'intérêt
        try:
            has_interests = self.user.interests.interests_count > 0
        except UserInterests.DoesNotExist:
            has_interests = False
        
        # Calculer si tout est complété
        is_completed = self.current_step == 'COMPLETED' or (
            'PERSONAL_INFO' in completed_steps and
            ('PERSONALITY_TEST' in completed_steps or has_personality_results) and
            ('PASSION_SELECTION' in completed_steps or has_interests)
        )
        
        return {
            'current_step': self.current_step,
            'is_completed': is_completed,
            'completed_steps': completed_steps,
            'personal_info_completed': 'PERSONAL_INFO' in completed_steps,
            'personality_test_completed': 'PERSONALITY_TEST' in completed_steps or has_personality_results,
            'passion_selection_completed': 'PASSION_SELECTION' in completed_steps or has_interests,
            'next_step': self._get_next_step()
        }
    
    def _get_next_step(self):
        """Détermine la prochaine étape basée sur l'état actuel"""
        completed_steps = self.completed_steps or []
        
        if 'PERSONAL_INFO' not in completed_steps:
            return 'PERSONAL_INFO'
        elif 'PERSONALITY_TEST' not in completed_steps:
            return 'PERSONALITY_TEST'
        elif 'PASSION_SELECTION' not in completed_steps:
            return 'PASSION_SELECTION'
        else:
            return 'COMPLETED'


class PersonalityTestSession(models.Model):
    """Modèle pour une session de test de personnalité"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personality_test_sessions')
    session_id = models.CharField('ID de session', max_length=50, unique=True)
    
    # Métadonnées du test
    started_at = models.DateTimeField('Commencé le', auto_now_add=True)
    completed_at = models.DateTimeField('Terminé le', null=True, blank=True)
    duration_seconds = models.IntegerField('Durée en secondes', null=True, blank=True)
    
    # Statut
    is_completed = models.BooleanField('Test complété', default=False)
    current_question = models.IntegerField('Question actuelle', default=0)
    
    class Meta:
        verbose_name = 'Session de test de personnalité'
        verbose_name_plural = 'Sessions de test de personnalité'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.email} - Session {self.session_id}"


class PersonalityTestAnswer(models.Model):
    """Modèle pour stocker chaque réponse du test de personnalité"""
    
    session = models.ForeignKey(PersonalityTestSession, on_delete=models.CASCADE, related_name='answers')
    question_id = models.IntegerField('ID de la question')
    question_text = models.TextField('Texte de la question')
    answer_index = models.IntegerField('Index de la réponse choisie')
    answer_text = models.TextField('Texte de la réponse')
    
    # Scores attribués par cette réponse
    mbti_scores = models.JSONField('Scores MBTI', default=dict)  # Ex: {"E": 2, "T": 1}
    disc_scores = models.JSONField('Scores DISC', default=dict)  # Ex: {"D": 3}
    
    answered_at = models.DateTimeField('Répondu le', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Réponse au test de personnalité'
        verbose_name_plural = 'Réponses au test de personnalité'
        unique_together = ['session', 'question_id']
    
    def __str__(self):
        return f"Q{self.question_id} - {self.session.user.email}"


class PersonalityTestResult(models.Model):
    """Résultats détaillés du test de personnalité"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='personality_result')
    session = models.OneToOneField(PersonalityTestSession, on_delete=models.CASCADE, related_name='result', null=True, blank=True)
    
    # Scores MBTI (0-100)
    extraversion_score = models.IntegerField('Score Extraversion', default=50)
    intuition_score = models.IntegerField('Score Intuition', default=50)
    thinking_score = models.IntegerField('Score Thinking', default=50)
    judging_score = models.IntegerField('Score Judging', default=50)
    
    # Scores DISC (0-100)
    dominance_score = models.IntegerField('Score Dominance', default=25)
    influence_score = models.IntegerField('Score Influence', default=25)
    steadiness_score = models.IntegerField('Score Steadiness', default=25)
    conscientiousness_score = models.IntegerField('Score Conscientiousness', default=25)
    
    # Résultats calculés
    mbti_result = models.CharField('Résultat MBTI', max_length=4, choices=User.PERSONALITY_TYPE_CHOICES)
    disc_result = models.CharField('Résultat DISC dominant', max_length=1, choices=User.DISC_TYPE_CHOICES)
    
    # Scores détaillés (pour analyse)
    detailed_mbti_scores = models.JSONField('Scores MBTI détaillés', default=dict)
    detailed_disc_scores = models.JSONField('Scores DISC détaillés', default=dict)
    
    # Métadonnées
    test_duration_seconds = models.IntegerField('Durée du test (secondes)', default=0)
    completed_at = models.DateTimeField('Complété le', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Résultat de test de personnalité'
        verbose_name_plural = 'Résultats de tests de personnalité'
    
    def __str__(self):
        return f"{self.user.full_name} - {self.mbti_result}/{self.disc_result}"


class VerificationCode(models.Model):
    """Modèle pour les codes de vérification temporaires"""
    
    CODE_TYPES = [
        ('EMAIL_VERIFICATION', 'Vérification email'),
        ('PASSWORD_RESET', 'Réinitialisation mot de passe'),
        ('PHONE_VERIFICATION', 'Vérification téléphone'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField('Code', max_length=6)
    code_type = models.CharField('Type de code', max_length=20, choices=CODE_TYPES)
    
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    expires_at = models.DateTimeField('Expire le')
    used_at = models.DateTimeField('Utilisé le', null=True, blank=True)
    is_used = models.BooleanField('Utilisé', default=False)
    
    class Meta:
        verbose_name = 'Code de vérification'
        verbose_name_plural = 'Codes de vérification'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.code} ({self.get_code_type_display()})"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired
    
    def mark_as_used(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
    
    @classmethod
    def create_verification_code(cls, user, code_type, duration_minutes=10):
        """Créer un nouveau code de vérification"""
        from .utils import generate_verification_code
        
        # Invalider les anciens codes du même type
        cls.objects.filter(
            user=user,
            code_type=code_type,
            is_used=False
        ).update(is_used=True)
        
        # Créer le nouveau code
        code = generate_verification_code()
        expires_at = timezone.now() + timedelta(minutes=duration_minutes)
        
        verification_code = cls.objects.create(
            user=user,
            code=code,
            code_type=code_type,
            expires_at=expires_at
        )
        
        return verification_code


class UserPassion(models.Model):
    """Modèle pour les passions des utilisateurs"""
    
    PASSION_CATEGORIES = [
        ('SPORT', 'Sport'),
        ('ART', 'Art & Culture'),
        ('TECH', 'Technologie'),
        ('TRAVEL', 'Voyage'),
        ('FOOD', 'Cuisine'),
        ('MUSIC', 'Musique'),
        ('READING', 'Lecture'),
        ('GAMING', 'Jeux'),
        ('NATURE', 'Nature'),
        ('FITNESS', 'Fitness'),
        ('PHOTOGRAPHY', 'Photographie'),
        ('COOKING', 'Cuisine'),
        ('DANCING', 'Danse'),
        ('MOVIES', 'Cinéma'),
        ('OTHER', 'Autre'),
    ]
    
    name = models.CharField('Nom de la passion', max_length=100)
    category = models.CharField('Catégorie', max_length=20, choices=PASSION_CATEGORIES)
    description = models.TextField('Description', blank=True)
    icon = models.CharField('Icône', max_length=50, blank=True)  # nom de l'icône Lucide
    is_active = models.BooleanField('Actif', default=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Passion'
        verbose_name_plural = 'Passions'
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name


class UserPassionSelection(models.Model):
    """Relation many-to-many entre User et UserPassion"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passion_selections')
    passion = models.ForeignKey(UserPassion, on_delete=models.CASCADE, related_name='user_selections')
    intensity_level = models.IntegerField('Niveau d\'intensité', default=1, help_text='1-5 niveau de passion')
    selected_at = models.DateTimeField('Sélectionné le', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Sélection de passion'
        verbose_name_plural = 'Sélections de passions'
        unique_together = ['user', 'passion']
        ordering = ['-intensity_level', '-selected_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.passion.name} (Niveau {self.intensity_level})"


class UserInterests(models.Model):
    """Modèle pour stocker les centres d'intérêt sélectionnés par l'utilisateur"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='interests')
    selected_interests = models.JSONField(
        default=list,
        help_text="Liste des centres d'intérêt sélectionnés (id, name, color)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Centres d'intérêt utilisateur"
        verbose_name_plural = "Centres d'intérêt utilisateurs"
    
    def __str__(self):
        return f"Centres d'intérêt de {self.user.email}"
    
    def add_interests(self, interests_data):
        """Ajoute ou met à jour les centres d'intérêt"""
        self.selected_interests = interests_data
        self.save()
        return self
    
    @property
    def interests_count(self):
        """Retourne le nombre de centres d'intérêt sélectionnés"""
        return len(self.selected_interests) if self.selected_interests else 0


class Reservation(models.Model):
    """Modèle pour stocker les réservations confirmées"""
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('CONFIRMED', 'Confirmée'),
        ('CANCELLED', 'Annulée'),
        ('COMPLETED', 'Terminée'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    
    # Informations de l'activité
    activity_name = models.CharField('Nom de l\'activité', max_length=200)
    activity_description = models.TextField('Description', blank=True)
    
    # Date et heure
    reservation_date = models.DateField('Date de réservation')
    reservation_time = models.TimeField('Heure', default='20:00')
    
    # Lieu
    venue_name = models.CharField('Nom du lieu', max_length=200, default='Paris')
    venue_address = models.TextField('Adresse complète', blank=True)
    
    # Tarification
    price_plan = models.CharField('Plan tarifaire', max_length=100)  # 'basic', 'premium', etc.
    price_amount = models.DecimalField('Montant', max_digits=10, decimal_places=2)
    currency = models.CharField('Devise', max_length=3, default='EUR')
    
    # Statut et paiement
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    stripe_payment_intent_id = models.CharField('Stripe Payment Intent ID', max_length=200, blank=True)
    paid_at = models.DateTimeField('Payé le', null=True, blank=True)
    
    # Métadonnées
    participants_count = models.PositiveIntegerField('Nombre de participants', default=1)
    special_requests = models.TextField('Demandes spéciales', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    updated_at = models.DateTimeField('Mis à jour le', auto_now=True)
    
    # Limite d'annulation (mardi 23h59)
    cancellation_deadline = models.DateTimeField('Limite d\'annulation', null=True, blank=True)
    
    # Relation avec le groupe (ajoutée après)
    # group sera accessible via group_membership.group
    
    class Meta:
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'
        ordering = ['reservation_date', 'reservation_time']
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_name} ({self.reservation_date})"
    
    @property
    def is_modifiable(self):
        """Vérifie si la réservation peut encore être modifiée"""
        if not self.cancellation_deadline:
            return False
        return timezone.now() < self.cancellation_deadline
    
    @property
    def is_upcoming(self):
        """Vérifie si la réservation est à venir"""
        now = timezone.now().date()
        return self.reservation_date >= now
    
    def set_cancellation_deadline(self):
        """Définit la limite d'annulation (mardi 23h59 avant l'événement)"""
        # Trouver le mardi précédent l'événement
        event_date = self.reservation_date
        days_before_tuesday = (event_date.weekday() - 1) % 7  # 1 = mardi
        tuesday_before = event_date - timedelta(days=days_before_tuesday)
        
        # Si c'est le mardi même, prendre le mardi précédent
        if days_before_tuesday == 0:
            tuesday_before = event_date - timedelta(days=7)
        
        # Fixer l'heure à 23h59
        from datetime import time
        self.cancellation_deadline = timezone.make_aware(
            timezone.datetime.combine(tuesday_before, time(23, 59))
        )
    
    @property
    def group(self):
        """Retourne le groupe associé à cette réservation"""
        try:
            return self.group_membership.group
        except:
            return None
    
    @property
    def has_group(self):
        """Vérifie si la réservation est assignée à un groupe"""
        return hasattr(self, 'group_membership') and self.group_membership is not None
    
    def save(self, *args, **kwargs):
        # Définir automatiquement la deadline d'annulation
        if not self.cancellation_deadline:
            self.set_cancellation_deadline()
        super().save(*args, **kwargs)


class EventGroup(models.Model):
    """Modèle pour représenter un groupe d'utilisateurs pour un événement"""
    
    name = models.CharField('Nom du groupe', max_length=100)
    event_date = models.DateField('Date de l\'événement')
    activity_name = models.CharField('Nom de l\'activité', max_length=200)
    
    # Point de rendez-vous
    meeting_point_name = models.CharField('Lieu de rendez-vous', max_length=200, blank=True)
    meeting_point_address = models.TextField('Adresse du rendez-vous', blank=True)
    meeting_time = models.TimeField('Heure de rendez-vous', default='20:00')
    
    # Révélation du lieu
    location_reveal_time = models.DateTimeField('Heure de révélation du lieu', null=True, blank=True)
    
    # Métadonnées
    max_participants = models.PositiveIntegerField('Nombre max de participants', default=6)
    is_confirmed = models.BooleanField('Groupe confirmé', default=False)
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    updated_at = models.DateTimeField('Mis à jour le', auto_now=True)
    
    class Meta:
        verbose_name = 'Groupe d\'événement'
        verbose_name_plural = 'Groupes d\'événements'
        ordering = ['event_date', 'created_at']
    
    def __str__(self):
        return f"{self.name} - {self.event_date} ({self.activity_name})"
    
    @property
    def participants_count(self):
        """Retourne le nombre actuel de participants"""
        return self.memberships.filter(reservation__status='CONFIRMED').count()
    
    @property
    def is_full(self):
        """Vérifie si le groupe est complet"""
        return self.participants_count >= self.max_participants
    
    @property
    def can_reveal_location(self):
        """Vérifie si le lieu peut être révélé"""
        if not self.location_reveal_time:
            return False
        return timezone.now() >= self.location_reveal_time


class GroupMembership(models.Model):
    """Modèle pour lier les réservations aux groupes"""
    
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='group_membership')
    group = models.ForeignKey(EventGroup, on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateTimeField('Rejoint le', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Appartenance au groupe'
        verbose_name_plural = 'Appartenances aux groupes'
        unique_together = ['reservation', 'group']
    
    def __str__(self):
        return f"{self.reservation.user.email} dans {self.group.name}"


class UserTicket(models.Model):
    """Modèle pour gérer les tickets d'utilisateur (crédits pour réservations futures)"""
    
    TICKET_STATUS_CHOICES = [
        ('ACTIVE', 'Actif'),
        ('USED', 'Utilisé'),
        ('EXPIRED', 'Expiré'),
    ]
    
    TICKET_SOURCE_CHOICES = [
        ('CANCELLATION', 'Annulation de réservation'),
        ('REFUND', 'Remboursement'),
        ('PROMOTIONAL', 'Promotionnel'),
        ('GIFT', 'Cadeau'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    amount = models.DecimalField('Montant du ticket', max_digits=10, decimal_places=2)
    status = models.CharField('Statut', max_length=20, choices=TICKET_STATUS_CHOICES, default='ACTIVE')
    source = models.CharField('Source', max_length=20, choices=TICKET_SOURCE_CHOICES)
    
    # Référence à la réservation originale si le ticket vient d'une annulation
    original_reservation = models.ForeignKey(
        Reservation, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='generated_tickets'
    )
    
    # Réservation où le ticket a été utilisé
    used_for_reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_tickets'
    )
    
    # Dates
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    expires_at = models.DateTimeField('Expire le', null=True, blank=True)
    used_at = models.DateTimeField('Utilisé le', null=True, blank=True)
    
    # Notes optionnelles
    notes = models.TextField('Notes', blank=True)
    
    class Meta:
        verbose_name = 'Ticket utilisateur'
        verbose_name_plural = 'Tickets utilisateur'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Ticket {self.amount}€ - {self.user.email} ({self.status})"
    
    @property
    def is_valid(self):
        """Vérifie si le ticket est valide (actif et non expiré)"""
        if self.status != 'ACTIVE':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def use_ticket(self, reservation):
        """Marque le ticket comme utilisé pour une réservation"""
        if not self.is_valid:
            raise ValueError("Ce ticket n'est pas valide")
        
        self.status = 'USED'
        self.used_for_reservation = reservation
        self.used_at = timezone.now()
        self.save()
    
    def expire_ticket(self):
        """Marque le ticket comme expiré"""
        self.status = 'EXPIRED'
        self.save()


class UserSubscription(models.Model):
    """Modèle pour gérer les abonnements des utilisateurs"""
    
    SUBSCRIPTION_TYPE_CHOICES = [
        ('MONTHLY', '1 mois'),
        ('QUARTERLY', '3 mois'),
        ('SEMESTRIAL', '6 mois'),
    ]
    
    SUBSCRIPTION_STATUS_CHOICES = [
        ('ACTIVE', 'Actif'),
        ('EXPIRED', 'Expiré'),
        ('CANCELLED', 'Annulé'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_subscriptions')
    subscription_type = models.CharField('Type d\'abonnement', max_length=20, choices=SUBSCRIPTION_TYPE_CHOICES)
    status = models.CharField('Statut', max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='ACTIVE')
    
    # Dates de validité
    start_date = models.DateTimeField('Date de début')
    end_date = models.DateTimeField('Date de fin')
    
    # Informations de paiement
    price_paid = models.DecimalField('Prix payé', max_digits=10, decimal_places=2)
    stripe_subscription_id = models.CharField('Stripe Subscription ID', max_length=200, blank=True)
    
    # Utilisation
    reservations_used = models.PositiveIntegerField('Réservations utilisées', default=0)
    current_reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subscription_used'
    )
    
    # Métadonnées
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    updated_at = models.DateTimeField('Mis à jour le', auto_now=True)
    cancelled_at = models.DateTimeField('Annulé le', null=True, blank=True)
    
    # Mode test
    is_test_mode = models.BooleanField('Mode test', default=False)
    
    class Meta:
        verbose_name = 'Abonnement utilisateur'
        verbose_name_plural = 'Abonnements utilisateurs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_subscription_type_display()} ({self.status})"
    
    @property
    def is_active(self):
        """Vérifie si l'abonnement est actif"""
        if self.status != 'ACTIVE':
            return False
        return timezone.now() <= self.end_date
    
    @property
    def can_make_reservation(self):
        """Vérifie si l'utilisateur peut faire une nouvelle réservation"""
        if not self.is_active:
            return False
        # Vérifier s'il n'a pas déjà une réservation en cours
        return self.current_reservation is None or self.current_reservation.status in ['CANCELLED', 'COMPLETED']
    
    @property
    def days_remaining(self):
        """Retourne le nombre de jours restants"""
        if not self.is_active:
            return 0
        delta = self.end_date - timezone.now()
        return max(0, delta.days)
    
    def use_for_reservation(self, reservation):
        """Utilise l'abonnement pour une réservation"""
        self.current_reservation = reservation
        self.reservations_used += 1
        self.save()
        return True
    
    def release_reservation(self):
        """Libère la réservation actuelle (en cas d'annulation)"""
        if self.current_reservation:
            self.current_reservation = None
            self.reservations_used = max(0, self.reservations_used - 1)
            self.save()
            return True
        return False
    
    @classmethod
    def get_active_subscription(cls, user):
        """Récupère l'abonnement actif d'un utilisateur"""
        return cls.objects.filter(
            user=user,
            status='ACTIVE',
            end_date__gt=timezone.now()
        ).first()
    
    def check_and_update_status(self):
        """Vérifie et met à jour le statut si nécessaire"""
        if self.status == 'ACTIVE' and timezone.now() > self.end_date:
            self.status = 'EXPIRED'
            self.save()
            # Mettre à jour le statut premium de l'utilisateur
            self.user.is_premium = False
            self.user.premium_until = None
            self.user.save()
            return True
        return False


class FriendInvitation(models.Model):
    """Modèle pour les invitations d'amis"""
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('ACCEPTED', 'Acceptée'),
        ('EXPIRED', 'Expirée'),
        ('USED', 'Utilisée'),
    ]
    
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invited_email = models.EmailField('Email de l\'invité')
    invited_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_invitations')
    
    # Token unique pour l'invitation
    invitation_token = models.CharField('Token d\'invitation', max_length=100, unique=True)
    
    # Réservation associée
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='invitations')
    
    # Statut et métadonnées
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    message = models.TextField('Message personnalisé', blank=True)
    
    # Dates importantes
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    expires_at = models.DateTimeField('Expire le')
    accepted_at = models.DateTimeField('Accepté le', null=True, blank=True)
    used_at = models.DateTimeField('Utilisé le', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Invitation d\'ami'
        verbose_name_plural = 'Invitations d\'amis'
        ordering = ['-created_at']
        unique_together = ['inviter', 'invited_email', 'reservation']
    
    def __str__(self):
        return f"{self.inviter.email} invite {self.invited_email} pour {self.reservation.activity_name}"
    
    @property
    def is_valid(self):
        """Vérifie si l'invitation est encore valide"""
        return (
            self.status == 'PENDING' and 
            timezone.now() < self.expires_at
        )
    
    @property
    def can_be_used(self):
        """Vérifie si l'invitation peut être utilisée maintenant"""
        return self.status == 'ACCEPTED' and self.invited_user is not None
    
    def mark_as_accepted(self, user):
        """Marque l'invitation comme acceptée"""
        self.status = 'ACCEPTED'
        self.invited_user = user
        self.accepted_at = timezone.now()
        self.save()
    
    def mark_as_used(self):
        """Marque l'invitation comme utilisée"""
        self.status = 'USED'
        self.used_at = timezone.now()
        self.save()
    
    @classmethod
    def create_invitation(cls, inviter, invited_email, reservation, message=""):
        """Créer une nouvelle invitation avec validation de timing"""
        from datetime import datetime, time
        import uuid
        
        # Vérifier qu'on est avant mercredi 00:00
        reservation_date = reservation.reservation_date
        wednesday_deadline = datetime.combine(
            reservation_date - timedelta(days=1),  # Mardi
            time(23, 59, 59)
        )
        wednesday_deadline = timezone.make_aware(wednesday_deadline)
        
        if timezone.now() > wednesday_deadline:
            raise ValueError("Les invitations ne sont plus possibles après mardi 23h59")
        
        # Générer un token unique
        invitation_token = str(uuid.uuid4()).replace('-', '')[:32]
        
        # L'invitation expire le mercredi à 00:00
        expires_at = datetime.combine(
            reservation_date - timedelta(days=1),  # Mardi
            time(23, 59, 59)
        )
        expires_at = timezone.make_aware(expires_at) + timedelta(minutes=1)  # Mercredi 00:00
        
        invitation = cls.objects.create(
            inviter=inviter,
            invited_email=invited_email,
            reservation=reservation,
            invitation_token=invitation_token,
            message=message,
            expires_at=expires_at
        )
        
        return invitation
