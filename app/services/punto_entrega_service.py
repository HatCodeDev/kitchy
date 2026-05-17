from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.punto_entrega import PuntoEntrega
from app.schemas.punto_entrega import PuntoEntregaCreate, PuntoEntregaUpdate, PuntoEntregaPatch


class PuntoEntregaService:
    @staticmethod
    async def list_activos(db: AsyncSession, usuario_id: UUID) -> List[PuntoEntrega]:
        """Obtiene todos los puntos de entrega activos del usuario."""
        query = select(PuntoEntrega).where(
            and_(
                PuntoEntrega.usuario_id == usuario_id,
                PuntoEntrega.activo == True
            )
        ).order_by(PuntoEntrega.nombre)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create(
        db: AsyncSession,
        usuario_id: UUID,
        data: PuntoEntregaCreate
    ) -> PuntoEntrega:
        """Crea un nuevo punto de entrega.

        Valida:
        - nombre no duplicado entre registros activos del usuario (R2)
        """
        # Verificar nombre único entre puntos activos del mismo usuario
        query = select(PuntoEntrega).where(
            and_(
                PuntoEntrega.usuario_id == usuario_id,
                PuntoEntrega.nombre == data.nombre,
                PuntoEntrega.activo == True
            )
        )
        existing = await db.execute(query)
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Ya existe un punto de entrega con el nombre '{data.nombre}'"
            )

        nuevo = PuntoEntrega(
            usuario_id=usuario_id,
            nombre=data.nombre,
            descripcion=data.descripcion,
            direccion=data.direccion,
            activo=True
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        return nuevo

    @staticmethod
    async def get_or_404(db: AsyncSession, punto_entrega_id: UUID, usuario_id: UUID) -> PuntoEntrega:
        """Obtiene un punto de entrega específico.

        Retorna 404 si:
        - No existe el ID
        - Pertenece a otro usuario
        - Ha sido soft-deleted (activo=False)
        """
        query = select(PuntoEntrega).where(
            and_(
                PuntoEntrega.id == punto_entrega_id,
                PuntoEntrega.usuario_id == usuario_id,
                PuntoEntrega.activo == True
            )
        )
        result = await db.execute(query)
        punto = result.scalar_one_or_none()

        if not punto:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Punto de entrega no encontrado")

        return punto

    @staticmethod
    async def update(
        db: AsyncSession,
        punto_entrega_id: UUID,
        usuario_id: UUID,
        data: PuntoEntregaUpdate
    ) -> PuntoEntrega:
        """Actualiza completamente un punto de entrega."""
        punto = await PuntoEntregaService.get_or_404(db, punto_entrega_id, usuario_id)

        # Validar nombre único si cambió
        if data.nombre and data.nombre != punto.nombre:
            query = select(PuntoEntrega).where(
                and_(
                    PuntoEntrega.usuario_id == usuario_id,
                    PuntoEntrega.nombre == data.nombre,
                    PuntoEntrega.activo == True
                )
            )
            existing = await db.execute(query)
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ya existe un punto de entrega con el nombre '{data.nombre}'"
                )

        if data.nombre:
            punto.nombre = data.nombre
        if data.descripcion is not None:
            punto.descripcion = data.descripcion
        if data.direccion is not None:
            punto.direccion = data.direccion

        punto.fecha_modificacion = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(punto)
        return punto

    @staticmethod
    async def patch(
        db: AsyncSession,
        punto_entrega_id: UUID,
        usuario_id: UUID,
        data: PuntoEntregaPatch
    ) -> PuntoEntrega:
        """Actualiza parcialmente un punto de entrega."""
        punto = await PuntoEntregaService.get_or_404(db, punto_entrega_id, usuario_id)

        # Validar nombre único si cambió
        if data.nombre and data.nombre != punto.nombre:
            query = select(PuntoEntrega).where(
                and_(
                    PuntoEntrega.usuario_id == usuario_id,
                    PuntoEntrega.nombre == data.nombre,
                    PuntoEntrega.activo == True
                )
            )
            existing = await db.execute(query)
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Ya existe un punto de entrega con el nombre '{data.nombre}'"
                )

        # Solo actualizar campos que fueron proporcionados
        if data.nombre is not None:
            punto.nombre = data.nombre
        if data.descripcion is not None:
            punto.descripcion = data.descripcion
        if data.direccion is not None:
            punto.direccion = data.direccion

        punto.fecha_modificacion = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(punto)
        return punto

    @staticmethod
    async def soft_delete(db: AsyncSession, punto_entrega_id: UUID, usuario_id: UUID) -> PuntoEntrega:
        """Soft-deletes un punto de entrega (activo=False).

        Retorna 404 si no existe o ya fue eliminado.
        Los nombres soft-deleted pueden reutilizarse.
        """
        punto = await PuntoEntregaService.get_or_404(db, punto_entrega_id, usuario_id)

        punto.activo = False
        punto.fecha_modificacion = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(punto)
        return punto
