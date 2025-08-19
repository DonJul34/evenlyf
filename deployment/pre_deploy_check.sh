#!/usr/bin/env bash

# =============================================================================
# SCRIPT DE VÉRIFICATION PRÉ-DÉPLOIEMENT EVENLYF
# =============================================================================
# Ce script vérifie que tout est prêt avant le déploiement

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Variables
ERRORS=0
WARNINGS=0

check_failed() {
    ERRORS=$((ERRORS + 1))
}

check_warning() {
    WARNINGS=$((WARNINGS + 1))
}

# =============================================================================
# VÉRIFICATIONS
# =============================================================================

check_os() {
    log_info "Vérification du système d'exploitation..."
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" == "ubuntu" ]] || [[ "$ID" == "debian" ]]; then
            log_success "OS supporté: $PRETTY_NAME"
        else
            log_warning "OS non testé: $PRETTY_NAME (devrait fonctionner)"
            check_warning
        fi
    else
        log_warning "Impossible de détecter l'OS"
        check_warning
    fi
}

check_root() {
    log_info "Vérification des permissions..."
    
    if [[ $EUID -eq 0 ]]; then
        log_success "Exécuté en tant que root"
    else
        log_error "Ce script doit être exécuté avec sudo"
        check_failed
    fi
}

check_files() {
    log_info "Vérification des fichiers du projet..."
    
    required_files=(
        "backend/requirements.txt"
        "backend/manage_env.py"
        "backend/env_example.txt"
        "frontend/package.json"
        "deployment/services/evenlyf-backend.service"
        "deployment/services/evenlyf-frontend.service"
        "deployment/nginx/evenlyf.conf"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_success "Fichier trouvé: $file"
        else
            log_error "Fichier manquant: $file"
            check_failed
        fi
    done
}

check_network() {
    log_info "Vérification de la connectivité réseau..."
    
    if ping -c 1 google.com &> /dev/null; then
        log_success "Connexion Internet active"
    else
        log_error "Pas de connexion Internet"
        check_failed
    fi
}

check_ports() {
    log_info "Vérification des ports..."
    
    ports=(80 443 3000 8000)
    
    for port in "${ports[@]}"; do
        if netstat -tuln | grep ":$port " &> /dev/null; then
            log_warning "Port $port déjà utilisé (sera libéré par l'arrêt de Docker)"
            check_warning
        else
            log_success "Port $port disponible"
        fi
    done
}

check_disk_space() {
    log_info "Vérification de l'espace disque..."
    
    available=$(df / | awk 'NR==2 {print $4}')
    required=2000000  # 2GB en KB
    
    if [[ $available -gt $required ]]; then
        log_success "Espace disque suffisant: $(($available / 1024 / 1024))GB disponibles"
    else
        log_error "Espace disque insuffisant: $(($available / 1024 / 1024))GB disponibles, 2GB requis"
        check_failed
    fi
}

check_existing_services() {
    log_info "Vérification des services existants..."
    
    services=("evenlyf-backend" "evenlyf-frontend")
    
    for service in "${services[@]}"; do
        if systemctl list-unit-files | grep "$service" &> /dev/null; then
            log_warning "Service $service existe déjà (sera remplacé)"
            check_warning
        else
            log_success "Service $service n'existe pas encore"
        fi
    done
}

check_docker() {
    log_info "Vérification de Docker..."
    
    if command -v docker &> /dev/null; then
        if systemctl is-active docker &> /dev/null; then
            log_warning "Docker est actif (sera arrêté)"
            check_warning
        else
            log_success "Docker installé mais inactif"
        fi
        
        # Vérifier s'il y a des conteneurs
        running_containers=$(docker ps -q 2>/dev/null | wc -l)
        if [[ $running_containers -gt 0 ]]; then
            log_warning "$running_containers conteneur(s) en cours d'exécution (seront arrêtés)"
            check_warning
        fi
    else
        log_success "Docker n'est pas installé"
    fi
}

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

main() {
    echo "=========================================="
    echo "    VÉRIFICATION PRÉ-DÉPLOIEMENT EVENLYF"
    echo "=========================================="
    echo
    
    check_os
    check_root
    check_files
    check_network
    check_ports
    check_disk_space
    check_existing_services
    check_docker
    
    echo
    echo "=========================================="
    echo "               RÉSUMÉ"
    echo "=========================================="
    
    if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
        log_success "Toutes les vérifications sont passées! Prêt pour le déploiement."
        echo
        log_info "Pour déployer, exécutez:"
        echo "  sudo ./deployment/deploy.sh"
        exit 0
    elif [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -gt 0 ]]; then
        log_warning "$WARNINGS avertissement(s) trouvé(s). Le déploiement peut continuer."
        echo
        log_info "Pour déployer malgré les avertissements:"
        echo "  sudo ./deployment/deploy.sh"
        exit 0
    else
        log_error "$ERRORS erreur(s) et $WARNINGS avertissement(s) trouvé(s)."
        echo
        log_error "Corrigez les erreurs avant de continuer le déploiement."
        exit 1
    fi
}

# Vérifier si le script est dans le bon répertoire
if [[ ! -f "deployment/deploy.sh" ]]; then
    log_error "Ce script doit être exécuté depuis la racine du projet evenlyf"
    exit 1
fi

main "$@" 