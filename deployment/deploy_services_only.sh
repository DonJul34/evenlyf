#!/usr/bin/env bash

# =============================================================================
# SCRIPT DE DÉPLOIEMENT SERVICES EVENLYF UNIQUEMENT
# =============================================================================
# Ce script configure seulement les services systemd
# Utilisation: sudo ./deploy_services_only.sh

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
PROJECT_USER="evenlyf"
PROJECT_DIR="/opt/evenlyf"
SERVICES_DIR="$(pwd)/deployment/services"
NGINX_CONFIG="$(pwd)/deployment/nginx/evenlyf.conf"

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
# CRÉER L'UTILISATEUR ET RÉPERTOIRES (SI NÉCESSAIRE)
# =============================================================================
setup_directories() {
    log_info "Vérification des répertoires..."
    
    # Créer l'utilisateur s'il n'existe pas
    if ! id "$PROJECT_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$PROJECT_DIR" "$PROJECT_USER"
        log_success "Utilisateur $PROJECT_USER créé"
    else
        log_info "Utilisateur $PROJECT_USER existe déjà"
    fi
    
    # Créer les répertoires nécessaires
    mkdir -p "$PROJECT_DIR"/{backend,frontend}
    mkdir -p "$PROJECT_DIR"/backend/{logs,media,staticfiles}
    mkdir -p /var/log/nginx
    
    # S'assurer que les fichiers du projet sont là
    if [[ -d "$(pwd)/backend" ]]; then
        log_info "Backend trouvé, copie si nécessaire..."
        rsync -av "$(pwd)/backend/" "$PROJECT_DIR/backend/" --exclude='venv' --exclude='__pycache__' --exclude='*.pyc'
        log_success "Backend synchronisé"
    fi
    
    # Pour le frontend, gérer le cas où il pourrait être vide
    if [[ -d "$(pwd)/frontend" ]]; then
        log_info "Frontend trouvé, copie si nécessaire..."
        # Créer un index.html basique si le frontend est vide
        if [[ ! -f "$(pwd)/frontend/package.json" ]]; then
            log_warning "Frontend semble vide, création d'un placeholder..."
            mkdir -p "$PROJECT_DIR/frontend/build"
            echo '<html><body><h1>Frontend React en cours de configuration...</h1></body></html>' > "$PROJECT_DIR/frontend/build/index.html"
        else
            rsync -av "$(pwd)/frontend/" "$PROJECT_DIR/frontend/" --exclude='node_modules' --exclude='build'
        fi
        log_success "Frontend synchronisé"
    fi
    
    # Permissions
    chown -R "$PROJECT_USER:$PROJECT_USER" "$PROJECT_DIR" 2>/dev/null || chown -R "$PROJECT_USER" "$PROJECT_DIR"
    
    log_success "Répertoires configurés"
}

# =============================================================================
# CONFIGURER LES SERVICES SYSTEMD
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
    log_success "Systemd rechargé"
    
    # Activer et démarrer les services
    services=("evenlyf-backend" "evenlyf-frontend")
    
    for service in "${services[@]}"; do
        log_info "Configuration du service $service..."
        
        # Arrêter le service s'il tourne déjà
        systemctl stop "$service" 2>/dev/null || true
        
        # Activer le service
        systemctl enable "$service"
        
        # Démarrer le service
        systemctl start "$service"
        
        # Attendre un peu pour le démarrage
        sleep 2
        
        # Vérifier le statut
        if systemctl is-active --quiet "$service"; then
            log_success "Service $service démarré avec succès"
        else
            log_error "Échec du démarrage du service $service"
            log_info "Logs du service $service:"
            journalctl -u "$service" --no-pager -n 10
        fi
    done
}

# =============================================================================
# CONFIGURER NGINX
# =============================================================================
setup_nginx() {
    log_info "Configuration de Nginx..."
    
    # Installer nginx si pas déjà fait
    if ! command -v nginx &> /dev/null; then
        log_info "Installation de Nginx..."
        apt update
        apt install -y nginx
    fi
    
    # Copier la configuration
    if [[ -f "$NGINX_CONFIG" ]]; then
        cp "$NGINX_CONFIG" /etc/nginx/sites-available/evenlyf.conf
        
        # Créer le lien symbolique
        ln -sf /etc/nginx/sites-available/evenlyf.conf /etc/nginx/sites-enabled/
        
        # Supprimer la configuration par défaut
        rm -f /etc/nginx/sites-enabled/default
        
        # Tester la configuration
        if nginx -t; then
            log_success "Configuration Nginx valide"
            systemctl enable nginx
            systemctl restart nginx
            log_success "Nginx redémarré et activé"
        else
            log_error "Configuration Nginx invalide!"
            nginx -t
        fi
    else
        log_warning "Fichier de configuration Nginx non trouvé, ignoré"
    fi
}

# =============================================================================
# VÉRIFICATIONS FINALES
# =============================================================================
final_checks() {
    log_info "Vérifications finales..."
    
    echo "=== STATUS DES SERVICES ==="
    for service in "evenlyf-backend" "evenlyf-frontend" "nginx"; do
        echo "--- $service ---"
        systemctl status "$service" --no-pager -l || true
        echo
    done
    
    # Vérifier les ports
    echo "=== PORTS OUVERTS ==="
    ss -tlnp | grep -E ":80|:443|:3000|:8000" || echo "Aucun port trouvé"
    echo
    
    # URLs de test
    log_info "URLs de test:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8000/api/"
    echo "  Admin Django: http://localhost:8000/admin/"
    echo "  Production: http://$(hostname -I | awk '{print $1}')"
}

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================
main() {
    log_info "=== DÉPLOIEMENT SERVICES EVENLYF ==="
    
    check_root
    
    echo "Ce script va:"
    echo "  1. Vérifier les répertoires"
    echo "  2. Configurer les services systemd"
    echo "  3. Configurer Nginx"
    echo "  4. Démarrer tous les services"
    echo
    
    read -p "Continuer? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Déploiement annulé"
        exit 0
    fi
    
    setup_directories
    setup_systemd_services
    setup_nginx
    final_checks
    
    log_success "=== DÉPLOIEMENT SERVICES TERMINÉ ==="
    log_info "Utilisez './deployment/manage_services.sh status' pour vérifier les services"
}

# Vérifier si le script est dans le bon répertoire
if [[ ! -f "deployment/services/evenlyf-backend.service" ]]; then
    log_error "Ce script doit être exécuté depuis la racine du projet (où se trouve le dossier deployment/)"
    exit 1
fi

main "$@" 