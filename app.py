from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
import sqlite3
import hashlib
import os
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============ تنظیمات Flask-Login ============
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

# مدل کاربر
class User(UserMixin):
    def __init__(self, id, email, name=None):
        self.id = id
        self.email = email
        self.name = name

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['email'], user['name'])
    return None

# ============ تنظیمات OAuth گوگل ============
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='YOUR_GOOGLE_CLIENT_ID',  # جایگزین با Client ID خود
    client_secret='YOUR_GOOGLE_CLIENT_SECRET',  # جایگزین با Client Secret خود
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    client_kwargs={
        'scope': 'openid email profile',
    },
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

# ============ دیتابیس ============
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT,
            name TEXT,
            google_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            movie_name TEXT,
            watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# هش کردن رمز عبور
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ============ API برای فیلم‌ها ============
# دیتابیس فیلم‌ها (در حافظه برای سادگی)
MOVIES_DB = [
    {"id": 1, "name": "رستگاری در شاوشنگ", "genre": "درام", "rating": 9.3, "year": 1994, "director": "فرانک دارابونت", "views": 12500},
    {"id": 2, "name": "پدرخوانده", "genre": "جنایی", "rating": 9.2, "year": 1972, "director": "فرانسیس فورد کوپولا", "views": 11200},
    {"id": 3, "name": "تایتانیک", "genre": "عاشقانه", "rating": 8.5, "year": 1997, "director": "جیمز کامرون", "views": 15800},
    {"id": 4, "name": "ماتریکس", "genre": "علمی تخیلی", "rating": 8.7, "year": 1999, "director": "واچوفسکی", "views": 13200},
    {"id": 5, "name": "فارست گامپ", "genre": "درام", "rating": 8.8, "year": 1994, "director": "رابرت زمکیس", "views": 11900},
    {"id": 6, "name": "تلقین", "genre": "علمی تخیلی", "rating": 8.8, "year": 2010, "director": "کریستوفر نولان", "views": 14100},
    {"id": 7, "name": "جوینده", "genre": "جنایی", "rating": 8.6, "year": 2014, "director": "دنی ویلنوو", "views": 8900},
    {"id": 8, "name": "لا لا لند", "genre": "عاشقانه", "rating": 8.0, "year": 2016, "director": "دامین شزل", "views": 9700},
    {"id": 9, "name": "بین ستاره‌ای", "genre": "علمی تخیلی", "rating": 8.6, "year": 2014, "director": "کریستوفر نولان", "views": 12300},
    {"id": 10, "name": "ددپول", "genre": "کمدی", "rating": 8.0, "year": 2016, "director": "تیم میلر", "views": 10500},
    {"id": 11, "name": "جوکر", "genre": "درام", "rating": 8.4, "year": 2019, "director": "تاد فیلیپس", "views": 15200},
    {"id": 12, "name": "انگل", "genre": "درام", "rating": 8.6, "year": 2019, "director": "بونگ جون-هو", "views": 11800}
]

@app.route('/api/movies')
def api_movies():
    return jsonify(MOVIES_DB)

@app.route('/api/movies/search')
def api_search_movies():
    query = request.args.get('q', '').lower()
    genre = request.args.get('genre', '')
    min_rating = request.args.get('min_rating', 0, type=float)
    results = MOVIES_DB
    if query:
        results = [m for m in results if query in m['name'].lower()]
    if genre:
        results = [m for m in results if m['genre'] == genre]
    if min_rating:
        results = [m for m in results if m['rating'] >= min_rating]
    return jsonify(results)

@app.route('/api/movies/recommend')
def api_recommend():
    genre = request.args.get('genre', '')
    results = MOVIES_DB
    if genre:
        results = [m for m in results if m['genre'] == genre]
    results = sorted(results, key=lambda x: x['rating'] * 0.7 + min(x['views'] / 2000, 3) * 0.3, reverse=True)[:8]
    return jsonify(results)

@app.route('/api/movies/similar/<int:movie_id>')
def api_similar(movie_id):
    target = next((m for m in MOVIES_DB if m['id'] == movie_id), None)
    if not target:
        return jsonify([])
    similar = []
    for m in MOVIES_DB:
        if m['id'] == movie_id:
            continue
        score = 0
        if m['genre'] == target['genre']:
            score += 50
        score += (1 - abs(m['rating'] - target['rating']) / 10) * 30
        if m.get('year') and target.get('year'):
            score += (1 - min(abs(m['year'] - target['year']) / 50, 1)) * 20
        similar.append({**m, 'similarity': int(score)})
    similar.sort(key=lambda x: x['similarity'], reverse=True)
    return jsonify(similar[:6])

@app.route('/api/movies/stats')
def api_stats():
    total = len(MOVIES_DB)
    avg_rating = sum(m['rating'] for m in MOVIES_DB) / total
    best = max(MOVIES_DB, key=lambda x: x['rating'])
    genres = {}
    for m in MOVIES_DB:
        genres[m['genre']] = genres.get(m['genre'], 0) + 1
    return jsonify({
        'total': total,
        'avg_rating': round(avg_rating, 2),
        'best_movie': best['name'],
        'best_rating': best['rating'],
        'genres': genres
    })

@app.route('/api/movies/add', methods=['POST'])
def api_add_movie():
    data = request.get_json()
    new_movie = {
        'id': len(MOVIES_DB) + 1,
        'name': data.get('name'),
        'genre': data.get('genre'),
        'rating': data.get('rating'),
        'year': 2024,
        'director': 'کاربر',
        'views': 0
    }
    MOVIES_DB.append(new_movie)
    return jsonify({'success': True, 'movie': new_movie})

@app.route('/api/history/add', methods=['POST'])
@login_required
def api_add_history():
    data = request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO user_history (user_id, movie_id, movie_name) VALUES (?, ?, ?)',
                 (current_user.id, data.get('movie_id'), data.get('movie_name')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/user/movies')
@login_required
def api_user_movies():
    conn = get_db_connection()
    history = conn.execute('SELECT movie_id, movie_name, watched_at FROM user_history WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    return jsonify([dict(row) for row in history])

# ============ مسیرها ============
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth/local', methods=['POST'])
def auth_local():
    email = request.form.get('email')
    password = request.form.get('password')
    action = request.form.get('action')
    
    conn = get_db_connection()
    
    if action == 'register':
        existing = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('این ایمیل قبلاً ثبت شده است', 'error')
            return redirect(url_for('index'))
        
        if not password or len(password) < 8:
            flash('رمز عبور باید حداقل ۸ کاراکتر باشد', 'error')
            return redirect(url_for('index'))
        
        has_upper = any(c.isupper() for c in password)
        has_special = any(c in '@#$%^&+=!' for c in password)
        if not (has_upper and has_special):
            flash('رمز عبور باید شامل حروف بزرگ و کاراکترهای خاص باشد', 'error')
            return redirect(url_for('index'))
        
        hashed = hash_password(password)
        conn.execute('INSERT INTO users (email, password, name) VALUES (?, ?, ?)',
                     (email, hashed, email.split('@')[0]))
        conn.commit()
        
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        login_user(User(user['id'], user['email'], user['name']))
        flash('ثبت‌نام با موفقیت انجام شد! خوش آمدید', 'success')
        
    elif action == 'login':
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if not user or not user['password'] or hash_password(password) != user['password']:
            flash('ایمیل یا رمز عبور اشتباه است', 'error')
            return redirect(url_for('index'))
        login_user(User(user['id'], user['email'], user['name']))
        flash(f'خوش آمدید {user["name"]}!', 'success')
    
    conn.close()
    return redirect(url_for('index'))

@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = google.parse_id_token(token)
    
    email = user_info.get('email')
    name = user_info.get('name', email.split('@')[0])
    google_id = user_info.get('sub')
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ? OR google_id = ?', (email, google_id)).fetchone()
    
    if not user:
        conn.execute('INSERT INTO users (email, name, google_id) VALUES (?, ?, ?)',
                     (email, name, google_id))
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    
    conn.close()
    login_user(User(user['id'], user['email'], user['name']))
    flash(f'خوش آمدید {name}!', 'success')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('شما از حساب خود خارج شدید', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)