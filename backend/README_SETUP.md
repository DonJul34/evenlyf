# Evenlyf Backend - Configuration et Setup

## 🚀 Nouvelle Architecture

Le backend Evenlyf a été restructuré pour supporter différents environnements avec des configurations spécialisées :

- **Développement** : Tests locaux avec emails en console
- **Production** : Déploiement Azure avec envoi d'emails réels

## 📁 Structure des Settings

```
backend/evenlyf_backend/
├── settings/
│   ├── __init__.py
│   ├── base.py         # Configuration commune
│   ├── development.py  # Paramètres de développement
│   └── production.py   # Paramètres de production
└── settings.py         # Importeur automatique
```

## 🔧 Configuration Initiale

### 1. Copier le fichier d'environnement

```bash
cd backend/
cp env_example.txt .env
```

### 2. Configurer les variables d'environnement

Éditez le fichier `.env` avec vos vraies valeurs :

```bash
# Variables essentielles à configurer
SECRET_KEY=votre_cle_secrete_django_50_caracteres_minimum
DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.development

# Azure Email (production)
AZURE_TENANT_ID=c66708ef-4611-4722-b403-3dd1e0b73e20
AZURE_CLIENT_ID=f4dbd28e-8c4f-4fdf-9249-675349c9d20d
AZURE_CLIENT_SECRET=votre_secret_azure
AZURE_EMAIL_HOST_USER=support@evenlyf.com
AZURE_EMAIL_HOST_PASSWORD=jfqJ9X4-a5P_/2

# Stripe (vos clés sont déjà dans le fichier exemple)
STRIPE_PUBLISHABLE_KEY=pk_test_51RrF0kPHpBkFAEFI9pEe4laBErt9Vz6efzQs34lbHZUT2WbOrq5TQD87f6AKyp6wuj1W7bUxbUwxdWh6MUgQFCYc00cTFtDsOf
STRIPE_SECRET_KEY=sk_test_51RrF0kPHpBkFAEFIeVCgTiffjfLLm0d4aMk9QcpONZXcglttKlgfkhXpOoGvST3AnzgMSIFsrWeoolYtMhHkTBKt00AgF554tB

# Google/Apple OAuth (à configurer avec vos clés)
GOOGLE_OAUTH2_CLIENT_ID=votre_google_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=votre_google_client_secret
APPLE_OAUTH2_CLIENT_ID=votre_apple_client_id
# ... etc
```

### 3. Vérifier que les fichiers de clés sont présents

Les fichiers suivants doivent être dans le dossier `backend/` :
- `client_secret_1037941969319-t3q2mii9jn2efsjc9dtu35plluofgltk.apps.googleusercontent.com.json`
- `AuthKey_R65DX5A653.p8`

## 🚀 Utilisation avec Make

### Commandes principales

```bash
# Afficher l'aide
make help

# Setup initial complet
make setup

# Lancer en développement
make dev

# Lancer en production
make prod

# Tester toutes les connexions
make test-connections

# Tester spécifiquement Azure Email
make test-azure

# Tester Azure Email vers un email spécifique
make test-azure-email EMAIL=votre@email.com
```

### Commandes utiles

```bash
# Appliquer les migrations
make migrate

# Créer un superutilisateur
make superuser

# Ouvrir un shell Django
make shell

# Nettoyer les fichiers temporaires
make clean

# Lancer Celery
make celery-worker
make celery-beat
```

## 🔧 Utilisation sans Make

### Mode Développement

```bash
cd backend/
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.development
python manage.py runserver
```

### Mode Production

```bash
cd backend/
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.production
python manage.py collectstatic --noinput
python manage.py runserver
```

### Tests de connexions

```bash
# Test complet
python test_connections.py

# Test Azure Email uniquement
python test_azure_email.py votre@email.com
```

## 📧 Configuration Email

### Développement
- Les emails sont affichés dans la console
- Aucune configuration SMTP requise
- Idéal pour les tests

### Production
- Utilise Azure App pour l'envoi SMTP
- Configuration via variables d'environnement Azure
- Envoi réel d'emails

## 🔐 Services Configurés

### Azure App (Email)
- **Tenant ID** : `c66708ef-4611-4722-b403-3dd1e0b73e20`
- **Client ID** : `f4dbd28e-8c4f-4fdf-9249-675349c9d20d`
- **Email** : `support@evenlyf.com`
- **SMTP** : `smtp-mail.outlook.com:587`

### Stripe (Paiements)
- Clés de test configurées
- Webhook endpoint : `https://evenlyf.com/stripe/webhook`

### Google OAuth2
- Fichier de configuration : `client_secret_*.json`
- Scopes : profile, email

### Apple OAuth2
- Fichier de clé : `AuthKey_*.p8`
- Configuration Team ID, Key ID, Client ID

## 🧪 Scripts de Test

### `test_connections.py`
Script complet qui teste :
- ✅ Configuration Django
- ✅ Base de données
- ✅ Redis (Celery)
- ✅ Azure Email
- ✅ Stripe
- ✅ Google OAuth2
- ✅ Apple OAuth2

### `test_azure_email.py`
Script spécialisé Azure qui teste :
- ✅ Connexion SMTP directe
- ✅ Envoi d'email direct
- ✅ Envoi d'email via Django
- 📧 Email de test HTML/texte

## 🚨 Résolution de Problèmes

### Erreur : "Module settings not found"
```bash
export DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.development
```

### Erreur : "Azure authentication failed"
Vérifiez :
- `AZURE_EMAIL_HOST_PASSWORD` correctement configuré
- Le compte `support@evenlyf.com` est bien activé
- Les permissions Azure App sont correctes

### Erreur : "Stripe authentication failed"
Vérifiez :
- `STRIPE_SECRET_KEY` commence par `sk_test_` ou `sk_live_`
- La clé n'est pas expirée
- Les permissions Stripe sont correctes

### Erreur : "Redis connection failed"
```bash
# Installer Redis (Ubuntu/Debian)
sudo apt-get install redis-server
sudo systemctl start redis-server

# Ou avec Docker
docker run -d -p 6379:6379 redis:alpine
```

## 📝 Variables d'Environnement Importantes

| Variable | Développement | Production | Description |
|----------|---------------|------------|-------------|
| `DJANGO_SETTINGS_MODULE` | `...development` | `...production` | Module de settings |
| `DEBUG` | `True` | `False` | Mode debug |
| `SECRET_KEY` | Obligatoire | Obligatoire | Clé secrète Django |
| `AZURE_EMAIL_HOST_PASSWORD` | Optionnel | Obligatoire | Mot de passe Azure |
| `STRIPE_SECRET_KEY` | Test | Production | Clé secrète Stripe |
| `DATABASE_URL` | SQLite | PostgreSQL | URL base de données |

## 🌐 Déploiement Production

### Azure App Service

1. **Variables d'environnement** :
```bash
DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.production
SECRET_KEY=votre_cle_production_securisee
DATABASE_URL=postgresql://user:pass@host:port/dbname
# + toutes les variables Azure, Stripe, etc.
```

2. **Commandes de déploiement** :
```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

### Vérification Déploiement

```bash
# Tester toutes les connexions en production
make test-connections

# Tester spécifiquement l'envoi d'emails
make test-azure-email EMAIL=admin@evenlyf.com
```

## 📞 Support

Pour toute question ou problème :
1. Vérifiez les logs : `make logs` ou `tail -f debug.log`
2. Lancez les tests : `make test-connections`
3. Vérifiez la configuration : `make check-env`

Les scripts de test fournissent des diagnostics détaillés pour identifier rapidement les problèmes de configuration. 