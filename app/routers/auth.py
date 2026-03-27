from fastapi import APIRouter, Depends, HTTPException, status
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
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
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
async def login_for_access_token(
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