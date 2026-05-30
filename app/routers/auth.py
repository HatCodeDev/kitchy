"""
Controlador de Autenticación.

Este router expone los endpoints públicos de Kitchy para permitir el autoregistro
de nuevos usuarios y el intercambio de credenciales por tokens de acceso JWT.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.core.limiter import limiter
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_user(request: Request, user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Registra una nueva cuenta de usuario en la plataforma Kitchy.

    Valida que el correo no esté registrado previamente. Realiza el hasheo
    seguro de la contraseña antes de persistir la entidad en PostgreSQL.

    ### Rate Limiting:
    * Máximo **10 peticiones por minuto** por dirección IP.

    ### Respuestas:
    * **201 Created**: Usuario registrado de manera exitosa. Retorna sus metadatos (excluyendo contraseña).
    * **400 Bad Request**: Si el correo ya se encuentra en uso.
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
    Autentica credenciales de usuario y expide un Token de Acceso JWT (Bearer).

    Realiza una verificación de hashing contra la base de datos.
    El token resultante contiene el ID de usuario como subject (`sub`), sirviendo como
    mecanismo base para el aislamiento multi-tenancy del backend.

    ### OAuth2 Specification:
    * El estándar requiere que el correo electrónico se envíe en el campo **`username`**
      y la contraseña en **`password`** usando el formato `application/x-www-form-urlencoded`.

    ### Rate Limiting:
    * Máximo **10 peticiones por minuto** por dirección IP.

    ### Respuestas:
    * **200 OK**: Credenciales válidas. Devuelve el token JWT y su tipo ('bearer').
    * **401 Unauthorized**: Correo o contraseña incorrectos.
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