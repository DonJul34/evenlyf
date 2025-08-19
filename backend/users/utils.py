import secrets
import string
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def generate_verification_code():
    """Générer un code de vérification à 6 chiffres"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def send_verification_email(user, code):
    """Envoyer un email de vérification"""
    subject = 'Vérification de votre compte Evenlyf'
    message = f"""
Bonjour {user.first_name},

Bienvenue sur Evenlyf ! 🎉

Votre code de vérification est : {code}

Ce code est valide pendant 10 minutes.

Si vous n'avez pas créé de compte, ignorez cet email.

L'équipe Evenlyf
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False


def send_password_reset_email(user, code):
    """Envoyer un email de réinitialisation de mot de passe"""
    subject = 'Réinitialisation de votre mot de passe Evenlyf'
    message = f"""
Bonjour {user.first_name},

Vous avez demandé la réinitialisation de votre mot de passe.

Votre code de réinitialisation est : {code}

Ce code est valide pendant 15 minutes.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

L'équipe Evenlyf
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False 


def send_friend_invitation_email(invitation):
    """Envoyer un email d'invitation d'ami"""
    inviter = invitation.inviter
    invited_email = invitation.invited_email
    reservation = invitation.reservation
    invitation_link = f"http://localhost:8080/invitation/{invitation.invitation_token}"
    
    subject = f'{inviter.first_name} vous invite à une activité sur Evenlyf ! 🎉'
    
    message = f"""
Bonjour !

{inviter.first_name} {inviter.last_name} vous invite à rejoindre une activité fantastique ! 

🎯 Activité : {reservation.activity_name}
📅 Date : {reservation.reservation_date.strftime('%d/%m/%Y')}
⏰ Heure : {reservation.reservation_time.strftime('%H:%M')}
📍 Lieu : {reservation.venue_name}
     {reservation.venue_address}

💬 Message personnel : "{invitation.message}"

✨ Pourquoi accepter cette invitation ?
Si vous acceptez avant mercredi 0h00, vous aurez automatiquement la même activité que votre ami le jeudi ! 
Plus besoin de passer par la sélection, vous serez directement jumelé ensemble.

👆 Cliquez sur ce lien pour accepter l'invitation :
{invitation_link}

🎯 Le lien vous redirigera automatiquement vers la page de création de compte.
Si vous avez déjà un compte, vous pourrez vous connecter directement.

⚠️ Cette invitation expire le mercredi à 0h00.

Découvrez de nouvelles passions, rencontrez des personnes formidables !

L'équipe Evenlyf 💙
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [invited_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Erreur envoi email d'invitation: {e}")
        return False 