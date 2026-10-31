"""FindMe AI matching engine.

Pure-Python, dependency-free similarity scoring between lost and found
reports.  The module is deliberately isolated from Flask: the only entry
points used by ``app.py`` are ``find_potential_matches()``,
``backfill_matches()`` and ``rerun_all_matches()``.

Scoring is a 12-factor weighted sum (weights total exactly 1.00).  The
engine also applies a few hard rules that a pure weighted sum cannot
express:

* a *matching* serial number is near-proof (score floor 96 %);
* a *conflicting* serial number is near-proof that the reports are not the
  same item (score ceiling 35 %);
* two known but different categories are penalised;
* a very close item name can still be proposed when the report is sparse.

The minimum confidence stored in ``matches`` is ``MIN_MATCH_CONFIDENCE``.
"""

import os
import re
from datetime import date, datetime, time, timedelta
from difflib import SequenceMatcher

# ── Tunables ──────────────────────────────────────────────────────────────
MIN_MATCH_CONFIDENCE = 25.0
MAX_CANDIDATE_ITEMS = 200
MAX_MATCHES_PER_RUN = 10
OPEN_STATUSES = ('reported', 'under_review', 'potential_match',
                 'match_pending_approval')

# Words that add noise to similarity comparisons.  "lost"/"found" are
# removed because every report contains one of them.
_STOPWORDS = {
    'a', 'an', 'the', 'my', 'mine', 'our', 'this', 'that', 'these', 'those',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'has', 'have', 'had',
    'with', 'and', 'or', 'of', 'for', 'to', 'in', 'on', 'at', 'near', 'from',
    'by', 'it', 'its', 'i', 'me', 'some', 'really', 'very', 'lost', 'found',
    'item', 'items', 'thing', 'things',
}

_COLOR_GROUPS = [
    {'black', 'dark', 'charcoal', 'midnight', 'ebony'},
    {'white', 'light', 'cream', 'ivory', 'snow'},
    {'blue', 'navy', 'cyan', 'azure', 'indigo', 'sky'},
    {'red', 'darkred', 'crimson', 'scarlet', 'maroon', 'burgundy'},
    {'green', 'darkgreen', 'forest', 'olive', 'lime', 'emerald'},
    {'silver', 'gray', 'grey', 'metallic', 'chrome'},
    {'gold', 'golden', 'yellow', 'brass', 'amber'},
    {'brown', 'tan', 'beige', 'darkbrown', 'chocolate', 'khaki'},
    {'pink', 'rose', 'magenta', 'fuchsia'},
    {'purple', 'violet', 'lavender', 'plum'},
    {'orange', 'coral', 'peach', 'tangerine'},
]

_SHAPE_ALIASES = [
    {'rectangular', 'rectangle', 'oblong', 'rectangular-shaped'},
    {'round', 'circular', 'circle', 'oval', 'elliptical'},
    {'cylindrical', 'cylinder', 'tube', 'tubular'},
    {'square', 'box-shaped', 'cubical', 'boxy'},
    {'triangular', 'triangle', 'pyramid'},
    {'irregular', 'asymmetric', 'irregularly-shaped'},
    {'flat', 'thin', 'pancake', 'disc-shaped'},
    {'compact', 'small', 'tiny', 'miniature'},
    {'slim', 'narrow', 'thin'},
    {'large', 'big', 'oversized', 'bulky'},
]

# Optional image keywords.  Kept for the (clearly labelled) simulated image
# comparison used when Cloudinary/disk images are unavailable.
_IMAGE_KEYWORDS = (
    'phone', 'laptop', 'tablet', 'wallet', 'bag', 'watch', 'ring', 'keys',
    'book', 'glasses', 'camera', 'headphones', 'charger', 'umbrella',
)


def row_to_dict(cursor, row):
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def rows_to_dicts(cursor, rows):
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


# ══════════════════════════════════════════════════════════════════════════
# Text helpers
# ══════════════════════════════════════════════════════════════════════════

def _normalize(value):
    """Lower-case and collapse punctuation/whitespace."""
    if value is None:
        return ''
    text = str(value).strip().lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return ' '.join(text.split())


def _tokens(value):
    """Meaningful word set (stopwords removed)."""
    words = _normalize(value).split()
    meaningful = [w for w in words if w not in _STOPWORDS]
    return set(meaningful or words)


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def text_similarity(str1, str2):
    """Fuzzy similarity in [0, 1] combining edit distance and word overlap."""
    s1 = _normalize(str1)
    s2 = _normalize(str2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    sequence = SequenceMatcher(None, s1, s2).ratio()

    tokens1 = _tokens(str1)
    tokens2 = _tokens(str2)
    if not tokens1 or not tokens2:
        return round(sequence, 4)

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    jaccard = len(intersection) / len(union) if union else 0.0
    containment = len(intersection) / min(len(tokens1), len(tokens2))
    overlap = (jaccard + containment) / 2 * 0.95

    return round(min(max(sequence, overlap), 1.0), 4)


def category_match(cat1, cat2):
    """1.0 same category, 0.5 both unknown, 0.25 one unknown, 0.15 different."""
    c1, c2 = _as_int(cat1), _as_int(cat2)
    if c1 is None and c2 is None:
        return 0.5
    if c1 is None or c2 is None:
        return 0.25
    return 1.0 if c1 == c2 else 0.15


def color_match(color1, color2):
    if not color1 or not color2:
        return 0.0
    c1 = _normalize(color1)
    c2 = _normalize(color2)
    if not c1 or not c2:
        return 0.0
    if c1 == c2:
        return 1.0

    tokens1 = set(c1.split())
    tokens2 = set(c2.split())
    if tokens1 & tokens2:
        return 0.8

    for group in _COLOR_GROUPS:
        if tokens1 & group and tokens2 & group:
            return 0.85

    return round(text_similarity(c1, c2) * 0.6, 4)


def brand_match(brand1, brand2):
    if not brand1 or not brand2:
        return 0.0
    b1 = _normalize(brand1)
    b2 = _normalize(brand2)
    if not b1 or not b2:
        return 0.0
    if b1 == b2:
        return 1.0
    if b1 in b2 or b2 in b1:
        return 0.9
    return text_similarity(b1, b2)


def location_match(loc_id1, loc_id2, loc_detail1=None, loc_detail2=None):
    l1, l2 = _as_int(loc_id1), _as_int(loc_id2)
    if l1 is None or l2 is None:
        base = 0.0
    elif l1 == l2:
        base = 1.0
    else:
        base = 0.15

    bonus = 0.0
    if loc_detail1 and loc_detail2:
        bonus = text_similarity(loc_detail1, loc_detail2) * 0.35
    return round(min(base + bonus, 1.0), 4)


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def date_proximity(date1_str, date2_str):
    d1 = _parse_date(date1_str)
    d2 = _parse_date(date2_str)
    if d1 is None or d2 is None:
        return 0.3
    diff_days = abs((d1 - d2).days)
    if diff_days == 0:
        return 1.0
    if diff_days <= 1:
        return 0.95
    if diff_days <= 3:
        return 0.85
    if diff_days <= 7:
        return 0.7
    if diff_days <= 14:
        return 0.5
    if diff_days <= 30:
        return 0.3
    return 0.1


def _parse_minutes(value):
    """Return minutes since midnight for TIME/TIMEDELTA/date/time/string."""
    if value is None:
        return None
    if isinstance(value, timedelta):
        return int(value.total_seconds() // 60) % (24 * 60)
    if isinstance(value, datetime):
        return value.hour * 60 + value.minute
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    text = str(value).strip()
    match = re.match(r'^(\d{1,2}):(\d{2})', text)
    if match:
        try:
            return int(match.group(1)) * 60 + int(match.group(2))
        except (ValueError, TypeError):
            return None
    return None


def time_proximity(time1, time2):
    m1 = _parse_minutes(time1)
    m2 = _parse_minutes(time2)
    if m1 is None or m2 is None:
        return 0.3
    diff_minutes = abs(m1 - m2)
    diff_minutes = min(diff_minutes, 24 * 60 - diff_minutes)
    if diff_minutes <= 30:
        return 1.0
    if diff_minutes <= 60:
        return 0.9
    if diff_minutes <= 120:
        return 0.7
    if diff_minutes <= 360:
        return 0.5
    return 0.2


def description_similarity(desc1, desc2):
    if not desc1 or not desc2:
        return 0.0
    s1 = _normalize(desc1)
    s2 = _normalize(desc2)
    if not s1 or not s2:
        return 0.0
    tokens1 = _tokens(desc1)
    tokens2 = _tokens(desc2)
    if not tokens1 or not tokens2:
        return text_similarity(s1, s2)
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    jaccard = len(intersection) / len(union) if union else 0.0
    base_text = text_similarity(s1, s2)
    return round(jaccard * 0.6 + base_text * 0.4, 4)


def image_similarity_simulated(img_path1, img_path2):
    """Best-effort image hint (filename heuristics).

    This is intentionally labelled *simulated*: it never pretends to be a
    vision model.  Real visual matching can be added later by replacing this
    function without touching the rest of the engine.
    """
    if not img_path1 or not img_path2:
        return 0.0
    name1 = os.path.basename(str(img_path1)).lower()
    name2 = os.path.basename(str(img_path2)).lower()
    name1_no_ext = os.path.splitext(name1)[0]
    name2_no_ext = os.path.splitext(name2)[0]
    if name1_no_ext == name2_no_ext:
        return 1.0
    if name1_no_ext in name2_no_ext or name2_no_ext in name1_no_ext:
        return 0.85
    ext1 = os.path.splitext(name1)[1]
    ext2 = os.path.splitext(name2)[1]
    if ext1 and ext2 and ext1 == ext2:
        return 0.45
    for keyword in _IMAGE_KEYWORDS:
        k1 = keyword in name1_no_ext
        k2 = keyword in name2_no_ext
        if k1 and k2:
            return 0.6
        if k1 or k2:
            return 0.35
    return 0.25


def shape_match(shape1, shape2):
    if not shape1 or not shape2:
        return 0.0
    s1 = _normalize(shape1)
    s2 = _normalize(shape2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    tokens1 = set(s1.split())
    tokens2 = set(s2.split())
    if tokens1 & tokens2:
        return 0.85
    for group in _SHAPE_ALIASES:
        if tokens1 & group and tokens2 & group:
            return 0.85
    return round(text_similarity(s1, s2) * 0.75, 4)


def appearance_match(lost, found):
    if not lost and not found:
        return 0.0
    image_score = image_similarity_simulated(
        lost.get('image_path'), found.get('image_path')
    )
    shape_score = shape_match(lost.get('shape'), found.get('shape'))
    combined = image_score * 0.6 + shape_score * 0.4
    return round(min(max(combined, 0.0), 1.0), 4)


def serial_number_match(sn1, sn2):
    if not sn1 or not sn2:
        return None
    s1 = _normalize(sn1)
    s2 = _normalize(sn2)
    if not s1 or not s2:
        return None
    return 1.0 if s1 == s2 else 0.0


def unique_marks_match(marks1, marks2):
    if not marks1 or not marks2:
        return None
    m1 = _normalize(marks1)
    m2 = _normalize(marks2)
    if not m1 or not m2:
        return None
    return text_similarity(m1, m2)


def approximate_value_match(val1, val2):
    if val1 is None or val2 is None:
        return None
    try:
        v1 = float(val1)
        v2 = float(val2)
    except (ValueError, TypeError):
        return None
    if v1 <= 0 or v2 <= 0:
        return None
    ratio = min(v1, v2) / max(v1, v2)
    if ratio >= 0.9:
        return 1.0
    if ratio >= 0.7:
        return 0.8
    if ratio >= 0.5:
        return 0.5
    if ratio >= 0.3:
        return 0.3
    return 0.1


def identical_features_match(lost, found):
    """Average of serial number / unique marks / approximate value (if given)."""
    if not lost and not found:
        return 0.0, []
    scores = {}
    explanations = []

    serial = serial_number_match(lost.get('serial_number'), found.get('serial_number'))
    if serial is not None:
        scores['serial_number'] = serial
        explanations.append(('Serial number match', serial))

    marks = unique_marks_match(lost.get('unique_marks'), found.get('unique_marks'))
    if marks is not None:
        scores['unique_marks'] = marks
        explanations.append(('Unique marks similarity', marks))

    value = approximate_value_match(
        lost.get('approximate_value'), found.get('approximate_value')
    )
    if value is not None:
        scores['approximate_value'] = value
        explanations.append(('Approximate value match', value))

    if not scores:
        return 0.0, []
    return round(sum(scores.values()) / len(scores), 4), explanations


def compute_match_score(lost, found):
    """Score a lost/found pair on 12 factors whose weights sum to 1.00."""
    lost = lost or {}
    found = found or {}

    weights = {
        'item_name': 0.22,
        'category': 0.10,
        'color': 0.08,
        'brand': 0.07,
        'model': 0.06,
        'description': 0.10,
        'location': 0.10,
        'date': 0.04,
        'time': 0.02,
        'appearance': 0.07,
        'shape': 0.04,
        'identical_features': 0.10,
    }
    assert abs(sum(weights.values()) - 1.0) < 1e-9, (
        f'AI matcher factor weights must sum to 1.00, got {sum(weights.values())}'
    )

    scores = {}
    explanations = []

    scores['item_name'] = text_similarity(
        lost.get('item_name'), found.get('item_name')
    )
    explanations.append(('Item name similarity', scores['item_name']))

    scores['category'] = category_match(
        lost.get('category_id'), found.get('category_id')
    )
    explanations.append(('Item category', scores['category']))

    scores['color'] = color_match(lost.get('color'), found.get('color'))
    explanations.append(('Color match', scores['color']))

    scores['brand'] = brand_match(lost.get('brand'), found.get('brand'))
    explanations.append(('Brand similarity', scores['brand']))

    scores['model'] = text_similarity(lost.get('model'), found.get('model'))
    explanations.append(('Model similarity', scores['model']))

    scores['description'] = description_similarity(
        lost.get('description'), found.get('description')
    )
    explanations.append(('Description similarity', scores['description']))

    scores['location'] = location_match(
        lost.get('location_id'), found.get('location_id'),
        lost.get('location_detail'), found.get('location_detail'),
    )
    explanations.append(('Location similarity', scores['location']))

    scores['date'] = date_proximity(
        lost.get('date_lost'), found.get('date_found')
    )
    explanations.append(('Date proximity', scores['date']))

    scores['time'] = time_proximity(
        lost.get('time_lost'), found.get('time_found')
    )
    explanations.append(('Time proximity', scores['time']))

    scores['appearance'] = appearance_match(lost, found)
    explanations.append(('Appearance / photo similarity', scores['appearance']))

    scores['shape'] = shape_match(lost.get('shape'), found.get('shape'))
    explanations.append(('Shape match', scores['shape']))

    id_score, id_explanations = identical_features_match(lost, found)
    scores['identical_features'] = id_score
    explanations.extend(id_explanations)

    total_score = sum(scores[key] * weights[key] for key in weights) * 100

    # ── Hard rules ────────────────────────────────────────────────────────
    serial1 = _normalize(lost.get('serial_number'))
    serial2 = _normalize(found.get('serial_number'))
    serial_conflict = bool(serial1 and serial2 and serial1 != serial2)

    cat1, cat2 = _as_int(lost.get('category_id')), _as_int(found.get('category_id'))
    category_conflict = bool(cat1 is not None and cat2 is not None and cat1 != cat2)

    if serial1 and serial2 and serial1 == serial2:
        total_score = max(total_score, 96.0)
        explanations.append(('Serial numbers are identical (near-certain match)', 1.0))
    elif scores.get('unique_marks', 0) >= 0.95:
        total_score = max(total_score, 90.0)
        explanations.append(('Unique identifying marks are identical', 1.0))

    if serial_conflict:
        # Different serial numbers on serialised devices (phones, laptops)
        # strongly indicate two different items.
        total_score = min(total_score, 35.0)
        explanations.append(('Serial numbers differ (strong negative signal)', 0.0))

    if category_conflict:
        total_score *= 0.9
        explanations.append(('Reported categories differ', 0.0))

    total_score = round(min(max(total_score, 0.0), 100.0), 2)

    explanation_lines = [
        f'{label}: {int(score * 100)}%' for label, score in explanations
    ]
    explanation_text = '\n'.join(f'• {line}' for line in explanation_lines)
    explanation_text += f'\n\n**Overall Confidence: {int(total_score)}%**'

    if total_score >= 90:
        level = 'very_high'
    elif total_score >= 75:
        level = 'high'
    elif total_score >= 50:
        level = 'possible'
    else:
        level = 'low'

    return {
        'confidence_score': total_score,
        'match_level': level,
        'explanation': explanation_text,
        'scores': scores,
        'hard_conflict': serial_conflict,
    }


def is_match_candidate(result):
    """Whether a scored pair is worth storing for human review."""
    if not result or result.get('hard_conflict'):
        return False
    score = result.get('confidence_score', 0)
    if score >= MIN_MATCH_CONFIDENCE:
        return True
    # Sparse reports: a very strong name match is still a useful lead, even
    # when there is not enough metadata to cross the normal threshold.
    name_score = result.get('scores', {}).get('item_name', 0)
    return name_score >= 0.85 and score >= 18.0


# ══════════════════════════════════════════════════════════════════════════
# Database pipeline
# ══════════════════════════════════════════════════════════════════════════

def _placeholders(values):
    return ', '.join(['%s'] * len(values))


def _fetch_items(cursor, table, limit=MAX_CANDIDATE_ITEMS):
    statuses = _placeholders(OPEN_STATUSES)
    cursor.execute(
        f'SELECT * FROM {table} WHERE status IN ({statuses}) '
        f'ORDER BY created_at DESC LIMIT {int(limit)}',
        OPEN_STATUSES,
    )
    return rows_to_dicts(cursor, cursor.fetchall())


def _notify(cursor, user_ids, title, message, match_id):
    """Insert one notification per distinct user; never abort a match for this."""
    for user_id in sorted({uid for uid in user_ids if uid}):
        try:
            cursor.execute(
                'INSERT INTO notifications '
                '(user_id, title, message, type, related_type, related_id) '
                'VALUES (%s, %s, %s, %s, %s, %s)',
                (user_id, title, message, 'match', 'match', match_id),
            )
        except Exception:
            # A notification is nice-to-have: the match itself must survive.
            continue


def _set_status(cursor, table, item_id):
    statuses = _placeholders(OPEN_STATUSES)
    cursor.execute(
        f'UPDATE {table} SET status = %s WHERE id = %s AND status IN ({statuses})',
        ('potential_match', item_id) + OPEN_STATUSES,
    )


def _create_match(db, cursor, lost, found, result):
    cursor.execute(
        'INSERT INTO matches '
        '(lost_item_id, found_item_id, confidence_score, match_level, explanation, status) '
        'VALUES (%s, %s, %s, %s, %s, %s)',
        (
            lost['id'], found['id'], result['confidence_score'],
            result['match_level'], result['explanation'], 'pending',
        ),
    )
    match_id = cursor.lastrowid

    _set_status(cursor, 'lost_items', lost['id'])
    _set_status(cursor, 'found_items', found['id'])

    confidence = int(result['confidence_score'])
    reporter_id = lost.get('reporter_id')
    finder_id = found.get('finder_id')
    if reporter_id and reporter_id == finder_id:
        # One person reported both sides: one notification is enough.
        _notify(
            cursor, [reporter_id], 'Potential Match Found',
            f'Your lost and found reports may describe the same item. '
            f'Confidence: {confidence}%',
            match_id,
        )
    else:
        _notify(
            cursor, [reporter_id], 'Potential Match Found',
            f'A found item may match your lost item report. Confidence: {confidence}%',
            match_id,
        )
        _notify(
            cursor, [finder_id], 'Potential Match Found',
            f'A lost item may match the item you found. Confidence: {confidence}%',
            match_id,
        )

    db.commit()
    return {
        'match_id': match_id,
        'lost_item_id': lost['id'],
        'found_item_id': found['id'],
        'confidence_score': result['confidence_score'],
        'match_level': result['match_level'],
    }


def find_potential_matches(item_type, item_id, db):
    """Score one report against all open reports of the opposite type.

    Called immediately after a report is saved (synchronously by ``app.py``),
    so a newly reported lost item instantly finds existing found items and
    vice-versa.  Returns the list of newly created matches.
    """
    cursor = db.cursor()
    try:
        if item_type == 'lost':
            cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
            lost_item = row_to_dict(cursor, cursor.fetchone())
            if not lost_item:
                return []
            candidates_items = _fetch_items(cursor, 'found_items')
            cursor.execute(
                'SELECT found_item_id FROM matches WHERE lost_item_id = %s',
                (item_id,),
            )
            already_matched = {row[0] for row in cursor.fetchall()}

            pairs = (
                (lost_item, other) for other in candidates_items
                if other['id'] not in already_matched
            )
        elif item_type == 'found':
            cursor.execute('SELECT * FROM found_items WHERE id = %s', (item_id,))
            found_item = row_to_dict(cursor, cursor.fetchone())
            if not found_item:
                return []
            candidates_items = _fetch_items(cursor, 'lost_items')
            cursor.execute(
                'SELECT lost_item_id FROM matches WHERE found_item_id = %s',
                (item_id,),
            )
            already_matched = {row[0] for row in cursor.fetchall()}

            pairs = (
                (other, found_item) for other in candidates_items
                if other['id'] not in already_matched
            )
        else:
            return []

        scored = []
        for lost, found in pairs:
            result = compute_match_score(lost, found)
            if is_match_candidate(result):
                scored.append((result, lost, found))

        # Best leads first, then cap spam (one report should not create
        # dozens of notifications).
        scored.sort(key=lambda row: row[0]['confidence_score'], reverse=True)

        new_matches = []
        for result, lost, found in scored[:MAX_MATCHES_PER_RUN]:
            try:
                new_matches.append(_create_match(db, cursor, lost, found, result))
            except Exception:
                db.rollback()
        return new_matches
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


def backfill_matches(db, limit=15, days=30):
    """Safety net: match recent open reports that have *no* matches yet.

    The report routes match synchronously, but this sweep repairs data from
    older deployments, failed runs or reports created while the app was
    restarting.  At most ``limit`` lost and ``limit`` found reports are
    processed per call.
    """
    statuses = _placeholders(OPEN_STATUSES)
    cursor = db.cursor()
    try:
        date_filter = ''
        base_params = list(OPEN_STATUSES)
        if days is not None:
            date_filter = ' AND created_at >= %s'
            base_params.append(datetime.now() - timedelta(days=int(days)))

        cursor.execute(
            f'SELECT li.id FROM lost_items li '
            f'WHERE li.status IN ({statuses}) '
            f'AND NOT EXISTS (SELECT 1 FROM matches m WHERE m.lost_item_id = li.id)'
            f'{date_filter.replace("created_at", "li.created_at")} '
            f'ORDER BY li.created_at DESC LIMIT {int(limit)}',
            tuple(base_params),
        )
        lost_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            f'SELECT fi.id FROM found_items fi '
            f'WHERE fi.status IN ({statuses}) '
            f'AND NOT EXISTS (SELECT 1 FROM matches m WHERE m.found_item_id = fi.id)'
            f'{date_filter.replace("created_at", "fi.created_at")} '
            f'ORDER BY fi.created_at DESC LIMIT {int(limit)}',
            tuple(base_params),
        )
        found_ids = [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()

    created = 0
    for lost_id in lost_ids:
        created += len(find_potential_matches('lost', lost_id, db))
    for found_id in found_ids:
        created += len(find_potential_matches('found', found_id, db))
    return created


def rerun_all_matches(db):
    """Rebuild pending matches while preserving approved/rejected decisions."""
    cursor = db.cursor()
    try:
        # Only remove untouched suggestions; approved/rejected pairs carry
        # human decisions (and may be referenced by verification/recovery
        # rows, which would block a DELETE).
        cursor.execute(
            'SELECT m.id FROM matches m '
            'LEFT JOIN verification_requests v ON v.match_id = m.id '
            'LEFT JOIN recoveries r ON r.match_id = m.id '
            "WHERE m.status IN ('pending', 'uncertain') "
            'AND v.id IS NULL AND r.id IS NULL'
        )
        ids = [row[0] for row in cursor.fetchall()]
        if ids:
            cursor.executemany(
                'DELETE FROM matches WHERE id = %s', [(match_id,) for match_id in ids]
            )

        # Items that only had pending suggestions return to the open pool.
        cursor.execute(
            "UPDATE lost_items SET status = 'reported' "
            "WHERE status = 'potential_match' AND NOT EXISTS ("
            "  SELECT 1 FROM matches m WHERE m.lost_item_id = lost_items.id"
            ")"
        )
        cursor.execute(
            "UPDATE found_items SET status = 'reported' "
            "WHERE status = 'potential_match' AND NOT EXISTS ("
            "  SELECT 1 FROM matches m WHERE m.found_item_id = found_items.id"
            ")"
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()

    return backfill_matches(db, limit=MAX_CANDIDATE_ITEMS, days=None)
