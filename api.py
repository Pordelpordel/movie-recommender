from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db, MovieDB
from sqlalchemy import func
import os

app = FastAPI(title="سیستم توصیه‌گر فیلم")

# =============================================
# تنظیمات CORS - مهم برای ارتباط با فرانت‌اند
# =============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # اجازه به همه دامنه‌ها
    allow_credentials=True,
    allow_methods=["*"],  # اجازه به همه متدها (GET, POST, ...)
    allow_headers=["*"],  # اجازه به همه هدرها
)

# =============================================
# نمایش صفحه اصلی (index.html)
# =============================================
@app.get("/")
async def root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return {"پیام": "فایل index.html در کنار api.py پیدا نشد"}

# =============================================
# مدل‌های Pydantic
# =============================================
class MovieCreate(BaseModel):
    name: str
    genre: str
    rating: float
    year: Optional[str] = None
    director: Optional[str] = None
    poster: Optional[str] = None
    video: Optional[str] = None
    desc: Optional[str] = None

class MovieResponse(BaseModel):
    id: int
    name: str
    genre: str
    rating: float
    year: Optional[str] = None
    director: Optional[str] = None
    poster: Optional[str] = None
    video: Optional[str] = None
    desc: Optional[str] = None

class GenreRequest(BaseModel):
    genre: str

# =============================================
# اندپوینت‌ها
# =============================================

@app.get("/movies", response_model=List[MovieResponse])
def get_all_movies(db: Session = Depends(get_db)):
    return db.query(MovieDB).all()

@app.post("/add_movie")
def add_movie(movie: MovieCreate, db: Session = Depends(get_db)):
    existing = db.query(MovieDB).filter(MovieDB.name == movie.name).first()
    if existing:
        return {"error": "فیلمی با این نام قبلاً وجود دارد"}
    
    db_movie = MovieDB(
        name=movie.name,
        genre=movie.genre,
        rating=movie.rating,
        year=movie.year,
        director=movie.director,
        poster=movie.poster,
        video=movie.video,
        desc=movie.desc
    )
    db.add(db_movie)
    db.commit()
    db.refresh(db_movie)
    return {"message": "فیلم با موفقیت اضافه شد", "movie": db_movie}

@app.post("/recommend")
def recommend_film(request: GenreRequest, db: Session = Depends(get_db)):
    movies = db.query(MovieDB).filter(MovieDB.genre == request.genre).all()
    return {"پیشنهادها": movies}

@app.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    total = db.query(MovieDB).count()
    avg = db.query(func.avg(MovieDB.rating)).scalar()
    return {"total_movies": total, "average_rating": round(avg, 2) if avg else 0}