from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_current_token_payload, require_roles
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/signup", response_model=schemas.UserOut, status_code=201)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    if payload.role != models.UserRole.ACCOUNTS_STAFF.value:
        raise HTTPException(
            status_code=403,
            detail="Public signup is limited to accounts_staff accounts.",
        )

    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")

    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=models.UserRole.ACCOUNTS_STAFF,
        department=payload.department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(models.AuditLog(user_email=user.email, action="SIGNUP", details="New account created"))
    db.commit()

    return user


# Kept as an alias for backward compatibility with the original API surface
@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    return signup(payload, db)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    token, _, _ = create_access_token({"sub": user.email, "role": user.role.value})

    db.add(models.AuditLog(user_email=user.email, action="LOGIN", details="User logged in"))
    db.commit()

    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/logout", response_model=schemas.LogoutResponse)
def logout(
    payload: dict = Depends(get_current_token_payload),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revokes the current JWT by recording its jti — real logout semantics
    on top of an otherwise stateless token."""
    jti = payload.get("jti")
    exp_ts = payload.get("exp")
    expires_at = datetime.utcfromtimestamp(exp_ts) if exp_ts else None

    if jti and not db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first():
        db.add(models.RevokedToken(jti=jti, user_email=current_user.email, expires_at=expires_at))
        db.add(models.AuditLog(user_email=current_user.email, action="LOGOUT", details="Session revoked"))
        db.commit()

    return schemas.LogoutResponse()


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin")),
):
    return db.query(models.User).all()
