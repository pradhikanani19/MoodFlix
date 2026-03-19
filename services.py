import requests
import random
import math
import numpy as np

TMDB_GENRE_NAMES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi",
    53: "Thriller", 10752: "War", 37: "Western"
}

# TV uses same genre IDs as movies for most genres
MOOD_GENRE_MAP = {
    'chill':         {'genres': [18],        'keywords': 'calm relaxing slice of life peaceful'},
    'emotional':     {'genres': [18],        'keywords': 'emotional touching heartfelt drama tears'},
    'romantic':      {'genres': [10749],     'keywords': 'romance love relationship couple'},
    'thrilling':     {'genres': [53],        'keywords': 'thriller suspense tension action exciting'},
    'fun':           {'genres': [35],        'keywords': 'funny comedy laugh entertaining'},
    'motivational':  {'genres': [18],        'keywords': 'inspiring motivation triumph overcome'},
    'romcom':        {'genres': [10749, 35], 'keywords': 'romantic comedy love funny'},
    'comedy':        {'genres': [35],        'keywords': 'comedy humor funny laugh'},
    'dark-comedy':   {'genres': [35],        'keywords': 'dark comedy satire black humor'},
    'horror':        {'genres': [27],        'keywords': 'horror scary frightening terror'},
    'horror-comedy': {'genres': [27, 35],    'keywords': 'horror comedy funny scary'},
    'psychological': {'genres': [53],        'keywords': 'psychological mind manipulation'},
    'crime':         {'genres': [80],        'keywords': 'crime detective murder heist'},
    'mystery':       {'genres': [9648],      'keywords': 'mystery investigation detective'},
    'action':        {'genres': [28],        'keywords': 'action fight explosion hero'},
    'adventure':     {'genres': [12],        'keywords': 'adventure journey quest discovery'},
    'fantasy':       {'genres': [14],        'keywords': 'fantasy magic wizard dragon'},
    'sci-fi':        {'genres': [878],       'keywords': 'sci-fi space future technology'},
    'feel-good':     {'genres': [35],        'keywords': 'feel good happy uplifting positive'},
    'slice-of-life': {'genres': [18],        'keywords': 'everyday life slice ordinary'},
    'sad':           {'genres': [18],        'keywords': 'sad tragic heartbreak loss grief'},
    'inspiring':     {'genres': [18],        'keywords': 'inspiring hope dream achieve'},
    'mind-bending':  {'genres': [878],       'keywords': 'mind bending twist reality complex'},
    'suspense':      {'genres': [53],        'keywords': 'suspense tension thriller gripping'},
}

INDUSTRY_LANGUAGE_MAP = {
    'all':       None,
    'hollywood': 'en',
    'bollywood': 'hi',
    'tollywood': 'te',
    'korean':    'ko',
    'japanese':  'ja',
    'french':    'fr',
    'spanish':   'es',
}


class TMDBClient:
    def __init__(self, api_key, base_url, img_base):
        self.api_key = api_key
        self.base = base_url
        self.img_base = img_base

    def get(self, endpoint, params=None):
        if not self.api_key:
            return None
        p = {'api_key': self.api_key, 'language': 'en-US'}
        if params:
            p.update(params)
        try:
            r = requests.get(f"{self.base}{endpoint}", params=p, timeout=8)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"TMDB error: {e}")
            return None

    def format_item(self, item, media_type='movie'):
        poster = f"{self.img_base}{item.get('poster_path')}" if item.get('poster_path') else None
        backdrop = f"https://image.tmdb.org/t/p/w1280{item.get('backdrop_path')}" if item.get('backdrop_path') else None
        gids = item.get('genre_ids', [])
        return {
            'tmdb_id': item.get('id'),
            'media_type': media_type,
            'title': item.get('title') or item.get('name', ''),
            'original_title': item.get('original_title') or item.get('original_name', ''),
            'poster_path': poster,
            'backdrop_path': backdrop,
            'overview': item.get('overview', ''),
            'vote_average': round(item.get('vote_average', 0), 1),
            'vote_count': item.get('vote_count', 0),
            'popularity': item.get('popularity', 0),
            'release_date': item.get('release_date') or item.get('first_air_date', ''),
            'original_language': item.get('original_language', ''),
            'genre_ids': gids,
            'genre_names': [TMDB_GENRE_NAMES.get(g, '') for g in gids if TMDB_GENRE_NAMES.get(g)],
        }

    def discover(self, media_type='movie', genre_ids=None, language=None,
                 year_from=None, year_to=None, sort_by='popularity.desc', page=1,
                 genre_logic='AND', min_votes=50):
        if media_type == 'tv' and 'release_date' in sort_by:
            sort_by = 'popularity.desc'
        params = {
            'sort_by': sort_by,
            'page': page,
            'vote_count.gte': min_votes,
            'vote_average.gte': 5.0,  # always enforce minimum quality
        }
        if genre_ids:
            unique = list(dict.fromkeys(genre_ids))
            params['with_genres'] = ','.join(map(str, unique)) if genre_logic == 'AND' else '|'.join(map(str, unique))
        if language:
            params['with_original_language'] = language
        if year_from:
            key = 'first_air_date.gte' if media_type == 'tv' else 'primary_release_date.gte'
            params[key] = f'{year_from}-01-01'
        if year_to:
            key = 'first_air_date.lte' if media_type == 'tv' else 'primary_release_date.lte'
            params[key] = f'{year_to}-12-31'
        data = self.get(f'/discover/{media_type}', params)
        if not data:
            return []
        return [self.format_item(r, media_type) for r in data.get('results', [])]

    def trending(self, media_type='all', time_window='week'):
        data = self.get(f'/trending/{media_type}/{time_window}')
        if not data:
            return []
        results = []
        for r in data.get('results', []):
            mt = r.get('media_type', 'movie')
            if mt in ('movie', 'tv'):
                results.append(self.format_item(r, mt))
        return results

    def search(self, query, page=1):
        data = self.get('/search/multi', {'query': query, 'page': page})
        if not data:
            return []
        results = []
        for r in data.get('results', []):
            mt = r.get('media_type', 'movie')
            if mt in ('movie', 'tv'):
                results.append(self.format_item(r, mt))
        return results

    def details(self, tmdb_id, media_type='movie'):
        data = self.get(f'/{media_type}/{tmdb_id}')
        if not data:
            return None
        item = self.format_item(data, media_type)
        item['genres'] = [g['name'] for g in data.get('genres', [])]
        item['runtime'] = data.get('runtime') or (data.get('episode_run_time') or [None])[0]
        item['tagline'] = data.get('tagline', '')
        credits = self.get(f'/{media_type}/{tmdb_id}/credits')
        if credits:
            item['cast'] = [
                {'name': c['name'], 'character': c.get('character', ''),
                 'profile': f"https://image.tmdb.org/t/p/w185{c['profile_path']}" if c.get('profile_path') else None}
                for c in credits.get('cast', [])[:6]
            ]
            item['director'] = next((c['name'] for c in credits.get('crew', []) if c.get('job') == 'Director'), None)
        sim = self.get(f'/{media_type}/{tmdb_id}/similar')
        if sim:
            item['similar'] = [self.format_item(r, media_type) for r in sim.get('results', [])[:6]]
        else:
            item['similar'] = []
        return item

    def now_playing(self):
        data = self.get('/movie/now_playing')
        if not data:
            return []
        return [self.format_item(r) for r in data.get('results', [])[:10]]

    def mood_recommendations(self, mood_ids, industry='all', media_type='movie', page=1):
        if not mood_ids:
            return self.trending(media_type, 'week')

        primary_genres = []
        for mood in mood_ids:
            genres = MOOD_GENRE_MAP.get(mood, {}).get('genres', [])
            if genres:
                primary_genres.append(genres[0])
        genre_ids = list(dict.fromkeys(primary_genres))

        lang = INDUSTRY_LANGUAGE_MAP.get(industry.lower())

        if media_type == 'tv' and lang:
            results = self.discover(media_type, genre_ids=genre_ids[:1] if genre_ids else None,
                                    language=lang, page=page, genre_logic='AND')
            if not results:
                results = self.discover(media_type, genre_ids=None, language=lang, page=page)
        else:
            results = self.discover(media_type, genre_ids=genre_ids or None,
                                    language=lang, page=page, genre_logic='AND')
            if not results and lang:
                results = self.discover(media_type, genre_ids=genre_ids or None, page=page, genre_logic='AND')

        if not results:
            results = self.trending(media_type, 'week')

        genre_set = set(genre_ids) if genre_ids else set()
        filtered = []
        for item in results:
            item_genres = set(item['genre_ids'])
            if genre_set and not item_genres.intersection(genre_set):
                continue
            overlap = len(item_genres & genre_set) if genre_set else 1
            mood_score = overlap / max(len(genre_set), 1) if genre_set else 0.5
            pop_score = min(item.get('vote_average', 0) / 10, 1.0)
            item['mood_score'] = round(mood_score * 0.6 + pop_score * 0.4, 3)
            filtered.append(item)

        filtered.sort(key=lambda x: x.get('mood_score', 0), reverse=True)
        return filtered

    def surprise(self, media_type='movie'):
        mood = random.choice(list(MOOD_GENRE_MAP.keys()))
        genre_ids = MOOD_GENRE_MAP[mood]['genres'][:2]
        lang = random.choice([None, 'en', 'hi', 'ko', 'ja'])
        results = self.discover(media_type, genre_ids=genre_ids, language=lang)
        if results:
            return random.choice(results[:10]), mood
        return None, mood

    # ── FOR US — Smart joint recommendation engine ────────────────────────────
    def for_us(self, user1_ratings, user2_ratings, media_type='movie', count=50, year_from=None, year_to=None):
        from collections import Counter

        # Build genre taste profile from ratings
        def parse_genres(r):
            raw = r.get('genre_ids') or ''
            if isinstance(raw, list):
                return [int(x) for x in raw if str(x).strip().isdigit()]
            return [int(x.strip()) for x in str(raw).split(',') if x.strip().isdigit()]

        def build_profile(ratings):
            p = Counter()
            wmap = {5: 3, 4: 2, 3: 1, 2: 0, 1: 0}
            for r in ratings:
                w = wmap.get(int(r.get('score', 3)), 1)
                if w <= 0:
                    continue
                for g in parse_genres(r):
                    p[g] += w
            return p

        p1 = build_profile(user1_ratings)
        p2 = build_profile(user2_ratings)

        # Shared genres — both users like them
        shared = {}
        for g in set(p1) | set(p2):
            w1, w2 = p1.get(g, 0), p2.get(g, 0)
            if w1 > 0 and w2 > 0:
                shared[g] = min(w1, w2)

        # Fallback when users have no taste data yet
        if not shared:
            shared = {35: 3, 10749: 3, 28: 2, 18: 2, 878: 1, 53: 1}

        top_genres = [g for g, _ in sorted(shared.items(), key=lambda x: x[1], reverse=True)][:6]
        total_shared = sum(shared.values()) or 1
        p1_total = sum(p1.values()) or 1
        p2_total = sum(p2.values()) or 1

        # IDs to exclude — already rated or watchlisted by either user
        exclude = {r['tmdb_id'] for r in user1_ratings + user2_ratings}

        # Collect candidates from TMDB
        pool = {}

        def collect(items):
            for item in items:
                tid = item.get('tmdb_id')
                if not tid or tid in exclude or tid in pool:
                    continue
                if item.get('vote_average', 0) < 6.0:
                    continue
                if item.get('vote_count', 0) < 50:
                    continue
                # Strict year filter
                if year_from or year_to:
                    rel = (item.get('release_date') or '').strip()
                    if not rel or len(rel) < 4:
                        continue
                    try:
                        yr = int(rel[:4])
                    except (ValueError, TypeError):
                        continue
                    if year_from and yr < int(year_from):
                        continue
                    if year_to and yr > int(year_to):
                        continue
                pool[tid] = item

        yd = {}
        if year_from:
            yd['year_from'] = year_from
        if year_to:
            yd['year_to'] = year_to

        # Fetch from each shared genre — popularity sort
        for gid in top_genres:
            for pg in range(1, 6):
                collect(self.discover(media_type, genre_ids=[gid],
                                      sort_by='popularity.desc', page=pg,
                                      genre_logic='OR', min_votes=100, **yd))
                if len(pool) >= count * 5:
                    break

        # Also fetch by rating (with high vote threshold to avoid junk)
        for gid in top_genres[:4]:
            for pg in range(1, 4):
                collect(self.discover(media_type, genre_ids=[gid],
                                      sort_by='vote_average.desc', page=pg,
                                      genre_logic='OR', min_votes=500, **yd))

        # Genre pair combos (AND) — precise matches e.g. RomCom
        for i in range(min(3, len(top_genres))):
            for j in range(i + 1, min(5, len(top_genres))):
                collect(self.discover(media_type,
                                      genre_ids=[top_genres[i], top_genres[j]],
                                      sort_by='popularity.desc', page=1,
                                      genre_logic='AND', min_votes=100, **yd))

        # Score each candidate
        scored = []
        for item in pool.values():
            raw = item.get('genre_ids', [])
            if isinstance(raw, list):
                gids = set(int(g) for g in raw if str(g).strip().isdigit())
            else:
                gids = set(int(g.strip()) for g in str(raw).split(',') if g.strip().isdigit())

            # Shared taste match
            shared_match = sum(shared.get(g, 0) for g in gids) / total_shared

            # Per-user taste match
            u1 = sum(p1.get(g, 0) for g in gids) / p1_total
            u2 = sum(p2.get(g, 0) for g in gids) / p2_total

            if u1 <= 0 or u2 <= 0:
                continue

            # Harmonic mean — both must enjoy it
            both = 2 * u1 * u2 / (u1 + u2)

            # Quality and popularity
            rating = item.get('vote_average', 6)
            quality = max(0.0, (rating - 6.0) / 4.0)
            pop_raw = max(float(item.get('popularity', 1)), 1.0)
            pop = min(math.log(pop_raw) / math.log(500), 1.0)

            score = shared_match * 0.40 + both * 0.35 + quality * 0.15 + pop * 0.10
            item['_s'] = score
            scored.append(item)

        scored.sort(key=lambda x: x['_s'], reverse=True)
        for item in scored:
            item.pop('_s', None)
        return scored[:count]

    # ── COMPATIBILITY ─────────────────────────────────────────────────────────
    def compatibility(self, u1_ratings, u2_ratings, u1_watched, u2_watched,
                      u1_genres=None, u2_genres=None):
        from collections import Counter
        w1, w2 = set(u1_watched), set(u2_watched)
        watch_overlap = len(w1 & w2) / max(len(w1 | w2), 1) if (w1 or w2) else 0

        u1r = {r['tmdb_id']: r['score'] for r in u1_ratings}
        u2r = {r['tmdb_id']: r['score'] for r in u2_ratings}
        common = set(u1r.keys()) & set(u2r.keys())
        if len(common) >= 2:
            a = np.array([u1r[k] for k in common], dtype=float)
            b = np.array([u2r[k] for k in common], dtype=float)
            norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
            cosine = float(np.dot(a, b) / (norm_a * norm_b)) if norm_a and norm_b else 0.5
            avg_diff = sum(abs(u1r[k] - u2r[k]) for k in common) / len(common)
            agreement = max(0.0, 1.0 - avg_diff / 4.0)
            rating_sim = cosine * 0.6 + agreement * 0.4
        elif len(common) == 1:
            diff = abs(u1r[list(common)[0]] - u2r[list(common)[0]])
            rating_sim = max(0.3, 1.0 - diff / 4.0)
        else:
            rating_sim = 0.35

        if u1_genres and u2_genres:
            g1, g2 = Counter(u1_genres), Counter(u2_genres)
            all_g = set(g1) | set(g2)
            overlap = sum(min(g1.get(g, 0), g2.get(g, 0)) for g in all_g)
            total = sum(max(g1.get(g, 0), g2.get(g, 0)) for g in all_g)
            genre_sim = overlap / total if total else 0.5
        else:
            genre_sim = 0.5

        score = rating_sim * 0.50 + genre_sim * 0.30 + watch_overlap * 0.20
        if len(w1 & w2) >= 3:
            score = min(score + 0.04, 1.0)
        if len(w1 & w2) >= 8:
            score = min(score + 0.04, 1.0)
        return min(round(score * 100), 100)