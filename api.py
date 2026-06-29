from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta
from database import get_db, MovieDB
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
import os

app = FastAPI(title="سیستم توصیه‌گر فیلم", description="API برای پیشنهاد فیلم بر اساس ژانر و امتیاز")

# =============================================
# نمایش صفحه اصلی (index.html)
# =============================================
@app.get("/")
async def root():
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return {"پیام": "فایل index.html در مسیر frontend/index.html پیدا نشد"}

# =============================================
# مدل‌های Pydantic برای درخواست/پاسخ
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
    movies = db.query(MovieDB).all()
    return movies

@app.get("/movie/{name}")
def get_movie_by_name(name: str, db: Session = Depends(get_db)):
    movie = db.query(MovieDB).filter(MovieDB.name == name).first()
    if not movie:
        return {"error": "فیلمی با این نام یافت نشد"}
    return movie

@app.post("/recommend")
def recommend_film(request: GenreRequest, db: Session = Depends(get_db)):
    movies = db.query(MovieDB).filter(MovieDB.genre == request.genre).all()
    if not movies:
        return {"پیشنهادها": [], "message": "فیلمی با این ژانر یافت نشد"}
    return {"پیشنهادها": movies}

@app.get("/recommend/rating/{min_rating}")
def recommend_by_rating(min_rating: float, db: Session = Depends(get_db)):
    movies = db.query(MovieDB).filter(MovieDB.rating >= min_rating).all()
    return {"count": len(movies), "پیشنهادها": movies}

@app.get("/genres")
def get_genres(db: Session = Depends(get_db)):
    genres = db.query(MovieDB.genre).distinct().all()
    return {"genres": [g[0] for g in genres]}

@app.post("/add_movie")
def add_movie(movie: MovieCreate, db: Session = Depends(get_db)):
    existing_movie = db.query(MovieDB).filter(MovieDB.name == movie.name).first()
    if existing_movie:
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

@app.delete("/delete_movie/{movie_id}")
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(MovieDB).filter(MovieDB.id == movie_id).first()
    if not movie:
        return {"error": "فیلمی با این شناسه یافت نشد"}
    
    db.delete(movie)
    db.commit()
    return {"message": f"فیلم '{movie.name}' با موفقیت حذف شد"}

@app.put("/update_movie/{movie_id}")
def update_movie(movie_id: int, movie: MovieCreate, db: Session = Depends(get_db)):
    db_movie = db.query(MovieDB).filter(MovieDB.id == movie_id).first()
    if not db_movie:
        return {"error": "فیلمی با این شناسه یافت نشد"}
    
    db_movie.name = movie.name
    db_movie.genre = movie.genre
    db_movie.rating = movie.rating
    db_movie.year = movie.year
    db_movie.director = movie.director
    db_movie.poster = movie.poster
    db_movie.video = movie.video
    db_movie.desc = movie.desc
    
    db.commit()
    db.refresh(db_movie)
    return {"message": "فیلم با موفقیت به‌روزرسانی شد", "movie": db_movie}

@app.get("/search/")
def search_movies(
    name: str = None,
    genre: str = None,
    min_rating: float = None,
    max_rating: float = None,
    db: Session = Depends(get_db)
):
    query = db.query(MovieDB)
    
    if name:
        query = query.filter(MovieDB.name.contains(name))
    if genre:
        query = query.filter(MovieDB.genre == genre)
    if min_rating:
        query = query.filter(MovieDB.rating >= min_rating)
    if max_rating:
        query = query.filter(MovieDB.rating <= max_rating)
    
    results = query.all()
    return {"count": len(results), "results": results}

@app.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    total_movies = db.query(MovieDB).count()
    avg_rating = db.query(func.avg(MovieDB.rating)).scalar()
    max_rating = db.query(func.max(MovieDB.rating)).scalar()
    min_rating = db.query(func.min(MovieDB.rating)).scalar()
    genres_count = db.query(MovieDB.genre, func.count(MovieDB.genre)).group_by(MovieDB.genre).all()
    
    return {
        "total_movies": total_movies,
        "average_rating": round(avg_rating, 2) if avg_rating else 0,
        "highest_rating": max_rating,
        "lowest_rating": min_rating,
        "genres_distribution": [{"genre": g[0], "count": g[1]} for g in genres_count]
    }

@app.get("/top/{count}")
def get_top_movies(count: int = 3, db: Session = Depends(get_db)):
    movies = db.query(MovieDB).order_by(MovieDB.rating.desc()).limit(count).all()
    return {"top": movies}