from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# =============================================
# اتصال به دیتابیس SQLite
# =============================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # مخصوص SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# =============================================
# مدل فیلم (جدول movies)
# =============================================
class MovieDB(Base):
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    rating = Column(Float, default=0)
    
    # فیلدهای اضافی برای اطلاعات کامل فیلم
    year = Column(String, nullable=True)
    director = Column(String, nullable=True)
    poster = Column(String, nullable=True)
    video = Column(String, nullable=True)
    desc = Column(String, nullable=True)

# =============================================
# ایجاد جداول در دیتابیس (اگر وجود نداشته باشند)
# =============================================
def create_tables():
    Base.metadata.create_all(bind=engine)

# =============================================
# دریافت session برای ارتباط با دیتابیس
# =============================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()