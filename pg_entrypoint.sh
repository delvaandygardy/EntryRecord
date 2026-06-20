#!/bin/sh
# Contournement QNAP kernel: execve() bloqué pour processus non-root dans containers
#
# Solution: LD_PRELOAD=/fake_uid.so (compilé sur le NAS via Alpine gcc)
#   - Intercepte getuid/geteuid → retourne UID 70 (postgres dans Alpine)
#   - Intercepte chown/chmod → NOP (fichiers restent owned root)
#   - initdb et postgres exécutés en root (exec OK), pensent être UID 70
#   - PGDATA doit être owned UID 70 sur l'HOST avant montage (stat().st_uid check)
#
# Prérequis NAS host:
#   chown -R 70:70 /share/Container/enreg/pgdata
#   chmod 700 /share/Container/enreg/pgdata

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
PGDB="${POSTGRES_DB:-postgres}"
PGUSER="${POSTGRES_USER:-postgres}"
PGPASS="${POSTGRES_PASSWORD:-}"
PG_BIN="/usr/local/bin"
FAKEUID="${FAKE_UID_SO:-/fake_uid.so}"

if [ ! -f "$FAKEUID" ]; then
    echo "ERREUR: $FAKEUID manquant - voir commentaire en tête de script"
    exit 1
fi

export LD_PRELOAD="$FAKEUID"

if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Initialisation PostgreSQL dans $PGDATA..."
    "$PG_BIN/initdb" -D "$PGDATA" \
        --auth-local=trust \
        --auth-host=md5 \
        --username="$PGUSER"
fi

# pg_hba.conf
cat > "$PGDATA/pg_hba.conf" << 'HBA'
local   all   all              trust
host    all   all   0.0.0.0/0  md5
host    all   all   ::1/128    md5
HBA

# listen_addresses
if grep -q "^listen_addresses" "$PGDATA/postgresql.conf" 2>/dev/null; then
    sed -i "s/^listen_addresses.*/listen_addresses = '*'/" "$PGDATA/postgresql.conf"
else
    echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"
fi

# Créer la base si différente de postgres
if [ "$PGDB" != "postgres" ] && [ "$PGDB" != "$PGUSER" ]; then
    echo "Création de la base $PGDB..."
    "$PG_BIN/postgres" --single -j -D "$PGDATA" template1 \
        <<< "CREATE DATABASE \"$PGDB\";" 2>/dev/null || true
fi

# Configurer le mot de passe
if [ -n "$PGPASS" ]; then
    "$PG_BIN/postgres" --single -j -D "$PGDATA" template1 \
        <<< "ALTER USER \"$PGUSER\" PASSWORD '$PGPASS';" 2>/dev/null || true
fi

echo "Démarrage PostgreSQL..."
exec "$PG_BIN/postgres" -D "$PGDATA"
