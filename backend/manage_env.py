#!/usr/bin/env python3
"""
Script de lancement manage.py avec chargement automatique des variables d'environnement.

Ce script remplace manage.py et charge automatiquement les variables du fichier .env
avant de démarrer Django.

Usage: python manage_env.py [commandes Django]
"""

import os
import sys

if __name__ == '__main__':
    # Charger les variables d'environnement depuis .env
    try:
        from decouple import config
        settings_module = config('DJANGO_SETTINGS_MODULE', default='evenlyf_backend.settings.development')
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
    except ImportError:
        # Fallback si decouple n'est pas disponible
        os.environ['DJANGO_SETTINGS_MODULE'] = 'evenlyf_backend.settings.development'
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv) 