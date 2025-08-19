from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from users.models import Reservation, PersonalityTestResult, UserInterests, OnboardingProgress
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Crée des faux comptes avec des réservations payées pour tester'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Création des faux comptes...'))
        
        # Données de test
        fake_users = [
            {
                'email': 'alice.martin@example.com',
                'first_name': 'Alice',
                'last_name': 'Martin',
                'password': 'password123',
                'personality': {'mbti': 'ENFP', 'disc': 'I'},
                'interests': ['🎵 Musique', '🎭 Théâtre', '📚 Lecture']
            },
            {
                'email': 'bob.durand@example.com',
                'first_name': 'Bob',
                'last_name': 'Durand',
                'password': 'password123',
                'personality': {'mbti': 'ISFJ', 'disc': 'S'},
                'interests': ['🍳 Cuisine', '🌱 Jardinage', '🎨 Art']
            },
            {
                'email': 'claire.bernard@example.com',
                'first_name': 'Claire',
                'last_name': 'Bernard',
                'password': 'password123',
                'personality': {'mbti': 'ENTJ', 'disc': 'D'},
                'interests': ['💼 Business', '🏃‍♂️ Sport', '📈 Finance']
            },
            {
                'email': 'david.petit@example.com',
                'first_name': 'David',
                'last_name': 'Petit',
                'password': 'password123',
                'personality': {'mbti': 'INFP', 'disc': 'C'},
                'interests': ['🎮 Gaming', '🎬 Cinéma', '🍕 Food']
            },
            {
                'email': 'emma.rodriguez@example.com',
                'first_name': 'Emma',
                'last_name': 'Rodriguez',
                'password': 'password123',
                'personality': {'mbti': 'ESTP', 'disc': 'I'},
                'interests': ['🎪 Spectacles', '🍷 Oenologie', '✈️ Voyage']
            },
            {
                'email': 'felix.garcia@example.com',
                'first_name': 'Felix',
                'last_name': 'Garcia',
                'password': 'password123',
                'personality': {'mbti': 'ISTJ', 'disc': 'C'},
                'interests': ['📖 Histoire', '🔬 Sciences', '♟️ Échecs']
            }
        ]
        
        # Dates des prochains jeudis
        today = datetime.now().date()
        next_thursdays = []
        current_date = today
        
        # Trouver les 3 prochains jeudis
        while len(next_thursdays) < 3:
            if current_date.weekday() == 3:  # 3 = Jeudi
                if current_date >= today:
                    next_thursdays.append(current_date)
            current_date += timedelta(days=1)
        
        # Créer les utilisateurs et leurs données
        for user_data in fake_users:
            # Créer l'utilisateur
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={
                    'username': user_data['email'],  # Use email as username
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'email_verified': True,
                    'onboarding_completed': True,
                    'personality_test_completed': True
                }
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(f'✓ Utilisateur créé: {user.email}')
            else:
                self.stdout.write(f'- Utilisateur existe déjà: {user.email}')
            
            # Créer les données d'onboarding
            OnboardingProgress.objects.get_or_create(
                user=user,
                defaults={
                    'current_step': 'COMPLETED',
                    'temp_data': {}
                }
            )
            
            # Créer les résultats de personnalité
            PersonalityTestResult.objects.get_or_create(
                user=user,
                defaults={
                    'mbti_result': user_data['personality']['mbti'],
                    'disc_result': user_data['personality']['disc'],
                    'extraversion_score': random.randint(40, 80),
                    'intuition_score': random.randint(40, 80),
                    'thinking_score': random.randint(40, 80),
                    'judging_score': random.randint(40, 80),
                    'dominance_score': random.randint(40, 80),
                    'influence_score': random.randint(40, 80),
                    'steadiness_score': random.randint(40, 80),
                    'conscientiousness_score': random.randint(40, 80),
                    'completed_at': timezone.now()
                }
            )
            
            # Créer les intérêts
            UserInterests.objects.get_or_create(
                user=user,
                defaults={
                    'selected_interests': user_data['interests']
                }
            )
            
            # Créer une réservation payée pour un jeudi aléatoire
            selected_thursday = random.choice(next_thursdays)
            activities = [
                'Bowling', 'Bar à jeux', 'Karaoké', 'Escape Game', 
                'Laser Game', 'Mini Golf', 'Billard'
            ]
            selected_activity = random.choice(activities)
            
            reservation, created = Reservation.objects.get_or_create(
                user=user,
                reservation_date=selected_thursday,
                defaults={
                    'activity_name': selected_activity,
                    'activity_description': f'Soirée {selected_activity} conviviale',
                    'reservation_time': '20:00',
                    'venue_name': 'Paris',
                    'venue_address': 'Lieu à confirmer',
                    'price_plan': random.choice(['ticket', 'monthly-1', 'monthly-3']),
                    'price_amount': random.choice([8.99, 18.99, 39.99]),
                    'currency': 'EUR',
                    'status': 'CONFIRMED',
                                    'participants_count': 1,
                'paid_at': timezone.now() - timedelta(hours=random.randint(1, 48))
                }
            )
            
            if created:
                self.stdout.write(f'  ✓ Réservation créée: {selected_activity} le {selected_thursday}')
            else:
                self.stdout.write(f'  - Réservation existe déjà pour {user.email}')
        
        self.stdout.write(self.style.SUCCESS('\n📊 Résumé:'))
        self.stdout.write(f'• {len(fake_users)} comptes créés/vérifiés')
        self.stdout.write(f'• Réservations pour les dates: {", ".join(str(d) for d in next_thursdays)}')
        
        self.stdout.write(self.style.SUCCESS('\n🔑 Identifiants de connexion:'))
        for user_data in fake_users:
            self.stdout.write(f'• {user_data["email"]} / {user_data["password"]}')
        
        self.stdout.write(self.style.SUCCESS('\n🌐 URLs:'))
        self.stdout.write('• Interface admin: http://localhost:3000/admin')
        self.stdout.write('• Frontend: http://localhost:3000')
        
        self.stdout.write(self.style.SUCCESS('\nTous les comptes ont des réservations PAYÉES et peuvent être utilisés pour tester les groupes !')) 