#!/usr/bin/env python3
"""
Script de test spécialisé pour Azure Email

Ce script teste spécifiquement l'envoi d'emails avec Azure App
et fournit des diagnostics détaillés.

Usage:
    python test_azure_email.py [email_destination]
"""

import os
import sys
import django
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from decouple import config
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'evenlyf_backend.settings.production')
django.setup()

from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings

def test_smtp_connection():
    """Test direct de la connexion SMTP Azure"""
    print("=" * 60)
    print(" TEST CONNEXION SMTP AZURE DIRECTE ")
    print("=" * 60)
    
    # Configuration SMTP Azure
    smtp_server = "smtp-mail.outlook.com"
    smtp_port = 587
    username = config('AZURE_EMAIL_HOST_USER', default='support@evenlyf.com')
    password = config('AZURE_EMAIL_HOST_PASSWORD', default='')
    
    if not password:
        print("❌ AZURE_EMAIL_HOST_PASSWORD non configuré")
        return False
    
    try:
        print(f"Tentative de connexion à {smtp_server}:{smtp_port}")
        print(f"Utilisateur: {username}")
        
        # Création du contexte SSL
        context = ssl.create_default_context()
        
        # Connexion au serveur SMTP
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("✅ Connexion SMTP établie")
            
            # Activation du mode debug pour voir les échanges
            server.set_debuglevel(1)
            
            # Démarrage TLS
            server.starttls(context=context)
            print("✅ TLS activé")
            
            # Authentification
            server.login(username, password)
            print("✅ Authentification réussie")
        
        print("🎉 Test de connexion SMTP : SUCCÈS")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Erreur d'authentification SMTP : {e}")
        print("Vérifiez vos identifiants Azure")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ Erreur SMTP : {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur générale : {e}")
        return False

def send_test_email_direct(to_email):
    """Envoi d'email de test direct via SMTP"""
    print("\n" + "=" * 60)
    print(" ENVOI EMAIL DIRECT VIA SMTP ")
    print("=" * 60)
    
    # Configuration
    smtp_server = "smtp-mail.outlook.com"
    smtp_port = 587
    username = config('AZURE_EMAIL_HOST_USER', default='support@evenlyf.com')
    password = config('AZURE_EMAIL_HOST_PASSWORD', default='')
    
    if not password:
        print("❌ Mot de passe Azure non configuré")
        return False
    
    try:
        # Création du message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Test Email Azure - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        msg['From'] = username
        msg['To'] = to_email
        
        # Corps du message
        text_content = f"""
Bonjour,

Ceci est un email de test envoyé depuis Evenlyf Backend.

Informations du test :
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Serveur SMTP: {smtp_server}
- Port: {smtp_port}
- Expéditeur: {username}
- Destinataire: {to_email}

Si vous recevez cet email, la configuration Azure Email fonctionne correctement !

Cordialement,
L'équipe Evenlyf
"""
        
        html_content = f"""
<html>
  <head></head>
  <body>
    <h2>🎉 Test Email Azure - Evenlyf</h2>
    <p>Bonjour,</p>
    <p>Ceci est un email de test envoyé depuis <strong>Evenlyf Backend</strong>.</p>
    
    <h3>Informations du test :</h3>
    <ul>
        <li><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
        <li><strong>Serveur SMTP:</strong> {smtp_server}</li>
        <li><strong>Port:</strong> {smtp_port}</li>
        <li><strong>Expéditeur:</strong> {username}</li>
        <li><strong>Destinataire:</strong> {to_email}</li>
    </ul>
    
    <p>Si vous recevez cet email, la configuration Azure Email fonctionne correctement ! ✅</p>
    
    <p>Cordialement,<br>
    L'équipe Evenlyf</p>
  </body>
</html>
"""
        
        # Ajout des parties du message
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Envoi de l'email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.send_message(msg)
        
        print(f"✅ Email envoyé avec succès à {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi : {e}")
        return False

def send_test_email_django(to_email):
    """Envoi d'email de test via Django"""
    print("\n" + "=" * 60)
    print(" ENVOI EMAIL VIA DJANGO ")
    print("=" * 60)
    
    try:
        # Configuration Django pour forcer l'utilisation d'Azure
        from django.conf import settings
        
        print("Configuration Django actuelle :")
        print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        print(f"  EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Non défini')}")
        print(f"  EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'Non défini')}")
        print(f"  EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Non défini')}")
        print(f"  EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'Non défini')}")
        print(f"  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # Test avec send_mail simple
        print("\n1. Test avec send_mail() simple...")
        send_mail(
            subject=f'Test Django Simple - {datetime.now().strftime("%H:%M:%S")}',
            message=f'Email de test simple envoyé à {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        print("✅ send_mail() simple : SUCCÈS")
        
        # Test avec EmailMultiAlternatives (HTML)
        print("\n2. Test avec EmailMultiAlternatives() (HTML)...")
        
        text_content = f"""
Test Email Django/Azure - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Cet email confirme que Django peut envoyer des emails via Azure.

Configuration utilisée :
- Backend: {settings.EMAIL_BACKEND}
- Host: {getattr(settings, 'EMAIL_HOST', 'N/A')}
- Port: {getattr(settings, 'EMAIL_PORT', 'N/A')}
- From: {settings.DEFAULT_FROM_EMAIL}
"""
        
        html_content = f"""
<html>
<head></head>
<body>
    <h2>🚀 Test Email Django/Azure</h2>
    <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <p>Cet email confirme que Django peut envoyer des emails via Azure.</p>
    
    <h3>Configuration utilisée :</h3>
    <ul>
        <li><strong>Backend:</strong> {settings.EMAIL_BACKEND}</li>
        <li><strong>Host:</strong> {getattr(settings, 'EMAIL_HOST', 'N/A')}</li>
        <li><strong>Port:</strong> {getattr(settings, 'EMAIL_PORT', 'N/A')}</li>
        <li><strong>From:</strong> {settings.DEFAULT_FROM_EMAIL}</li>
    </ul>
    
    <p style="color: green;">✅ Test réussi !</p>
</body>
</html>
"""
        
        email = EmailMultiAlternatives(
            subject=f'Test Django HTML - {datetime.now().strftime("%H:%M:%S")}',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print("✅ EmailMultiAlternatives() HTML : SUCCÈS")
        
        print(f"\n🎉 Tous les emails Django ont été envoyés à {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Django : {e}")
        return False

def show_azure_config():
    """Affiche la configuration Azure actuelle"""
    print("=" * 60)
    print(" CONFIGURATION AZURE ACTUELLE ")
    print("=" * 60)
    
    config_items = [
        ('AZURE_TENANT_ID', config('AZURE_TENANT_ID', default='')),
        ('AZURE_CLIENT_ID', config('AZURE_CLIENT_ID', default='')),
        ('AZURE_CLIENT_SECRET', config('AZURE_CLIENT_SECRET', default='')),
        ('AZURE_EMAIL_HOST_USER', config('AZURE_EMAIL_HOST_USER', default='')),
        ('AZURE_EMAIL_HOST_PASSWORD', config('AZURE_EMAIL_HOST_PASSWORD', default='')),
        ('DEFAULT_FROM_EMAIL', config('DEFAULT_FROM_EMAIL', default='')),
    ]
    
    for key, value in config_items:
        if 'PASSWORD' in key or 'SECRET' in key:
            display_value = '***masqué***' if value else 'NON CONFIGURÉ'
        else:
            display_value = value if value else 'NON CONFIGURÉ'
        
        status = '✅' if value else '❌'
        print(f"{status} {key:25} : {display_value}")
    
    print(f"\nServeur SMTP: smtp-mail.outlook.com:587")
    print(f"TLS: Activé")

def main():
    """Fonction principale"""
    print("📧 EVENLYF - TEST AZURE EMAIL")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Settings Module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    
    # Récupération de l'email de destination
    if len(sys.argv) > 1:
        to_email = sys.argv[1]
    else:
        to_email = config('AZURE_EMAIL_HOST_USER', default='support@evenlyf.com')
        print(f"ℹ️  Aucun email de destination fourni, utilisation de : {to_email}")
    
    print(f"📨 Email de destination : {to_email}")
    
    # Affichage de la configuration
    show_azure_config()
    
    # Tests
    results = {}
    
    # Test de connexion SMTP
    results['smtp_connection'] = test_smtp_connection()
    
    # Test d'envoi direct
    if results['smtp_connection']:
        results['direct_email'] = send_test_email_direct(to_email)
    else:
        print("\n⏭️  Test d'envoi direct ignoré (connexion SMTP échouée)")
        results['direct_email'] = False
    
    # Test via Django
    results['django_email'] = send_test_email_django(to_email)
    
    # Résumé
    print("\n" + "=" * 60)
    print(" RÉSUMÉ DES TESTS ")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ SUCCÈS" if result else "❌ ÉCHEC"
        print(f"{test_name.replace('_', ' ').upper():20} : {status}")
    
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    print(f"\nRésultat : {success_count}/{total_count} tests réussis")
    
    if success_count == total_count:
        print("🎉 Configuration Azure Email fonctionnelle !")
        print(f"📧 Vérifiez la boîte mail de {to_email}")
        return 0
    else:
        print("⚠️  Problèmes détectés dans la configuration Azure Email")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print(__doc__)
        sys.exit(0)
    
    exit_code = main()
    sys.exit(exit_code)