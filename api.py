from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db, MovieDB, create_tables
from sqlalchemy import func

# =============================================
# ایجاد جداول دیتابیس در هنگام شروع
# =============================================
create_tables()

app = FastAPI(title="سیستم توصیه‌گر فیلم")

# =============================================
# تنظیمات CORS
# =============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# نمایش صفحه اصلی
# =============================================
@app.get("/")
async def root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return {"پیام": "فایل index.html پیدا نشد"}

# =============================================
# مدل‌ها
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
    try:
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
    except Exception as e:
        return {"error": str(e)}

@app.post("/recommend")
def recommend_film(request: GenreRequest, db: Session = Depends(get_db)):
    movies = db.query(MovieDB).filter(MovieDB.genre == request.genre).all()
    return {"پیشنهادها": movies}

@app.get("/stats")
def get_statistics(db: Session = Depends(get_db)):
    total = db.query(MovieDB).count()
    avg = db.query(func.avg(MovieDB.rating)).scalar()
    return {"total_movies": total, "average_rating": round(avg, 2) if avg else 0}

@app.get("/genres")
def get_genres(db: Session = Depends(get_db)):
    genres = db.query(MovieDB.genre).distinct().all()
    return {"genres": [g[0] for g in genres]}

@app.get("/search/")
def search_movies(name: str = None, db: Session = Depends(get_db)):
    query = db.query(MovieDB)
    if name:
        query = query.filter(MovieDB.name.contains(name))
    return {"results": query.all()}

@app.get("/top/{count}")
def get_top_movies(count: int = 5, db: Session = Depends(get_db)):
    movies = db.query(MovieDB).order_by(MovieDB.rating.desc()).limit(count).all()
    return {"top": movies}

@app.delete("/delete_movie/{movie_id}")
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(MovieDB).filter(MovieDB.id == movie_id).first()
    if not movie:
        return {"error": "فیلمی با این شناسه یافت نشد"}
    db.delete(movie)
    db.commit()
    return {"message": "فیلم با موفقیت حذف شد"}

@app.put("/update_movie/{movie_id}")
def update_movie(movie_id: int, movie: MovieCreate, db: Session = Depends(get_db)):
    db_movie = db.query(MovieDB).filter(MovieDB.id == movie_id).first()
    if not db_movie:
        return {"error": "فیلمی با این شناسه یافت نشد"}
    for key, value in movie.dict().items():
        setattr(db_movie, key, value)
    db.commit()
    db.refresh(db_movie)
    return {"message": "فیلم با موفقیت به‌روزرسانی شد", "movie": db_movie}