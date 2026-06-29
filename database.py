from sqlalchemy import Column, Integer, String, Float
from database import Base

class MovieDB(Base):
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    rating = Column(Float, default=0)
    year = Column(String, nullable=True)
    director = Column(String, nullable=True)
    poster = Column(String, nullable=True)
    video = Column(String, nullable=True)
    desc = Column(String, nullable=True)