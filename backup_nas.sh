#!/bin/sh
# Backup complet du système enregistrement auto — NAS 172.20.24.90
# Usage: sh backup_nas.sh
# Crée: /share/CACHEDEV1_DATA/Container/backups/YYYY-MM-DD_HHMMSS/

QPKG_DIR=/share/CACHEDEV1_DATA/.qpkg/container-station
DOCKER="$QPKG_DIR/usr/bin/.libs/docker"
export DOCKER_HOST=unix:///var/run/system-docker.sock

BACKUP_ROOT=/share/CACHEDEV1_DATA/Container/backups
DATE=$(date +%Y-%m-%d_%H%M%S)
DEST="$BACKUP_ROOT/$DATE"

log() { echo "[$(date +%H:%M:%S)] $*"; }

mkdir -p "$DEST"
log "=== Backup démarré → $DEST ==="

# ── 1. Base de données PostgreSQL ─────────────────────────────────────────────
log "Dump PostgreSQL..."
$DOCKER exec enreg_db pg_dump -U postgres enregistrement_auto \
  > "$DEST/database.sql" 2>/dev/null
if [ $? -eq 0 ]; then
  gzip "$DEST/database.sql"
  log "DB: $(du -sh $DEST/database.sql.gz | cut -f1)"
else
  log "ERREUR: dump PostgreSQL échoué"
fi

# ── 2. Fichiers de configuration ──────────────────────────────────────────────
log "Configs..."
cp /share/CACHEDEV1_DATA/Container/enreg/docker-compose.yml "$DEST/"
cp /share/CACHEDEV1_DATA/Container/enreg/nginx.conf         "$DEST/"
cp /share/CACHEDEV1_DATA/Container/enreg/mediamtx.yml       "$DEST/" 2>/dev/null || true
cp /share/CACHEDEV1_DATA/Container/enreg/start_after_reboot.sh "$DEST/"
cp /share/CACHEDEV1_DATA/Container/enreg/pg_entrypoint.sh   "$DEST/"
# .env sans les vrais mots de passe
grep -v "PASSWORD\|SECRET\|TOKEN\|API_KEY" \
  /share/CACHEDEV1_DATA/Container/enreg/.env > "$DEST/env.template" 2>/dev/null || true

# ── 3. Frontend dist ──────────────────────────────────────────────────────────
log "Frontend dist..."
tar -czf "$DEST/frontend_dist.tar.gz" \
  -C /share/CACHEDEV1_DATA/Container/enreg frontend_dist/ 2>/dev/null
log "Frontend: $(du -sh $DEST/frontend_dist.tar.gz | cut -f1)"

# ── 4. Assets uploadés ────────────────────────────────────────────────────────
if [ -d /share/CACHEDEV1_DATA/Container/enreg/assets ]; then
  ASSET_COUNT=$(find /share/CACHEDEV1_DATA/Container/enreg/assets -type f | wc -l)
  if [ "$ASSET_COUNT" -gt 0 ]; then
    log "Assets ($ASSET_COUNT fichiers)..."
    tar -czf "$DEST/assets.tar.gz" \
      -C /share/CACHEDEV1_DATA/Container/enreg assets/ 2>/dev/null
    log "Assets: $(du -sh $DEST/assets.tar.gz | cut -f1)"
  fi
fi

# ── 5. Récapitulatif ──────────────────────────────────────────────────────────
TOTAL=$(du -sh "$DEST" | cut -f1)
log "=== Backup terminé — Total: $TOTAL ==="
log "Emplacement: $DEST"
ls -lh "$DEST/"

# ── 6. Rotation: garder les 7 derniers backups ────────────────────────────────
cd "$BACKUP_ROOT" && ls -dt */ 2>/dev/null | tail -n +8 | while read old; do
  log "Suppression ancien backup: $old"
  rm -rf "$old"
done
