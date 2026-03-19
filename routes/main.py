from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user
from services import TMDBClient, MOOD_GENRE_MAP, TMDB_GENRE_NAMES

main_bp = Blueprint('main', __name__)


def tmdb():
    return TMDBClient(
        current_app.config['TMDB_API_KEY'],
        current_app.config['TMDB_BASE_URL'],
        current_app.config['TMDB_IMG_BASE']
    )


@main_bp.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return render_template('landing.html')


@main_bp.route('/home')
@login_required
def home():
    client = tmdb()
    trending = client.trending('all', 'week')[:12]
    now_playing = client.now_playing()[:8]
    return render_template('home.html',
        trending=trending,
        now_playing=now_playing,
        moods=list(MOOD_GENRE_MAP.keys()),
        genres=TMDB_GENRE_NAMES
    )


@main_bp.route('/discover')
@login_required
def discover():
    return render_template('discover.html',
        moods=list(MOOD_GENRE_MAP.keys()),
        genres=TMDB_GENRE_NAMES
    )


@main_bp.route('/watchlist')
@login_required
def watchlist():
    from models import WatchlistItem
    items = WatchlistItem.query.filter_by(user_id=current_user.id).order_by(WatchlistItem.added_at.desc()).all()
    return render_template('watchlist.html',
        unwatched=[i for i in items if not i.watched],
        watched=[i for i in items if i.watched]
    )


@main_bp.route('/friends')
@login_required
def friends():
    from models import SharedWatchlist
    shared_lists = SharedWatchlist.query.filter(
        (SharedWatchlist.creator_id == current_user.id) |
        (SharedWatchlist.friend_id == current_user.id)
    ).all()
    return render_template('friends.html',
        friends=current_user.friends.all(),
        shared_lists=shared_lists
    )


@main_bp.route('/dashboard')
@login_required
def dashboard():
    from models import Rating, WatchlistItem
    ratings = Rating.query.filter_by(user_id=current_user.id).order_by(Rating.rated_at.desc()).all()
    watchlist_items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', ratings=ratings, watchlist=watchlist_items)


@main_bp.route('/movie/<int:tmdb_id>')
@login_required
def movie_detail(tmdb_id):
    from models import WatchlistItem, Rating
    movie = tmdb().details(tmdb_id, 'movie')
    in_wl = WatchlistItem.query.filter_by(user_id=current_user.id, tmdb_id=tmdb_id).first()
    ur = Rating.query.filter_by(user_id=current_user.id, tmdb_id=tmdb_id).first()
    return render_template('detail.html', item=movie, media_type='movie', in_watchlist=in_wl, user_rating=ur)


@main_bp.route('/tv/<int:tmdb_id>')
@login_required
def tv_detail(tmdb_id):
    from models import WatchlistItem, Rating
    show = tmdb().details(tmdb_id, 'tv')
    in_wl = WatchlistItem.query.filter_by(user_id=current_user.id, tmdb_id=tmdb_id).first()
    ur = Rating.query.filter_by(user_id=current_user.id, tmdb_id=tmdb_id).first()
    return render_template('detail.html', item=show, media_type='tv', in_watchlist=in_wl, user_rating=ur)
