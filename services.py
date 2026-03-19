import requests
import random
import numpy as np

TMDB_GENRE_NAMES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi",
    53: "Thriller", 10752: "War", 37: "Western"
}

# Each mood maps to a SINGLE primary genre for strict TMDB AND filtering
# with_genres uses comma = AND logic on TMDB
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
                 genre_logic='AND'):
        if media_type == 'tv' and 'release_date' in sort_by:
            sort_by = 'popularity.desc'
        params = {'sort_by': sort_by, 'page': page, 'vote_count.gte': 5}
        if genre_ids:
            unique = list(dict.fromkeys(genre_ids))  # preserve order, dedupe
            if genre_logic == 'AND':
                # TMDB: comma-separated = AND (must have ALL genres)
                params['with_genres'] = ','.join(map(str, unique))
            else:
                # TMDB: pipe-separated = OR (any genre)
                params['with_genres'] = '|'.join(map(str, unique))
        if language:
            params['with_original_language'] = language
        if year_from:
            if media_type == 'tv':
                params['first_air_date.gte'] = f'{year_from}-01-01'
            else:
                params['primary_release_date.gte'] = f'{year_from}-01-01'
        if year_to:
            if media_type == 'tv':
                params['first_air_date.lte'] = f'{year_to}-12-31'
            else:
                params['primary_release_date.lte'] = f'{year_to}-12-31'
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

        # Use only the PRIMARY genre from each mood for strict AND filtering
        # This ensures Romantic only shows Romance, not Crime+Drama+Romance
        primary_genres = []
        for mood in mood_ids:
            genres = MOOD_GENRE_MAP.get(mood, {}).get('genres', [])
            if genres:
                primary_genres.append(genres[0])
        genre_ids = list(dict.fromkeys(primary_genres))  # dedupe, preserve order

        lang = INDUSTRY_LANGUAGE_MAP.get(industry.lower())

        # For TV + language: genres are too restrictive, prioritise language
        if media_type == 'tv' and lang:
            results = self.discover(media_type, genre_ids=genre_ids[:1] if genre_ids else None,
                                    language=lang, page=page, genre_logic='AND')
            if not results:
                results = self.discover(media_type, genre_ids=None, language=lang, page=page)
        else:
            results = self.discover(media_type, genre_ids=genre_ids or None,
                                    language=lang, page=page, genre_logic='AND')
            # Fallback: drop language but keep genre
            if not results and lang:
                results = self.discover(media_type, genre_ids=genre_ids or None, page=page,
                                        genre_logic='AND')
        # Last resort
        if not results:
            results = self.trending(media_type, 'week')

        # Score AND filter: keep only items that actually contain AT LEAST ONE selected genre
        filtered = []
        genre_set = set(genre_ids) if genre_ids else set()
        for item in results:
            item_genres = set(item['genre_ids'])
            if genre_set and not item_genres.intersection(genre_set):
                continue  # skip items with zero genre overlap
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

    def for_us(self, user1_ratings, user2_ratings, media_type='movie', count=50):
        """
        Find For Us — accurate + generous recommendations.

        Strategy:
        - Build separate genre+language taste profiles for each user
        - Identify SHARED preferences (genres both enjoy, weighted by rating)
        - Fetch candidates from TMDB across many angles: shared genres, shared
          languages, top-rated in taste overlap, popular in taste overlap
        - Score every candidate: how much does User1 like it? User2? Combined?
        - Hard-filter out anything already in either user's watchlist/ratings
        - Return top N sorted by combined taste fit
        """
        from collections import Counter

        # ── Build taste profiles ──────────────────────────────────────────────
        def extract_genres(r):
            raw = r.get('genre_ids') or ''
            if isinstance(raw, list):
                return [int(g) for g in raw if str(g).isdigit()]
            return [int(g.strip()) for g in str(raw).split(',') if g.strip().isdigit()]

        def build_profile(ratings):
            genres = Counter()
            langs  = Counter()
            for r in ratings:
                score = r.get('score', 3)
                # Weight: 5★=3, 4★=2, 3★=1, 1-2★ = negative
                w = {5: 3.0, 4: 2.0, 3: 1.0, 2: -0.5, 1: -1.0}.get(score, 1.0)
                for g in extract_genres(r):
                    genres[g] += w
                lang = r.get('original_language', '')
                if lang:
                    langs[lang] += max(w, 0)
            # Remove negatively weighted genres
            genres = Counter({g: v for g, v in genres.items() if v > 0})
            return genres, langs

        p1_genres, p1_langs = build_profile(user1_ratings)
        p2_genres, p2_langs = build_profile(user2_ratings)

        # Shared genres: only genres BOTH users have positive weight for
        all_g = set(p1_genres.keys()) | set(p2_genres.keys())
        shared_genres = {}
        for g in all_g:
            w1 = p1_genres.get(g, 0)
            w2 = p2_genres.get(g, 0)
            if w1 > 0 and w2 > 0:
                # Harmonic mean — penalises when one user barely likes it
                shared_genres[g] = 2 * w1 * w2 / (w1 + w2)
            elif w1 > 0 or w2 > 0:
                shared_genres[g] = (w1 + w2) * 0.25  # weak signal

        # Fallback defaults if no data
        if not shared_genres:
            shared_genres = {18: 2.0, 35: 2.0, 28: 1.5, 10749: 1.5,
                             878: 1.2, 9648: 1.2, 53: 1.0, 12: 1.0}

        top_shared = sorted(shared_genres.items(), key=lambda x: x[1], reverse=True)
        top_genre_ids = [g[0] for g in top_shared[:8]]  # top 8 shared genres

        # Shared languages
        all_l = set(p1_langs.keys()) | set(p2_langs.keys())
        shared_langs = {l: min(p1_langs.get(l,0), p2_langs.get(l,0)) for l in all_l}
        top_langs = [l for l, _ in sorted(shared_langs.items(), key=lambda x: x[1], reverse=True)[:3]]

        # Already seen by either user
        exclude = {r['tmdb_id'] for r in user1_ratings + user2_ratings}

        # ── Fetch candidates from many angles ─────────────────────────────────
        candidates = {}  # tmdb_id → item

        def collect(results):
            for r in results:
                if r['tmdb_id'] not in exclude and r['tmdb_id'] not in candidates:
                    if r.get('vote_average', 0) >= 5.5:  # min quality bar
                        candidates[r['tmdb_id']] = r

        # Angle 1: top 5 shared genres, sorted by rating, 5 pages each
        for gid in top_genre_ids[:5]:
            for pg in range(1, 6):
                collect(self.discover(media_type, genre_ids=[gid],
                                      sort_by='vote_average.desc', page=pg, genre_logic='OR'))
                if len(candidates) >= count * 6:
                    break

        # Angle 2: top 5 shared genres sorted by popularity, 3 pages each
        for gid in top_genre_ids[:5]:
            for pg in range(1, 4):
                collect(self.discover(media_type, genre_ids=[gid],
                                      sort_by='popularity.desc', page=pg, genre_logic='OR'))

        # Angle 3: shared languages + top genre combo
        for lang in top_langs[:2]:
            for gid in top_genre_ids[:3]:
                for pg in range(1, 3):
                    collect(self.discover(media_type, genre_ids=[gid],
                                          language=lang, sort_by='popularity.desc',
                                          page=pg, genre_logic='OR'))

        # Angle 4: pairs of top genres (genre1 AND genre2 = precise)
        for i in range(min(3, len(top_genre_ids))):
            for j in range(i+1, min(5, len(top_genre_ids))):
                for pg in range(1, 3):
                    collect(self.discover(media_type,
                                          genre_ids=[top_genre_ids[i], top_genre_ids[j]],
                                          sort_by='vote_average.desc', page=pg,
                                          genre_logic='AND'))

        # Angle 5: pure language fetch (taste through language preference)
        for lang in top_langs[:3]:
            for pg in range(1, 4):
                collect(self.discover(media_type, language=lang,
                                      sort_by='popularity.desc', page=pg))

        # Fallback: trending if still not enough
        if len(candidates) < count:
            collect(self.trending(media_type, 'week'))
            collect(self.trending(media_type, 'day'))

        # ── Score every candidate ─────────────────────────────────────────────
        def score_for_user(item_genres, profile_genres):
            """0-1: how well do this item's genres match a user's taste?"""
            if not profile_genres or not item_genres:
                return 0.4
            total = sum(profile_genres.values()) or 1
            match = sum(profile_genres.get(g, 0) for g in item_genres)
            return min(match / total, 1.0)

        scored = []
        for item in candidates.values():
            gids = item.get('genre_ids', [])
            if isinstance(gids, list):
                item_genres = [int(g) for g in gids if str(g).isdigit()]
            else:
                item_genres = [int(g.strip()) for g in str(gids).split(',') if g.strip().isdigit()]

            s1 = score_for_user(item_genres, p1_genres)
            s2 = score_for_user(item_genres, p2_genres)

            # Language bonus: if item language is in shared preference
            lang = item.get('original_language', '')
            lang_bonus = 0.08 if lang in top_langs else 0.0

            # Quality score: normalise vote_average to 0-1
            quality = max(0, (item.get('vote_average', 5) - 5.5) / 4.5)

            # Popularity score (normalised, capped)
            pop = min(item.get('popularity', 0) / 200, 1.0)

            # Combined score:
            # - Harmonic mean of both taste scores (both must like it)
            # - + quality (good movies rank higher)
            # - + small popularity signal
            # - + language bonus
            if s1 > 0 and s2 > 0:
                taste = 2 * s1 * s2 / (s1 + s2)  # harmonic mean
            else:
                taste = (s1 + s2) * 0.3  # one person doesn't like genre → low score

            final = taste * 0.55 + quality * 0.25 + pop * 0.12 + lang_bonus + 0.08

            item['_score'] = round(final, 4)
            scored.append(item)

        # Sort by score descending
        scored.sort(key=lambda x: x['_score'], reverse=True)

        # Clean internal key
        for item in scored:
            item.pop('_score', None)

        return scored[:count]

    def compatibility(self, u1_ratings, u2_ratings, u1_watched, u2_watched,
                      u1_genres=None, u2_genres=None):
        """Improved compatibility score 0-100."""
        from collections import Counter
        # 1. Watch overlap
        w1, w2 = set(u1_watched), set(u2_watched)
        watch_overlap = len(w1 & w2) / max(len(w1 | w2), 1) if (w1 or w2) else 0

        # 2. Rating cosine similarity on commonly rated items
        u1r = {r['tmdb_id']: r['score'] for r in u1_ratings}
        u2r = {r['tmdb_id']: r['score'] for r in u2_ratings}
        common = set(u1r.keys()) & set(u2r.keys())
        if len(common) >= 2:
            a = np.array([u1r[k] for k in common], dtype=float)
            b = np.array([u2r[k] for k in common], dtype=float)
            norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
            cosine = float(np.dot(a, b) / (norm_a * norm_b)) if norm_a and norm_b else 0.5
            # Rating agreement: penalise large differences
            avg_diff = sum(abs(u1r[k] - u2r[k]) for k in common) / len(common)
            agreement = max(0.0, 1.0 - avg_diff / 4.0)
            rating_sim = (cosine * 0.6 + agreement * 0.4)
        elif len(common) == 1:
            diff = abs(u1r[list(common)[0]] - u2r[list(common)[0]])
            rating_sim = max(0.3, 1.0 - diff / 4.0)
        else:
            rating_sim = 0.35

        # 3. Genre taste overlap using Jaccard on top genres
        if u1_genres and u2_genres:
            g1 = Counter(u1_genres)
            g2 = Counter(u2_genres)
            all_g = set(g1.keys()) | set(g2.keys())
            if all_g:
                overlap = sum(min(g1.get(g, 0), g2.get(g, 0)) for g in all_g)
                total = sum(max(g1.get(g, 0), g2.get(g, 0)) for g in all_g)
                genre_sim = overlap / total if total else 0.5
            else:
                genre_sim = 0.5
        else:
            genre_sim = 0.5

        # Weighted: rating similarity most important
        score = rating_sim * 0.50 + genre_sim * 0.30 + watch_overlap * 0.20

        # Bonus for meaningful shared watching history
        if len(w1 & w2) >= 3:
            score = min(score + 0.04, 1.0)
        if len(w1 & w2) >= 8:
            score = min(score + 0.04, 1.0)

        return min(round(score * 100), 100)