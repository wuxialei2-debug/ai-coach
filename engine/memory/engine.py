"""Memory Engine — unified entry point.

Provides:
    update(user_goal_id)    Re-run all analyzers for a goal.
    get_insights(user_goal_id)  Return current insights dict.

Analyzers are in sibling modules: habits, preferences, execution, growth_profile.
"""

import json
from models import db, MemoryInsight
from .common import apply_confidence_decay

from .habits import analyze_habits
from .preferences import analyze_preferences
from .execution import analyze_execution
from .growth_profile import analyze_growth_profile


# ── Public API ───────────────────────────────────────────────────────────────

def update(user_goal_id):
    """Run all memory analyzers for *user_goal_id* and persist insights."""
    analyze_habits(user_goal_id)
    analyze_preferences(user_goal_id)
    analyze_execution(user_goal_id)
    analyze_growth_profile(user_goal_id)


def get_insights(user_goal_id):
    """Return dict of {insight_type: {data, confidence, updated_at}}.

    Applies confidence decay for long-inactive goals.
    """
    rows = MemoryInsight.query.filter_by(user_goal_id=user_goal_id).all()
    result = {}
    for row in rows:
        conf = apply_confidence_decay(row.confidence, user_goal_id)
        result[row.insight_type] = {
            'data': json.loads(row.data) if row.data else {},
            'confidence': conf,
            'updated_at': row.updated_at.isoformat() if row.updated_at else None,
        }
    # Ensure every type is present in the response
    for t in ('habits', 'preferences', 'execution', 'growth_profile'):
        result.setdefault(t, {'data': {}, 'confidence': 0.0, 'updated_at': None})
    return result


# ── Confidence helpers ───────────────────────────────────────────────────────
