#!/usr/bin/env python3
"""
Script de démarrage pour Evenlyf Backend

Ce script s'assure que le serveur démarre en mode développement par défaut,
sauf si explicitement configuré en production.
"""

import os
import sys
import subprocess

def main():
    # Charger les variables du fichier .env
    try:
        from decouple import config
        settings_module = config('DJANGO_SETTINGS_MODULE', default='evenlyf_backend.settings.development')
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
    except ImportError:
        # Fallback si decouple n'est pas disponible
        if not os.environ.get('DJANGO_SETTINGS_MODULE'):
            os.environ['DJANGO_SETTINGS_MODULE'] = 'evenlyf_backend.settings.development'
    
    # Vérifier si on a un .env
    if not os.path.exists('.env'):
        print("⚠️  Fichier .env manquant !")
        print("📋 Copiez env_example.txt vers .env et configurez vos variables")
        print("💡 Commande : cp env_example.txt .env")
        return 1
    
    print(f"🚀 Démarrage du serveur Evenlyf Backend")
    print(f"📁 Mode : {os.environ['DJANGO_SETTINGS_MODULE']}")
    print(f"🔧 Pour changer de mode, utilisez : export DJANGO_SETTINGS_MODULE=...")
    print()
    
    # Arguments par défaut si aucun fourni
    args = sys.argv[1:] if len(sys.argv) > 1 else ['runserver', '0.0.0.0:8000']
    
    # Lancer Django
    try:
        subprocess.run([sys.executable, 'manage.py'] + args, check=True)
    except KeyboardInterrupt:
        print("\n👋 Arrêt du serveur")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du démarrage : {e}")
        return e.returncode

if __name__ == "__main__":
    sys.exit(main()) 