#!/usr/bin/env python3
"""
Script de test des connexions pour evenlyf_backend

Ce script teste toutes les connexions et authentifications :
- Azure App pour l'envoi d'emails
- Stripe pour les paiements
- Google OAuth2
- Apple OAuth2
- Base de données
- Redis (Celery)

Usage:
    python test_connections.py
"""

import os
import sys
import django
from django.conf import settings
from django.core.mail import send_mail
from decouple import config
import requests
import json
import redis
import stripe
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evenlyf_backend.settings.development')
django.setup()

def print_separator(title):
    """Affiche un séparateur avec titre"""
    print("\n" + "=" * 60)
    print(f" {title} ")
    print("=" * 60)

def test_database():
    """Test de la connexion à la base de données"""
    print_separator("TEST BASE DE DONNÉES")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        print("✅ Connexion à la base de données : SUCCÈS")
        print(f"   Database: {settings.DATABASES['default']['ENGINE']}")
        return True
    except Exception as e:
        print(f"❌ Connexion à la base de données : ÉCHEC")
        print(f"   Erreur: {e}")
        return False

def test_redis():
    """Test de la connexion Redis pour Celery"""
    print_separator("TEST REDIS (CELERY)")
    try:
        redis_url = config('REDIS_URL', default='redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        print("✅ Connexion Redis : SUCCÈS")
        print(f"   URL: {redis_url}")
        return True
    except Exception as e:
        print(f"❌ Connexion Redis : ÉCHEC")
        print(f"   Erreur: {e}")
        print("   Note: Assurez-vous que Redis est installé et en cours d'exécution")
        return False

def test_azure_email():
    """Test de l'envoi d'email avec Azure App"""
    print_separator("TEST AZURE EMAIL")
    
    # Vérification des variables d'environnement
    azure_user = config('AZURE_EMAIL_HOST_USER', default='')
    azure_password = config('AZURE_EMAIL_HOST_PASSWORD', default='')
    azure_tenant = config('AZURE_TENANT_ID', default='')
    azure_client_id = config('AZURE_CLIENT_ID', default='')
    
    if not all([azure_user, azure_password, azure_tenant, azure_client_id]):
        print("❌ Configuration Azure Email : INCOMPLÈTE")
        print("   Variables manquantes :")
        if not azure_user: print("   - AZURE_EMAIL_HOST_USER")
        if not azure_password: print("   - AZURE_EMAIL_HOST_PASSWORD")
        if not azure_tenant: print("   - AZURE_TENANT_ID")
        if not azure_client_id: print("   - AZURE_CLIENT_ID")
        return False
    
    try:
        # En développement, les emails sont affichés dans la console
        if settings.DEBUG:
            print("ℹ️  Mode développement détecté")
            print("   Les emails sont affichés dans la console (pas d'envoi réel)")
            send_mail(
                'Test Email - Evenlyf',
                'Ceci est un email de test depuis evenlyf_backend.',
                settings.DEFAULT_FROM_EMAIL,
                ['test@example.com'],
                fail_silently=False,
            )
            print("✅ Test d'envoi d'email : SUCCÈS (console)")
        else:
            # En production, test d'envoi réel
            send_mail(
                'Test Email - Evenlyf Production',
                'Ceci est un email de test depuis evenlyf_backend en production.',
                settings.DEFAULT_FROM_EMAIL,
                [azure_user],  # Envoyer à l'adresse de l'expéditeur
                fail_silently=False,
            )
            print("✅ Test d'envoi d'email Azure : SUCCÈS")
        
        print(f"   From: {settings.DEFAULT_FROM_EMAIL}")
        print(f"   Azure User: {azure_user}")
        print(f"   Tenant ID: {azure_tenant}")
        print(f"   Client ID: {azure_client_id}")
        return True
        
    except Exception as e:
        print(f"❌ Test d'envoi d'email Azure : ÉCHEC")
        print(f"   Erreur: {e}")
        return False

def test_stripe():
    """Test de la configuration Stripe"""
    print_separator("TEST STRIPE")
    
    stripe_secret = config('STRIPE_SECRET_KEY', default='')
    stripe_public = config('STRIPE_PUBLISHABLE_KEY', default='')
    stripe_webhook = config('STRIPE_WEBHOOK_SECRET', default='')
    
    if not stripe_secret:
        print("❌ Configuration Stripe : STRIPE_SECRET_KEY manquante")
        return False
    
    try:
        stripe.api_key = stripe_secret
        
        # Test de récupération du compte Stripe
        account = stripe.Account.retrieve()
        
        print("✅ Connexion Stripe : SUCCÈS")
        print(f"   Account ID: {account.id}")
        print(f"   Country: {account.country}")
        print(f"   Currency: {account.default_currency}")
        print(f"   Mode: {'Test' if 'test' in stripe_secret else 'Production'}")
        print(f"   Public Key: {stripe_public[:20]}..." if stripe_public else "   Public Key: Non configurée")
        print(f"   Webhook Secret: {'Configuré' if stripe_webhook else 'Non configuré'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connexion Stripe : ÉCHEC")
        print(f"   Erreur: {e}")
        return False

def test_google_oauth():
    """Test de la configuration Google OAuth2"""
    print_separator("TEST GOOGLE OAUTH2")
    
    google_client_id = config('GOOGLE_OAUTH2_CLIENT_ID', default='')
    google_client_secret = config('GOOGLE_OAUTH2_CLIENT_SECRET', default='')
    
    if not all([google_client_id, google_client_secret]):
        print("❌ Configuration Google OAuth2 : INCOMPLÈTE")
        if not google_client_id: print("   - GOOGLE_OAUTH2_CLIENT_ID manquante")
        if not google_client_secret: print("   - GOOGLE_OAUTH2_CLIENT_SECRET manquante")
        return False
    
    # Vérification du fichier de credentials
    credentials_file = config('GOOGLE_CREDENTIALS_FILE', default='')
    if credentials_file and os.path.exists(credentials_file):
        try:
            with open(credentials_file, 'r') as f:
                creds = json.load(f)
            print(f"✅ Fichier de credentials Google trouvé : {credentials_file}")
            print(f"   Project ID: {creds.get('web', {}).get('project_id', 'N/A')}")
        except Exception as e:
            print(f"⚠️  Erreur lecture fichier credentials : {e}")
    
    try:
        # Test basique de validation du client ID
        # (pas de vraie authentification sans interaction utilisateur)
        print("✅ Configuration Google OAuth2 : VALIDE")
        print(f"   Client ID: {google_client_id[:20]}...")
        print(f"   Client Secret: {'Configuré' if google_client_secret else 'Non configuré'}")
        
        # Vérification de la configuration dans Django settings
        google_config = settings.SOCIALACCOUNT_PROVIDERS.get('google', {})
        if google_config:
            print("   Django Allauth: Configuré")
            scopes = google_config.get('SCOPE', [])
            print(f"   Scopes: {', '.join(scopes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration Google OAuth2 : ÉCHEC")
        print(f"   Erreur: {e}")
        return False

def test_apple_oauth():
    """Test de la configuration Apple OAuth2"""
    print_separator("TEST APPLE OAUTH2")
    
    apple_client_id = config('APPLE_OAUTH2_CLIENT_ID', default='')
    apple_client_secret = config('APPLE_OAUTH2_CLIENT_SECRET', default='')
    apple_key_id = config('APPLE_OAUTH2_KEY_ID', default='')
    apple_team_id = config('APPLE_OAUTH2_TEAM_ID', default='')
    
    if not all([apple_client_id, apple_key_id, apple_team_id]):
        print("❌ Configuration Apple OAuth2 : INCOMPLÈTE")
        if not apple_client_id: print("   - APPLE_OAUTH2_CLIENT_ID manquante")
        if not apple_key_id: print("   - APPLE_OAUTH2_KEY_ID manquante")
        if not apple_team_id: print("   - APPLE_OAUTH2_TEAM_ID manquante")
        return False
    
    # Vérification du fichier de clé Apple
    apple_key_file = config('APPLE_KEY_FILE', default='')
    if apple_key_file and os.path.exists(apple_key_file):
        print(f"✅ Fichier de clé Apple trouvé : {apple_key_file}")
        try:
            with open(apple_key_file, 'r') as f:
                key_content = f.read()
            if 'BEGIN PRIVATE KEY' in key_content:
                print("   Format de clé: Valide")
            else:
                print("   ⚠️  Format de clé: Invalide")
        except Exception as e:
            print(f"   ⚠️  Erreur lecture fichier clé : {e}")
    else:
        print(f"⚠️  Fichier de clé Apple non trouvé : {apple_key_file}")
    
    try:
        print("✅ Configuration Apple OAuth2 : VALIDE")
        print(f"   Client ID: {apple_client_id}")
        print(f"   Key ID: {apple_key_id}")
        print(f"   Team ID: {apple_team_id}")
        
        # Vérification de la configuration dans Django settings
        apple_config = settings.SOCIALACCOUNT_PROVIDERS.get('apple', {})
        if apple_config:
            print("   Django Allauth: Configuré")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration Apple OAuth2 : ÉCHEC")
        print(f"   Erreur: {e}")
        return False

def test_django_settings():
    """Test de la configuration Django"""
    print_separator("TEST CONFIGURATION DJANGO")
    
    try:
        print("✅ Configuration Django : CHARGÉE")
        print(f"   Settings Module: {os.environ.get('DJANGO_SETTINGS_MODULE', 'default')}")
        print(f"   Debug Mode: {settings.DEBUG}")
        print(f"   Secret Key: {'Configurée' if settings.SECRET_KEY != 'django-insecure-change-me-in-production' else 'DÉFAUT (À CHANGER)'}")
        print(f"   Allowed Hosts: {settings.ALLOWED_HOSTS}")
        print(f"   Time Zone: {settings.TIME_ZONE}")
        print(f"   Language: {settings.LANGUAGE_CODE}")
        
        # Vérification des apps installées
        critical_apps = ['rest_framework', 'corsheaders', 'allauth', 'oauth2_provider']
        missing_apps = [app for app in critical_apps if app not in settings.INSTALLED_APPS]
        
        if missing_apps:
            print(f"   ⚠️  Apps manquantes : {', '.join(missing_apps)}")
        else:
            print("   Apps critiques : Toutes installées")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration Django : ÉCHEC")
        print(f"   Erreur: {e}")
        return False

def main():
    """Fonction principale qui exécute tous les tests"""
    print("🔧 EVENLYF BACKEND - TEST DES CONNEXIONS")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Exécution de tous les tests
    results['django'] = test_django_settings()
    results['database'] = test_database()
    results['redis'] = test_redis()
    results['azure_email'] = test_azure_email()
    results['stripe'] = test_stripe()
    results['google'] = test_google_oauth()
    results['apple'] = test_apple_oauth()
    
    # Résumé final
    print_separator("RÉSUMÉ DES TESTS")
    
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    for service, result in results.items():
        status = "✅ SUCCÈS" if result else "❌ ÉCHEC"
        print(f"{service.upper():15} : {status}")
    
    print(f"\nRésultat global: {success_count}/{total_count} tests réussis")
    
    if success_count == total_count:
        print("🎉 Tous les tests sont passés avec succès !")
        return 0
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez la configuration.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 