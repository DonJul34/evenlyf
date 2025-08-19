from django.db import models
from django.utils import timezone
from users.models import User
from events.models import Event, EventRegistration


class SubscriptionPlan(models.Model):
    """Modèle pour les plans d'abonnement"""
    
    PLAN_TYPES = [
        ('TICKET', 'Ticket unique'),
        ('MONTHLY_1', 'Abonnement 1 mois'),
        ('MONTHLY_3', 'Abonnement 3 mois'),
        ('MONTHLY_6', 'Abonnement 6 mois'),
    ]
    
    name = models.CharField('Nom du plan', max_length=100)
    plan_type = models.CharField('Type de plan', max_length=20, choices=PLAN_TYPES)
    description = models.TextField('Description', blank=True)
    
    # Prix et durée
    price = models.DecimalField('Prix', max_digits=10, decimal_places=2)
    monthly_equivalent = models.DecimalField('Prix équivalent mensuel', max_digits=10, decimal_places=2, null=True, blank=True)
    duration_months = models.IntegerField('Durée en mois', default=1)
    
    # Avantages
    events_included = models.IntegerField('Événements inclus', default=1, help_text='Nombre d\'événements inclus ou -1 pour illimité')
    discount_percentage = models.IntegerField('Pourcentage de réduction', default=0)
    
    # Configuration Stripe
    stripe_price_id = models.CharField('Stripe Price ID', max_length=100, blank=True)
    stripe_product_id = models.CharField('Stripe Product ID', max_length=100, blank=True)
    
    # Statut
    is_active = models.BooleanField('Actif', default=True)
    is_popular = models.BooleanField('Plan populaire', default=False)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Plan d\'abonnement'
        verbose_name_plural = 'Plans d\'abonnement'
        ordering = ['duration_months', 'price']
    
    def __str__(self):
        return f"{self.name} - {self.price}€"


class Subscription(models.Model):
    """Modèle pour les abonnements utilisateurs"""
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Actif'),
        ('CANCELLED', 'Annulé'),
        ('EXPIRED', 'Expiré'),
        ('PENDING', 'En attente'),
        ('FAILED', 'Échec'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscriptions')
    
    # Dates
    start_date = models.DateTimeField('Date de début')
    end_date = models.DateTimeField('Date de fin')
    auto_renew = models.BooleanField('Renouvellement automatique', default=True)
    
    # Statut et utilisation
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    events_used = models.IntegerField('Événements utilisés', default=0)
    
    # Configuration Stripe
    stripe_subscription_id = models.CharField('Stripe Subscription ID', max_length=100, blank=True)
    stripe_customer_id = models.CharField('Stripe Customer ID', max_length=100, blank=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Abonnement'
        verbose_name_plural = 'Abonnements'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.plan.name}"
    
    @property
    def is_active(self):
        now = timezone.now()
        return (self.status == 'ACTIVE' and 
                self.start_date <= now <= self.end_date)
    
    @property
    def events_remaining(self):
        if self.plan.events_included == -1:  # Illimité
            return float('inf')
        return max(0, self.plan.events_included - self.events_used)
    
    def can_use_event(self):
        return self.is_active and (self.events_remaining > 0 or self.plan.events_included == -1)


class Payment(models.Model):
    """Modèle pour les paiements"""
    
    PAYMENT_TYPES = [
        ('SUBSCRIPTION', 'Abonnement'),
        ('EVENT', 'Événement ponctuel'),
        ('REFUND', 'Remboursement'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('PROCESSING', 'En cours'),
        ('SUCCEEDED', 'Réussi'),
        ('FAILED', 'Échec'),
        ('CANCELLED', 'Annulé'),
        ('REFUNDED', 'Remboursé'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField('Type de paiement', max_length=20, choices=PAYMENT_TYPES)
    
    # Montants
    amount = models.DecimalField('Montant', max_digits=10, decimal_places=2)
    currency = models.CharField('Devise', max_length=3, default='EUR')
    
    # Relations optionnelles
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    event_registration = models.ForeignKey(EventRegistration, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    # Configuration Stripe
    stripe_payment_intent_id = models.CharField('Stripe Payment Intent ID', max_length=100, blank=True)
    stripe_charge_id = models.CharField('Stripe Charge ID', max_length=100, blank=True)
    
    # Statut et métadonnées
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    failure_reason = models.TextField('Raison de l\'échec', blank=True)
    refund_reason = models.TextField('Raison du remboursement', blank=True)
    
    # Dates
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    processed_at = models.DateTimeField('Date de traitement', null=True, blank=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.amount}€ ({self.get_status_display()})"


class PaymentMethod(models.Model):
    """Modèle pour les méthodes de paiement sauvegardées"""
    
    CARD_BRANDS = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('diners', 'Diners Club'),
        ('jcb', 'JCB'),
        ('unionpay', 'UnionPay'),
        ('unknown', 'Inconnue'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    
    # Configuration Stripe
    stripe_payment_method_id = models.CharField('Stripe Payment Method ID', max_length=100)
    stripe_customer_id = models.CharField('Stripe Customer ID', max_length=100)
    
    # Informations de la carte (partielles pour affichage)
    card_brand = models.CharField('Marque de la carte', max_length=20, choices=CARD_BRANDS, default='unknown')
    card_last4 = models.CharField('4 derniers chiffres', max_length=4, blank=True)
    card_exp_month = models.IntegerField('Mois d\'expiration', null=True, blank=True)
    card_exp_year = models.IntegerField('Année d\'expiration', null=True, blank=True)
    
    # Statut
    is_default = models.BooleanField('Méthode par défaut', default=False)
    is_active = models.BooleanField('Active', default=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Méthode de paiement'
        verbose_name_plural = 'Méthodes de paiement'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.card_brand.title()} ****{self.card_last4}"


class Invoice(models.Model):
    """Modèle pour les factures"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('SENT', 'Envoyée'),
        ('PAID', 'Payée'),
        ('OVERDUE', 'En retard'),
        ('CANCELLED', 'Annulée'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='invoice', null=True, blank=True)
    
    # Numérotation
    invoice_number = models.CharField('Numéro de facture', max_length=50, unique=True)
    
    # Montants
    subtotal = models.DecimalField('Sous-total', max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField('Montant de la TVA', max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField('Montant total', max_digits=10, decimal_places=2)
    
    # Dates
    issue_date = models.DateField('Date d\'émission')
    due_date = models.DateField('Date d\'échéance')
    paid_date = models.DateField('Date de paiement', null=True, blank=True)
    
    # Statut
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Configuration Stripe
    stripe_invoice_id = models.CharField('Stripe Invoice ID', max_length=100, blank=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Facture {self.invoice_number} - {self.user.full_name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Générer un numéro de facture unique
            year = timezone.now().year
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=f"INV{year}"
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
                
            self.invoice_number = f"INV{year}-{new_number:06d}"
        
        super().save(*args, **kwargs)


class Discount(models.Model):
    """Modèle pour les codes de réduction"""
    
    DISCOUNT_TYPES = [
        ('PERCENTAGE', 'Pourcentage'),
        ('FIXED', 'Montant fixe'),
    ]
    
    code = models.CharField('Code de réduction', max_length=50, unique=True)
    description = models.TextField('Description', blank=True)
    
    # Type et valeur de réduction
    discount_type = models.CharField('Type de réduction', max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField('Valeur de la réduction', max_digits=10, decimal_places=2)
    
    # Limites d'utilisation
    max_uses = models.IntegerField('Utilisations maximales', default=1)
    used_count = models.IntegerField('Nombre d\'utilisations', default=0)
    max_uses_per_user = models.IntegerField('Utilisations max par utilisateur', default=1)
    
    # Dates de validité
    valid_from = models.DateTimeField('Valide à partir de')
    valid_until = models.DateTimeField('Valide jusqu\'à')
    
    # Restrictions
    minimum_amount = models.DecimalField('Montant minimum', max_digits=10, decimal_places=2, default=0)
    applicable_plans = models.ManyToManyField(SubscriptionPlan, blank=True, related_name='discounts')
    
    # Statut
    is_active = models.BooleanField('Actif', default=True)
    
    created_at = models.DateTimeField('Date de création', auto_now_add=True)
    updated_at = models.DateTimeField('Dernière modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Code de réduction'
        verbose_name_plural = 'Codes de réduction'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.discount_type == 'PERCENTAGE' else '€'}"
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_until and
                self.used_count < self.max_uses)
    
    def can_be_used_by(self, user):
        if not self.is_valid:
            return False
        
        user_usage = DiscountUsage.objects.filter(
            discount=self,
            user=user
        ).count()
        
        return user_usage < self.max_uses_per_user


class DiscountUsage(models.Model):
    """Modèle pour tracer l'utilisation des codes de réduction"""
    
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discount_usages')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='discount_usage')
    
    discount_amount = models.DecimalField('Montant de la réduction appliquée', max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField('Date d\'utilisation', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Utilisation de code de réduction'
        verbose_name_plural = 'Utilisations de codes de réduction'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.discount.code} ({self.discount_amount}€)"
