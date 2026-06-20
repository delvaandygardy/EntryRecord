from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    nom: Optional[str] = None
    prenom: Optional[str] = None
    role_id: int = 3


class UserUpdate(BaseModel):
    email: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    role_id: Optional[int] = None
    actif: Optional[bool] = None
    password: Optional[str] = None


class VehiculeCreate(BaseModel):
    plaque: str
    confidence: Optional[float] = 1.0
    point_entree: str = "Principal"
    notes: Optional[str] = None


class PersonneCreate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    numero_document: Optional[str] = None
    type_document: str = "CNI"
    date_naissance: Optional[str] = None
    nationalite: Optional[str] = None
    date_expiration: Optional[str] = None
    point_entree: str = "Principal"


class EmployeCreate(BaseModel):
    matricule: str
    nom: str
    prenom: str
    poste: Optional[str] = None
    departement: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[str] = None
    date_embauche: Optional[str] = None
    statut: str = "Actif"


class PresenceCreate(BaseModel):
    employe_id: int
    type: str  # ENTREE | SORTIE
    methode: str = "BADGE"
    point_entree: str = "Principal"


class BadgeRequest(BaseModel):
    matricule: str
    point_entree: str = "Principal"


class BlacklistPlaqueCreate(BaseModel):
    plaque: str
    motif: Optional[str] = None
    severite: str = "HAUTE"


class BlacklistPersonneCreate(BaseModel):
    numero_document: str
    nom: Optional[str] = None
    prenom: Optional[str] = None
    motif: Optional[str] = None
    severite: str = "HAUTE"


class AlerteUpdate(BaseModel):
    traitee: bool = True


class CameraCreate(BaseModel):
    nom: str
    url_rtsp: str
    point_entree: str = "Principal"
    actif: bool = True


class ReportRequest(BaseModel):
    format: str = "pdf"   # pdf | excel
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None
    tables: List[str] = ["vehicules", "conducteurs", "pietons", "employes"]
