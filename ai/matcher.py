"""FindMe AI matching engine.

Pure-Python similarity scoring between lost and found reports.  The module
is deliberately isolated from Flask: the only entry points used by
``app.py`` are ``find_potential_matches()``, ``backfill_matches()`` and
``rerun_all_matches()``.

The engine is built for *precision*: items are valuable, so a wrong match is
worse than no match.  It applies deterministic hard rules where possible and
a conservative evidence gate everywhere else:

* an identical serial number is a deterministic 100 % match;
* identical unique marks are near-deterministic (96 % floor);
* a conflicting serial number hard-rejects the pair;
* unknown fields contribute zero evidence instead of partial credit;
* generic names ("phone", "bag", "bottle") are weakened;
* a perceptual image hash (dHash) is used when both reports have a photo;
* at least two independent strong signals are required for fuzzy matches.

The minimum confidence stored in ``matches`` is ``MIN_MATCH_CONFIDENCE``.
"""

import re
from datetime import date, datetime, time, timedelta
from difflib import SequenceMatcher

# ── Tunables ──────────────────────────────────────────────────────────────
MIN_MATCH_CONFIDENCE = 50.0
MIN_EVIDENCE_SIGNALS = 5
MAX_CANDIDATE_ITEMS = 500
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

# A name made only of these words describes a whole class of items, not one
# specific item.  It still counts a little, but it cannot carry a match.
_GENERIC_NAME_WORDS = {
    'phone', 'phones', 'mobile', 'smartphone', 'laptop', 'computer', 'pc',
    'tablet', 'ipad', 'bag', 'bags', 'backpack', 'handbag', 'wallet', 'purse',
    'watch', 'ring', 'keys', 'key', 'book', 'books', 'notebook', 'glasses',
    'spectacles', 'camera', 'headphones', 'earphones', 'earbuds', 'charger',
    'umbrella', 'bottle', 'flask', 'cup', 'jacket', 'coat', 'hoodie',
    'sweater', 'shirt', 'trousers', 'shoes', 'sandals', 'cap', 'hat',
    'id', 'card', 'student', 'identity', 'calculator', 'power', 'bank',
    'cable', 'adapter', 'mouse', 'keyboard', 'usb',
    'flash', 'disk', 'drive', 'mat', 'towel', 'jersey', 'uniform',
}

# Values people type when they do not actually know an identifier.
_IDENTIFIER_NOISE = {
    'na', 'n/a', 'none', 'nil', 'null', 'unknown', 'noserial', 'notserial',
    'no', 'not', 'notavailable', 'notknown', 'x', 'xx', 'xxx', '0', '00',
    '0000', '000000', '1234', '12345', '123456', '12345678', 'abcdef',
}


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


def _normalize_identifier(value):
    """Compact identifier form: letters/digits only, lower-case.

    ``"SN-123 456"`` and ``"sn123456"`` are the same serial number.
    Returns '' for empty or obvious placeholder values.
    """
    if value is None:
        return ''
    compact = re.sub(r'[^a-z0-9]+', '', str(value).lower())
    if compact in _IDENTIFIER_NOISE:
        return ''
    return compact


def _is_generic_name(value):
    """True when a name contains only class words (no model/brand detail)."""
    words = _normalize(value).split()
    meaningful = [word for word in words if word not in _STOPWORDS]
    if not meaningful:
        return True
    return all(word in _GENERIC_NAME_WORDS for word in meaningful)


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def image_hash_similarity(hash1, hash2):
    """Similarity in [0, 1] between two 64-bit dHash hex strings.

    Photos of the same object usually differ by only a handful of bits.
    Missing hashes return 0.0: unknown evidence must never add confidence.
    """
    if not hash1 or not hash2:
        return 0.0
    h1 = str(hash1).strip().lower()
    h2 = str(hash2).strip().lower()
    if len(h1) != 16 or len(h2) != 16:
        return 0.0
    try:
        v1 = int(h1, 16)
        v2 = int(h2, 16)
    except ValueError:
        return 0.0

    distance = bin(v1 ^ v2).count('1')
    if distance <= 4:
        return 1.0
    if distance <= 8:
        return 0.9
    if distance <= 12:
        return 0.75
    if distance <= 18:
        return 0.5
    if distance <= 26:
        return 0.25
    return 0.0


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
    """1.0 same category, 0.05 different, 0.0 when either is unknown."""
    c1, c2 = _as_int(cat1), _as_int(cat2)
    if c1 is None or c2 is None:
        return 0.0
    return 1.0 if c1 == c2 else 0.05


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
        return 0.0
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
        return 0.0
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
    """Real visual similarity from the stored perceptual hashes.

    Both reports must carry a dHash; a missing photo is unknown evidence and
    therefore scores zero.  Shape has its own weighted factor.
    """
    if not lost and not found:
        return 0.0
    return round(image_hash_similarity(
        lost.get('image_hash'), found.get('image_hash')
    ), 4)


def serial_number_match(sn1, sn2):
    """1.0 exact serial, 0.0 conflict, None when unknown/placeholder."""
    s1 = _normalize_identifier(sn1)
    s2 = _normalize_identifier(sn2)
    if not s1 or not s2:
        return None
    return 1.0 if s1 == s2 else 0.0


def unique_marks_match(marks1, marks2):
    if not marks1 or not marks2:
        return None
    m1 = _normalize(marks1)
    m2 = _normalize(marks2)
    if not m1 or not m2 or m1 in _IDENTIFIER_NOISE or m2 in _IDENTIFIER_NOISE:
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
    """Score a lost/found pair on 12 factors whose weights sum to 1.00.

    Unknown fields always score zero.  The returned ``evidence`` count is
    the number of independent signal groups that agree, and is used by
    :func:`is_match_candidate` to reject weak coincidences.
    """
    lost = lost or {}
    found = found or {}

    weights = {
        'item_name': 0.20,
        'category': 0.08,
        'color': 0.08,
        'brand': 0.08,
        'model': 0.08,
        'description': 0.10,
        'location': 0.10,
        'date': 0.03,
        'time': 0.01,
        'appearance': 0.10,
        'shape': 0.04,
        'identical_features': 0.10,
    }
    assert abs(sum(weights.values()) - 1.0) < 1e-9, (
        f'AI matcher factor weights must sum to 1.00, got {sum(weights.values())}'
    )

    scores = {}
    explanations = []

    # ── Text / metadata factors ───────────────────────────────────────────
    name_score = text_similarity(lost.get('item_name'), found.get('item_name'))
    both_generic = (
        _is_generic_name(lost.get('item_name'))
        and _is_generic_name(found.get('item_name'))
    )
    generic_name = _is_generic_name(lost.get('item_name')) or _is_generic_name(
        found.get('item_name')
    )
    if both_generic:
        name_score = round(name_score * 0.35, 4)
        explanations.append(('Item name is generic (weak evidence)', name_score))
    elif generic_name:
        name_score = round(name_score * 0.75, 4)
        explanations.append(('Item name similarity (partly generic)', name_score))
    else:
        explanations.append(('Item name similarity', name_score))
    scores['item_name'] = name_score

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
    explanations.append(('Photo similarity (perceptual hash)', scores['appearance']))

    scores['shape'] = shape_match(lost.get('shape'), found.get('shape'))
    explanations.append(('Shape match', scores['shape']))

    id_score, id_explanations = identical_features_match(lost, found)
    scores['identical_features'] = id_score
    explanations.extend(id_explanations)

    total_score = sum(scores[key] * weights[key] for key in weights) * 100

    # ── Deterministic identifiers ─────────────────────────────────────────
    serial1 = _normalize_identifier(lost.get('serial_number'))
    serial2 = _normalize_identifier(found.get('serial_number'))
    serial_exact = bool(
        serial1 and serial2 and serial1 == serial2 and len(serial1) >= 3
    )
    serial_conflict = bool(serial1 and serial2 and serial1 != serial2)

    marks1 = _normalize(lost.get('unique_marks'))
    marks2 = _normalize(found.get('unique_marks'))
    marks_exact = bool(
        marks1 and marks2 and marks1 == marks2 and len(marks1) >= 6
        and marks1 not in _IDENTIFIER_NOISE and not _is_generic_name(marks1)
    )

    deterministic = serial_exact or marks_exact
    if serial_exact:
        total_score = 100.0
        explanations.append(('IDENTICAL SERIAL NUMBER - deterministic match', 1.0))
    elif marks_exact:
        total_score = max(total_score, 96.0)
        explanations.append(('IDENTICAL UNIQUE MARKS - near-deterministic', 1.0))

    # ── Conflicts ─────────────────────────────────────────────────────────
    cat1, cat2 = _as_int(lost.get('category_id')), _as_int(found.get('category_id'))
    category_conflict = bool(cat1 is not None and cat2 is not None and cat1 != cat2)

    brand1 = _normalize(lost.get('brand'))
    brand2 = _normalize(found.get('brand'))
    model1 = _normalize(lost.get('model'))
    model2 = _normalize(found.get('model'))
    brand_conflict = bool(brand1 and brand2 and scores['brand'] < 0.5)
    model_conflict = bool(model1 and model2 and scores['model'] < 0.5)

    conflicts = []
    if serial_conflict:
        total_score = min(total_score, 10.0)
        conflicts.append('serial numbers differ')
    if category_conflict:
        total_score *= 0.70
        conflicts.append('categories differ')
    if brand_conflict:
        total_score *= 0.85
        conflicts.append('brands differ')
    if model_conflict:
        total_score *= 0.88
        conflicts.append('models differ')
    if brand_conflict and model_conflict and not serial_conflict:
        # Same class of item but a different make and model is very unlikely
        # to be the same physical object.
        total_score = min(total_score, 35.0)

    # ── Independent evidence groups ───────────────────────────────────────
    evidence = set()
    if scores['item_name'] >= 0.60 and not both_generic:
        evidence.add('name')
    if scores['category'] >= 0.99:
        evidence.add('category')
    if scores['color'] >= 0.85:
        evidence.add('color')
    if scores['brand'] >= 0.85 or scores['model'] >= 0.85:
        evidence.add('brand/model')
    if scores['description'] >= 0.45:
        evidence.add('description')
    if scores['location'] >= 0.85:
        evidence.add('location')
    if scores['date'] >= 0.85 or scores['time'] >= 0.70:
        evidence.add('date/time')
    if scores['appearance'] >= 0.85:
        evidence.add('photo')
    if scores['shape'] >= 0.85:
        evidence.add('shape')
    if scores.get('unique_marks', 0) >= 0.90:
        evidence.add('unique marks')

    total_score = round(min(max(total_score, 0.0), 100.0), 2)

    # ── Human-readable explanation ────────────────────────────────────────
    explanation_lines = [
        f'{label}: {int(score * 100)}%' for label, score in explanations
    ]
    explanation_text = '\n'.join(f'• {line}' for line in explanation_lines)
    if deterministic:
        explanation_text += (
            '\n\n**Deterministic identifier match - this pair is certain.**'
        )
    if conflicts:
        explanation_text += '\n\nConflicts: ' + ', '.join(conflicts) + '.'
    explanation_text += (
        f'\n\nIndependent matching signals: {len(evidence)}'
        f' ({", ".join(sorted(evidence)) if evidence else "none"})'
    )
    explanation_text += f'\n\n**Overall Confidence: {int(total_score)}%**'

    if total_score >= 95:
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
        'deterministic': deterministic,
        'evidence': sorted(evidence),
        'evidence_count': len(evidence),
    }


def is_match_candidate(result):
    """Whether a scored pair is strong enough to store for human review.

    Deterministic identifiers always pass.  Fuzzy evidence must clear the
    confidence threshold *and* have several independent signal groups, which
    is what stops "two black phones" from becoming a match:

    * >= 50 % confidence with >= 5 agreeing groups;
    * >= 65 % confidence with >= 2 groups (e.g. exact photo hash + name);
    * >= 45 % confidence with >= 5 groups (coherent but sparse reports).
    """
    if not result or result.get('hard_conflict'):
        return False
    if result.get('deterministic'):
        return True

    score = result.get('confidence_score', 0)
    evidence = result.get('evidence_count', 0)
    if score >= MIN_MATCH_CONFIDENCE and evidence >= MIN_EVIDENCE_SIGNALS:
        return True
    # A very strong pair with two independent groups (for example an exact
    # photo hash plus matching name/brand) is still worth a human look.
    if score >= 65.0 and evidence >= 2:
        return True
    # Coherent but sparse reports: five independent groups agreeing (name,
    # category, colour, location and date/time) is a useful lead even when
    # the weighted score stays below the normal threshold.
    return score >= 45.0 and evidence >= 5


# ══════════════════════════════════════════════════════════════════════════
# Database pipeline
# ══════════════════════════════════════════════════════════════════════════

def _placeholders(values):
    return ', '.join(['%s'] * len(values))


def _attach_image_hashes(cursor, items):
    """Add the perceptual hash for each item's photo (when one exists).

    Hashes live in the ``images`` table so item rows stay unchanged.  A
    missing table (older deployment) simply means no photo evidence.
    """
    paths = sorted({
        item.get('image_path') for item in items if item.get('image_path')
    })
    if not paths:
        for item in items:
            item['image_hash'] = None
        return

    hashes = {}
    try:
        cursor.execute(
            f'SELECT path, dhash FROM images WHERE path IN ({_placeholders(paths)})',
            tuple(paths),
        )
        hashes = {row[0]: row[1] for row in cursor.fetchall()}
    except Exception:
        # Older database without the images table: fall back to no photo
        # evidence rather than failing the whole match run.
        hashes = {}

    for item in items:
        item['image_hash'] = hashes.get(item.get('image_path'))


def _fetch_items(cursor, table, limit=MAX_CANDIDATE_ITEMS):
    statuses = _placeholders(OPEN_STATUSES)
    cursor.execute(
        f'SELECT * FROM {table} WHERE status IN ({statuses}) '
        f'ORDER BY created_at DESC LIMIT {int(limit)}',
        OPEN_STATUSES,
    )
    items = rows_to_dicts(cursor, cursor.fetchall())
    _attach_image_hashes(cursor, items)
    return items


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
            _attach_image_hashes(cursor, [lost_item])
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
            _attach_image_hashes(cursor, [found_item])
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
