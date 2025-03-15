from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.future import select

from .database_provider import Base, async_session

T = TypeVar("T", bound=Base)


class Repository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def add(self, data: Dict[str, Any]) -> T:
        async with async_session() as session:
            async with session.begin():
                instance = self.model(**data)
                session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance

    async def get_all(self) -> List[T]:
        async with async_session() as session:
            result = await session.execute(select(self.model))
            return result.scalars().all()

    async def get_by_id(self, id_value: int) -> Optional[T]:
        async with async_session() as session:
            result = await session.execute(
                select(self.model).where(self.model.id == id_value)
            )
            return result.scalars().first()

    async def update(self, id_value: int, data: Dict[str, Any]) -> Optional[T]:
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(self.model).where(self.model.id == id_value)
                )
                instance = result.scalars().first()
                if not instance:
                    return None
                for key, value in data.items():
                    setattr(instance, key, value)
            await session.commit()
            await session.refresh(instance)
            return instance

    async def delete(self, id_value: int) -> Optional[T]:
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(self.model).where(self.model.id == id_value)
                )
                instance = result.scalars().first()
                if instance:
                    await session.delete(instance)
                    await session.commit()
            return instance
