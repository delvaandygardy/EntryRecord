from fastapi import APIRouter, Depends, Query
from backend.deps import get_db, get_current_user
from backend.schemas import AlerteUpdate
import psycopg2.extras
from datetime import datetime

router = APIRouter(prefix="/api/alertes", tags=["Alertes"])


def _s(rows):
    for r in rows:
        for k in ("timestamp", "traitee_le"):
            if isinstance(r.get(k), datetime):
                r[k] = r[k].isoformat()
    return rows


@router.get("")
def list_alertes(traitee: bool = Query(False), limit: int = 100,
                 conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM alertes WHERE traitee=%s ORDER BY timestamp DESC LIMIT %s",
                (traitee, limit))
    return _s([dict(r) for r in cur.fetchall()])


@router.get("/stats")
def alertes_stats(conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM alertes WHERE traitee=FALSE")
    non_traitees = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM alertes WHERE traitee=FALSE AND severite='CRITIQUE'")
    critiques = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM alertes WHERE timestamp::date=CURRENT_DATE")
    aujourd_hui = cur.fetchone()[0]
    return {"non_traitees": non_traitees, "critiques": critiques, "aujourd_hui": aujourd_hui}


@router.patch("/{aid}")
def update_alerte(aid: int, body: AlerteUpdate, conn=Depends(get_db),
                  user=Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("""UPDATE alertes SET traitee=%s, traitee_par=%s,
                   traitee_le=CASE WHEN %s THEN NOW() ELSE NULL END WHERE id=%s""",
                (body.traitee, user["id"], body.traitee, aid))
    conn.commit()
    return {"ok": True}


@router.delete("/{aid}", status_code=204)
def delete_alerte(aid: int, conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor()
    cur.execute("DELETE FROM alertes WHERE id=%s", (aid,))
    conn.commit()
