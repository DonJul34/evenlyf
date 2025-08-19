from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from users.models import Reservation
import logging

logger = logging.getLogger(__name__)

# TODO: Imports will be added when serializers are created
# from .models import SubscriptionPlan, Subscription, Payment, PaymentMethod
# from .serializers import SubscriptionPlanSerializer, SubscriptionSerializer


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les plans d'abonnement"""
    permission_classes = [AllowAny]
    
    def list(self, request):
        return Response({'message': 'Subscription plans list - à implémenter'})


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les abonnements"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        return Response({'message': 'Subscriptions list - à implémenter'})


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les paiements"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        return Response({'message': 'Payments list - à implémenter'})


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """ViewSet pour les méthodes de paiement"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        return Response({'message': 'Payment methods list - à implémenter'})


class CreatePaymentIntentView(APIView):
    """Vue pour créer un payment intent Stripe"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Create payment intent - à implémenter'})


class ConfirmPaymentView(APIView):
    """Vue pour confirmer un paiement (mode local dev)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            payment_intent_id = data.get('payment_intent_id')
            status_payment = data.get('status')
            
            logger.info(f"Confirmation paiement pour {request.user.email}: {payment_intent_id}")
            
            # Récupérer la réservation en attente de l'utilisateur
            try:
                reservation = Reservation.objects.get(
                    user=request.user, 
                    status='PENDING'
                )
            except Reservation.DoesNotExist:
                return Response({
                    'error': 'Aucune réservation en attente trouvée'
                }, status=status.HTTP_404_NOT_FOUND)
            except Reservation.MultipleObjectsReturned:
                # Prendre la plus récente
                reservation = Reservation.objects.filter(
                    user=request.user, 
                    status='PENDING'
                ).order_by('-created_at').first()
            
            # Vérifier le statut du paiement (local dev)
            if status_payment == 'succeeded':
                # Marquer la réservation comme payée
                reservation.status = 'CONFIRMED'
                reservation.paid_at = timezone.now()
                reservation.stripe_payment_intent_id = payment_intent_id
                reservation.save()
                
                logger.info(f"Réservation {reservation.id} marquée comme payée pour {request.user.email}")
                
                # Retourner les détails de la réservation
                reservation_data = {
                    'id': reservation.id,
                    'activity_name': reservation.activity_name,
                    'reservation_date': reservation.reservation_date.isoformat(),
                    'reservation_time': reservation.reservation_time.strftime('%H:%M'),
                    'venue_name': reservation.venue_name,
                    'price_amount': str(reservation.price_amount),
                    'status': reservation.status,
                    'paid_at': reservation.paid_at.isoformat() if reservation.paid_at else None,
                    'is_modifiable': reservation.is_modifiable,
                    'participants_count': reservation.participants_count,
                }
                
                return Response({
                    'success': True,
                    'message': 'Paiement confirmé avec succès',
                    'reservation': reservation_data
                })
            else:
                return Response({
                    'error': f'Statut de paiement invalide: {status_payment}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Erreur lors de la confirmation de paiement: {str(e)}", exc_info=True)
            return Response({
                'error': 'Erreur lors de la confirmation de paiement',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StripeWebhookView(APIView):
    """Vue pour les webhooks Stripe"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        return Response({'message': 'Stripe webhook - à implémenter'})


class SubscribeView(APIView):
    """Vue pour s'abonner"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Subscribe - à implémenter'})


class CancelSubscriptionView(APIView):
    """Vue pour annuler un abonnement"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Cancel subscription - à implémenter'})


class AddPaymentMethodView(APIView):
    """Vue pour ajouter une méthode de paiement"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Add payment method - à implémenter'})


class SetDefaultPaymentMethodView(APIView):
    """Vue pour définir la méthode de paiement par défaut"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, method_id):
        return Response({'message': f'Set default payment method {method_id} - à implémenter'})


class InvoiceListView(APIView):
    """Vue pour lister les factures"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({'message': 'Invoice list - à implémenter'})


class InvoiceDetailView(APIView):
    """Vue pour le détail d'une facture"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, invoice_id):
        return Response({'message': f'Invoice detail {invoice_id} - à implémenter'})


class ValidateDiscountView(APIView):
    """Vue pour valider un code de réduction"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Validate discount - à implémenter'})
