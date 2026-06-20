#!/bin/bash
# Déploiement automatique sur NAS QNAP
# Usage : bash deploy_nas.sh

NAS_IP="172.20.24.91"
NAS_USER="admin"
NAS_DIR="/share/Container/enreg"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${BLUE}▶ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; exit 1; }

# Docker TCP endpoint QNAP (Container Station écoute sur TCP)
DOCKER_ENV="DOCKER_HOST=tcp://127.0.0.1:2376 DOCKER_TLS_VERIFY=0"

echo ""
echo "=========================================================="
echo "  Déploiement Système Enregistrement → NAS $NAS_IP"
echo "=========================================================="
echo ""
read -s -p "Mot de passe NAS (admin@$NAS_IP) : " NAS_PASS
echo ""
export SSHPASS="$NAS_PASS"
SSH="sshpass -e ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
SCP="sshpass -e scp -o StrictHostKeyChecking=no"
RSYNC="sshpass -e rsync -avz"

# ── 1. Test connexion ────────────────────────────────────────
info "Test connexion SSH..."
$SSH ${NAS_USER}@${NAS_IP} "echo ok" > /dev/null 2>&1 \
    && ok "Connexion SSH établie" \
    || err "Connexion SSH échouée — vérifiez l'IP et le mot de passe"

# ── 2. Créer les dossiers sur le NAS ────────────────────────
info "Création des dossiers sur le NAS..."
$SSH ${NAS_USER}@${NAS_IP} \
    "mkdir -p ${NAS_DIR}/assets ${NAS_DIR}/pgdata" \
    && ok "Dossiers créés" || err "Impossible de créer les dossiers"

# ── 3. Build du frontend en local ───────────────────────────
info "Build du frontend React (local)..."
cd "${PROJECT_DIR}/frontend"
if [ ! -d node_modules ]; then npm ci --silent; fi
npm run build --silent && ok "Frontend buildé" || err "Échec build frontend"
cd "${PROJECT_DIR}"

# ── 4. Copier les fichiers du projet ────────────────────────
info "Transfert des fichiers vers le NAS..."
$RSYNC \
    --exclude='venv/' \
    --exclude='node_modules/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='registrations.db' \
    "${PROJECT_DIR}/" \
    "${NAS_USER}@${NAS_IP}:${NAS_DIR}/" \
    && ok "Fichiers transférés" || err "Échec du transfert rsync"

# ── 5. Permissions et configuration NAS ─────────────────────
info "Configuration sur le NAS..."
$SSH ${NAS_USER}@${NAS_IP} "
    # Rendre pg_entrypoint.sh exécutable
    chmod +x ${NAS_DIR}/pg_entrypoint.sh

    # Copier docker-compose NAS comme docker-compose.yml
    cp ${NAS_DIR}/docker-compose.nas.yml ${NAS_DIR}/docker-compose.yml
" && ok "Configuration OK"

# ── 6. Configurer .env sur le NAS ───────────────────────────
info "Configuration .env sur le NAS..."
$SSH ${NAS_USER}@${NAS_IP} "cat > ${NAS_DIR}/.env" << 'ENVEOF'
DB_HOST=db
DB_PORT=5432
DB_NAME=enregistrement_auto
DB_USER=postgres
DB_PASSWORD=Enreg2024!
SECRET_KEY=nas-secret-$(hostname)-$(date +%Y%m%d)
PLATERECOGNIZER_API_KEY=
ENVEOF
ok ".env configuré"

# ── 7. Vérifier bind mount /var/lib/docker ───────────────────
info "Vérification stockage Docker..."
$SSH ${NAS_USER}@${NAS_IP} "
    if ! mountpoint -q /var/lib/docker 2>/dev/null; then
        echo 'Remontage bind mount /var/lib/docker...'
        mount --bind /share/CACHEDEV1_DATA/Container/docker-data /var/lib/docker || true
    fi
    df -h /var/lib/docker
" && ok "Stockage Docker OK"

# ── 8. Démarrer les containers ──────────────────────────────
info "Démarrage des containers Docker (peut prendre 3-5 min pour le build)..."
$SSH ${NAS_USER}@${NAS_IP} "
    set -e
    export ${DOCKER_ENV}
    cd ${NAS_DIR}

    # Nettoyer les anciens containers
    docker compose down 2>/dev/null || true
    docker rm -f enreg_db enreg_backend enreg_nginx 2>/dev/null || true

    # Build et démarrage
    echo 'Build...'
    docker compose build

    echo 'Démarrage...'
    docker compose up -d
    echo 'Containers lancés'
" && ok "Containers démarrés" || err "Erreur démarrage Docker"

# ── 9. Attendre PostgreSQL ───────────────────────────────────
info "Attente démarrage PostgreSQL (jusqu'à 2 min)..."
READY=0
for i in $(seq 1 24); do
    sleep 5
    STATUS=$($SSH ${NAS_USER}@${NAS_IP} \
        "export ${DOCKER_ENV}; cd ${NAS_DIR}; docker compose exec -T db pg_isready -U postgres 2>/dev/null && echo READY" 2>/dev/null || echo "")
    if echo "$STATUS" | grep -q "READY"; then
        ok "PostgreSQL prêt"
        READY=1
        break
    fi
    printf "  . %ds " $((i*5))
done
echo ""
[ $READY -eq 0 ] && warn "PostgreSQL pas encore prêt — vérifiez les logs"

# ── 10. Migrations Alembic ───────────────────────────────────
if [ $READY -eq 1 ]; then
    info "Migrations base de données..."
    $SSH ${NAS_USER}@${NAS_IP} "
        export ${DOCKER_ENV}
        cd ${NAS_DIR}
        docker compose exec -T backend python3 -m alembic upgrade head 2>&1
    " && ok "Migrations OK" || warn "Migrations : vérifiez manuellement"

    # ── 11. Créer le compte admin ────────────────────────────
    info "Création du compte admin..."
    $SSH ${NAS_USER}@${NAS_IP} "
        export ${DOCKER_ENV}
        cd ${NAS_DIR}
        docker compose exec -T backend python3 -c \"
import sys, os
sys.path.insert(0, '/app')
from backend.database import SessionLocal
from backend.models import Utilisateur, Role
from passlib.context import CryptContext
pwd_ctx = CryptContext(schemes=['bcrypt'])
db = SessionLocal()
try:
    role = db.query(Role).filter_by(nom='admin').first()
    if not role:
        role = Role(nom='admin', permissions='*')
        db.add(role)
        db.commit()
        db.refresh(role)
    existing = db.query(Utilisateur).filter_by(username='admin').first()
    if not existing:
        u = Utilisateur(username='admin',
            password_hash=pwd_ctx.hash('Admin1234!'),
            role_id=role.id)
        db.add(u)
        db.commit()
        print('Admin créé: admin / Admin1234!')
    else:
        print('Admin existe déjà')
finally:
    db.close()
\" 2>&1
    " && ok "Compte admin OK" || warn "Admin : vérifiez manuellement"
fi

# ── 12. Vérification finale ──────────────────────────────────
info "Vérification accès HTTP..."
sleep 5
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://${NAS_IP}/ 2>/dev/null)
HTTP_API=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://${NAS_IP}:8000/api/health 2>/dev/null)

echo ""
echo "=========================================================="
if [ "$HTTP" = "200" ] || [ "$HTTP" = "301" ] || [ "$HTTP" = "302" ]; then
    ok "DÉPLOIEMENT RÉUSSI !"
    echo -e "  ${GREEN}URL :${NC}       http://${NAS_IP}"
    echo -e "  ${GREEN}Login :${NC}     admin"
    echo -e "  ${GREEN}Password :${NC}  Admin1234!"
    open "http://${NAS_IP}" 2>/dev/null || true
elif [ "$HTTP_API" = "200" ]; then
    ok "Backend OK (nginx non accessible)"
    echo -e "  ${GREEN}API :${NC}       http://${NAS_IP}:8000"
    echo -e "  ${GREEN}Login :${NC}     admin"
    echo -e "  ${GREEN}Password :${NC}  Admin1234!"
else
    warn "L'application ne répond pas encore (HTTP: $HTTP, API: $HTTP_API)"
    echo ""
    echo "  Vérifiez les logs avec:"
    echo "  ! ssh admin@${NAS_IP}"
    echo "  export DOCKER_HOST=tcp://127.0.0.1:2376 DOCKER_TLS_VERIFY=0"
    echo "  cd ${NAS_DIR} && docker compose logs --tail=40"
fi
echo "=========================================================="
