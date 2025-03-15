from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.future import select

from .database_provider import Base, async_session


class Music(Base):
    __tablename__ = "musics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


async def add_music(message_id: int, url: str) -> Music:
    async with async_session() as session:
        async with session.begin():
            music = Music(message_id=message_id, url=url)
            session.add(music)
        await session.commit()
        await session.refresh(music)
        return music


async def get_music_by_url(url: str) -> Music:
    async with async_session() as session:
        result = await session.execute(select(Music).where(Music.url == url))
        return result.scalars().first()
