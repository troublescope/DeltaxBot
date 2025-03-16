from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime
from sqlalchemy.future import select

from .database_provider import Base, async_session


class System(Base):
    __tablename__ = "systems"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    chat_id = Column(BigInteger, nullable=False)
    restart_id = Column(BigInteger, nullable=False)
    last_restart = Column(DateTime, nullable=False)


async def get_system(system_id: int):
    async with async_session() as session:
        result = await session.execute(select(System).filter(System.id == system_id))
        return result.scalars().first()


async def update_system(
    system_id: int, chat_id: int, new_restart_id: int, new_last_restart: datetime
):
    async with async_session() as session:
        result = await session.execute(select(System).filter(System.id == system_id))
        system = result.scalars().first()

        if system is None:
            system = System(
                id=system_id,
                chat_id=chat_id,
                restart_id=new_restart_id,
                last_restart=new_last_restart,
            )
            session.add(system)
        else:
            system.chat_id = chat_id
            system.restart_id = new_restart_id
            system.last_restart = new_last_restart

        await session.commit()
        return system


async def clear_system(system_id: int):
    async with async_session() as session:
        result = await session.execute(select(System).filter(System.id == system_id))
        system = result.scalars().first()

        if system:
            await session.delete(system)
            await session.commit()
            return True
        return False
