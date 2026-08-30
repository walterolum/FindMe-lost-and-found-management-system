import math
from difflib import SequenceMatcher
from datetime import datetime


def row_to_dict(cursor, row):
    if row is None:
        return None
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def rows_to_dicts(cursor, rows):
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def text_similarity(str1, str2):
    if not str1 or not str2:
        return 0.0
    s1 = str(str1).lower().strip()
    s2 = str(str2).lower().strip()
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1, s2).ratio()


def category_match(cat1, cat2):
    if cat1 and cat2:
        try:
            if int(cat1) == int(cat2):
                return 1.0
        except (ValueError, TypeError):
            pass
    return 0.3


def color_match(color1, color2):
    if not color1 or not color2:
        return 0.0
    c1 = str(color1).lower().strip()
    c2 = str(color2).lower().strip()
    if c1 == c2:
        return 1.0
    color_groups = {
        'black': ['black', 'dark', 'charcoal', 'midnight'],
        'white': ['white', 'light', 'cream', 'ivory'],
        'blue': ['blue', 'navy', 'cyan', 'azure'],
        'red': ['red', 'darkred', 'crimson', 'scarlet'],
        'green': ['green', 'darkgreen', 'forest', 'olive'],
        'silver': ['silver', 'gray', 'grey', 'gray', 'metallic'],
        'gold': ['gold', 'golden', 'yellow', 'brass'],
        'brown': ['brown', 'tan', 'beige', 'darkbrown'],
        'pink': ['pink', 'rose', 'magenta'],
        'purple': ['purple', 'violet', 'lavender'],
    }
    for group in color_groups.values():
        if c1 in group and c2 in group:
            return 0.8
    return 0.0


def brand_match(brand1, brand2):
    if not brand1 or not brand2:
        return 0.0
    b1 = str(brand1).lower().strip()
    b2 = str(brand2).lower().strip()
    if b1 == b2:
        return 1.0
    if b1 in b2 or b2 in b1:
        return 0.9
    return text_similarity(b1, b2)


def location_match(loc_id1, loc_id2, loc_detail1=None, loc_detail2=None):
    if not loc_id1 or not loc_id2:
        return 0.0
    if int(loc_id1) == int(loc_id2):
        base = 1.0
    else:
        base = 0.2
    bonus = 0.0
    if loc_detail1 and loc_detail2:
        bonus = text_similarity(loc_detail1, loc_detail2) * 0.3
    return min(base + bonus, 1.0)


def date_proximity(date1_str, date2_str):
    if not date1_str or not date2_str:
        return 0.3
    try:
        d1 = datetime.strptime(str(date1_str), '%Y-%m-%d')
        d2 = datetime.strptime(str(date2_str), '%Y-%m-%d')
        diff_days = abs((d1 - d2).days)
        if diff_days == 0:
            return 1.0
        elif diff_days <= 1:
            return 0.95
        elif diff_days <= 3:
            return 0.85
        elif diff_days <= 7:
            return 0.7
        elif diff_days <= 14:
            return 0.5
        elif diff_days <= 30:
            return 0.3
        else:
            return 0.1
    except (ValueError, TypeError):
        return 0.3


def time_proximity(time1, time2):
    if not time1 or not time2:
        return 0.3
    try:
        t1 = datetime.strptime(str(time1), '%H:%M')
        t2 = datetime.strptime(str(time2), '%H:%M')
        diff_minutes = abs((t1 - t2).total_seconds()) / 60
        if diff_minutes <= 30:
            return 1.0
        elif diff_minutes <= 60:
            return 0.9
        elif diff_minutes <= 120:
            return 0.7
        elif diff_minutes <= 360:
            return 0.5
        else:
            return 0.2
    except (ValueError, TypeError):
        return 0.3


def description_similarity(desc1, desc2):
    if not desc1 or not desc2:
        return 0.0
    s1 = str(desc1).lower().strip()
    s2 = str(desc2).lower().strip()
    if not s1 or not s2:
        return 0.0
    words1 = set(s1.split())
    words2 = set(s2.split())
    if not words1 or not words2:
        return text_similarity(s1, s2)
    intersection = words1 & words2
    union = words1 | words2
    jaccard = len(intersection) / len(union) if union else 0
    base_text = text_similarity(s1, s2)
    return jaccard * 0.6 + base_text * 0.4


def image_similarity_simulated(img_path1, img_path2):
    if not img_path1 or not img_path2:
        return 0.3
    import os
    name1 = os.path.basename(img_path1).lower()
    name2 = os.path.basename(img_path2).lower()
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
    keywords = ['phone', 'laptop', 'tablet', 'wallet', 'bag', 'watch', 'ring', 'keys', 'book', 'glasses', 'camera', 'headphones']
    for kw in keywords:
        k1 = kw in name1_no_ext
        k2 = kw in name2_no_ext
        if k1 and k2:
            return 0.6
        elif k1 or k2:
            return 0.35
    return 0.25


def appearance_match(lost, found):
    if not lost and not found:
        return 0.0
    image_score = image_similarity_simulated(lost.get('image_path'), found.get('image_path'))
    shape_score = shape_match(lost.get('shape'), found.get('shape'))
    combined = image_score * 0.6 + shape_score * 0.4
    return round(min(max(combined, 0.0), 1.0), 4)


def shape_match(shape1, shape2):
    if not shape1 or not shape2:
        return 0.0
    s1 = str(shape1).lower().strip()
    s2 = str(shape2).lower().strip()
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    shape_aliases = {
        'rectangular': ['rectangular', 'rectangle', 'oblong', 'rectangular-shaped'],
        'round': ['round', 'circular', 'circle', 'oval', 'elliptical'],
        'cylindrical': ['cylindrical', 'cylinder', 'tube', 'tubular'],
        'square': ['square', 'box-shaped', 'cubical'],
        'triangular': ['triangular', 'triangle', 'pyramid'],
        'irregular': ['irregular', 'asymmetric', 'irregularly shaped'],
        'flat': ['flat', 'thin', 'pancake', 'disc-shaped'],
        'compact': ['compact', 'small', 'tiny', 'miniature'],
    }
    for group in shape_aliases.values():
        if s1 in group and s2 in group:
            return 0.85
    return text_similarity(s1, s2)


def serial_number_match(sn1, sn2):
    if not sn1 or not sn2:
        return None
    s1 = str(sn1).strip()
    s2 = str(sn2).strip()
    if not s1 or not s2:
        return None
    if s1 == s2:
        return 1.0
    return 0.0


def unique_marks_match(marks1, marks2):
    if not marks1 or not marks2:
        return None
    m1 = str(marks1).lower().strip()
    m2 = str(marks2).lower().strip()
    if not m1 or not m2:
        return None
    return text_similarity(m1, m2)


def approximate_value_match(val1, val2):
    if val1 is None or val2 is None:
        return None
    try:
        v1 = float(val1)
        v2 = float(val2)
        if v1 == 0 and v2 == 0:
            return 1.0
        if v1 == 0 or v2 == 0:
            return 0.1
        ratio = min(v1, v2) / max(v1, v2)
        if ratio >= 0.9:
            return 1.0
        elif ratio >= 0.7:
            return 0.8
        elif ratio >= 0.5:
            return 0.5
        elif ratio >= 0.3:
            return 0.3
        else:
            return 0.1
    except (ValueError, TypeError):
        return None


def identical_features_match(lost, found):
    if not lost and not found:
        return 0.0, []
    scores = {}
    explanations = []
    sn = serial_number_match(lost.get('serial_number'), found.get('serial_number'))
    if sn is not None:
        scores['serial_number'] = sn
        explanations.append(('Serial number match', sn))
    marks = unique_marks_match(lost.get('unique_marks'), found.get('unique_marks'))
    if marks is not None:
        scores['unique_marks'] = marks
        explanations.append(('Unique marks similarity', marks))
    val = approximate_value_match(lost.get('approximate_value'), found.get('approximate_value'))
    if val is not None:
        scores['approximate_value'] = val
        explanations.append(('Approximate value match', val))
    if not scores:
        return 0.0, []
    total = sum(scores.values()) / len(scores) if scores else 0.0
    return round(total, 4), explanations


def compute_match_score(lost, found):
    explanations = []
    weights = {
        'item_name': 0.20,
        'category': 0.10,
        'color': 0.08,
        'brand': 0.08,
        'model': 0.06,
        'description': 0.10,
        'location': 0.10,
        'date': 0.04,
        'time': 0.02,
        'appearance': 0.08,
        'shape': 0.04,
        'identical_features': 0.06,
    }
    scores = {}

    scores['item_name'] = text_similarity(lost.get('item_name'), found.get('item_name'))
    explanations.append(('Item name similarity', scores['item_name']))

    scores['category'] = category_match(lost.get('category_id'), found.get('category_id'))
    explanations.append(('Same item category', scores['category']))

    scores['color'] = color_match(lost.get('color'), found.get('color'))
    explanations.append(('Color match', scores['color']))

    scores['brand'] = brand_match(lost.get('brand'), found.get('brand'))
    explanations.append(('Brand similarity', scores['brand']))

    model_sim = text_similarity(lost.get('model'), found.get('model'))
    scores['model'] = model_sim
    explanations.append(('Model similarity', scores['model']))

    desc_sim = description_similarity(lost.get('description'), found.get('description'))
    scores['description'] = desc_sim
    explanations.append(('Description similarity', scores['description']))

    scores['location'] = location_match(
        lost.get('location_id'), found.get('location_id'),
        lost.get('location_detail'), found.get('location_detail')
    )
    explanations.append(('Location similarity', scores['location']))

    scores['date'] = date_proximity(lost.get('date_lost'), found.get('date_found'))
    explanations.append(('Date proximity', scores['date']))

    scores['time'] = time_proximity(lost.get('time_lost'), found.get('time_found'))
    explanations.append(('Time proximity', scores['time']))

    scores['appearance'] = appearance_match(lost, found)
    explanations.append(('Appearance/image similarity', scores['appearance']))

    scores['shape'] = shape_match(lost.get('shape'), found.get('shape'))
    explanations.append(('Shape match', scores['shape']))

    id_score, id_explanations = identical_features_match(lost, found)
    scores['identical_features'] = id_score
    explanations.extend(id_explanations)

    total_score = sum(scores[k] * weights[k] for k in weights) * 100
    total_score = min(max(total_score, 0), 100)

    explanation_lines = []
    for label, score in explanations:
        pct = int(score * 100)
        explanation_lines.append(f'{label}: {pct}%')

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
        'confidence_score': round(total_score, 2),
        'match_level': level,
        'explanation': explanation_text,
        'scores': scores,
    }


def find_potential_matches(item_type, item_id, db):
    cursor = db.cursor()

    lost_item = None
    found_item = None

    if item_type == 'lost':
        cursor.execute('SELECT * FROM lost_items WHERE id = %s', (item_id,))
        lost_item = row_to_dict(cursor, cursor.fetchone())
    elif item_type == 'found':
        cursor.execute('SELECT * FROM found_items WHERE id = %s', (item_id,))
        found_item = row_to_dict(cursor, cursor.fetchone())

    if not lost_item and not found_item:
        cursor.close()
        return []

    cursor.execute(
        'SELECT lost_item_id, found_item_id FROM matches WHERE status IN ("pending", "approved")'
    )
    existing_matches = set()
    for row in cursor.fetchall():
        existing_matches.add((row[0], row[1]))

    new_matches = []

    if item_type == 'lost' and lost_item:
        cursor.execute(
            'SELECT * FROM found_items WHERE status IN ("reported", "under_review", "potential_match", "match_pending_approval") ORDER BY created_at DESC LIMIT 200'
        )
        found_items = rows_to_dicts(cursor, cursor.fetchall())

        for found in found_items:
            pair = (item_id, found['id'])
            reverse_pair = (found['id'], item_id)
            if pair in existing_matches or reverse_pair in existing_matches:
                continue

            result = compute_match_score(lost_item, found)

            if result['confidence_score'] >= 30:
                cursor.execute(
                    'INSERT INTO matches (lost_item_id, found_item_id, confidence_score, match_level, explanation, status) VALUES (%s, %s, %s, %s, %s, "pending")',
                    (item_id, found['id'], result['confidence_score'], result['match_level'], result['explanation'])
                )
                db.commit()
                match_id = cursor.lastrowid
                new_matches.append({
                    'match_id': match_id,
                    'lost_item_id': item_id,
                    'found_item_id': found['id'],
                    'confidence_score': result['confidence_score'],
                    'match_level': result['match_level'],
                })

                cursor.execute(
                    'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
                    (found['finder_id'], 'Potential Match Found', f'A found item may match your report. Confidence: {int(result["confidence_score"])}%', 'match', 'match', match_id)
                )
                cursor.execute(
                    'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
                    (lost_item['reporter_id'], 'Potential Match Found', f'A found item may match your lost item report. Confidence: {int(result["confidence_score"])}%', 'match', 'match', match_id)
                )

        db.commit()

    elif item_type == 'found' and found_item:
        cursor.execute(
            'SELECT * FROM lost_items WHERE status IN ("reported", "under_review", "potential_match", "match_pending_approval") ORDER BY created_at DESC LIMIT 200'
        )
        lost_items = rows_to_dicts(cursor, cursor.fetchall())

        for lost in lost_items:
            pair = (lost['id'], item_id)
            reverse_pair = (item_id, lost['id'])
            if pair in existing_matches or reverse_pair in existing_matches:
                continue

            result = compute_match_score(lost, found_item)

            if result['confidence_score'] >= 30:
                cursor.execute(
                    'INSERT INTO matches (lost_item_id, found_item_id, confidence_score, match_level, explanation, status) VALUES (%s, %s, %s, %s, %s, "pending")',
                    (lost['id'], item_id, result['confidence_score'], result['match_level'], result['explanation'])
                )
                db.commit()
                match_id = cursor.lastrowid
                new_matches.append({
                    'match_id': match_id,
                    'lost_item_id': lost['id'],
                    'found_item_id': item_id,
                    'confidence_score': result['confidence_score'],
                    'match_level': result['match_level'],
                })

                cursor.execute(
                    'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
                    (lost['reporter_id'], 'Potential Match Found', f'A lost item may match your found item report. Confidence: {int(result["confidence_score"])}%', 'match', 'match', match_id)
                )
                cursor.execute(
                    'INSERT INTO notifications (user_id, title, message, type, related_type, related_id) VALUES (%s, %s, %s, %s, %s, %s)',
                    (found_item['finder_id'], 'Potential Match Found', f'A lost item may match the item you found. Confidence: {int(result["confidence_score"])}%', 'match', 'match', match_id)
                )

        db.commit()

    cursor.close()
    return new_matches


def rerun_all_matches(db):
    cursor = db.cursor()
    cursor.execute('DELETE FROM matches')
    db.commit()
    cursor.close()

    cursor = db.cursor()
    cursor.execute('SELECT * FROM lost_items WHERE status IN ("reported", "under_review", "potential_match", "match_pending_approval") ORDER BY created_at DESC LIMIT 200')
    lost_items = rows_to_dicts(cursor, cursor.fetchall())
    cursor.execute('SELECT * FROM found_items WHERE status IN ("reported", "under_review", "potential_match", "match_pending_approval") ORDER BY created_at DESC LIMIT 200')
    found_items = rows_to_dicts(cursor, cursor.fetchall())
    cursor.close()

    all_results = []
    for lost in lost_items:
        for found in found_items:
            result = compute_match_score(lost, found)
            if result['confidence_score'] >= 30:
                all_results.append({
                    'lost_item_id': lost['id'],
                    'found_item_id': found['id'],
                    **result
                })

    cursor = db.cursor()
    for r in all_results:
        cursor.execute(
            'INSERT INTO matches (lost_item_id, found_item_id, confidence_score, match_level, explanation, status) VALUES (%s, %s, %s, %s, %s, "pending")',
            (r['lost_item_id'], r['found_item_id'], r['confidence_score'], r['match_level'], r['explanation'])
        )
    db.commit()
    cursor.close()
    return len(all_results)