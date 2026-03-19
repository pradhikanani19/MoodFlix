import requests
import random
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
        import math
        from collections import Counter

        # ── 1. Build taste profiles ───────────────────────────────────────────
        def parse_genres(r):
            raw = r.get('genre_ids') or ''
            if isinstance(raw, list):
                return [int(g) for g in raw if str(g).strip().isdigit()]
            return [int(g.strip()) for g in str(raw).split(',') if g.strip().isdigit()]

        def build_profile(ratings):
            genres = Counter()
            langs  = Counter()
            score_map = {5: 3.0, 4: 2.0, 3: 1.0, 2: -1.5, 1: -3.0}
            for r in ratings:
                w = score_map.get(int(r.get('score', 3)), 1.0)
                for g in parse_genres(r):
                    genres[g] += w
                lang = (r.get('original_language') or '').strip()
                if lang and w > 0:
                    langs[lang] += w
            # Only keep genres with net positive weight
            genres = Counter({g: v for g, v in genres.items() if v > 0})
            return genres, langs

        p1g, p1l = build_profile(user1_ratings)
        p2g, p2l = build_profile(user2_ratings)

        # ── 2. Shared genre weights ───────────────────────────────────────────
        # Only genres BOTH users like get a strong shared weight
        # Genres only one user likes get a very small weight
        shared = {}
        for g in set(p1g) | set(p2g):
            w1, w2 = p1g.get(g, 0), p2g.get(g, 0)
            if w1 > 0 and w2 > 0:
                shared[g] = 2 * w1 * w2 / (w1 + w2)  # harmonic mean
            # deliberately skip genres only one user likes

        if not shared:
            # No overlap at all — use safe popular genres as fallback
            shared = {35: 2.0, 10749: 2.0, 28: 1.5, 18: 1.5, 878: 1.0, 53: 1.0}

        ranked = sorted(shared.items(), key=lambda x: x[1], reverse=True)
        top_gids = [g for g, _ in ranked[:8]]   # ONLY shared genres, top 8

        # Shared languages
        shared_langs = {}
        for l in set(p1l) | set(p2l):
            if p1l.get(l, 0) > 0 and p2l.get(l, 0) > 0:
                shared_langs[l] = min(p1l[l], p2l[l])
        top_langs = [l for l, _ in sorted(shared_langs.items(), key=lambda x: x[1], reverse=True)[:3]]

        exclude = {r['tmdb_id'] for r in user1_ratings + user2_ratings}
        top_gids_set = set(top_gids)

        # ── 3. Fetch candidates ───────────────────────────────────────────────
        pool = {}

        def add(items):
            for item in items:
                tid = item.get('tmdb_id')
                if not tid or tid in exclude or tid in pool:
                    continue
                # Hard quality gates
                if item.get('vote_average', 0) < 6.2:
                    continue
                if item.get('vote_count', 0) < 80:
                    continue
                # YEAR GATE — strictly reject items outside range
                # If year filter is active and date is missing/empty → reject
                if year_from or year_to:
                    rel = (item.get('release_date') or '').strip()
                    if not rel or len(rel) < 4:
                        continue  # no date = can't verify = reject when filter active
                    try:
                        yr = int(rel[:4])
                    except ValueError:
                        continue
                    if year_from and yr < year_from:
                        continue
                    if year_to and yr > year_to:
                        continue
                # GENRE GATE: item must share at least one top shared genre
                raw = item.get('genre_ids', [])
                gids = set(int(g) for g in (raw if isinstance(raw, list)
                           else str(raw).split(',')) if str(g).strip().isdigit())
                if top_gids_set and not gids.intersection(top_gids_set):
                    continue  # reject — not in our shared taste
                item['_gids'] = gids
                pool[tid] = item

        yd = dict(year_from=year_from, year_to=year_to)

        # A: Each shared genre, popularity sort — main source, 5 pages
        for gid in top_gids:
            for pg in range(1, 6):
                add(self.discover(media_type, genre_ids=[gid],
                                  sort_by='popularity.desc', page=pg,
                                  genre_logic='OR', min_votes=100, **yd))

        # B: Each shared genre, rating sort (500+ votes = real quality)
        for gid in top_gids:
            for pg in range(1, 4):
                add(self.discover(media_type, genre_ids=[gid],
                                  sort_by='vote_average.desc', page=pg,
                                  genre_logic='OR', min_votes=500, **yd))

        # C: Genre pairs AND — very precise taste match
        if len(top_gids) >= 2:
            for i in range(min(3, len(top_gids))):
                for j in range(i+1, min(5, len(top_gids))):
                    for pg in range(1, 4):
                        add(self.discover(media_type,
                                          genre_ids=[top_gids[i], top_gids[j]],
                                          sort_by='popularity.desc', page=pg,
                                          genre_logic='AND', min_votes=100, **yd))

        # D: Shared language + genre combos
        for lang in top_langs:
            for gid in top_gids[:4]:
                for pg in range(1, 3):
                    add(self.discover(media_type, genre_ids=[gid], language=lang,
                                      sort_by='popularity.desc', page=pg,
                                      genre_logic='OR', min_votes=30, **yd))

        # E: Shared language standalone
        for lang in top_langs:
            for pg in range(1, 4):
                add(self.discover(media_type, language=lang,
                                  sort_by='popularity.desc', page=pg,
                                  min_votes=50, **yd))

        # F: Fallback — MORE pages, SAME year filter, SAME genre gate
        if len(pool) < count * 2:
            for gid in top_gids[:4]:
                for pg in range(6, 10):
                    add(self.discover(media_type, genre_ids=[gid],
                                      sort_by='popularity.desc', page=pg,
                                      genre_logic='OR', min_votes=50, **yd))

        # G: Last resort — use discover with popularity sort (trending bypasses year filter)
        if len(pool) < count:
            for gid in top_gids[:4]:
                add(self.discover(media_type, genre_ids=[gid],
                                  sort_by='popularity.desc', page=1,
                                  genre_logic='OR', min_votes=30, **yd))
            # Only use actual trending if NO year filter is set
            if not year_from and not year_to:
                for item in self.trending(media_type, 'week'):
                    add([item])

        # ── 4. Score every candidate ──────────────────────────────────────────
        # shared_weights maps genre_id → combined shared weight (used for ranking)
        shared_weights = dict(ranked)  # genre_id → shared harmonic weight
        total_shared_weight = sum(shared_weights.values()) or 1.0

        def item_taste_score(gids_set, profile):
            """How much does this user like the genres in this item? 0-1."""
            if not profile or not gids_set:
                return 0.0
            profile_total = sum(profile.values()) or 1.0
            match = sum(profile.get(g, 0) for g in gids_set if profile.get(g, 0) > 0)
            return min(match / profile_total, 1.0)

        def shared_alignment(gids_set):
            """
            How well do item genres align with SHARED taste?
            Weighted by shared_weights — RomCom scores 3x if both love it equally.
            Crime scores near-zero if only one user likes it a little.
            """
            match = sum(shared_weights.get(g, 0) for g in gids_set)
            return min(match / total_shared_weight, 1.0)

        scored = []
        for item in pool.values():
            gids_set = item.pop('_gids', set())

            s1 = item_taste_score(gids_set, p1g)
            s2 = item_taste_score(gids_set, p2g)

            # Skip items either user definitely wouldn't enjoy
            if s1 <= 0 or s2 <= 0:
                continue

            # Harmonic mean of both taste scores — BOTH must like it
            taste_hmean = 2 * s1 * s2 / (s1 + s2)

            # Shared alignment — proportional to how strongly BOTH users like these genres
            # This ensures RomCom >> Crime when both users are mainly RomCom watchers
            s_align = shared_alignment(gids_set)

            # Quality (6.2-10 → 0-1, requires 100+ votes to count)
            rating = item.get('vote_average', 6)
            votes  = item.get('vote_count', 0)
            quality = max(0.0, (rating - 6.2) / 3.8) if votes >= 100 else 0.0

            # Popularity — log scale so mega-hits don't dominate
            pop = min(math.log(max(item.get('popularity', 1), 1)) / math.log(300), 1.0)

            # Language bonus
            lang_bonus = 0.06 if item.get('original_language') in top_langs else 0.0

            # Final formula:
            # taste_hmean:  both users like it personally
            # s_align:      it matches SHARED taste proportion (RomCom >> Crime)
            # quality:      well-rated
            # pop:          somewhat popular
            final = (
                taste_hmean * 0.40 +   # personal taste match
                s_align     * 0.35 +   # shared genre alignment (THIS fixes the ordering)
                quality     * 0.15 +
                pop         * 0.04 +
                lang_bonus
            )

            item['_score'] = round(final, 5)
            scored.append(item)

        scored.sort(key=lambda x: x['_score'], reverse=True)
        for item in scored:
            item.pop('_score', None)

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