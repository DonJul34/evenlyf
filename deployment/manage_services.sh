#!/usr/bin/env bash

# =============================================================================
# SCRIPT DE GESTION DES SERVICES EVENLYF
# =============================================================================
# Utilisation: ./manage_services.sh [start|stop|restart|status|logs]

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Services
SERVICES=("evenlyf-backend" "evenlyf-frontend" "nginx")

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour démarrer les services
start_services() {
    log_info "Démarrage des services evenlyf..."
    
    for service in "${SERVICES[@]}"; do
        echo "Démarrage de $service..."
        systemctl start "$service"
        
        if systemctl is-active --quiet "$service"; then
            log_success "$service démarré"
        else
            log_error "Échec du démarrage de $service"
        fi
    done
}

# Fonction pour arrêter les services
stop_services() {
    log_info "Arrêt des services evenlyf..."
    
    for service in "${SERVICES[@]}"; do
        echo "Arrêt de $service..."
        systemctl stop "$service"
        log_success "$service arrêté"
    done
}

# Fonction pour redémarrer les services
restart_services() {
    log_info "Redémarrage des services evenlyf..."
    
    for service in "${SERVICES[@]}"; do
        echo "Redémarrage de $service..."
        systemctl restart "$service"
        
        if systemctl is-active --quiet "$service"; then
            log_success "$service redémarré"
        else
            log_error "Échec du redémarrage de $service"
        fi
    done
}

# Fonction pour vérifier le statut
check_status() {
    log_info "Statut des services evenlyf..."
    
    for service in "${SERVICES[@]}"; do
        echo "=== $service ==="
        systemctl status "$service" --no-pager -l
        echo
    done
    
    # Vérifier les ports
    echo "=== PORTS UTILISÉS ==="
    netstat -tlnp | grep -E ":80|:443|:3000|:8000" || echo "Aucun port trouvé"
    echo
    
    # URLs de test
    echo "=== URLS DE TEST ==="
    echo "Frontend: http://localhost:3000"
    echo "Backend API: http://localhost:8000/api/"
    echo "Admin: http://localhost:8000/admin/"
    echo "Production: https://evenlyf.com"
}

# Fonction pour voir les logs
show_logs() {
    log_info "Logs des services evenlyf..."
    
    if [[ -n "${2:-}" ]]; then
        # Log d'un service spécifique
        service="evenlyf-$2"
        echo "=== Logs de $service ==="
        journalctl -u "$service" -f --no-pager
    else
        # Logs de tous les services
        for service in "${SERVICES[@]}"; do
            echo "=== Logs récents de $service ==="
            journalctl -u "$service" --no-pager -n 20
            echo
        done
    fi
}

# Fonction pour mettre à jour le code
update_code() {
    log_info "Mise à jour du code..."
    
    # Arrêter les services
    stop_services
    
    # Mettre à jour le backend
    cd /opt/evenlyf/backend
    sudo -u evenlyf git pull origin main
    sudo -u evenlyf venv/bin/pip install -r requirements.txt
    sudo -u evenlyf venv/bin/python manage_env.py migrate
    sudo -u evenlyf venv/bin/python manage_env.py collectstatic --noinput
    
    # Mettre à jour le frontend
    cd /opt/evenlyf/frontend
    sudo -u evenlyf git pull origin main
    sudo -u evenlyf npm install
    sudo -u evenlyf npm run build
    
    # Redémarrer les services
    start_services
    
    log_success "Code mis à jour et services redémarrés"
}

# Fonction d'aide
show_help() {
    echo "Utilisation: $0 [commande] [service]"
    echo
    echo "Commandes disponibles:"
    echo "  start     - Démarrer tous les services"
    echo "  stop      - Arrêter tous les services"
    echo "  restart   - Redémarrer tous les services"
    echo "  status    - Afficher le statut des services"
    echo "  logs      - Afficher les logs (optionnel: spécifier backend|frontend)"
    echo "  update    - Mettre à jour le code et redémarrer"
    echo "  help      - Afficher cette aide"
    echo
    echo "Exemples:"
    echo "  $0 start"
    echo "  $0 logs backend"
    echo "  $0 restart"
}

# Fonction principale
main() {
    case "${1:-}" in
        "start")
            start_services
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "status")
            check_status
            ;;
        "logs")
            show_logs "$@"
            ;;
        "update")
            update_code
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        "")
            log_error "Aucune commande spécifiée"
            show_help
            exit 1
            ;;
        *)
            log_error "Commande inconnue: $1"
            show_help
            exit 1
            ;;
    esac
}

# Vérifier les permissions
if [[ $EUID -ne 0 ]] && [[ "${1:-}" != "help" ]] && [[ "${1:-}" != "--help" ]] && [[ "${1:-}" != "-h" ]]; then
    log_error "Ce script doit être exécuté en tant que root (sudo)"
    exit 1
fi

main "$@" 