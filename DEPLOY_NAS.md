# Déploiement sur NAS QNAP

## Prérequis
- QNAP avec Container Station installé (Docker)
- Accès SSH au NAS
- Docker disponible (Container Station active)

## Étapes

### 1. Préparer le NAS
```bash
# Sur le NAS via SSH
mkdir -p /share/Container/enreg/assets
mkdir -p /share/Container/enreg/pgdata
```

### 2. Builder l'image sur votre Mac
```bash
cd ~/enregistrement_auto
docker build -t enreg_backend:latest .
docker save enreg_backend:latest | gzip > enreg_backend.tar.gz
```

### 3. Transférer sur le NAS
```bash
scp enreg_backend.tar.gz admin@<IP_NAS>:/share/Container/enreg/
scp docker-compose.nas.yml admin@<IP_NAS>:/share/Container/enreg/docker-compose.yml
scp nginx.conf admin@<IP_NAS>:/share/Container/enreg/
scp .env admin@<IP_NAS>:/share/Container/enreg/
```

### 4. Charger l'image et démarrer
```bash
ssh admin@<IP_NAS>
cd /share/Container/enreg
docker load < enreg_backend.tar.gz
docker-compose up -d
```

### 5. Initialiser la base de données
```bash
# Sur le NAS
docker-compose exec backend alembic upgrade head
```

### 6. Créer l'utilisateur admin initial
```bash
docker-compose exec backend python -c "
import psycopg2, bcrypt, os
from dotenv import load_dotenv
load_dotenv('/app/.env')
conn = psycopg2.connect(host='db', port=5432,
    dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'))
cur = conn.cursor()
pw = bcrypt.hashpw(b'Admin1234!', bcrypt.gensalt()).decode()
cur.execute(\"\"\"
    INSERT INTO utilisateurs (username, password_hash, role_id)
    VALUES ('admin', %s, (SELECT id FROM roles WHERE nom='admin'))
    ON CONFLICT (username) DO NOTHING
\"\"\", (pw,))
conn.commit()
print('Compte admin créé : admin / Admin1234!')
"
```

### 7. Accéder à l'application
- **URL locale** : http://<IP_NAS>
- **Login** : admin / Admin1234!

## Configuration .env (à adapter)
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=enregistrement_auto
DB_USER=postgres
DB_PASSWORD=MonMotDePasseSecurise123!
PLATERECOGNIZER_API_KEY=votre_cle_api   # optionnel
SECRET_KEY=une_cle_secrete_longue_et_aleatoire
```

## Mise à jour
```bash
# Rebuilder sur Mac + retransférer
docker build -t enreg_backend:latest .
docker save enreg_backend:latest | gzip > enreg_backend.tar.gz
scp enreg_backend.tar.gz admin@<IP_NAS>:/share/Container/enreg/
ssh admin@<IP_NAS> "cd /share/Container/enreg && docker load < enreg_backend.tar.gz && docker-compose up -d backend && docker-compose exec backend alembic upgrade head"
```

## Lancer les tests
```bash
# En local (nécessite PostgreSQL de test)
createdb enreg_test
DB_NAME=enreg_test alembic upgrade head
DB_NAME=enreg_test pytest tests/ -v --cov=backend
```
