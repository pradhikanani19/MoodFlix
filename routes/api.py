from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from extensions import db
from models import User, WatchlistItem, Rating, SharedWatchlist, SharedWatchlistItem, FriendRequest
from services import TMDBClient, MOOD_GENRE_MAP, INDUSTRY_LANGUAGE_MAP, TMDB_GENRE_NAMES

api_bp = Blueprint('api', __name__)


def tmdb():
    return TMDBClient(
        current_app.config['TMDB_API_KEY'],
        current_app.config['TMDB_BASE_URL'],
        current_app.config['TMDB_IMG_BASE']
    )


# ── SEARCH / DISCOVER ────────────────────────────────────────────────────────
@api_bp.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    if not q:
        return jsonify([])
    return jsonify(tmdb().search(q, page))


@api_bp.route('/trending')
@login_required
def trending():
    media = request.args.get('media', 'all')
    window = request.args.get('window', 'week')
    return jsonify(tmdb().trending(media, window))


@api_bp.route('/discover')
@login_required
def discover():
    client = tmdb()
    moods = request.args.getlist('mood')
    genre_ids = request.args.getlist('genre', type=int)
    industry = request.args.get('industry', 'all')
    media_type = request.args.get('media_type', 'movie')
    year_from = request.args.get('year_from', type=int)
    year_to = request.args.get('year_to', type=int)
    sort_by = request.args.get('sort_by', 'popularity.desc')
    page = int(request.args.get('page', 1))

    strict_genres = list(genre_ids)
    mood_genres = []
    for mood in moods:
        primary = MOOD_GENRE_MAP.get(mood, {}).get('genres', [])
        if primary:
            mood_genres.append(primary[0])
    all_genres = list(dict.fromkeys(strict_genres + mood_genres))

    lang = INDUSTRY_LANGUAGE_MAP.get(industry.lower())

    if media_type == 'tv' and lang and all_genres:
        results = client.discover(media_type, genre_ids=all_genres[:1],
                                  language=lang, year_from=year_from,
                                  year_to=year_to, sort_by=sort_by, page=page, genre_logic='AND')
        if not results:
            results = client.discover(media_type, genre_ids=None,
                                      language=lang, year_from=year_from,
                                      year_to=year_to, sort_by=sort_by, page=page)
    else:
        results = client.discover(media_type, genre_ids=all_genres or None,
                                  language=lang, year_from=year_from,
                                  year_to=year_to, sort_by=sort_by, page=page, genre_logic='AND')
    return jsonify(results)


@api_bp.route('/recommend/mood')
@login_required
def recommend_mood():
    moods = request.args.getlist('mood')
    industry = request.args.get('industry', 'all')
    media_type = request.args.get('media_type', 'movie')
    page = int(request.args.get('page', 1))
    return jsonify(tmdb().mood_recommendations(moods, industry, media_type, page))


@api_bp.route('/recommend/surprise')
@login_required
def surprise():
    media_type = request.args.get('media_type', 'movie')
    item, mood = tmdb().surprise(media_type)
    return jsonify({'item': item, 'mood': mood})


@api_bp.route('/recommend/similar/<int:tmdb_id>')
@login_required
def similar(tmdb_id):
    media_type = request.args.get('media_type', 'movie')
    data = tmdb().details(tmdb_id, media_type)
    return jsonify(data.get('similar', []) if data else [])


# ── WATCHLIST ─────────────────────────────────────────────────────────────────
@api_bp.route('/watchlist', methods=['GET'])
@login_required
def get_watchlist():
    items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    return jsonify([i.to_dict() for i in items])


@api_bp.route('/watchlist', methods=['POST'])
@login_required
def add_watchlist():
    data = request.get_json()
    if WatchlistItem.query.filter_by(user_id=current_user.id, tmdb_id=data['tmdb_id']).first():
        return jsonify({'error': 'Already in watchlist'}), 400
    item = WatchlistItem(
        user_id=current_user.id,
        tmdb_id=data['tmdb_id'],
        media_type=data.get('media_type', 'movie'),
        title=data.get('title', ''),
        poster_path=data.get('poster_path'),
        genre_ids=','.join(map(str, data.get('genre_ids', []))),
        overview=data.get('overview', ''),
        vote_average=data.get('vote_average', 0),
        release_date=data.get('release_date', ''),
        original_language=data.get('original_language', '')
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@api_bp.route('/watchlist/<int:tmdb_id>', methods=['DELETE'])
@login_required
def remove_watchlist(tmdb_id):
    item = WatchlistItem.query.filter_by(user_id=current_user.id, tmdb_id=tmdb_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/watchlist/<int:tmdb_id>/watched', methods=['PATCH'])
@login_required
def mark_watched(tmdb_id):
    from datetime import datetime
    item = WatchlistItem.query.filter_by(user_id=current_user.id, tmdb_id=tmdb_id).first_or_404()
    data = request.get_json()
    item.watched = data.get('watched', True)
    item.review = data.get('review', item.review)
    if item.watched:
        item.watched_at = datetime.utcnow()
    db.session.commit()
    return jsonify(item.to_dict())


# ── RATINGS ───────────────────────────────────────────────────────────────────
@api_bp.route('/ratings', methods=['GET'])
@login_required
def get_ratings():
    ratings = Rating.query.filter_by(user_id=current_user.id).all()
    return jsonify([r.to_dict() for r in ratings])


@api_bp.route('/rating', methods=['POST'])
@login_required
def rate():
    data = request.get_json()
    existing = Rating.query.filter_by(user_id=current_user.id, tmdb_id=data['tmdb_id']).first()
    if existing:
        existing.score = data['score']
        db.session.commit()
        return jsonify(existing.to_dict())

    genre_ids_raw = data.get('genre_ids', [])
    orig_lang = data.get('original_language', '')
    title = data.get('title', '')

    if not genre_ids_raw or not orig_lang:
        wl_item = WatchlistItem.query.filter_by(
            user_id=current_user.id, tmdb_id=data['tmdb_id']
        ).first()
        if wl_item:
            if not genre_ids_raw and wl_item.genre_ids:
                genre_ids_raw = [int(x) for x in wl_item.genre_ids.split(',') if x.strip().isdigit()]
            if not orig_lang and wl_item.original_language:
                orig_lang = wl_item.original_language
            if not title and wl_item.title:
                title = wl_item.title

    r = Rating(
        user_id=current_user.id,
        tmdb_id=data['tmdb_id'],
        media_type=data.get('media_type', 'movie'),
        title=title,
        genre_ids=','.join(map(str, genre_ids_raw)),
        original_language=orig_lang,
        score=data['score']
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


# ── FRIEND REQUESTS ───────────────────────────────────────────────────────────
@api_bp.route('/friend-requests', methods=['GET'])
@login_required
def get_friend_requests():
    """Get pending incoming friend requests"""
    requests_in = FriendRequest.query.filter_by(
        receiver_id=current_user.id, status='pending'
    ).all()
    return jsonify([r.to_dict() for r in requests_in])


@api_bp.route('/friend-requests/sent', methods=['GET'])
@login_required
def get_sent_requests():
    """Get pending outgoing requests"""
    requests_out = FriendRequest.query.filter_by(
        sender_id=current_user.id, status='pending'
    ).all()
    return jsonify([r.to_dict() for r in requests_out])


@api_bp.route('/friends/add', methods=['POST'])
@login_required
def add_friend():
    data = request.get_json()
    username = data.get('username', '').strip()
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot add yourself'}), 400
    if current_user.friends.filter_by(id=user.id).first():
        return jsonify({'error': 'Already friends'}), 400

    # Check if request already sent
    existing = FriendRequest.query.filter_by(
        sender_id=current_user.id, receiver_id=user.id, status='pending'
    ).first()
    if existing:
        return jsonify({'error': 'Request already sent'}), 400

    # Check if they already sent us a request — auto-accept
    reverse = FriendRequest.query.filter_by(
        sender_id=user.id, receiver_id=current_user.id, status='pending'
    ).first()
    if reverse:
        reverse.status = 'accepted'
        current_user.friends.append(user)
        user.friends.append(current_user)
        db.session.commit()
        return jsonify({'success': True, 'auto_accepted': True, 'friend': user.to_dict()})

    # Create new request
    fr = FriendRequest(sender_id=current_user.id, receiver_id=user.id)
    db.session.add(fr)
    db.session.commit()
    return jsonify({'success': True, 'pending': True, 'message': f'Friend request sent to {username}'})


@api_bp.route('/friend-requests/<int:request_id>/accept', methods=['POST'])
@login_required
def accept_request(request_id):
    fr = FriendRequest.query.get_or_404(request_id)
    if fr.receiver_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    fr.status = 'accepted'
    sender = User.query.get(fr.sender_id)
    current_user.friends.append(sender)
    sender.friends.append(current_user)
    db.session.commit()
    return jsonify({'success': True, 'friend': sender.to_dict()})


@api_bp.route('/friend-requests/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_request(request_id):
    fr = FriendRequest.query.get_or_404(request_id)
    if fr.receiver_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    fr.status = 'rejected'
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/friends', methods=['GET'])
@login_required
def get_friends():
    result = []
    my_ratings = [r.to_dict() for r in current_user.ratings]
    my_watched = [w.tmdb_id for w in WatchlistItem.query.filter_by(user_id=current_user.id, watched=True).all()]
    my_watchlist_genres = []
    for w in WatchlistItem.query.filter_by(user_id=current_user.id).all():
        for g in (w.genre_ids or '').split(','):
            if g.strip().isdigit():
                my_watchlist_genres.append(int(g.strip()))

    for f in current_user.friends.all():
        f_ratings = [r.to_dict() for r in f.ratings]
        f_watched = [w.tmdb_id for w in WatchlistItem.query.filter_by(user_id=f.id, watched=True).all()]
        f_watchlist_genres = []
        for w in WatchlistItem.query.filter_by(user_id=f.id).all():
            for g in (w.genre_ids or '').split(','):
                if g.strip().isdigit():
                    f_watchlist_genres.append(int(g.strip()))
        score = tmdb().compatibility(my_ratings, f_ratings, my_watched, f_watched,
                                     my_watchlist_genres, f_watchlist_genres)
        result.append({**f.to_dict(), 'compatibility': score})
    return jsonify(result)


@api_bp.route('/friends/<int:friend_id>/compatibility')
@login_required
def compatibility(friend_id):
    friend = User.query.get_or_404(friend_id)
    my_ratings = [r.to_dict() for r in current_user.ratings]
    f_ratings = [r.to_dict() for r in friend.ratings]
    my_watched = [w.tmdb_id for w in WatchlistItem.query.filter_by(user_id=current_user.id, watched=True).all()]
    f_watched = [w.tmdb_id for w in WatchlistItem.query.filter_by(user_id=friend.id, watched=True).all()]
    my_wg = [int(g.strip()) for w in WatchlistItem.query.filter_by(user_id=current_user.id).all()
             for g in (w.genre_ids or '').split(',') if g.strip().isdigit()]
    f_wg = [int(g.strip()) for w in WatchlistItem.query.filter_by(user_id=friend.id).all()
            for g in (w.genre_ids or '').split(',') if g.strip().isdigit()]
    score = tmdb().compatibility(my_ratings, f_ratings, my_watched, f_watched, my_wg, f_wg)
    return jsonify({'score': score, 'friend': friend.to_dict()})


@api_bp.route('/friends/<int:friend_id>/for-us')
@login_required
def for_us(friend_id):
    import traceback
    try:
        friend = User.query.get_or_404(friend_id)
        my_ratings = [r.to_dict() for r in current_user.ratings]
        f_ratings = [r.to_dict() for r in friend.ratings]
        # Add watchlist items as implicit taste signals (score=3)
        my_wl = WatchlistItem.query.filter_by(user_id=current_user.id).all()
        f_wl = WatchlistItem.query.filter_by(user_id=friend.id).all()
        rated_ids = {r['tmdb_id'] for r in my_ratings}
        for w in my_wl:
            if w.tmdb_id not in rated_ids:
                my_ratings.append({'tmdb_id': w.tmdb_id, 'score': 3,
                                   'genre_ids': w.genre_ids or '',
                                   'original_language': w.original_language or ''})
        f_rated_ids = {r['tmdb_id'] for r in f_ratings}
        for w in f_wl:
            if w.tmdb_id not in f_rated_ids:
                f_ratings.append({'tmdb_id': w.tmdb_id, 'score': 3,
                                   'genre_ids': w.genre_ids or '',
                                   'original_language': w.original_language or ''})
        media_type = request.args.get('media_type', 'movie')
        results = tmdb().for_us(my_ratings, f_ratings, media_type=media_type, count=30)
        if not results:
            results = tmdb().trending(media_type, 'week')[:30]
        return jsonify(results)
    except Exception as e:
        err = traceback.format_exc()
        print(f"FOR_US ERROR: {err}")
        return jsonify({'error': str(e), 'trace': err}), 500


@api_bp.route('/friends/<int:friend_id>/remove', methods=['POST'])
@login_required
def remove_friend(friend_id):
    friend = User.query.get_or_404(friend_id)
    current_user.friends.filter(User.id == friend_id).delete()
    friend.friends.filter(User.id == current_user.id).delete()
    db.session.commit()
    return jsonify({'success': True})


# ── SHARED WATCHLIST ──────────────────────────────────────────────────────────
@api_bp.route('/shared-watchlist', methods=['GET'])
@login_required
def get_shared_lists():
    lists = SharedWatchlist.query.filter(
        (SharedWatchlist.creator_id == current_user.id) |
        (SharedWatchlist.friend_id == current_user.id)
    ).all()
    return jsonify([sl.to_dict() for sl in lists])


@api_bp.route('/shared-watchlist', methods=['POST'])
@login_required
def create_shared():
    data = request.get_json()
    friend = User.query.get_or_404(data['friend_id'])
    sw = SharedWatchlist(
        name=data.get('name', f"List with {friend.username}"),
        creator_id=current_user.id,
        friend_id=friend.id
    )
    db.session.add(sw)
    db.session.commit()
    return jsonify(sw.to_dict()), 201


@api_bp.route('/shared-watchlist/<int:list_id>', methods=['GET'])
@login_required
def get_shared_list(list_id):
    sw = SharedWatchlist.query.get_or_404(list_id)
    if current_user.id not in [sw.creator_id, sw.friend_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify(sw.to_dict())


@api_bp.route('/shared-watchlist/<int:list_id>/item', methods=['POST'])
@login_required
def add_to_shared(list_id):
    sw = SharedWatchlist.query.get_or_404(list_id)
    if current_user.id not in [sw.creator_id, sw.friend_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    # Check duplicate
    existing = SharedWatchlistItem.query.filter_by(
        list_id=list_id, tmdb_id=data['tmdb_id']
    ).first()
    if existing:
        return jsonify({'error': 'Already in list'}), 400
    item = SharedWatchlistItem(
        list_id=list_id,
        added_by=current_user.id,
        tmdb_id=data['tmdb_id'],
        media_type=data.get('media_type', 'movie'),
        title=data.get('title', ''),
        poster_path=data.get('poster_path'),
        vote_average=data.get('vote_average', 0)
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@api_bp.route('/shared-watchlist/<int:list_id>/item/<int:item_id>/watched', methods=['PATCH'])
@login_required
def mark_shared_watched(list_id, item_id):
    item = SharedWatchlistItem.query.get_or_404(item_id)
    data = request.get_json()
    item.watched = data.get('watched', True)
    db.session.commit()
    return jsonify(item.to_dict())


@api_bp.route('/shared-watchlist/<int:list_id>/item/<int:item_id>', methods=['DELETE'])
@login_required
def remove_from_shared(list_id, item_id):
    item = SharedWatchlistItem.query.get_or_404(item_id)
    sw = SharedWatchlist.query.get_or_404(list_id)
    if current_user.id not in [sw.creator_id, sw.friend_id]:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})


# ── ANALYTICS ─────────────────────────────────────────────────────────────────
@api_bp.route('/analytics')
@login_required
def analytics():
    ratings = Rating.query.filter_by(user_id=current_user.id).all()
    watchlist = WatchlistItem.query.filter_by(user_id=current_user.id).all()

    genre_counts = {}
    lang_counts = {}
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    monthly = {}

    for r in ratings:
        rating_dist[r.score] = rating_dist.get(r.score, 0) + 1
        lang = r.original_language or 'unknown'
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        for gid in (r.genre_ids or '').split(','):
            gid = gid.strip()
            if gid.isdigit():
                name = TMDB_GENRE_NAMES.get(int(gid), '')
                if name:
                    genre_counts[name] = genre_counts.get(name, 0) + 1

    for w in watchlist:
        for gid in (w.genre_ids or '').split(','):
            gid = gid.strip()
            if gid.isdigit():
                name = TMDB_GENRE_NAMES.get(int(gid), '')
                if name:
                    genre_counts[name] = genre_counts.get(name, 0) + 1
        if w.original_language:
            lang_counts[w.original_language] = lang_counts.get(w.original_language, 0) + 1
        if w.watched and w.watched_at:
            key = w.watched_at.strftime('%Y-%m')
            monthly[key] = monthly.get(key, 0) + 1

    return jsonify({
        'total_watched': len([w for w in watchlist if w.watched]),
        'total_rated': len(ratings),
        'avg_rating': round(sum(r.score for r in ratings) / len(ratings), 1) if ratings else 0,
        'top_genres': sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:8],
        'language_diversity': sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:6],
        'rating_distribution': rating_dist,
        'monthly_watches': sorted(monthly.items()),
    })



# ── PROFILE ───────────────────────────────────────────────────────────────────
@api_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    avatar_color = data.get('avatar_color', current_user.avatar_color)

    if not username or not email:
        return jsonify({'error': 'Username and email required'}), 400

    # Check username taken by someone else
    existing = User.query.filter_by(username=username).first()
    if existing and existing.id != current_user.id:
        return jsonify({'error': 'Username already taken'}), 400

    existing_email = User.query.filter_by(email=email).first()
    if existing_email and existing_email.id != current_user.id:
        return jsonify({'error': 'Email already in use'}), 400

    current_user.username = username
    current_user.email = email
    current_user.avatar_color = avatar_color
    db.session.commit()
    return jsonify({'success': True, 'user': current_user.to_dict()})


@api_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    from extensions import bcrypt
    data = request.get_json()
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')

    if not bcrypt.check_password_hash(current_user.password_hash, current_pw):
        return jsonify({'error': 'Current password is incorrect'}), 400
    if len(new_pw) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/me')
@login_required
def me():
    return jsonify(current_user.to_dict())