# 🔧 Solution : Problème DJANGO_SETTINGS_MODULE

## ❌ Problème Rencontré

```bash
python manage.py runserver
CommandError: You must set settings.ALLOWED_HOSTS if DEBUG is False.
```

**Cause** : Django ne charge pas automatiquement les variables du fichier `.env`, notamment `DJANGO_SETTINGS_MODULE`.

## ✅ Solutions Disponibles

### Solution 1 : Utiliser `manage_env.py` (RECOMMANDÉ)

```bash
# Au lieu de :
python manage.py runserver

# Utilisez :
python manage_env.py runserver
```

**Avantages** :
- ✅ Charge automatiquement les variables du `.env`
- ✅ Fonctionne exactement comme `manage.py`
- ✅ Pas besoin d'exporter des variables manuellement

### Solution 2 : Utiliser `runserver.py`

```bash
python runserver.py
# ou
python runserver.py migrate
# ou
python runserver.py check
```

### Solution 3 : Utiliser le Makefile

```bash
# Développement
make dev

# Production
make prod

# Tests
make test-connections
```

### Solution 4 : Export manuel (temporaire)

```bash
export DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.development
python manage.py runserver
```

## 📋 Configuration dans .env

Votre fichier `.env` contient déjà la bonne configuration :

```bash
DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.development
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,evenlyf.com
```

## 🔄 Mode Production

Pour basculer en production, changez dans `.env` :

```bash
DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.production
DEBUG=False
```

## 🧪 Test de la Configuration

```bash
# Vérifier que tout fonctionne
python manage_env.py check

# Tester toutes les connexions
python test_connections.py

# Tester Azure Email
python test_azure_email.py
```

## 💡 Recommandation

**Utilisez `manage_env.py` pour toutes vos commandes Django** :

```bash
# Migration
python manage_env.py migrate

# Créer superuser
python manage_env.py createsuperuser

# Shell Django
python manage_env.py shell

# Lancer serveur
python manage_env.py runserver

# Tests
python manage_env.py test
```

## 🔧 Alias Bash (Optionnel)

Pour simplifier, ajoutez à votre `~/.bashrc` :

```bash
alias dj="python manage_env.py"
```

Puis :

```bash
dj runserver
dj migrate
dj check
```

## 📁 Structure des Settings

```
backend/evenlyf_backend/
├── settings/
│   ├── base.py         # Configuration commune
│   ├── development.py  # Mode développement (DEBUG=True)
│   └── production.py   # Mode production (DEBUG=False, Azure)
└── settings.py         # Détection automatique
```

## ✨ Avantages de cette Solution

1. **🚀 Simplicité** : Un seul script remplace `manage.py`
2. **🔄 Compatibilité** : Fonctionne avec toutes les commandes Django
3. **⚙️ Automatique** : Charge les variables d'environnement automatiquement
4. **🛡️ Sécurité** : Sépare développement et production
5. **📧 Azure Email** : Configuration intégrée pour la production 