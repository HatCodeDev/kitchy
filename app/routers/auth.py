from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.core.limiter import limiter
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, ForgotPasswordRequest, ResetPasswordRequest
from app.services.email.base import EmailSender
from app.services.email.smtp import SmtpEmailSender
from app.services.password_reset_service import password_reset_service, InvalidTokenError


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_user(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Registra un nuevo usuario en Kitchy.
    """
    # Verificamos si el correo ya existe en la base de datos
    query = select(User).where(User.email == user_data.email)
    result = await db.execute(query)
    user_exists = result.scalars().first()

    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado."
        )

    # Hasheamos la contraseña por seguridad
    hashed_pwd = get_password_hash(user_data.password)

    # Creamos el objeto de base de datos
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_pwd
    )

    # Guardamos en PostgreSQL
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)  # Refresca para obtener el 'id' generado por la BD

    return new_user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
        request: Request,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """
    Inicia sesión y devuelve un Token JWT.
    OAuth2 espera que el correo venga en el campo 'username'.
    """
    # Buscamos al usuario por su email
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalars().first()

    # Verificamos que el usuario exista y que la contraseña coincida
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generamos el Gafete VIP (Token JWT)
    # MULTI-TENANCY BASE: Inyectamos el ID del usuario en el token.
    # Gracias a esto, sabremos de quién es cada petición en el futuro.
    access_token = create_access_token(data={"sub": str(user.id)})

    return {"access_token": access_token, "token_type": "bearer"}


def get_email_sender() -> EmailSender:
    return SmtpEmailSender()


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
):
    """
    Sends a password reset email if the address belongs to an active account.
    Always returns 200 to prevent user enumeration.
    """
    client_ip = request.client.host if request.client else "unknown"
    await password_reset_service.request_reset(db, email_sender, body.email, client_ip)
    return {"message": "If that email is registered, you will receive a reset link shortly."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Validates the reset token and updates the user's password.
    Returns 400 with a generic message for any token validation failure.
    """
    try:
        await password_reset_service.reset_password(db, body.token, body.new_password)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )
    return {"message": "Password updated successfully."}