#!/bin/bash
# Déploiement : sortie automatique ANPR + type/région/couleur véhicule
set -e

NAS="admin1@172.20.24.90"
BASE="/share/CACHEDEV1_DATA/Container/enreg"
QPKG="/share/CACHEDEV1_DATA/.qpkg/container-station"
DOCKER="DOCKER_HOST=unix:///var/run/system-docker.sock $QPKG/usr/bin/.libs/docker"
COMPOSE="DOCKER_HOST=unix:///var/run/system-docker.sock $QPKG/usr/local/lib/docker/cli-plugins/docker-compose"

echo "=== 1. Copie fichiers backend ==="
scp backend/routers/vehicules.py "${NAS}:${BASE}/backend/routers/vehicules.py"
scp backend/schemas.py            "${NAS}:${BASE}/backend/schemas.py"

echo "=== 2. Copie worker ANPR ==="
scp anpr_worker/main.py          "${NAS}:${BASE}/anpr_worker/main.py"
scp anpr_worker/requirements.txt "${NAS}:${BASE}/anpr_worker/requirements.txt"

echo "=== 3. Migration base de données ==="
ssh "${NAS}" "${DOCKER} exec enreg_db psql -U postgres -d enregistrement_auto -c \"
  ALTER TABLE vehicules ADD COLUMN IF NOT EXISTS type_vehicule TEXT;
  ALTER TABLE vehicules ADD COLUMN IF NOT EXISTS region_plaque TEXT;
  ALTER TABLE vehicules ADD COLUMN IF NOT EXISTS couleur_vehicule TEXT;
  SELECT 'OK: colonnes type_vehicule + region_plaque + couleur_vehicule ajoutées';
\""

echo "=== 4. Redémarrage backend ==="
ssh "${NAS}" "cd ${BASE} && ${COMPOSE} -f docker-compose.yml restart backend"

echo "=== 5. Attente démarrage backend (20s) ==="
sleep 20

echo "=== 6. Vérification API ==="
until curl -sf --max-time 5 http://172.20.24.90:8888/api/health | grep -q '"status":"ok"'; do
  echo "  En attente..."; sleep 5
done
echo "Backend OK !"

echo "=== 7. Build + déploiement frontend ==="
cd frontend && npm run build && cd ..
rsync -avz --delete frontend/dist/ "${NAS}:${BASE}/frontend_dist/"

echo "=== 8. Rebuild + redémarrage worker ANPR ==="
echo "IMPORTANT: assurez-vous que ANTHROPIC_API_KEY est défini dans ${BASE}/.env sur le NAS"
ssh "${NAS}" "cd ${BASE} && ${COMPOSE} -f docker-compose.yml build anpr && ${COMPOSE} -f docker-compose.yml up -d anpr"

echo ""
echo "=== Déploiement terminé ! ==="
echo "App : http://172.20.24.90:8888"
echo ""
echo "NOTE: Si ANTHROPIC_API_KEY n'est pas dans .env, ajoutez-le avec:"
echo "  ssh ${NAS} 'echo ANTHROPIC_API_KEY=sk-ant-... >> ${BASE}/.env'"
