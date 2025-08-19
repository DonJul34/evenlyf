from django.shortcuts import render
from django.contrib.auth import login, logout
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from oauth2_provider.contrib.rest_framework import TokenHasScope
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from .models import (
    User, PersonalityTestResult, 
    VerificationCode, OnboardingProgress, PersonalityTestSession, PersonalityTestAnswer, UserInterests, Reservation, EventGroup, GroupMembership, UserTicket, FriendInvitation, UserSubscription
)
from .serializers import (
    UserSerializer, UserProfileSerializer,
    RegisterSerializer, LoginSerializer, PersonalityTestSubmissionSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
    EmailVerificationSerializer
)
from .utils import send_verification_email, send_password_reset_email

import stripe
from django.conf import settings

# Configuration Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# Créer un logger pour cette app
logger = logging.getLogger('users')


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des utilisateurs"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Les utilisateurs ne peuvent voir que leur propre profil
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)





class RegisterView(APIView):
    """Vue pour l'inscription d'un nouvel utilisateur"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        logger.info(f"Tentative d'inscription avec les données: {request.data}")
        
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            logger.info("Les données d'inscription sont valides")
            try:
                user = serializer.save()
                logger.info(f"Utilisateur créé avec succès: {user.email}")
                
                # Créer un code de vérification
                verification_code = VerificationCode.create_verification_code(
                    user=user,
                    code_type='EMAIL_VERIFICATION',
                    duration_minutes=10
                )
                logger.info(f"Code de vérification créé: {verification_code.code}")
                
                # Envoyer l'email de vérification
                email_sent = send_verification_email(user, verification_code.code)
                logger.info(f"Email de vérification envoyé: {email_sent}")
                
                return Response({
                    'message': 'Compte créé avec succès. Vérifiez votre email.',
                    'user_id': user.id,
                    'email_sent': email_sent,
                    'verification_required': True
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Erreur lors de la création de l'utilisateur: {str(e)}", exc_info=True)
                return Response({
                    'error': 'Erreur lors de la création du compte',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.warning(f"Données d'inscription invalides: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """Vue pour la connexion"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            
            # Mettre à jour la dernière connexion
            user.last_login_at = timezone.now()
            user.save()
            
            # Créer ou récupérer le token (si utilisation de Token auth)
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'message': 'Connexion réussie',
                'token': token.key,
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Vue pour la déconnexion"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Supprimer le token de l'utilisateur
            request.user.auth_token.delete()
        except Token.DoesNotExist:
            pass
        
        logout(request)
        return Response({'message': 'Déconnexion réussie'})


class ProfileView(APIView):
    """Vue pour voir et modifier le profil utilisateur"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    """Vue pour vérifier l'email"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            verification_code = serializer.validated_data['verification_code']
            
            # Marquer le code comme utilisé
            verification_code.mark_as_used()
            
            # Vérifier l'email de l'utilisateur
            user.email_verified = True
            user.last_login_at = timezone.now()
            user.save()
            
            # Créer ou récupérer le token pour login automatique
            token, created = Token.objects.get_or_create(user=user)
            
            logger.info(f"Email vérifié et login automatique pour {user.email}")
            
            return Response({
                'message': 'Email vérifié avec succès',
                'user_id': user.id,
                'email_verified': True,
                'auto_login': True,
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationView(APIView):
    """Vue pour renvoyer l'email de vérification"""
    permission_classes = [AllowAny]  # Changé pour permettre aux non-connectés
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        
        if user.email_verified:
            return Response({'message': 'Email déjà vérifié'})
        
        # Créer un nouveau code de vérification
        verification_code = VerificationCode.create_verification_code(
            user=user,
            code_type='EMAIL_VERIFICATION',
            duration_minutes=10
        )
        
        # Envoyer l'email de vérification
        email_sent = send_verification_email(user, verification_code.code)
        
        return Response({
            'message': 'Email de vérification envoyé',
            'email_sent': email_sent
        })


class PasswordResetView(APIView):
    """Vue pour demander une réinitialisation de mot de passe"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            # TODO: Envoyer email de réinitialisation
            return Response({'message': 'Email de réinitialisation envoyé'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Vue pour confirmer la réinitialisation de mot de passe"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            # TODO: Implémenter la réinitialisation
            return Response({'message': 'Mot de passe réinitialisé avec succès'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PersonalityTestView(APIView):
    """Vue pour récupérer les questions du test de personnalité"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # TODO: Retourner les questions du test
        questions = {
            'mbti_questions': [
                {
                    'id': 1,
                    'text': 'Vous préférez passer du temps...',
                    'options': [
                        {'value': 'E', 'text': 'Avec d\'autres personnes'},
                        {'value': 'I', 'text': 'Seul(e)'}
                    ]
                },
                # Ajouter plus de questions...
            ],
            'disc_questions': [
                {
                    'id': 1,
                    'text': 'Dans un groupe, vous êtes plutôt...',
                    'options': [
                        {'value': 'D', 'text': 'Celui qui prend les décisions'},
                        {'value': 'I', 'text': 'Celui qui motive les autres'},
                        {'value': 'S', 'text': 'Celui qui écoute et soutient'},
                        {'value': 'C', 'text': 'Celui qui analyse et planifie'}
                    ]
                },
                # Ajouter plus de questions...
            ]
        }
        return Response(questions)


class OnboardingProgressView(APIView):
    """Vue pour gérer le progrès de l'onboarding"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupérer le progrès actuel de l'onboarding"""
        progress, created = OnboardingProgress.objects.get_or_create(
            user=request.user,
            defaults={
                'current_step': 'PERSONAL_INFO',
                'completed_steps': [],
                'temp_data': {}
            }
        )
        
        # Utiliser la nouvelle méthode get_completion_status
        completion_status = progress.get_completion_status()
        
        return Response({
            'current_step': progress.current_step,
            'completed_steps': progress.completed_steps,
            'temp_data': progress.temp_data,
            'is_completed': progress.current_step == 'COMPLETED',
            'completion_status': completion_status,
            'is_invited_user': request.user.is_invited_user,
            'invitation_data': {
                'activity_name': request.user.invitation_used.reservation.activity_name,
                'reservation_date': request.user.invitation_used.reservation.reservation_date,
                'inviter_name': request.user.invitation_used.inviter.full_name
            } if request.user.is_invited_user and request.user.invitation_used else None
        })
    
    def post(self, request):
        """Sauvegarder des données temporaires d'onboarding"""
        data = request.data
        
        progress, created = OnboardingProgress.objects.get_or_create(
            user=request.user,
            defaults={
                'current_step': 'PERSONAL_INFO',
                'completed_steps': [],
                'temp_data': {}
            }
        )
        
        # Sauvegarder les données temporaires
        if 'temp_data' in data:
            progress.save_temp_data(data['temp_data'])
        
        # Marquer une étape comme complétée
        if 'completed_step' in data:
            progress.mark_step_completed(data['completed_step'])
        
        # Changer l'étape actuelle
        if 'current_step' in data:
            progress.current_step = data['current_step']
            progress.save()
        
        # Marquer comme terminé si nécessaire
        if data.get('complete_onboarding'):
            progress.complete_onboarding()
        
        logger.info(f"Onboarding progress updated for user {request.user.email}: {progress.current_step}")
        
        return Response({
            'message': 'Progrès sauvegardé avec succès',
            'current_step': progress.current_step,
            'completed_steps': progress.completed_steps
        })


class PersonalityTestSessionView(APIView):
    """Vue pour gérer les sessions de test de personnalité"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Démarrer une nouvelle session de test de personnalité"""
        # Créer une nouvelle session
        session_id = str(uuid.uuid4())[:12]  # ID court mais unique
        
        session = PersonalityTestSession.objects.create(
            user=request.user,
            session_id=session_id,
            current_question=0
        )
        
        logger.info(f"Nouvelle session de test de personnalité créée: {session_id} pour {request.user.email}")
        
        return Response({
            'session_id': session_id,
            'message': 'Session de test démarrée',
            'current_question': 0
        })
    
    def get(self, request):
        """Récupérer l'état de la session actuelle"""
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response({'error': 'session_id requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = PersonalityTestSession.objects.get(
                session_id=session_id,
                user=request.user
            )
            
            return Response({
                'session_id': session.session_id,
                'current_question': session.current_question,
                'is_completed': session.is_completed,
                'started_at': session.started_at,
                'answers_count': session.answers.count()
            })
        except PersonalityTestSession.DoesNotExist:
            return Response({'error': 'Session non trouvée'}, status=status.HTTP_404_NOT_FOUND)


class PersonalityTestAnswerView(APIView):
    """Vue pour sauvegarder les réponses individuelles au test"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Sauvegarder une réponse à une question"""
        data = request.data
        session_id = data.get('session_id')
        question_id = data.get('question_id')
        answer_index = data.get('answer_index')
        question_text = data.get('question_text', '')
        answer_text = data.get('answer_text', '')
        mbti_scores = data.get('mbti_scores', {})
        disc_scores = data.get('disc_scores', {})
        
        if not all([session_id, question_id is not None, answer_index is not None]):
            return Response({
                'error': 'session_id, question_id et answer_index sont requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = PersonalityTestSession.objects.get(
                session_id=session_id,
                user=request.user
            )
            
            # Créer ou mettre à jour la réponse
            answer, created = PersonalityTestAnswer.objects.update_or_create(
                session=session,
                question_id=question_id,
                defaults={
                    'question_text': question_text,
                    'answer_index': answer_index,
                    'answer_text': answer_text,
                    'mbti_scores': mbti_scores,
                    'disc_scores': disc_scores
                }
            )
            
            # Mettre à jour la question actuelle dans la session
            session.current_question = max(session.current_question, question_id + 1)
            session.save()
            
            logger.info(f"Réponse sauvegardée: Q{question_id} pour session {session_id}")
            
            return Response({
                'message': 'Réponse sauvegardée avec succès',
                'question_id': question_id,
                'answer_created': created
            })
            
        except PersonalityTestSession.DoesNotExist:
            return Response({'error': 'Session non trouvée'}, status=status.HTTP_404_NOT_FOUND)


class SubmitPersonalityTestView(APIView):
    """Vue pour soumettre les résultats finaux du test de personnalité"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Permettre de refaire le test pour mettre à jour les résultats
        logger.info(f"Soumission test personnalité pour {request.user.email}")
        
        if request.user.personality_test_completed:
            logger.info(f"Utilisateur {request.user.email} refait son test de personnalité")
        
        data = request.data
        session_id = data.get('session_id')
        
        try:
            # Récupérer la session
            session = None
            if session_id:
                try:
                    session = PersonalityTestSession.objects.get(
                        session_id=session_id,
                        user=request.user
                    )
                    session.is_completed = True
                    session.completed_at = timezone.now()
                    session.duration_seconds = data.get('test_duration_seconds', 0)
                    session.save()
                except PersonalityTestSession.DoesNotExist:
                    logger.warning(f"Session {session_id} non trouvée, création du résultat sans session")
            
            serializer = PersonalityTestSubmissionSerializer(data=data)
            if serializer.is_valid():
                data = serializer.validated_data
                
                # Calculer les types de personnalité
                mbti_result, disc_result = serializer.calculate_personality_types(data)
                
                # Créer ou mettre à jour le résultat
                result, created = PersonalityTestResult.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'session': session,
                        'extraversion_score': data['extraversion_score'],
                        'intuition_score': data['intuition_score'],
                        'thinking_score': data['thinking_score'],
                        'judging_score': data['judging_score'],
                        'dominance_score': data['dominance_score'],
                        'influence_score': data['influence_score'],
                        'steadiness_score': data['steadiness_score'],
                        'conscientiousness_score': data['conscientiousness_score'],
                        'mbti_result': mbti_result,
                        'disc_result': disc_result,
                        'test_duration_seconds': data['test_duration_seconds'],
                        'detailed_mbti_scores': {
                            'E': data['extraversion_score'],
                            'I': 100 - data['extraversion_score'],
                            'N': data['intuition_score'],
                            'S': 100 - data['intuition_score'],
                            'T': data['thinking_score'],
                            'F': 100 - data['thinking_score'],
                            'J': data['judging_score'],
                            'P': 100 - data['judging_score']
                        },
                        'detailed_disc_scores': {
                            'D': data['dominance_score'],
                            'I': data['influence_score'],
                            'S': data['steadiness_score'],
                            'C': data['conscientiousness_score']
                        }
                    }
                )
                
                # Mettre à jour l'utilisateur
                request.user.personality_type = mbti_result
                request.user.disc_type = disc_result
                request.user.personality_test_completed = True
                request.user.personality_test_date = timezone.now()
                request.user.save()
                
                # Mettre à jour le progrès de l'onboarding
                try:
                    progress = OnboardingProgress.objects.get(user=request.user)
                    progress.mark_step_completed('PERSONALITY_TEST')
                    if progress.current_step == 'PERSONALITY_TEST':
                        progress.current_step = 'PASSION_SELECTION'
                        progress.save()
                except OnboardingProgress.DoesNotExist:
                    pass
                
                logger.info(f"Test de personnalité complété pour {request.user.email}: {mbti_result}/{disc_result}")
                
                return Response({
                    'message': 'Test de personnalité complété avec succès',
                    'results': {
                        'mbti_type': mbti_result,
                        'disc_type': disc_result,
                        'detailed_scores': {
                            'mbti': result.detailed_mbti_scores,
                            'disc': result.detailed_disc_scores
                        }
                    }
                })
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Erreur lors de la soumission du test de personnalité: {str(e)}", exc_info=True)
            return Response({
                'error': 'Erreur lors de la sauvegarde du test',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class GoogleOAuth2LoginView(APIView):
    """Vue pour la connexion via Google OAuth2"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        # TODO: Implémenter l'authentification Google
        access_token = request.data.get('access_token')
        if not access_token:
            return Response({'error': 'Token d\'accès Google requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier le token avec Google et créer/connecter l'utilisateur
        return Response({'message': 'Authentification Google en cours d\'implémentation'})


class AppleOAuth2LoginView(APIView):
    """Vue pour la connexion via Apple ID"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        # TODO: Implémenter l'authentification Apple
        access_token = request.data.get('access_token')
        if not access_token:
            return Response({'error': 'Token d\'accès Apple requis'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier le token avec Apple et créer/connecter l'utilisateur
        return Response({'message': 'Authentification Apple en cours d\'implémentation'})


class UserInterestsView(APIView):
    """
    Vue pour gérer les centres d'intérêt de l'utilisateur
    GET: Récupère les centres d'intérêt existants
    POST: Sauvegarde les centres d'intérêt sélectionnés
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupère les centres d'intérêt de l'utilisateur"""
        try:
            user_interests, created = UserInterests.objects.get_or_create(user=request.user)
            
            return Response({
                'selected_interests': user_interests.selected_interests,
                'interests_count': user_interests.interests_count,
                'created_at': user_interests.created_at,
                'updated_at': user_interests.updated_at
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des centres d'intérêt pour {request.user.email}: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la récupération des centres d\'intérêt'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Sauvegarde les centres d'intérêt sélectionnés"""
        try:
            interests_data = request.data.get('selected_interests', [])
            
            # Validation : maximum 3 centres d'intérêt
            if len(interests_data) > 3:
                return Response(
                    {'error': 'Maximum 3 centres d\'intérêt autorisés'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validation : structure des données
            for interest in interests_data:
                if not all(key in interest for key in ['id', 'name', 'color']):
                    return Response(
                        {'error': 'Structure de données invalide pour les centres d\'intérêt'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Créer ou mettre à jour les centres d'intérêt
            user_interests, created = UserInterests.objects.get_or_create(user=request.user)
            user_interests.add_interests(interests_data)
            
            # Mettre à jour le statut d'onboarding
            onboarding_progress, _ = OnboardingProgress.objects.get_or_create(user=request.user)
            onboarding_progress.mark_step_completed('PASSION_SELECTION')
            onboarding_progress.current_step = 'COMPLETED'
            onboarding_progress.save()
            
            logger.info(f"Centres d'intérêt sauvegardés pour {request.user.email}: {len(interests_data)} intérêts")
            
            return Response({
                'message': 'Centres d\'intérêt sauvegardés avec succès',
                'selected_interests': user_interests.selected_interests,
                'interests_count': user_interests.interests_count,
                'onboarding_completed': True
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des centres d'intérêt pour {request.user.email}: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la sauvegarde des centres d\'intérêt'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreatePaymentIntentView(APIView):
    """Vue pour créer un Payment Intent Stripe"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            amount = int(float(data.get('amount', 0)) * 100)  # Convertir en centimes
            currency = data.get('currency', 'eur')
            
            # Informations de réservation
            activity_name = data.get('activity_name', '')
            reservation_date = data.get('reservation_date', '')
            price_plan = data.get('price_plan', '')
            
            # Créer le Payment Intent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                metadata={
                    'user_id': request.user.id,
                    'user_email': request.user.email,
                    'activity_name': activity_name,
                    'reservation_date': reservation_date,
                    'price_plan': price_plan
                }
            )
            
            logger.info(f"Payment Intent créé pour {request.user.email}: {intent.id}")
            
            return Response({
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du Payment Intent: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la création du paiement'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReservationView(APIView):
    """Vue pour gérer les réservations"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupérer toutes les réservations de l'utilisateur"""
        try:
            reservations = Reservation.objects.filter(user=request.user).order_by('reservation_date', 'reservation_time')
            
            reservations_data = []
            for reservation in reservations:
                # Informations du groupe
                group_info = None
                if reservation.has_group:
                    group = reservation.group
                    group_info = {
                        'id': group.id,
                        'name': group.name,
                        'meeting_point_name': group.meeting_point_name,
                        'meeting_point_address': group.meeting_point_address,
                        'meeting_time': group.meeting_time,
                        'location_reveal_time': group.location_reveal_time,
                        'can_reveal_location': group.can_reveal_location,
                        'participants_count': group.participants_count,
                        'max_participants': group.max_participants,
                        'is_confirmed': group.is_confirmed
                    }
                
                reservations_data.append({
                    'id': reservation.id,
                    'activity_name': reservation.activity_name,
                    'activity_description': reservation.activity_description,
                    'reservation_date': reservation.reservation_date,
                    'reservation_time': reservation.reservation_time,
                    'venue_name': reservation.venue_name,
                    'venue_address': reservation.venue_address,
                    'price_plan': reservation.price_plan,
                    'price_amount': str(reservation.price_amount),
                    'currency': reservation.currency,
                    'status': reservation.status,
                    'participants_count': reservation.participants_count,
                    'special_requests': reservation.special_requests,
                    'is_modifiable': reservation.is_modifiable,
                    'is_upcoming': reservation.is_upcoming,
                    'cancellation_deadline': reservation.cancellation_deadline,
                    'created_at': reservation.created_at,
                    'paid_at': reservation.paid_at,
                    'has_group': reservation.has_group,
                    'group': group_info,
                })
            
            return Response({
                'reservations': reservations_data,
                'total_count': len(reservations_data)
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations pour {request.user.email}: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la récupération des réservations'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Créer une nouvelle réservation"""
        try:
            data = request.data
            
            # Convertir la date string en objet date
            reservation_date_str = data.get('reservation_date')
            if reservation_date_str:
                from datetime import datetime
                reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
            else:
                reservation_date = None
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                user=request.user,
                activity_name=data.get('activity_name', ''),
                activity_description=data.get('activity_description', ''),
                reservation_date=reservation_date,
                reservation_time=data.get('reservation_time', '20:00'),
                venue_name=data.get('venue_name', 'Paris'),
                venue_address=data.get('venue_address', ''),
                price_plan=data.get('price_plan', ''),
                price_amount=data.get('price_amount', 0),
                currency=data.get('currency', 'EUR'),
                stripe_payment_intent_id=data.get('payment_intent_id', ''),
                participants_count=data.get('participants_count', 1),
                special_requests=data.get('special_requests', ''),
                status='CONFIRMED'  # Confirmée après paiement
            )
            
            # Marquer comme payée
            if data.get('payment_intent_id'):
                reservation.paid_at = timezone.now()
                reservation.save()
            
            logger.info(f"Réservation créée pour {request.user.email}: {reservation.id}")
            
            return Response({
                'message': 'Réservation créée avec succès',
                'reservation_id': reservation.id,
                'cancellation_deadline': reservation.cancellation_deadline
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la réservation pour {request.user.email}: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la création de la réservation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfirmPaymentView(APIView):
    """Vue pour confirmer un paiement Stripe et créer la réservation"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Log détaillé des données reçues pour debug
            logger.info(f"ConfirmPaymentView - Données reçues: {request.data}")
            
            payment_intent_id = request.data.get('payment_intent_id')
            status_payment = request.data.get('status')
            reservation_data = request.data.get('reservation_data')
            
            logger.info(f"payment_intent_id: {payment_intent_id}")
            logger.info(f"status_payment: {status_payment}")  
            logger.info(f"reservation_data: {reservation_data}")
            logger.info(f"Type de reservation_data: {type(reservation_data)}")
            
            if not payment_intent_id:
                return Response(
                    {'error': 'Payment Intent ID requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Mode développement local avec simulation de paiement
            if payment_intent_id == 'pi_test_local_dev' and status_payment == 'succeeded':
                logger.info(f"Mode développement local - Simulation de paiement réussi pour {request.user.email}")
                
                # Récupérer les données de réservation du POST (ou chercher une réservation existante)
                reservation_data = request.data.get('reservation_data')
                
                if reservation_data:
                    # Nouveau flux : créer la réservation lors du paiement
                    from datetime import datetime, time
                    
                    # Vérifier et convertir reservation_date
                    reservation_date_str = reservation_data.get('reservation_date')
                    if not reservation_date_str:
                        logger.error(f"reservation_date manquante dans reservation_data: {reservation_data}")
                        return Response({
                            'error': 'Date de réservation manquante'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    try:
                        reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        logger.error(f"Erreur de format de date {reservation_date_str}: {e}")
                        return Response({
                            'error': 'Format de date invalide'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Convertir reservation_time en objet time si c'est une string
                    reservation_time_str = reservation_data.get('reservation_time', '20:00')
                    if isinstance(reservation_time_str, str):
                        reservation_time = datetime.strptime(reservation_time_str, '%H:%M').time()
                    else:
                        reservation_time = reservation_time_str
                    
                    # Vérifier si l'utilisateur a un abonnement actif
                    user_has_active_subscription = (
                        request.user.is_premium and 
                        request.user.premium_until and 
                        request.user.premium_until > timezone.now()
                    )
                    
                    # Déterminer le payment_intent_id approprié
                    if user_has_active_subscription:
                        final_payment_intent_id = f'subscription_{request.user.id}'
                        logger.info(f"Utilisateur {request.user.email} a un abonnement actif - réservation gratuite")
                    else:
                        final_payment_intent_id = payment_intent_id
                    
                    reservation = Reservation.objects.create(
                        user=request.user,
                        activity_name=reservation_data['activity_name'],
                        activity_description=reservation_data.get('activity_description', ''),
                        reservation_date=reservation_date,
                        reservation_time=reservation_time,
                        venue_name=reservation_data.get('venue_name', 'Paris'),
                        venue_address=reservation_data.get('venue_address', ''),
                        price_plan=reservation_data['price_plan'],
                        price_amount=reservation_data['price_amount'],
                        currency=reservation_data.get('currency', 'EUR'),
                        participants_count=reservation_data.get('participants_count', 1),
                        special_requests=reservation_data.get('special_requests', ''),
                        status='CONFIRMED',  # Directement confirmé puisque payé
                        paid_at=timezone.now(),
                        stripe_payment_intent_id=payment_intent_id
                    )
                    logger.info(f"Nouvelle réservation créée et payée pour {request.user.email}: {reservation.id}")
                    
                    # Créer un ticket si la formule est "ticket"
                    if reservation_data.get('price_plan') == 'ticket':
                        from datetime import timedelta
                        
                        ticket = UserTicket.objects.create(
                            user=request.user,
                            amount=reservation_data['price_amount'],
                            status='ACTIVE',
                            source='REFUND',  # Pour les tickets achetés
                            expires_at=timezone.now() + timedelta(days=365),  # Expire dans 1 an
                            notes=f"Ticket créé suite au paiement de la réservation {reservation.id}"
                        )
                        logger.info(f"Ticket créé pour {request.user.email}: {ticket.amount}€")
                        
                        # Mettre à jour le type de compte utilisateur
                        request.user.update_subscription_status()
                else:
                    # Ancien flux : chercher une réservation existante
                    try:
                        reservation = Reservation.objects.get(
                            user=request.user, 
                            status='PENDING'
                        )
                    except Reservation.DoesNotExist:
                        return Response({
                            'error': 'Aucune réservation en attente trouvée et aucune donnée fournie'
                        }, status=status.HTTP_404_NOT_FOUND)
                    except Reservation.MultipleObjectsReturned:
                        # Prendre la plus récente
                        reservation = Reservation.objects.filter(
                            user=request.user, 
                            status='PENDING'
                        ).order_by('-created_at').first()
                    
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
            
            # Mode production avec vérification Stripe réelle
            try:
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            except stripe.error.StripeError as e:
                logger.error(f"Erreur Stripe: {str(e)}")
                return Response(
                    {'error': 'Erreur lors de la vérification du paiement'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Vérifier que le paiement a réussi
            if intent.status != 'succeeded':
                return Response(
                    {'error': 'Le paiement n\'a pas été confirmé'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Extraire les métadonnées
            metadata = intent.metadata
            
            # Convertir la date string en objet date
            reservation_date_str = metadata.get('reservation_date')
            if reservation_date_str:
                from datetime import datetime
                reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
            else:
                reservation_date = None
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                user=request.user,
                activity_name=metadata.get('activity_name', ''),
                reservation_date=reservation_date,
                price_plan=metadata.get('price_plan', ''),
                price_amount=intent.amount / 100,  # Convertir depuis les centimes
                currency=intent.currency.upper(),
                stripe_payment_intent_id=payment_intent_id,
                status='CONFIRMED',
                paid_at=timezone.now()
            )
            
            logger.info(f"Paiement confirmé et réservation créée pour {request.user.email}: {reservation.id}")
            
            return Response({
                'message': 'Paiement confirmé et réservation créée',
                'reservation_id': reservation.id,
                'cancellation_deadline': reservation.cancellation_deadline
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la confirmation du paiement: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la confirmation du paiement'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateReservationView(APIView):
    """Vue pour préparer une réservation (sans la créer en DB tant que pas payée)"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            
            # Vérifier s'il y a une invitation acceptée pour cet utilisateur
            invited_user_flow = False
            try:
                invitation = FriendInvitation.objects.get(
                    invited_user=request.user,
                    status='ACCEPTED'
                )
                invited_user_flow = True
                logger.info(f"Flux utilisateur invité détecté pour {request.user.email}")
            except FriendInvitation.DoesNotExist:
                pass
            
            # Convertir la date string en objet date
            reservation_date_str = data.get('reservation_date')
            if reservation_date_str:
                from datetime import datetime
                reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
            else:
                reservation_date = None
            
            # NE PAS créer la réservation en DB, juste valider et préparer
            reservation_data = {
                'activity_name': data.get('activity_name', ''),
                'activity_description': data.get('activity_description', ''),
                'reservation_date': reservation_date_str,
                'reservation_time': data.get('reservation_time', '20:00'),
                'venue_name': data.get('venue_name', 'Paris'),
                'venue_address': data.get('venue_address', ''),
                'price_plan': data.get('price_plan', ''),
                'price_amount': data.get('price_amount', 0),
                'currency': data.get('currency', 'EUR'),
                'participants_count': data.get('participants_count', 1),
                'special_requests': data.get('special_requests', ''),
                'status': 'DRAFT'  # Statut temporaire avant paiement
            }
            
            logger.info(f"Données de réservation préparées pour {request.user.email} (pas encore en DB)")
            
            return Response({
                'message': 'Données de réservation validées',
                'reservation_data': reservation_data,
                'invited_user_flow': invited_user_flow,
                'status': 'DRAFT',
                'next_step': 'payment'
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la réservation pour {request.user.email}: {str(e)}")
            return Response(
                {'error': 'Erreur lors de la création de la réservation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminReservationsView(APIView):
    """Vue pour récupérer toutes les réservations (admin)"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupérer toutes les réservations pour l'admin"""
        try:
            # Pour l'instant, pas de vérification d'admin - à améliorer plus tard
            reservations = Reservation.objects.select_related('user').all().order_by('-created_at')
            
            reservations_data = []
            for reservation in reservations:
                # Récupérer les données de personnalité et intérêts
                user_data = {
                    'id': reservation.user.id,
                    'email': reservation.user.email,
                    'first_name': reservation.user.first_name or reservation.user.email.split('@')[0],
                    'mbti': 'N/A',
                    'disc': 'N/A',
                    'interests': [],
                    'is_invited_user': reservation.user.is_invited_user,
                    'inviter_email': None
                }
                
                # Récupérer les informations d'invitation si applicable
                if reservation.user.is_invited_user and reservation.user.invitation_used:
                    invitation = reservation.user.invitation_used
                    user_data['inviter_email'] = invitation.inviter.email
                
                # Récupérer les résultats de personnalité
                try:
                    personality = PersonalityTestResult.objects.get(user=reservation.user)
                    user_data['mbti'] = personality.mbti_result or 'N/A'
                    user_data['disc'] = personality.disc_result or 'N/A'
                except PersonalityTestResult.DoesNotExist:
                    pass
                
                # Récupérer les intérêts
                try:
                    interests = UserInterests.objects.get(user=reservation.user)
                    user_data['interests'] = interests.selected_interests or []
                except UserInterests.DoesNotExist:
                    pass
                
                # Informations du groupe si applicable
                group_info = None
                if reservation.has_group:
                    group = reservation.group
                    group_info = {
                        'id': group.id,
                        'name': group.name,
                        'meeting_point_name': group.meeting_point_name,
                        'meeting_point_address': group.meeting_point_address,
                        'participants_count': group.participants_count
                    }

                reservation_data = {
                    'id': reservation.id,
                    'activity_name': reservation.activity_name,
                    'activity_description': reservation.activity_description,
                    'reservation_date': reservation.reservation_date.isoformat() if reservation.reservation_date else None,
                    'reservation_time': reservation.reservation_time.strftime('%H:%M') if reservation.reservation_time else '20:00',
                    'venue_name': reservation.venue_name,
                    'venue_address': reservation.venue_address,
                    'price_plan': reservation.price_plan,
                    'price_amount': str(reservation.price_amount),
                    'currency': reservation.currency,
                    'status': reservation.status,
                    'paid_at': reservation.paid_at.isoformat() if reservation.paid_at else None,
                    'has_group': reservation.has_group,
                    'user': user_data,
                    'group': group_info
                }
                
                reservations_data.append(reservation_data)
            
            logger.info(f"Admin: {len(reservations_data)} réservations récupérées")
            # Log détaillé pour debug
            for i, res in enumerate(reservations_data[:3]):  # Log les 3 premières
                logger.info(f"Réservation {i+1}: {res['user']['email']} - {res['activity_name']} - MBTI: {res['user']['mbti']} - Intérêts: {len(res['user']['interests'])}")
            
            return Response({'reservations': reservations_data})
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations admin: {str(e)}")
            return Response({'error': 'Erreur lors de la récupération des réservations'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateGroupView(APIView):
    """Vue pour créer un groupe d'événement"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Créer un nouveau groupe avec les réservations sélectionnées"""
        try:
            data = request.data
            
            # Valider les données requises
            group_name = data.get('name')
            meeting_point_name = data.get('meeting_point_name')
            meeting_point_address = data.get('meeting_point_address')
            meeting_time = data.get('meeting_time', '20:00')
            selected_reservation_ids = data.get('selected_reservations', [])
            
            if not group_name:
                return Response({'error': 'Nom du groupe requis'}, status=status.HTTP_400_BAD_REQUEST)
            if not meeting_point_name:
                return Response({'error': 'Point de rendez-vous requis'}, status=status.HTTP_400_BAD_REQUEST)
            if not selected_reservation_ids:
                return Response({'error': 'Au moins une réservation doit être sélectionnée'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Récupérer les réservations sélectionnées
            reservations = Reservation.objects.filter(id__in=selected_reservation_ids, status='CONFIRMED')
            if not reservations.exists():
                return Response({'error': 'Aucune réservation confirmée trouvée'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier que toutes les réservations sont pour la même date et activité
            first_reservation = reservations.first()
            if not all(r.reservation_date == first_reservation.reservation_date for r in reservations):
                return Response({'error': 'Toutes les réservations doivent être pour la même date'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Convertir meeting_time en objet time
            from datetime import datetime
            if isinstance(meeting_time, str):
                meeting_time_obj = datetime.strptime(meeting_time, '%H:%M').time()
            else:
                meeting_time_obj = meeting_time
            
            # Créer le groupe
            group = EventGroup.objects.create(
                name=group_name,
                activity_name=first_reservation.activity_name,
                event_date=first_reservation.reservation_date,  # Utiliser event_date au lieu de reservation_date
                meeting_point_name=meeting_point_name,
                meeting_point_address=meeting_point_address,
                meeting_time=meeting_time_obj,
                max_participants=len(selected_reservation_ids),  # Supprimer participants_count (propriété calculée)
                is_confirmed=True
            )
            
            # Créer les adhésions au groupe
            group_members = []
            for reservation in reservations:
                # Créer l'adhésion (cela définit automatiquement has_group et group)
                GroupMembership.objects.create(
                    group=group,
                    reservation=reservation,
                    joined_at=timezone.now()
                )
                # Note: has_group et group sont maintenant automatiquement True/défini via group_membership
                
                # Récupérer les infos de personnalité pour la réponse
                mbti = 'N/A'
                disc = 'N/A'
                try:
                    personality = PersonalityTestResult.objects.get(user=reservation.user)
                    mbti = personality.mbti_result or 'N/A'
                    disc = personality.disc_result or 'N/A'
                except PersonalityTestResult.DoesNotExist:
                    pass
                
                group_members.append({
                    'id': reservation.user.id,
                    'email': reservation.user.email,
                    'first_name': reservation.user.first_name,
                    'mbti': mbti,
                    'disc': disc
                })
            
            # Préparer la réponse
            group_data = {
                'id': group.id,
                'name': group.name,
                'activity_name': group.activity_name,
                'reservation_date': group.event_date.isoformat(),  # Utiliser event_date
                'meeting_point_name': group.meeting_point_name,
                'meeting_point_address': group.meeting_point_address,
                'meeting_time': group.meeting_time.strftime('%H:%M'),
                'participants_count': group.participants_count,
                'created_at': group.created_at.isoformat(),
                'members': group_members
            }
            
            logger.info(f"Groupe '{group_name}' créé avec {len(selected_reservation_ids)} participants")
            
            return Response({
                'success': True,
                'message': f'Groupe "{group_name}" créé avec succès',
                'group': group_data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du groupe: {str(e)}")
            return Response({'error': 'Erreur lors de la création du groupe'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminGroupsView(APIView):
    """Vue pour récupérer tous les groupes (admin)"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupérer tous les groupes existants"""
        try:
            groups = EventGroup.objects.all().order_by('-created_at')
            
            groups_data = []
            for group in groups:
                # Récupérer les membres du groupe
                members = []
                for membership in group.memberships.all():
                    member_user = membership.reservation.user
                    
                    # Récupérer les infos de personnalité
                    mbti = 'N/A'
                    disc = 'N/A'
                    try:
                        personality = PersonalityTestResult.objects.get(user=member_user)
                        mbti = personality.mbti_result or 'N/A'
                        disc = personality.disc_result or 'N/A'
                    except PersonalityTestResult.DoesNotExist:
                        pass
                    
                    members.append({
                        'id': member_user.id,
                        'email': member_user.email,
                        'first_name': member_user.first_name,
                        'mbti': mbti,
                        'disc': disc
                    })
                
                groups_data.append({
                    'id': group.id,
                    'name': group.name,
                    'activity_name': group.activity_name,
                    'reservation_date': group.event_date.isoformat(),  # Utiliser event_date
                    'meeting_point_name': group.meeting_point_name,
                    'meeting_point_address': group.meeting_point_address,
                    'meeting_time': group.meeting_time.strftime('%H:%M'),
                    'participants_count': group.participants_count,
                    'created_at': group.created_at.isoformat(),
                    'members': members
                })
            
            return Response(groups_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des groupes: {str(e)}")
            return Response({'error': 'Erreur lors de la récupération des groupes'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReservationDetailView(APIView):
    """Vue pour récupérer une réservation spécifique"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, reservation_id):
        """Récupérer une réservation spécifique par son ID"""
        try:
            reservation = Reservation.objects.get(id=reservation_id, user=request.user)
            
            # Informations du groupe
            group_info = None 
            if reservation.has_group:
                group = reservation.group
                
                # Récupérer les membres du groupe avec leurs infos de personnalité
                members = []
                for membership in group.memberships.all():
                    member_user = membership.reservation.user
                    
                    # Récupérer les infos de personnalité
                    mbti = 'N/A'
                    disc = 'N/A'
                    try:
                        personality = PersonalityTestResult.objects.get(user=member_user)
                        mbti = personality.mbti_result or 'N/A'
                        disc = personality.disc_result or 'N/A'
                    except PersonalityTestResult.DoesNotExist:
                        pass
                    
                    # Récupérer les intérêts
                    interests = []
                    try:
                        user_interests = UserInterests.objects.get(user=member_user)
                        interests = user_interests.selected_interests or []
                    except UserInterests.DoesNotExist:
                        pass
                    
                    members.append({
                        'id': member_user.id,
                        'first_name': member_user.first_name,
                        'email': member_user.email,
                        'mbti': mbti,
                        'disc': disc,
                        'interests': interests
                    })
                
                group_info = {
                    'id': group.id,
                    'name': group.name,
                    'meeting_point_name': group.meeting_point_name,
                    'meeting_point_address': group.meeting_point_address,
                    'meeting_time': group.meeting_time.strftime('%H:%M') if group.meeting_time else '20:00',
                    'location_reveal_time': group.location_reveal_time.isoformat() if group.location_reveal_time else None,
                    'can_reveal_location': group.can_reveal_location,
                    'participants_count': group.participants_count,
                    'max_participants': group.max_participants,
                    'is_confirmed': group.is_confirmed,
                    'members': members
                }
            
            reservation_data = {
                'id': reservation.id,
                'activity_name': reservation.activity_name,
                'activity_description': reservation.activity_description,
                'reservation_date': reservation.reservation_date,
                'reservation_time': reservation.reservation_time,
                'venue_name': reservation.venue_name,
                'venue_address': reservation.venue_address,
                'price_plan': reservation.price_plan,
                'price_amount': str(reservation.price_amount),
                'currency': reservation.currency,
                'status': reservation.status,
                'participants_count': reservation.participants_count,
                'special_requests': reservation.special_requests,
                'is_modifiable': reservation.is_modifiable,
                'is_upcoming': reservation.is_upcoming,
                'cancellation_deadline': reservation.cancellation_deadline,
                'created_at': reservation.created_at,
                'paid_at': reservation.paid_at,
                'has_group': reservation.has_group,
                'group': group_info
            }
            
            logger.info(f"Réservation {reservation_id} récupérée pour {request.user.email}")
            return Response(reservation_data)
            
        except Reservation.DoesNotExist:
            logger.warning(f"Réservation {reservation_id} non trouvée pour {request.user.email}")
            return Response({'error': 'Réservation non trouvée'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la réservation {reservation_id} pour {request.user.email}: {str(e)}")
            return Response({'error': 'Erreur lors de la récupération de la réservation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileDetailView(APIView):
    """Vue pour récupérer les détails complets du profil d'un utilisateur (admin)"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Récupérer les détails complets du profil utilisateur pour l'admin"""
        try:
            # Pour l'instant, pas de vérification d'admin - à améliorer plus tard
            user = User.objects.get(id=user_id)
            
            # Informations de base
            user_data = {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() or user.email.split('@')[0],
                'phone': user.phone,
                'birth_date': user.birth_date,
                'age': user.age if hasattr(user, 'age') else None,
                'gender': user.get_gender_display() if user.gender else 'Non précisé',
                'location': user.location,
                'bio': user.bio,
                'created_at': user.date_joined,
                'last_login': user.last_login,
                'email_verified': user.email_verified,
                'onboarding_completed': user.onboarding_completed,
                'personality_test_completed': user.personality_test_completed,
                'personality_test_date': user.personality_test_date,
            }
            
            # Résultats de personnalité détaillés
            personality_data = None
            try:
                personality = PersonalityTestResult.objects.get(user=user)
                personality_data = {
                    'mbti_result': personality.mbti_result,
                    'disc_result': personality.disc_result,
                    'scores': {
                        'mbti': {
                            'extraversion': personality.extraversion_score,
                            'intuition': personality.intuition_score,
                            'thinking': personality.thinking_score,
                            'judging': personality.judging_score,
                        },
                        'disc': {
                            'dominance': personality.dominance_score,
                            'influence': personality.influence_score,
                            'steadiness': personality.steadiness_score,
                            'conscientiousness': personality.conscientiousness_score,
                        }
                    },
                    'detailed_scores': {
                        'mbti': personality.detailed_mbti_scores,
                        'disc': personality.detailed_disc_scores,
                    },
                    'test_duration_seconds': personality.test_duration_seconds,
                    'completed_at': personality.completed_at,
                }
            except PersonalityTestResult.DoesNotExist:
                pass
            
            # Réponses détaillées aux questions
            test_answers = []
            try:
                # Récupérer la dernière session de test complétée
                session = PersonalityTestSession.objects.filter(
                    user=user, 
                    is_completed=True
                ).order_by('-completed_at').first()
                
                if session:
                    answers = PersonalityTestAnswer.objects.filter(
                        session=session
                    ).order_by('question_id')
                    
                    for answer in answers:
                        test_answers.append({
                            'question_id': answer.question_id,
                            'question_text': answer.question_text,
                            'answer_index': answer.answer_index,
                            'answer_text': answer.answer_text,
                            'mbti_scores': answer.mbti_scores,
                            'disc_scores': answer.disc_scores,
                            'answered_at': answer.answered_at,
                        })
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération des réponses pour {user.email}: {str(e)}")
            
            # Intérêts sélectionnés
            interests_data = None
            try:
                interests = UserInterests.objects.get(user=user)
                interests_data = {
                    'selected_interests': interests.selected_interests,
                    'interests_count': interests.interests_count,
                    'created_at': interests.created_at,
                    'updated_at': interests.updated_at,
                }
            except UserInterests.DoesNotExist:
                pass
            
            # Statistiques des réservations
            reservations_stats = {
                'total_reservations': user.reservations.count(),
                'confirmed_reservations': user.reservations.filter(status='CONFIRMED').count(),
                'paid_reservations': user.reservations.filter(paid_at__isnull=False).count(),
                'pending_reservations': user.reservations.filter(status='PENDING').count(),
                'cancelled_reservations': user.reservations.filter(status='CANCELLED').count(),
            }
            
            # Progrès de l'onboarding
            onboarding_data = None
            try:
                progress = OnboardingProgress.objects.get(user=user)
                completion_status = progress.get_completion_status()
                onboarding_data = {
                    'current_step': progress.current_step,
                    'completed_steps': progress.completed_steps,
                    'is_completed': completion_status['is_completed'],
                    'temp_data': progress.temp_data,
                    'started_at': progress.started_at,
                    'last_updated': progress.last_updated,
                    'completed_at': progress.completed_at,
                }
            except OnboardingProgress.DoesNotExist:
                pass
            
            response_data = {
                'user': user_data,
                'personality': personality_data,
                'test_answers': test_answers,
                'interests': interests_data,
                'reservations_stats': reservations_stats,
                'onboarding': onboarding_data,
            }
            
            logger.info(f"Détails du profil récupérés pour l'utilisateur {user.email}")
            return Response(response_data)
            
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du profil utilisateur {user_id}: {str(e)}")
            return Response({'error': 'Erreur lors de la récupération du profil'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReservationCancelView(APIView):
    """Vue pour annuler une réservation et créer un ticket si nécessaire"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, reservation_id):
        try:
            # Récupérer la réservation
            reservation = Reservation.objects.get(id=reservation_id, user=request.user)
            
            # Vérifier si l'annulation est encore possible (avant mardi 23h59)
            from datetime import datetime, timedelta
            
            reservation_date = reservation.reservation_date
            tuesday_before = reservation_date - timedelta(days=2)  # Mardi avant le jeudi
            deadline = datetime.combine(tuesday_before, datetime.min.time().replace(hour=23, minute=59))
            deadline = timezone.make_aware(deadline)
            
            now = timezone.now()
            
            if now > deadline:
                return Response({
                    'error': 'La période d\'annulation est expirée (mardi 23h59)',
                    'deadline_passed': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer un ticket SEULEMENT si c'était un vrai paiement (pas ticket/abonnement)
            ticket_created = False
            ticket_amount = None
            
            if reservation.paid_at:
                # Vérifier si c'était payé avec un ticket existant
                was_paid_with_ticket = (
                    reservation.stripe_payment_intent_id and 
                    reservation.stripe_payment_intent_id.startswith('ticket_')
                )
                
                # Vérifier si c'était payé via un abonnement
                was_paid_with_subscription = (
                    reservation.stripe_payment_intent_id and 
                    reservation.stripe_payment_intent_id.startswith('subscription_')
                )
                
                # Vérifier le plan tarifaire
                is_ticket_plan = reservation.price_plan == 'TICKET'
                
                # Si c'était un abonnement, libérer la réservation de l'abonnement
                if was_paid_with_subscription:
                    # Trouver l'abonnement lié et libérer la réservation
                    subscription = UserSubscription.objects.filter(
                        user=request.user,
                        current_reservation=reservation
                    ).first()
                    if subscription:
                        subscription.release_reservation()
                        logger.info(f"Réservation libérée de l'abonnement {subscription.id}")
                
                # Ne créer un ticket que si c'était une formule ticket ET pas payé avec un ticket existant
                should_create_ticket = is_ticket_plan and not was_paid_with_ticket and not was_paid_with_subscription
                
                if should_create_ticket:
                    ticket = UserTicket.objects.create(
                        user=request.user,
                        amount=reservation.price_amount,
                        source='CANCELLATION',
                        original_reservation=reservation,
                        # Les tickets expirent après 6 mois
                        expires_at=timezone.now() + timedelta(days=180)
                    )
                    ticket_created = True
                    ticket_amount = str(reservation.price_amount)
                    logger.info(f"Ticket créé pour l'utilisateur {request.user.email}: {ticket.amount}€")
                else:
                    # Log pour debug - expliquer pourquoi pas de ticket
                    if was_paid_with_ticket:
                        reason = "ticket existant"
                    elif was_paid_with_subscription:
                        reason = "abonnement"
                    elif not is_ticket_plan:
                        reason = f"plan {reservation.price_plan}"
                    else:
                        reason = "autre"
                    logger.info(f"Pas de ticket créé pour {request.user.email} - Paiement original via {reason}")
            
            # Marquer la réservation comme annulée
            reservation.status = 'CANCELLED'
            reservation.save()
            
            logger.info(f"Réservation {reservation_id} annulée pour l'utilisateur {request.user.email}")
            
            return Response({
                'success': True,
                'message': 'Réservation annulée avec succès',
                'ticket_created': ticket_created,
                'ticket_amount': ticket_amount
            })
            
        except Reservation.DoesNotExist:
            return Response({'error': 'Réservation non trouvée'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de la réservation {reservation_id}: {str(e)}")
            return Response({'error': 'Erreur lors de l\'annulation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserTicketsView(APIView):
    """Vue pour récupérer les tickets d'un utilisateur"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tickets = UserTicket.objects.filter(user=request.user).order_by('-created_at')
            
            tickets_data = []
            for ticket in tickets:
                tickets_data.append({
                    'id': ticket.id,
                    'amount': str(ticket.amount),
                    'status': ticket.status,
                    'source': ticket.source,
                    'created_at': ticket.created_at.isoformat(),
                    'expires_at': ticket.expires_at.isoformat() if ticket.expires_at else None,
                    'used_at': ticket.used_at.isoformat() if ticket.used_at else None,
                    'is_valid': ticket.is_valid,
                    'notes': ticket.notes
                })
            
            return Response({'tickets': tickets_data})
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tickets pour {request.user.email}: {str(e)}")
            return Response({'error': 'Erreur lors de la récupération des tickets'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UseTicketView(APIView):
    """Vue pour utiliser un ticket pour une réservation"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            ticket_id = data.get('ticket_id')
            reservation_data = data.get('reservation_data')
            
            if not ticket_id:
                return Response({
                    'error': 'ID du ticket requis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not reservation_data:
                return Response({
                    'error': 'Données de réservation requises'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Récupérer le ticket
            try:
                ticket = UserTicket.objects.get(id=ticket_id, user=request.user)
            except UserTicket.DoesNotExist:
                return Response({
                    'error': 'Ticket non trouvé'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Vérifier que le ticket est valide
            if not ticket.is_valid:
                return Response({
                    'error': 'Ce ticket n\'est plus valide'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer la réservation comme dans ConfirmPaymentView
            from datetime import datetime
            reservation_date_str = reservation_data.get('reservation_date')
            if not reservation_date_str:
                return Response({
                    'error': 'Date de réservation manquante'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError) as e:
                logger.error(f"Erreur de format de date {reservation_date_str}: {e}")
                return Response({
                    'error': 'Format de date invalide'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Convertir reservation_time
            reservation_time_str = reservation_data.get('reservation_time', '20:00')
            if isinstance(reservation_time_str, str):
                reservation_time = datetime.strptime(reservation_time_str, '%H:%M').time()
            else:
                reservation_time = reservation_time_str
            
            # Créer la réservation
            reservation = Reservation.objects.create(
                user=request.user,
                activity_name=reservation_data['activity_name'],
                activity_description=reservation_data.get('activity_description', ''),
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                venue_name=reservation_data.get('venue_name', 'Paris'),
                venue_address=reservation_data.get('venue_address', ''),
                price_plan=reservation_data['price_plan'],
                price_amount=reservation_data['price_amount'],
                currency=reservation_data.get('currency', 'EUR'),
                participants_count=reservation_data.get('participants_count', 1),
                special_requests=reservation_data.get('special_requests', ''),
                status='CONFIRMED',  # Directement confirmé avec le ticket
                paid_at=timezone.now(),
                stripe_payment_intent_id=f'ticket_{ticket.id}'
            )
            
            # Utiliser le ticket
            ticket.use_ticket(reservation)
            
            logger.info(f"Réservation {reservation.id} créée avec ticket {ticket.id} pour {request.user.email}")
            
            # Retourner les détails de la réservation
            reservation_data_response = {
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
                'payment_method': 'ticket'
            }
            
            return Response({
                'success': True,
                'message': 'Réservation confirmée avec le ticket',
                'reservation': reservation_data_response,
                'ticket_used': {
                    'id': ticket.id,
                    'amount': str(ticket.amount)
                }
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de l'utilisation du ticket pour {request.user.email}: {str(e)}")
            return Response({'error': 'Erreur lors de l\'utilisation du ticket'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminUsersManagementView(APIView):
    """Vue admin pour gérer les utilisateurs, abonnements et tickets"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupérer tous les utilisateurs avec leurs infos d'abonnement et tickets"""
        try:
            # Pour l'instant, pas de vérification d'admin - à améliorer plus tard
            users = User.objects.all().order_by('-created_at')
            
            users_data = []
            for user in users:
                # Récupérer les réservations de l'utilisateur
                reservations = Reservation.objects.filter(user=user).order_by('-created_at')
                reservations_summary = {
                    'total': reservations.count(),
                    'confirmed': reservations.filter(status='CONFIRMED').count(),
                    'cancelled': reservations.filter(status='CANCELLED').count(),
                    'paid_with_ticket': reservations.filter(stripe_payment_intent_id__startswith='ticket_').count(),
                    'paid_with_subscription': reservations.filter(stripe_payment_intent_id__startswith='subscription_').count(),
                    'paid_with_payment': reservations.filter(
                        stripe_payment_intent_id__isnull=False
                    ).exclude(
                        stripe_payment_intent_id__startswith='ticket_'
                    ).exclude(
                        stripe_payment_intent_id__startswith='subscription_'
                    ).count(),
                }
                
                # Récupérer les tickets de l'utilisateur
                tickets = UserTicket.objects.filter(user=user)
                tickets_summary = {
                    'total': tickets.count(),
                    'active': tickets.filter(status='ACTIVE').count(),
                    'used': tickets.filter(status='USED').count(),
                    'expired': tickets.filter(status='EXPIRED').count(),
                    'total_value': sum(float(t.amount) for t in tickets.filter(status='ACTIVE')),
                }
                
                # Statut d'abonnement
                subscription_status = {
                    'is_premium': user.is_premium,
                    'premium_until': user.premium_until.isoformat() if user.premium_until else None,
                    'is_active': user.is_premium_active if hasattr(user, 'is_premium_active') else False,
                    'days_remaining': None
                }
                
                if user.premium_until and user.is_premium:
                    days_remaining = (user.premium_until.date() - timezone.now().date()).days
                    subscription_status['days_remaining'] = max(0, days_remaining)
                
                # Dernières réservations pour audit
                recent_reservations = []
                for res in reservations[:3]:  # 3 dernières
                    payment_method = 'Inconnu'
                    if res.stripe_payment_intent_id:
                        if res.stripe_payment_intent_id.startswith('ticket_'):
                            payment_method = 'Ticket'
                        elif res.stripe_payment_intent_id.startswith('subscription_'):
                            payment_method = 'Abonnement'
                        elif res.stripe_payment_intent_id == 'pi_test_local_dev':
                            payment_method = 'Test Local'
                        else:
                            payment_method = 'Stripe'
                    
                    recent_reservations.append({
                        'id': res.id,
                        'activity': res.activity_name,
                        'date': res.reservation_date.isoformat(),
                        'amount': str(res.price_amount),
                        'status': res.status,
                        'payment_method': payment_method,
                        'paid_at': res.paid_at.isoformat() if res.paid_at else None,
                        'created_at': res.created_at.isoformat()
                    })
                
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'date_joined': user.date_joined.isoformat(),
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'email_verified': user.email_verified,
                    'onboarding_completed': user.onboarding_completed,
                    'subscription_status': subscription_status,
                    'reservations_summary': reservations_summary,
                    'tickets_summary': tickets_summary,
                    'recent_reservations': recent_reservations,
                    'risk_level': self._calculate_risk_level(user, reservations_summary, tickets_summary)
                }
                
                users_data.append(user_data)
            
            # Statistiques globales
            global_stats = self._calculate_global_stats(users_data)
            
            logger.info(f"Admin: {len(users_data)} utilisateurs récupérés pour la gestion")
            
            return Response({
                'users': users_data,
                'global_stats': global_stats,
                'total_users': len(users_data)
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs admin: {str(e)}")
            return Response({'error': 'Erreur lors de la récupération des utilisateurs'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Actions admin sur les utilisateurs"""
        try:
            action = request.data.get('action')
            user_id = request.data.get('user_id')
            
            if not action or not user_id:
                return Response({
                    'error': 'Action et user_id requis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                target_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'error': 'Utilisateur non trouvé'
                }, status=status.HTTP_404_NOT_FOUND)
            
            if action == 'grant_premium':
                # Accorder un abonnement premium de test (30 jours)
                target_user.is_premium = True
                target_user.premium_until = timezone.now() + timedelta(days=30)
                target_user.save()
                
                logger.info(f"Admin {request.user.email} a accordé un abonnement premium à {target_user.email}")
                
                return Response({
                    'success': True,
                    'message': f'Abonnement premium accordé à {target_user.email} pour 30 jours'
                })
            
            elif action == 'revoke_premium':
                # Révoquer l'abonnement premium
                target_user.is_premium = False
                target_user.premium_until = None
                target_user.save()
                
                logger.info(f"Admin {request.user.email} a révoqué l'abonnement premium de {target_user.email}")
                
                return Response({
                    'success': True,
                    'message': f'Abonnement premium révoqué pour {target_user.email}'
                })
            
            elif action == 'expire_tickets':
                # Expirer tous les tickets actifs d'un utilisateur
                active_tickets = UserTicket.objects.filter(user=target_user, status='ACTIVE')
                expired_count = active_tickets.count()
                active_tickets.update(status='EXPIRED')
                
                logger.info(f"Admin {request.user.email} a expiré {expired_count} tickets de {target_user.email}")
                
                return Response({
                    'success': True,
                    'message': f'{expired_count} tickets expirés pour {target_user.email}'
                })
            
            else:
                return Response({
                    'error': 'Action non reconnue'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Erreur lors de l'action admin: {str(e)}")
            return Response({'error': 'Erreur lors de l\'action'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_risk_level(self, user, reservations_summary, tickets_summary):
        """Calcule le niveau de risque d'abus pour un utilisateur"""
        risk_points = 0
        
        # Ratio annulations élevé
        if reservations_summary['total'] > 0:
            cancellation_ratio = reservations_summary['cancelled'] / reservations_summary['total']
            if cancellation_ratio > 0.5:
                risk_points += 3
            elif cancellation_ratio > 0.3:
                risk_points += 2
        
        # Beaucoup de tickets actifs
        if tickets_summary['active'] > 5:
            risk_points += 2
        elif tickets_summary['active'] > 2:
            risk_points += 1
        
        # Trop de réservations avec tickets
        if reservations_summary['total'] > 0:
            ticket_ratio = reservations_summary['paid_with_ticket'] / reservations_summary['total']
            if ticket_ratio > 0.7:
                risk_points += 2
        
        # Abonnement + beaucoup de tickets (suspect)
        if user.is_premium and tickets_summary['active'] > 2:
            risk_points += 3
        
        if risk_points >= 5:
            return 'HIGH'
        elif risk_points >= 3:
            return 'MEDIUM'
        elif risk_points >= 1:
            return 'LOW'
        else:
            return 'NONE'
    
    def _calculate_global_stats(self, users_data):
        """Calcule les statistiques globales"""
        total_users = len(users_data)
        premium_users = len([u for u in users_data if u['subscription_status']['is_active']])
        high_risk_users = len([u for u in users_data if u['risk_level'] == 'HIGH'])
        
        total_reservations = sum(u['reservations_summary']['total'] for u in users_data)
        total_active_tickets = sum(u['tickets_summary']['active'] for u in users_data)
        total_ticket_value = sum(u['tickets_summary']['total_value'] for u in users_data)
        
        return {
            'total_users': total_users,
            'premium_users': premium_users,
            'premium_percentage': round((premium_users / total_users * 100) if total_users > 0 else 0, 1),
            'high_risk_users': high_risk_users,
            'total_reservations': total_reservations,
            'total_active_tickets': total_active_tickets,
            'total_ticket_value': round(total_ticket_value, 2),
            'avg_reservations_per_user': round(total_reservations / total_users if total_users > 0 else 0, 1)
        }


class CreateFriendInvitationView(APIView):
    """Vue pour créer une invitation d'ami"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            invited_email = data.get('invited_email')
            reservation_id = data.get('reservation_id')
            message = data.get('message', '')
            
            if not invited_email:
                return Response({
                    'error': 'Email de l\'invité requis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not reservation_id:
                return Response({
                    'error': 'ID de réservation requis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier si l'email invité a déjà un compte
            existing_user = User.objects.filter(email=invited_email).first()
            if existing_user:
                return Response({
                    'error': f'Cet ami est déjà inscrit sur Evenlyf avec l\'email {invited_email}',
                    'user_exists': True,
                    'existing_user_name': f"{existing_user.first_name} {existing_user.last_name}".strip()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier que la réservation appartient à l'utilisateur
            try:
                reservation = Reservation.objects.get(
                    id=reservation_id,
                    user=request.user
                )
            except Reservation.DoesNotExist:
                return Response({
                    'error': 'Réservation non trouvée'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Vérifier que la réservation est payée
            if reservation.status != 'CONFIRMED' or not reservation.paid_at:
                return Response({
                    'error': 'La réservation doit être payée pour inviter un ami'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier s'il existe déjà une invitation pour cette combinaison
            existing_invitation = FriendInvitation.objects.filter(
                inviter=request.user,
                invited_email=invited_email,
                reservation=reservation
            ).first()
            
            if existing_invitation:
                # Si l'invitation existe et est encore valide, la renvoyer
                if existing_invitation.is_valid:
                    # Mettre à jour le message si différent
                    if message and existing_invitation.message != message:
                        existing_invitation.message = message
                        existing_invitation.save()
                    
                    invitation = existing_invitation
                    logger.info(f"Invitation existante renvoyée pour {invited_email}")
                else:
                    # Si expirée, la supprimer et en créer une nouvelle
                    existing_invitation.delete()
                    logger.info(f"Invitation expirée supprimée pour {invited_email}")
                    
                    try:
                        invitation = FriendInvitation.create_invitation(
                            inviter=request.user,
                            invited_email=invited_email,
                            reservation=reservation,
                            message=message
                        )
                    except ValueError as e:
                        return Response({
                            'error': str(e)
                                                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Pas d'invitation existante, en créer une nouvelle
                try:
                    invitation = FriendInvitation.create_invitation(
                        inviter=request.user,
                        invited_email=invited_email,
                        reservation=reservation,
                        message=message
                    )
                except ValueError as e:
                    return Response({
                        'error': str(e)
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Envoyer l'email d'invitation
            from .utils import send_friend_invitation_email
            email_sent = send_friend_invitation_email(invitation)
            
            # Déterminer si c'est une nouvelle invitation ou un renvoi
            is_resend = bool(existing_invitation and existing_invitation.is_valid)
            
            if is_resend:
                logger.info(f"Invitation renvoyée par {request.user.email} pour {invited_email}")
            else:
                logger.info(f"Nouvelle invitation créée par {request.user.email} pour {invited_email}")
            
            if email_sent:
                logger.info(f"Email d'invitation envoyé à {invited_email}")
            else:
                logger.warning(f"Échec de l'envoi de l'email d'invitation à {invited_email}")
            
            return Response({
                'success': True,
                'invitation_id': invitation.id,
                'invitation_token': invitation.invitation_token,
                'invitation_link': f"http://localhost:8080/invitation/{invitation.invitation_token}",
                'expires_at': invitation.expires_at.isoformat(),
                'email_sent': email_sent,
                'is_resend': is_resend,
                'message': 'Invitation renvoyée avec succès' if is_resend else 'Invitation créée avec succès'
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'invitation: {str(e)}", exc_info=True)
            return Response({
                'error': 'Erreur lors de la création de l\'invitation'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcceptInvitationView(APIView):
    """Vue pour accepter une invitation (et créer/connecter l'utilisateur)"""
    permission_classes = [AllowAny]
    
    def post(self, request, invitation_token):
        try:
            # Récupérer l'invitation
            try:
                invitation = FriendInvitation.objects.get(
                    invitation_token=invitation_token
                )
            except FriendInvitation.DoesNotExist:
                return Response({
                    'error': 'Invitation non trouvée'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Vérifier que l'invitation est valide
            if not invitation.is_valid:
                return Response({
                    'error': 'Cette invitation a expiré'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            data = request.data
            email = data.get('email')
            password = data.get('password')
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            
            # Validation des données
            if not all([email, password, first_name, last_name]):
                return Response({
                    'error': 'Tous les champs sont requis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier que l'email correspond à l'invitation
            if email.lower() != invitation.invited_email.lower():
                return Response({
                    'error': 'L\'email ne correspond pas à l\'invitation'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer ou récupérer l'utilisateur
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'username': email,
                    'email_verified': True,  # Auto-vérifié pour les invitations
                    'is_invited_user': True,  # Marquer comme utilisateur invité
                    'invitation_used': invitation,  # Lier à l'invitation
                }
            )
            
            if created:
                user.set_password(password)
                user.save()
                logger.info(f"Nouvel utilisateur créé via invitation: {email}")
            else:
                # Utilisateur existant, vérifier le mot de passe
                if not user.check_password(password):
                    return Response({
                        'error': 'Mot de passe incorrect'
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Marquer l'utilisateur existant comme invité pour cette session
                if not user.is_invited_user:
                    user.is_invited_user = True
                    user.invitation_used = invitation
                    user.save()
            
            # Marquer l'invitation comme acceptée
            invitation.mark_as_accepted(user)
            
            # Créer le token d'authentification
            token, created = Token.objects.get_or_create(user=user)
            
            # Mettre à jour la dernière connexion
            user.last_login_at = timezone.now()
            user.save()
            
            logger.info(f"Invitation acceptée: {email} pour la réservation {invitation.reservation.id}")
            
            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'invitation': {
                    'id': invitation.id,
                    'reservation_id': invitation.reservation.id,
                    'activity_name': invitation.reservation.activity_name,
                    'reservation_date': invitation.reservation.reservation_date.isoformat(),
                    'inviter_name': invitation.inviter.full_name,
                    'message': invitation.message
                },
                'redirect_to': 'onboarding'  # Redirection vers l'onboarding
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de l'acceptation de l'invitation: {str(e)}", exc_info=True)
            return Response({
                'error': 'Erreur lors de l\'acceptation de l\'invitation'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvitationDetailsView(APIView):
    """Vue pour récupérer les détails d'une invitation"""
    permission_classes = [AllowAny]
    
    def get(self, request, invitation_token):
        try:
            invitation = FriendInvitation.objects.select_related(
                'inviter', 'reservation'
            ).get(invitation_token=invitation_token)
            
            if not invitation.is_valid:
                return Response({
                    'error': 'Cette invitation a expiré'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'invitation': {
                    'id': invitation.id,
                    'invited_email': invitation.invited_email,
                    'message': invitation.message,
                    'expires_at': invitation.expires_at.isoformat(),
                    'inviter': {
                        'name': invitation.inviter.full_name,
                        'first_name': invitation.inviter.first_name
                    },
                    'reservation': {
                        'id': invitation.reservation.id,
                        'activity_name': invitation.reservation.activity_name,
                        'reservation_date': invitation.reservation.reservation_date.isoformat(),
                        'venue_name': invitation.reservation.venue_name,
                        'price_amount': str(invitation.reservation.price_amount)
                    }
                }
            })
            
        except FriendInvitation.DoesNotExist:
            return Response({
                'error': 'Invitation non trouvée'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'invitation: {str(e)}")
            return Response({
                'error': 'Erreur lors de la récupération de l\'invitation'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProcessInvitedUserView(APIView):
    """Vue pour traiter un utilisateur invité après onboarding"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Chercher une invitation acceptée pour cet utilisateur
            try:
                invitation = FriendInvitation.objects.get(
                    invited_user=request.user,
                    status='ACCEPTED'
                )
            except FriendInvitation.DoesNotExist:
                return Response({
                    'error': 'Aucune invitation trouvée pour cet utilisateur'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Vérifier que l'invitation peut encore être utilisée
            if not invitation.can_be_used:
                return Response({
                    'error': 'Cette invitation ne peut plus être utilisée'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer une réservation pour l'invité (même activité, même date)
            original_reservation = invitation.reservation
            
            invited_reservation = Reservation.objects.create(
                user=request.user,
                activity_name=original_reservation.activity_name,
                activity_description=original_reservation.activity_description,
                reservation_date=original_reservation.reservation_date,
                reservation_time=original_reservation.reservation_time,
                venue_name=original_reservation.venue_name,
                venue_address=original_reservation.venue_address,
                price_plan=original_reservation.price_plan,
                price_amount=original_reservation.price_amount,
                currency=original_reservation.currency,
                status='PENDING',  # En attente de paiement
                participants_count=1
            )
            
            # Marquer l'invitation comme utilisée
            invitation.mark_as_used()
            
            logger.info(f"Réservation créée pour l'invité {request.user.email}: {invited_reservation.id}")
            
            return Response({
                'success': True,
                'reservation': {
                    'id': invited_reservation.id,
                    'activity_name': invited_reservation.activity_name,
                    'reservation_date': invited_reservation.reservation_date.isoformat(),
                    'price_amount': str(invited_reservation.price_amount),
                    'status': invited_reservation.status
                },
                'redirect_to': 'payment'
            })
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'utilisateur invité: {str(e)}", exc_info=True)
            return Response({
                'error': 'Erreur lors du traitement de l\'invitation'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserSubscriptionView(APIView):
    """Vue pour gérer les abonnements des utilisateurs"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupère l'abonnement actif de l'utilisateur"""
        try:
            user = request.user
            active_subscription = UserSubscription.get_active_subscription(user)
            
            if active_subscription:
                return Response({
                    'has_subscription': True,
                    'subscription': {
                        'id': active_subscription.id,
                        'type': active_subscription.subscription_type,
                        'type_display': active_subscription.get_subscription_type_display(),
                        'status': active_subscription.status,
                        'start_date': active_subscription.start_date.isoformat(),
                        'end_date': active_subscription.end_date.isoformat(),
                        'days_remaining': active_subscription.days_remaining,
                        'can_make_reservation': active_subscription.can_make_reservation,
                        'reservations_used': active_subscription.reservations_used,
                        'is_test_mode': active_subscription.is_test_mode,
                        'current_reservation_id': active_subscription.current_reservation_id if active_subscription.current_reservation else None
                    }
                })
            else:
                return Response({
                    'has_subscription': False,
                    'subscription': None
                })
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'abonnement: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Crée un nouvel abonnement (mode test ou production)"""
        try:
            subscription_type = request.data.get('subscription_type')
            is_test_mode = request.data.get('is_test_mode', False)
            
            if subscription_type not in ['MONTHLY', 'QUARTERLY', 'SEMESTRIAL']:
                return Response({
                    'error': 'Type d\'abonnement invalide'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier si l'utilisateur a déjà un abonnement actif
            existing_subscription = UserSubscription.get_active_subscription(request.user)
            if existing_subscription:
                return Response({
                    'error': 'Vous avez déjà un abonnement actif',
                    'existing_subscription_id': existing_subscription.id
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculer les dates et prix selon le type
            start_date = timezone.now()
            if subscription_type == 'MONTHLY':
                end_date = start_date + timedelta(days=30)
                price = Decimal('19.99') if not is_test_mode else Decimal('0.01')
            elif subscription_type == 'QUARTERLY':
                end_date = start_date + timedelta(days=90)
                price = Decimal('49.99') if not is_test_mode else Decimal('0.01')
            else:  # SEMESTRIAL
                end_date = start_date + timedelta(days=180)
                price = Decimal('89.99') if not is_test_mode else Decimal('0.01')
            
            # Créer l'abonnement
            subscription = UserSubscription.objects.create(
                user=request.user,
                subscription_type=subscription_type,
                status='ACTIVE',
                start_date=start_date,
                end_date=end_date,
                price_paid=price,
                stripe_subscription_id=f"test_sub_{request.user.id}_{timezone.now().timestamp()}" if is_test_mode else "",
                is_test_mode=is_test_mode
            )
            
            # Mettre à jour le statut de l'utilisateur
            request.user.update_subscription_status()
            
            logger.info(f"Abonnement {subscription_type} créé pour {request.user.email} (test={is_test_mode})")
            
            return Response({
                'success': True,
                'subscription_id': subscription.id,
                'message': f'Abonnement {subscription.get_subscription_type_display()} créé avec succès',
                'end_date': subscription.end_date.isoformat(),
                'is_test_mode': is_test_mode
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'abonnement: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        """Annule l'abonnement actif"""
        try:
            subscription = UserSubscription.get_active_subscription(request.user)
            
            if not subscription:
                return Response({
                    'error': 'Aucun abonnement actif trouvé'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Annuler l'abonnement
            subscription.status = 'CANCELLED'
            subscription.cancelled_at = timezone.now()
            subscription.save()
            
            # Mettre à jour le statut de l'utilisateur
            request.user.update_subscription_status()
            
            logger.info(f"Abonnement annulé pour {request.user.email}")
            
            return Response({
                'success': True,
                'message': 'Abonnement annulé avec succès'
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de l'abonnement: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckSubscriptionStatusView(APIView):
    """Vue pour vérifier le statut d'abonnement et mettre à jour si nécessaire"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Vérifie et met à jour le statut d'abonnement"""
        try:
            user = request.user
            account_type = user.update_subscription_status()
            
            # Vérifier les abonnements expirés
            expired_subscriptions = UserSubscription.objects.filter(
                user=user,
                status='ACTIVE',
                end_date__lt=timezone.now()
            )
            
            for subscription in expired_subscriptions:
                subscription.check_and_update_status()
            
            return Response({
                'account_type': account_type,
                'has_active_subscription': user.has_active_subscription,
                'can_skip_payment': user.can_skip_payment,
                'has_tickets': user.has_available_tickets
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du statut: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateReservationWithSubscriptionView(APIView):
    """Vue pour créer une réservation avec un abonnement actif"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Vérifier que l'utilisateur a un abonnement actif
            user = request.user
            active_subscription = UserSubscription.get_active_subscription(user)
            
            if not active_subscription:
                return Response({
                    'error': 'Aucun abonnement actif trouvé',
                    'require_payment': True
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            if not active_subscription.can_make_reservation:
                return Response({
                    'error': 'Vous avez déjà une réservation en cours avec votre abonnement',
                    'current_reservation_id': active_subscription.current_reservation_id
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Récupérer les données de la réservation
            data = request.data
            
            # Parser la date de réservation
            reservation_date_str = data.get('reservation_date')
            if reservation_date_str:
                from datetime import datetime
                reservation_date = datetime.strptime(reservation_date_str, '%Y-%m-%d').date()
            else:
                return Response({
                    'error': 'Date de réservation requise'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Créer la réservation avec l'abonnement
            reservation = Reservation.objects.create(
                user=user,
                activity_name=data.get('activity_name', ''),
                activity_description=data.get('activity_description', ''),
                reservation_date=reservation_date,
                reservation_time=data.get('reservation_time', '20:00'),
                venue_name=data.get('venue_name', 'Paris'),
                venue_address=data.get('venue_address', ''),
                price_plan='SUBSCRIPTION',  # Marquer comme payé par abonnement
                price_amount=0,  # Pas de montant car payé par abonnement
                currency='EUR',
                stripe_payment_intent_id=f'subscription_{active_subscription.id}',
                participants_count=data.get('participants_count', 1),
                special_requests=data.get('special_requests', ''),
                status='CONFIRMED',  # Directement confirmée
                paid_at=timezone.now()  # Marquer comme payée immédiatement
            )
            
            # Calculer la deadline d'annulation (mardi 23h59 avant le jeudi)
            from datetime import datetime, timedelta
            tuesday_before = reservation_date - timedelta(days=2)
            deadline = datetime.combine(tuesday_before, datetime.min.time().replace(hour=23, minute=59))
            reservation.cancellation_deadline = timezone.make_aware(deadline)
            reservation.save()
            
            # Lier la réservation à l'abonnement
            active_subscription.use_for_reservation(reservation)
            
            logger.info(f"Réservation créée avec abonnement pour {user.email}: {reservation.id}")
            
            return Response({
                'success': True,
                'message': 'Réservation créée avec votre abonnement',
                'reservation': {
                    'id': reservation.id,
                    'activity_name': reservation.activity_name,
                    'reservation_date': reservation.reservation_date.isoformat(),
                    'status': reservation.status,
                    'cancellation_deadline': reservation.cancellation_deadline.isoformat() if reservation.cancellation_deadline else None
                },
                'subscription_info': {
                    'type': active_subscription.get_subscription_type_display(),
                    'days_remaining': active_subscription.days_remaining,
                    'end_date': active_subscription.end_date.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de réservation avec abonnement: {str(e)}")
            return Response({
                'error': 'Erreur lors de la création de la réservation'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
