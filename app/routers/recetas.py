from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.receta import RecetaCreate, RecetaResponse

router = APIRouter()

@router.get("/", response_model=List[RecetaResponse])
async def get_recetas(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Obtiene todas las recetas del usuario autenticado."""
    # Aquí llamarás a tu RecetaService más adelante
    pass

@router.post("/", response_model=RecetaResponse, status_code=status.HTTP_201_CREATED)
async def create_receta(
    data: RecetaCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Crea una nueva receta validando ingredientes y margen."""
    # La validación de porciones > 0 y min_length=1 ocurre automáticamente gracias a Pydantic
    pass