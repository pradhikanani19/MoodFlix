from flask_login import UserMixin
from datetime import datetime
from extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Confirmed friendships (both accepted)
friendships = db.Table('friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_requests')

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'sender_username': self.sender.username if self.sender else '',
            'sender_avatar_color': self.sender.avatar_color if self.sender else '#FFB7A5',
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_color = db.Column(db.String(20), default='#FFB7A5')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    watchlist = db.relationship('WatchlistItem', backref='user', lazy=True, cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='user', lazy=True, cascade='all, delete-orphan')
    friends = db.relationship('User', secondary=friendships,
        primaryjoin=(friendships.c.user_id == id),
        secondaryjoin=(friendships.c.friend_id == id),
        lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar_color': self.avatar_color,
            'created_at': self.created_at.isoformat()
        }


class WatchlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tmdb_id = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(10), default='movie')
    title = db.Column(db.String(300), nullable=False)
    poster_path = db.Column(db.String(300))
    genre_ids = db.Column(db.String(200))
    overview = db.Column(db.Text)
    vote_average = db.Column(db.Float, default=0)
    release_date = db.Column(db.String(20))
    original_language = db.Column(db.String(10))
    watched = db.Column(db.Boolean, default=False)
    review = db.Column(db.Text)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    watched_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'tmdb_id': self.tmdb_id,
            'media_type': self.media_type,
            'title': self.title,
            'poster_path': self.poster_path,
            'genre_ids': self.genre_ids,
            'overview': self.overview,
            'vote_average': self.vote_average,
            'release_date': self.release_date,
            'original_language': self.original_language,
            'watched': self.watched,
            'review': self.review,
            'added_at': self.added_at.isoformat()
        }


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tmdb_id = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(10), default='movie')
    title = db.Column(db.String(300))
    genre_ids = db.Column(db.String(200))
    original_language = db.Column(db.String(10))
    score = db.Column(db.Integer, nullable=False)
    rated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'tmdb_id': self.tmdb_id,
            'media_type': self.media_type,
            'title': self.title,
            'score': self.score,
            'genre_ids': self.genre_ids,
            'original_language': self.original_language,
            'rated_at': self.rated_at.isoformat()
        }


class SharedWatchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('SharedWatchlistItem', backref='shared_list', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'creator_id': self.creator_id,
            'friend_id': self.friend_id,
            'created_at': self.created_at.isoformat(),
            'items': [i.to_dict() for i in self.items]
        }


class SharedWatchlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('shared_watchlist.id'), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tmdb_id = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(10), default='movie')
    title = db.Column(db.String(300))
    poster_path = db.Column(db.String(300))
    vote_average = db.Column(db.Float, default=0)
    watched = db.Column(db.Boolean, default=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'tmdb_id': self.tmdb_id,
            'media_type': self.media_type,
            'title': self.title,
            'poster_path': self.poster_path,
            'vote_average': self.vote_average,
            'watched': self.watched,
            'added_by': self.added_by,
            'added_at': self.added_at.isoformat()
        }