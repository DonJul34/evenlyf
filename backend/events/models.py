from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User


class Activity(models.Model):
    """Modèle pour les types d'activités (Bar à jeux, Bowling, etc.)"""
    
    ACTIVITY_TYPES = [
        ('BAR_GAMES', 'Bar à jeux'),
        ('BOWLING', 'Bowling'),
        ('KARAOKE', 'Karaoké'),
        ('ESCAPE_GAME', 'Escape Game'),
        ('RESTAURANT', 'Restaurant'),
        ('CINEMA', 'Cinéma'),
        ('MUSEUM', 'Musée'),
        ('CONCERT', 'Concert'),
        ('SPORT', 'Activité sportive'),
        ('OTHER', 'Autre'),
    ]
    
    name = models.CharField('Nom de l\'activité', max_length=100)
    activity_type = models.CharField('Type d\'activité', max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField('Description', blank=True)
    icon = models.CharField('Icône', max_length=50, blank=True)
    base_price = models.DecimalField('Prix de base', max_digits=10, decimal_places=2, default=0)
    duration_hours = models.FloatField('Durée en heures', default=2.0)
    min_participants = models.IntegerField('Minimum de participants', default=6)
    max_participants = models.IntegerField('Maximum de participants', default=6)
    is_active = models.BooleanField('Actif', default=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Activité'
        verbose_name_plural = 'Activités'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_activity_type_display()})"


class Venue(models.Model):
    """Modèle pour les lieux/établissements"""
    
    name = models.CharField('Nom du lieu', max_length=200)
    address = models.TextField('Adresse')
    city = models.CharField('Ville', max_length=100)
    postal_code = models.CharField('Code postal', max_length=10)
    phone = models.CharField('Téléphone', max_length=15, blank=True)
    email = models.EmailField('Email', blank=True)
    website = models.URLField('Site web', blank=True)
    
    # Coordonnées
    latitude = models.DecimalField('Latitude', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('Longitude', max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Capacité et services
    capacity = models.IntegerField('Capacité', default=50)
    has_accessibility = models.BooleanField('Accessible PMR', default=False)
    has_parking = models.BooleanField('Parking disponible', default=False)
    has_terrace = models.BooleanField('Terrasse', default=False)
    
    # Notes et validations
    rating = models.FloatField('Note moyenne', validators=[MinValueValidator(0), MaxValueValidator(5)], default=0)
    is_verified = models.BooleanField('Lieu vérifié', default=False)
    is_active = models.BooleanField('Actif', default=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Lieu'
        verbose_name_plural = 'Lieux'
        ordering = ['city', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class Event(models.Model):
    """Modèle pour les événements organisés"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('OPEN', 'Ouvert aux inscriptions'),
        ('MATCHING', 'En cours de matching'),
        ('CONFIRMED', 'Confirmé'),
        ('IN_PROGRESS', 'En cours'),
        ('COMPLETED', 'Terminé'),
        ('CANCELLED', 'Annulé'),
    ]
    
    title = models.CharField('Titre', max_length=200)
    description = models.TextField('Description', blank=True)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='events')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='events')
    
    # Dates et horaires
    scheduled_date = models.DateTimeField('Date programmée')
    registration_deadline = models.DateTimeField('Date limite d\'inscription')
    duration_hours = models.FloatField('Durée en heures', default=2.0)
    
    # Participants
    max_participants = models.IntegerField('Maximum de participants', default=6)
    current_participants = models.IntegerField('Participants actuels', default=0)
    
    # Prix et tarification
    price_per_person = models.DecimalField('Prix par personne', max_digits=10, decimal_places=2)
    includes_food = models.BooleanField('Inclut la nourriture', default=False)
    includes_drinks = models.BooleanField('Inclut les boissons', default=False)
    
    # Statut et gestion
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events', null=True, blank=True)
    is_public = models.BooleanField('Événement public', default=True)
    
    # Métadonnées
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Événement'
        verbose_name_plural = 'Événements'
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.title} - {self.scheduled_date.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def is_full(self):
        return self.current_participants >= self.max_participants
    
    @property
    def spots_remaining(self):
        return max(0, self.max_participants - self.current_participants)
    
    @property
    def is_registration_open(self):
        now = timezone.now()
        return (self.status == 'OPEN' and 
                now < self.registration_deadline and 
                not self.is_full)


class EventRegistration(models.Model):
    """Modèle pour les inscriptions aux événements"""
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('CONFIRMED', 'Confirmé'),
        ('CANCELLED', 'Annulé'),
        ('NO_SHOW', 'Absent'),
        ('COMPLETED', 'Participé'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Préférences
    dietary_restrictions = models.TextField('Restrictions alimentaires', blank=True)
    special_requests = models.TextField('Demandes spéciales', blank=True)
    
    # Métadonnées
    registered_at = models.DateTimeField('Date d\'inscription', auto_now_add=True)
    confirmed_at = models.DateTimeField('Date de confirmation', null=True, blank=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Inscription à un événement'
        verbose_name_plural = 'Inscriptions aux événements'
        unique_together = ['user', 'event']
        ordering = ['-registered_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.event.title}"


class MatchingGroup(models.Model):
    """Modèle pour les groupes créés par l'algorithme de matching"""
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('CONFIRMED', 'Confirmé'),
        ('ACTIVE', 'Actif'),
        ('COMPLETED', 'Terminé'),
        ('CANCELLED', 'Annulé'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='matching_groups')
    name = models.CharField('Nom du groupe', max_length=100, blank=True)
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Calcul de compatibilité
    average_compatibility_score = models.FloatField('Score de compatibilité moyen', default=0.0)
    personality_balance_score = models.FloatField('Score d\'équilibre des personnalités', default=0.0)
    passion_overlap_score = models.FloatField('Score de chevauchement des passions', default=0.0)
    
    # Métadonnées
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    confirmed_at = models.DateTimeField('Date de confirmation', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Groupe de matching'
        verbose_name_plural = 'Groupes de matching'
        ordering = ['-average_compatibility_score']
    
    def __str__(self):
        return f"Groupe {self.id} - {self.event.title}"
    
    @property
    def member_count(self):
        return self.members.filter(status='ACTIVE').count()


class MatchingGroupMember(models.Model):
    """Modèle pour les membres d'un groupe de matching"""
    
    STATUS_CHOICES = [
        ('INVITED', 'Invité'),
        ('ACTIVE', 'Actif'),
        ('DECLINED', 'Refusé'),
        ('LEFT', 'A quitté'),
    ]
    
    group = models.ForeignKey(MatchingGroup, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    registration = models.OneToOneField(EventRegistration, on_delete=models.CASCADE, related_name='group_membership')
    
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='INVITED')
    compatibility_score = models.FloatField('Score de compatibilité individuel', default=0.0)
    
    # Métadonnées
    joined_at = models.DateTimeField('Date d\'ajout', auto_now_add=True)
    status_updated_at = models.DateTimeField('Statut modifié le', auto_now=True)
    
    class Meta:
        verbose_name = 'Membre de groupe'
        verbose_name_plural = 'Membres de groupes'
        unique_together = ['group', 'user']
        ordering = ['-compatibility_score']
    
    def __str__(self):
        return f"{self.user.full_name} dans {self.group}"


class EventFeedback(models.Model):
    """Modèle pour les retours d'expérience après événement"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_feedbacks')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    group = models.ForeignKey(MatchingGroup, on_delete=models.CASCADE, related_name='feedbacks', null=True, blank=True)
    
    # Évaluations (1-5)
    overall_rating = models.IntegerField('Note générale', validators=[MinValueValidator(1), MaxValueValidator(5)])
    venue_rating = models.IntegerField('Note du lieu', validators=[MinValueValidator(1), MaxValueValidator(5)])
    group_compatibility_rating = models.IntegerField('Compatibilité du groupe', validators=[MinValueValidator(1), MaxValueValidator(5)])
    activity_rating = models.IntegerField('Note de l\'activité', validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Commentaires
    comment = models.TextField('Commentaire', blank=True)
    would_recommend = models.BooleanField('Recommanderait', default=True)
    would_join_again = models.BooleanField('Participerait à nouveau', default=True)
    
    # Suggestions d'amélioration
    suggestions = models.TextField('Suggestions', blank=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Retour d\'expérience'
        verbose_name_plural = 'Retours d\'expérience'
        unique_together = ['user', 'event']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback de {self.user.full_name} pour {self.event.title}"
