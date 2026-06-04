"""Preferences analyzer — learning style, difficulty acceptance, resource preference.

Inputs:  TaskFeedback (difficulty, completed_minutes, note)
         ResourceClick (resource_type, completed, duration_seconds)
Output:  memory_insight type = preferences
"""

from collections import Counter

from models import db, DailyTask, TaskFeedback, ResourceClick
from .common import data_volume_confidence, save_insight


def analyze_preferences(user_goal_id):
    """Analyze and persist preferences insight for *user_goal_id*."""
    # ── Gather data ──────────────────────────────────────────────────────────
    feedbacks = TaskFeedback.query.join(DailyTask).filter(
        DailyTask.user_goal_id == user_goal_id,
    ).order_by(TaskFeedback.completed_at).all()

    count = len(feedbacks)

    # ── Confidence ───────────────────────────────────────────────────────────
    confidence = data_volume_confidence(count)
    if confidence <= 0:
        save_insight(user_goal_id, 'preferences', {}, 0.0)
        return

    # ── 1. Difficulty distribution ───────────────────────────────────────────
    diff_counter = Counter(fb.difficulty for fb in feedbacks if fb.difficulty)

    # Consider None / just_right as "适中"
    just_right = diff_counter.get('just_right', 0) + diff_counter.get(None, 0)
    too_easy = diff_counter.get('too_easy', 0)
    too_hard = diff_counter.get('too_hard', 0)
    total_with_diff = just_right + too_easy + too_hard

    preferred_difficulty = '适中'
    if total_with_diff > 0:
        if too_easy / total_with_diff > 0.5:
            preferred_difficulty = '偏简单'
        elif too_hard / total_with_diff > 0.5:
            preferred_difficulty = '偏困难'

    # ── 2. Task acceptance (done vs skipped) ─────────────────────────────────
    tasks = DailyTask.query.filter_by(user_goal_id=user_goal_id).all()
    done = sum(1 for t in tasks if t.status == 'done')
    skipped = sum(1 for t in tasks if t.status == 'skipped')
    total_tasks = done + skipped
    completion_rate = round(done / total_tasks, 2) if total_tasks > 0 else 0

    # ── 3. Duration preference — minutes distribution ────────────────────────
    with_minutes = [fb.completed_minutes for fb in feedbacks
                    if fb.completed_minutes]
    preferred_duration = None
    if with_minutes:
        avg = sum(with_minutes) / len(with_minutes)
        preferred_duration = round(avg)

    data = {
        'difficulty_distribution': {
            'just_right': just_right,
            'too_easy': too_easy,
            'too_hard': too_hard,
        },
        'preferred_difficulty': preferred_difficulty,
        'task_completion_rate': completion_rate,
        'done_count': done,
        'skipped_count': skipped,
        'preferred_duration_minutes': preferred_duration,
        'average_completed_minutes': round(sum(with_minutes) / len(with_minutes)) if with_minutes else 0,
        'total_data_points': count,
    }

    # ── 4. Resource preference ────────────────────────────────────────────
    clicks = ResourceClick.query.filter_by(
        user_goal_id=user_goal_id,
    ).all()

    if clicks:
        type_counter = Counter(c.resource_type for c in clicks if c.resource_type)
        completed_by_type = Counter(c.resource_type for c in clicks if c.completed)
        total_clicks = len(clicks)

        # Find most clicked type
        most_clicked = type_counter.most_common(1)
        effective_mode = most_clicked[0][0] if most_clicked else None

        # Calculate completion rate per type
        resource_completion_rates = {}
        for rtype, cnt in type_counter.items():
            comp = completed_by_type.get(rtype, 0)
            resource_completion_rates[rtype] = round(comp / cnt, 2) if cnt > 0 else 0

        # Resource confidence: needs at least 3 clicks
        resource_confidence = min(0.3 + 0.05 * total_clicks, 0.9) if total_clicks >= 3 else 0

        data['resource_preference'] = {
            'effective_mode': effective_mode,
            'preferred_resource_type': effective_mode,
            'total_clicks': total_clicks,
            'type_distribution': dict(type_counter),
            'completion_rates': resource_completion_rates,
        }
        data['resource_confidence'] = resource_confidence
        data['resource_type_preference'] = {
            'preferred_resource_type': effective_mode,
            'confidence': resource_confidence,
        }

    save_insight(user_goal_id, 'preferences', data, confidence)
