# Makefile pour Evenlyf Backend
# 
# Usage:
#   make help          - Afficher cette aide
#   make install       - Installer les dépendances
#   make dev           - Lancer en mode développement
#   make prod          - Lancer en mode production
#   make test          - Lancer les tests unitaires
#   make test-connections - Tester toutes les connexions
#   make test-azure    - Tester Azure Email
#   make migrate       - Appliquer les migrations
#   make requirements  - Générer requirements.txt

.PHONY: help install dev prod test test-connections test-azure migrate requirements clean

# Variables
PYTHON = python3
PIP = pip3
VENV = venv
ACTIVATE = source $(VENV)/bin/activate

# Couleurs pour l'affichage
GREEN = \033[92m
BLUE = \033[94m
YELLOW = \033[93m
RED = \033[91m
ENDC = \033[0m

help: ## Afficher cette aide
	@echo "$(BLUE)Evenlyf Backend - Commandes disponibles:$(ENDC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(ENDC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Installer les dépendances
	@echo "$(BLUE)Installation des dépendances...$(ENDC)"
	@if [ ! -d "$(VENV)" ]; then \
		echo "$(YELLOW)Création de l'environnement virtuel...$(ENDC)"; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@$(ACTIVATE) && $(PIP) install --upgrade pip
	@$(ACTIVATE) && $(PIP) install -r requirements.txt
	@echo "$(GREEN)Installation terminée !$(ENDC)"

requirements: ## Générer requirements.txt depuis l'environnement virtuel
	@echo "$(BLUE)Génération de requirements.txt...$(ENDC)"
	@$(ACTIVATE) && $(PIP) freeze > requirements.txt
	@echo "$(GREEN)requirements.txt généré !$(ENDC)"

dev: ## Lancer le serveur en mode développement
	@echo "$(BLUE)Lancement du serveur en mode développement...$(ENDC)"
	@$(ACTIVATE) && $(PYTHON) runserver.py

prod: ## Lancer le serveur en mode production
	@echo "$(BLUE)Lancement du serveur en mode production...$(ENDC)"
	@$(ACTIVATE) && export DJANGO_SETTINGS_MODULE=evenlyf_backend.settings.production && \
	$(PYTHON) manage.py collectstatic --noinput && \
	$(PYTHON) manage.py runserver 0.0.0.0:8000

migrate: ## Appliquer les migrations de base de données
	@echo "$(BLUE)Application des migrations...$(ENDC)"
	@$(ACTIVATE) && $(PYTHON) manage.py makemigrations
	@$(ACTIVATE) && $(PYTHON) manage.py migrate
	@echo "$(GREEN)Migrations appliquées !$(ENDC)"

test: ## Lancer les tests unitaires Django
	@echo "$(BLUE)Lancement des tests unitaires...$(ENDC)"
	@$(ACTIVATE) && $(PYTHON) manage.py test

test-connections: ## Tester toutes les connexions (Azure, Stripe, Google, Apple, etc.)
	@echo "$(BLUE)Test de toutes les connexions...$(ENDC)"
	@$(ACTIVATE) && $(PYTHON) test_connections.py

test-azure: ## Tester spécifiquement Azure Email
	@echo "$(BLUE)Test Azure Email...$(ENDC)"
	@if [ -n "$(EMAIL)" ]; then \
		$(ACTIVATE) && $(PYTHON) test_azure_email.py $(EMAIL); \
	else \
		$(ACTIVATE) && $(PYTHON) test_azure_email.py; \
	fi

test-azure-email: ## Tester Azure Email avec email spécifique (usage: make test-azure-email EMAIL=user@example.com)
	@echo "$(BLUE)Test Azure Email vers $(EMAIL)...$(ENDC)"
	@$(ACTIVATE) && $(PYTHON) test_azure_email.py $(EMAIL)

shell: ## Ouvrir un shell Django
	@$(ACTIVATE) && $(PYTHON) manage.py shell

superuser: ## Créer un superutilisateur
	@$(ACTIVATE) && $(PYTHON) manage.py createsuperuser

clean: ## Nettoyer les fichiers temporaires
	@echo "$(BLUE)Nettoyage des fichiers temporaires...$(ENDC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type f -name "*.log" -delete
	@rm -rf .coverage htmlcov/
	@echo "$(GREEN)Nettoyage terminé !$(ENDC)"

check-env: ## Vérifier les variables d'environnement
	@echo "$(BLUE)Vérification des variables d'environnement...$(ENDC)"
	@if [ ! -f ".env" ]; then \
		echo "$(RED)Fichier .env manquant !$(ENDC)"; \
		echo "$(YELLOW)Copiez env_example.txt vers .env et configurez vos variables$(ENDC)"; \
		exit 1; \
	else \
		echo "$(GREEN)Fichier .env trouvé ✓$(ENDC)"; \
	fi

setup: install check-env migrate ## Installation complète et configuration initiale
	@echo "$(GREEN)🎉 Setup terminé ! Vous pouvez maintenant lancer 'make dev' ou 'make test-connections'$(ENDC)"

celery-worker: ## Lancer un worker Celery
	@echo "$(BLUE)Lancement du worker Celery...$(ENDC)"
	@$(ACTIVATE) && celery -A evenlyf_backend worker --loglevel=info

celery-beat: ## Lancer le scheduler Celery Beat
	@echo "$(BLUE)Lancement du scheduler Celery Beat...$(ENDC)"
	@$(ACTIVATE) && celery -A evenlyf_backend beat --loglevel=info

logs: ## Afficher les logs en temps réel
	@tail -f debug.log

# Alias utiles
run: dev ## Alias pour 'make dev'
start: dev ## Alias pour 'make dev' 