"""Shared helpers for the memory engine.

Broken out to avoid circular imports between engine.py and submodules.
"""

import json
from datetime import date, datetime
from models import db, MemoryInsight, LearningRecord


def data_volume_confidence(count):
    """Map record count to a base confidence score [0, 1]."""
    if count < 3:
        return 0.0
    if count < 10:
        return round(0.3 + 0.033 * (count - 3), 2)   # 0.30 → 0.53
    return round(min(0.55 + 0.04 * (count - 10), 0.95), 2)


def apply_confidence_decay(base_confidence, user_goal_id):
    """Reduce confidence when user has been inactive for a while."""
    if base_confidence <= 0:
        return 0.0

    last = LearningRecord.query.filter_by(user_goal_id=user_goal_id) \
        .order_by(LearningRecord.record_date.desc()).first()
    if not last:
        return 0.0

    days_since = (date.today() - last.record_date).days

    if days_since <= 3:
        return base_confidence
    if days_since <= 7:
        return round(base_confidence * 0.8, 2)
    if days_since <= 14:
        return round(base_confidence * 0.5, 2)
    if days_since <= 30:
        return round(base_confidence * 0.3, 2)
    return round(max(base_confidence * 0.1, 0.05), 2)


def save_insight(user_goal_id, insight_type, data, confidence):
    """Create or update a MemoryInsight row."""
    insight = MemoryInsight.query.filter_by(
        user_goal_id=user_goal_id, insight_type=insight_type,
    ).first()

    raw = json.dumps(data, ensure_ascii=False)
    if insight:
        insight.data = raw
        insight.confidence = confidence
        insight.updated_at = datetime.utcnow()
    else:
        insight = MemoryInsight(
            user_goal_id=user_goal_id,
            insight_type=insight_type,
            data=raw,
            confidence=confidence,
        )
        db.session.add(insight)

    db.session.commit()
