from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import httpx

from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Profile as ProfileModel

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ProfileService API", version="1.0.0")

# ======================
# Authenticator settings
# ======================
AUTH_API_URL = "https://web.socem.plymouth.ac.uk/COMP2001/auth/api/users"

ALLOWED_EMAILS = {
    "grace@plymouth.ac.uk",
    "tim@plymouth.ac.uk",
    "ada@plymouth.ac.uk",
}

def email_exists_in_authenticator(email: str) -> bool:
    """
    Checks if the email exists in the Authenticator API.
    Falls back to allowed list if API is unreachable.
    """
    try:
        r = httpx.get(AUTH_API_URL, timeout=5.0)
        r.raise_for_status()
        users = r.json()

        if isinstance(users, list):
            for u in users:
                if isinstance(u, dict):
                    api_email = u.get("email") or u.get("Email")
                    if isinstance(api_email, str) and api_email.lower() == email.lower():
                        return True
        return False
    except Exception:
        return email.lower() in ALLOWED_EMAILS

# ======================
# Database dependency
# ======================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ======================
# Pydantic schemas
# ======================
class ProfileCreate(BaseModel):
    auth_email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    role: str = "User"

class Profile(ProfileCreate):
    profile_id: int

    class Config:
        from_attributes = True

# ======================
# Endpoints
# ======================
@app.get("/")
def health():
    return {"status": "ok", "service": "ProfileService"}

# CREATE
@app.post("/profiles", response_model=Profile)
def create_profile(data: ProfileCreate, db: Session = Depends(get_db)):
    if data.role not in ["User", "Admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'User' or 'Admin'")

    if not email_exists_in_authenticator(str(data.auth_email)):
        raise HTTPException(status_code=403, detail="Email not recognised by Authenticator API")

    existing = db.query(ProfileModel).filter(ProfileModel.auth_email == data.auth_email).first()
    if existing:
        raise HTTPException(status_code=409, detail="auth_email already exists")

    row = ProfileModel(**data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

# READ (list)
@app.get("/profiles", response_model=List[Profile])
def list_profiles(db: Session = Depends(get_db)):
    return db.query(ProfileModel).all()

# READ (by id)
@app.get("/profiles/{profile_id}", response_model=Profile)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.query(ProfileModel).filter(ProfileModel.profile_id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return row

# UPDATE
@app.put("/profiles/{profile_id}", response_model=Profile)
def update_profile(profile_id: int, data: ProfileCreate, db: Session = Depends(get_db)):
    if data.role not in ["User", "Admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'User' or 'Admin'")

    row = db.query(ProfileModel).filter(ProfileModel.profile_id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    existing = db.query(ProfileModel).filter(ProfileModel.auth_email == data.auth_email).first()
    if existing and existing.profile_id != profile_id:
        raise HTTPException(status_code=409, detail="auth_email already exists")

    for k, v in data.model_dump().items():
        setattr(row, k, v)

    db.commit()
    db.refresh(row)
    return row

# DELETE
@app.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    row = db.query(ProfileModel).filter(ProfileModel.profile_id == profile_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.delete(row)
    db.commit()
    return {"deleted": True, "profile_id": profile_id}

