#!/usr/bin/env bash

# =============================================================================
# SCRIPT DE DÉPLOIEMENT EVENLYF - PRODUCTION
# =============================================================================
# Ce script configure les services systemd pour remplacer Docker
# Utilisation: sudo ./deploy.sh

set -e  # Arrêter si erreur
set -u  # Arrêter si variable non définie

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
PROJECT_USER="evenlyf"
PROJECT_DIR="/opt/evenlyf"
SERVICES_DIR="$(pwd)/deployment/services"
NGINX_CONFIG="$(pwd)/deployment/nginx/evenlyf.conf"

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Ce script doit être exécuté en tant que root (sudo)"
        exit 1
    fi
}

# =============================================================================
# ÉTAPE 1: ARRÊTER DOCKER ET NETTOYER
# =============================================================================

stop_docker() {
    log_info "Arrêt des conteneurs Docker..."
    
    if command -v docker &> /dev/null; then
        docker stop $(docker ps -aq) 2>/dev/null || true
        docker rm $(docker ps -aq) 2>/dev/null || true
        systemctl stop docker 2>/dev/null || true
        systemctl disable docker 2>/dev/null || true
        log_success "Docker arrêté et désactivé"
    else
        log_info "Docker n'est pas installé, passage à l'étape suivante"
    fi
}

# =============================================================================
# ÉTAPE 2: CRÉER L'UTILISATEUR ET LES RÉPERTOIRES
# =============================================================================

setup_user_and_dirs() {
    log_info "Configuration de l'utilisateur et des répertoires..."
    
    # Créer l'utilisateur s'il n'existe pas
    if ! id "$PROJECT_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$PROJECT_DIR" "$PROJECT_USER"
        log_success "Utilisateur $PROJECT_USER créé"
    else
        log_info "Utilisateur $PROJECT_USER existe déjà"
    fi
    
    # Créer les répertoires
    mkdir -p "$PROJECT_DIR"/{backend,frontend}
    mkdir -p "$PROJECT_DIR"/backend/{logs,media,staticfiles}
    mkdir -p /var/log/nginx
    
    # Copier les fichiers du projet
    if [[ -d "$(pwd)/backend" ]]; then
        cp -r "$(pwd)/backend"/* "$PROJECT_DIR/backend/"
        log_success "Backend copié"
    fi
    
    if [[ -d "$(pwd)/frontend" ]]; then
        cp -r "$(pwd)/frontend"/* "$PROJECT_DIR/frontend/"
        log_success "Frontend copié"
    fi
    
    # Permissions
    chown -R "$PROJECT_USER:$PROJECT_USER" "$PROJECT_DIR"
    chmod -R 755 "$PROJECT_DIR"
    
    log_success "Utilisateur et répertoires configurés"
}

# =============================================================================
# ÉTAPE 3: INSTALLER LES DÉPENDANCES SYSTÈME
# =============================================================================

install_dependencies() {
    log_info "Installation des dépendances système..."
    
    # Mise à jour du système
    apt update
    
    # Paquets essentiels
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        nodejs \
        npm \
        nginx \
        redis-server \
        postgresql-client \
        certbot \
        python3-certbot-nginx \
        htop \
        curl \
        git \
        unzip
    
    # Installer serve globalement pour le frontend
    npm install -g serve
    
    log_success "Dépendances système installées"
}

# =============================================================================
# ÉTAPE 4: CONFIGURER LE BACKEND
# =============================================================================

setup_backend() {
    log_info "Configuration du backend Django..."
    
    # Aller dans le répertoire backend
    cd "$PROJECT_DIR/backend"
    
    # Créer l'environnement virtuel
    sudo -u "$PROJECT_USER" python3 -m venv venv
    
    # Installer les dépendances Python
    sudo -u "$PROJECT_USER" venv/bin/pip install --upgrade pip
    sudo -u "$PROJECT_USER" venv/bin/pip install -r requirements.txt
    
    # Vérifier que le fichier .env existe
    if [[ ! -f .env ]]; then
        log_warning "Fichier .env manquant! Copie depuis env_example.txt"
        if [[ -f env_example.txt ]]; then
            sudo -u "$PROJECT_USER" cp env_example.txt .env
            log_warning "IMPORTANT: Configurez le fichier .env avec vos vraies clés!"
        else
            log_error "Fichier env_example.txt manquant!"
            exit 1
        fi
    fi
    
    # Migrations Django
    sudo -u "$PROJECT_USER" venv/bin/python manage_env.py migrate
    
    # Collecter les fichiers statiques
    sudo -u "$PROJECT_USER" venv/bin/python manage_env.py collectstatic --noinput
    
    log_success "Backend Django configuré"
}

# =============================================================================
# ÉTAPE 5: CONFIGURER LE FRONTEND
# =============================================================================

setup_frontend() {
    log_info "Configuration du frontend React..."
    
    cd "$PROJECT_DIR/frontend"
    
    # Installer les dépendances
    sudo -u "$PROJECT_USER" npm install
    
    # Build de production
    sudo -u "$PROJECT_USER" npm run build
    
    log_success "Frontend React configuré"
}

# =============================================================================
# ÉTAPE 6: CONFIGURER LES SERVICES SYSTEMD
# =============================================================================

setup_systemd_services() {
    log_info "Configuration des services systemd..."
    
    # Copier les fichiers de service
    for service_file in "$SERVICES_DIR"/*.service; do
        if [[ -f "$service_file" ]]; then
            service_name=$(basename "$service_file")
            cp "$service_file" "/etc/systemd/system/"
            log_info "Service $service_name copié"
        fi
    done
    
    # Recharger systemd
    systemctl daemon-reload
    
    # Activer et démarrer les services
    services=("evenlyf-backend" "evenlyf-frontend")
    
    for service in "${services[@]}"; do
        systemctl enable "$service"
        systemctl start "$service"
        
        # Vérifier le statut
        if systemctl is-active --quiet "$service"; then
            log_success "Service $service démarré avec succès"
        else
            log_error "Échec du démarrage du service $service"
            systemctl status "$service" --no-pager
        fi
    done
}

# =============================================================================
# ÉTAPE 7: CONFIGURER NGINX
# =============================================================================

setup_nginx() {
    log_info "Configuration de Nginx..."
    
    # Copier la configuration
    cp "$NGINX_CONFIG" /etc/nginx/sites-available/evenlyf.conf
    
    # Créer le lien symbolique
    ln -sf /etc/nginx/sites-available/evenlyf.conf /etc/nginx/sites-enabled/
    
    # Supprimer la configuration par défaut
    rm -f /etc/nginx/sites-enabled/default
    
    # Tester la configuration
    if nginx -t; then
        log_success "Configuration Nginx valide"
        systemctl restart nginx
        systemctl enable nginx
        log_success "Nginx redémarré et activé"
    else
        log_error "Configuration Nginx invalide!"
        exit 1
    fi
}

# =============================================================================
# ÉTAPE 8: CONFIGURER SSL (OPTIONNEL)
# =============================================================================

setup_ssl() {
    log_info "Configuration SSL avec Let's Encrypt..."
    
    read -p "Voulez-vous configurer SSL avec Let's Encrypt? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        certbot --nginx -d evenlyf.com -d www.evenlyf.com --non-interactive --agree-tos --email admin@evenlyf.com
        log_success "SSL configuré avec Let's Encrypt"
    else
        log_info "SSL ignoré - vous pouvez le configurer plus tard avec: certbot --nginx"
    fi
}

# =============================================================================
# ÉTAPE 9: VÉRIFICATIONS FINALES
# =============================================================================

final_checks() {
    log_info "Vérifications finales..."
    
    # Vérifier les services
    echo "=== STATUS DES SERVICES ==="
    systemctl status evenlyf-backend --no-pager -l
    echo
    systemctl status evenlyf-frontend --no-pager -l
    echo
    systemctl status nginx --no-pager -l
    echo
    
    # Vérifier les ports
    echo "=== PORTS OUVERTS ==="
    netstat -tlnp | grep -E ":80|:443|:3000|:8000"
    echo
    
    # URLs de test
    log_info "URLs de test:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8000/api/"
    echo "  Admin Django: http://localhost:8000/admin/"
    
    if [[ -f /etc/letsencrypt/live/evenlyf.com/fullchain.pem ]]; then
        echo "  Production: https://evenlyf.com"
    else
        echo "  Production: http://evenlyf.com (SSL non configuré)"
    fi
}

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

main() {
    log_info "=== DÉPLOIEMENT EVENLYF - PRODUCTION ==="
    
    check_root
    
    echo "Ce script va:"
    echo "  1. Arrêter Docker"
    echo "  2. Créer l'utilisateur et répertoires"
    echo "  3. Installer les dépendances"
    echo "  4. Configurer le backend Django"
    echo "  5. Configurer le frontend React"
    echo "  6. Créer les services systemd"
    echo "  7. Configurer Nginx"
    echo "  8. Optionnel: Configurer SSL"
    echo
    
    read -p "Continuer? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Déploiement annulé"
        exit 0
    fi
    
    stop_docker
    setup_user_and_dirs
    install_dependencies
    setup_backend
    setup_frontend
    setup_systemd_services
    setup_nginx
    setup_ssl
    final_checks
    
    log_success "=== DÉPLOIEMENT TERMINÉ ==="
    log_info "N'oubliez pas de configurer votre fichier .env avec vos vraies clés!"
}

# Exécuter le script principal
main "$@" 