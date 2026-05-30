"""
Servicio de Gestión de Puntos de Entrega.

Este módulo provee la lógica de negocio para crear, actualizar, listar y dar de baja
lógica los puntos de entrega recurrentes configurados por los usuarios para despachar sus pedidos.
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.punto_entrega import PuntoEntrega
from app.schemas.punto_entrega import PuntoEntregaCreate, PuntoEntregaUpdate, PuntoEntregaPatch


class PuntoEntregaService:
    """
    Servicio encargado de administrar las ubicaciones y puntos de encuentro de entregas culinarias.
    """

    @staticmethod
    async def list_activos(db: AsyncSession, usuario_id: UUID) -> List[PuntoEntrega]:
        """
        Recupera el listado de todos los puntos de entrega activos de un usuario ordenados alfabéticamente.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            usuario_id (UUID): ID del usuario que consulta sus puntos de entrega.

        Returns:
            List[PuntoEntrega]: Listado de puntos de entrega activos ordenados por nombre.
        """
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
        """
        Registra un nuevo punto de entrega validando que el nombre no esté duplicado.

        Verifica que no exista un punto de entrega activo con el mismo nombre
        para el mismo usuario antes de guardar.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            usuario_id (UUID): ID del usuario propietario.
            data (PuntoEntregaCreate): DTO con el nombre, descripción y dirección física.

        Returns:
            PuntoEntrega: La instancia recién persistida del Punto de Entrega.

        Raises:
            HTTPException: 422 si ya existe un punto activo registrado con el mismo nombre.
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
        """
        Busca un punto de entrega activo validando los permisos del usuario (Multi-tenancy).

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            punto_entrega_id (UUID): ID del punto de entrega a consultar.
            usuario_id (UUID): ID del usuario solicitante.

        Returns:
            PuntoEntrega: La instancia del Punto de Entrega activa hallada.

        Raises:
            HTTPException: 404 si no existe, si pertenece a otro usuario o si está desactivado.
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
        """
        Actualiza de forma completa las propiedades de un punto de entrega.

        Realiza validaciones de unicidad de nombre si el nombre es modificado.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            punto_entrega_id (UUID): ID del registro a modificar.
            usuario_id (UUID): ID del usuario propietario.
            data (PuntoEntregaUpdate): DTO con los nuevos datos completos.

        Returns:
            PuntoEntrega: La instancia de PuntoEntrega actualizada.

        Raises:
            HTTPException: 422 si el nuevo nombre ya está ocupado por otro punto activo.
        """
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
        """
        Actualiza parcialmente (PATCH) los atributos de un punto de entrega.

        Solo actualiza los campos provistos en la petición.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            punto_entrega_id (UUID): ID del registro a actualizar.
            usuario_id (UUID): ID del usuario propietario.
            data (PuntoEntregaPatch): DTO con los campos opcionales a modificar.

        Returns:
            PuntoEntrega: La instancia de PuntoEntrega con los cambios parciales guardados.

        Raises:
            HTTPException: 422 si el nombre a aplicar está duplicado con otro punto activo.
        """
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
        """
        Da de baja lógica (soft delete) a un punto de entrega desactivándolo.

        Establece `activo=False`. Esto preserva la integridad en los pedidos
        históricos ya entregados y permite la reutilización futura de su nombre.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            punto_entrega_id (UUID): ID del punto de entrega a desactivar.
            usuario_id (UUID): ID del usuario propietario.

        Returns:
            PuntoEntrega: La instancia del Punto de Entrega desactivada.
        """
        punto = await PuntoEntregaService.get_or_404(db, punto_entrega_id, usuario_id)

        punto.activo = False
        punto.fecha_modificacion = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(punto)
        return punto
