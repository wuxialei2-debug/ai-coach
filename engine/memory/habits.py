"""Habits analyzer — learning time, frequency, and rhythm patterns.

Inputs:  TaskFeedback (completed_at, completed_minutes)
         LearningRecord (record_date, completed_count)
Output:  memory_insight type = habits
"""

from datetime import datetime

from models import db, DailyTask, TaskFeedback, LearningRecord
from .common import data_volume_confidence, save_insight


def analyze_habits(user_goal_id):
    """Analyze and persist habits insight for *user_goal_id*."""
    # ── Gather data ──────────────────────────────────────────────────────────
    feedbacks = TaskFeedback.query.join(DailyTask).filter(
        DailyTask.user_goal_id == user_goal_id,
        TaskFeedback.completed_minutes.isnot(None),
    ).order_by(TaskFeedback.completed_at).all()

    total_feedbacks = TaskFeedback.query.join(DailyTask).filter(
        DailyTask.user_goal_id == user_goal_id,
    ).count()

    records = LearningRecord.query.filter_by(
        user_goal_id=user_goal_id,
    ).order_by(LearningRecord.record_date).all()

    # ── Confidence ───────────────────────────────────────────────────────────
    confidence = data_volume_confidence(total_feedbacks)
    if confidence <= 0:
        save_insight(user_goal_id, 'habits', {}, 0.0)
        return

    # ── 1. Average learning duration ─────────────────────────────────────────
    minutes = [fb.completed_minutes for fb in feedbacks if fb.completed_minutes]
    avg_duration = round(sum(minutes) / len(minutes)) if minutes else 0

    # ── 2. Common learning time (hour-of-day distribution) ───────────────────
    hour_count = {}
    for fb in feedbacks:
        fb_time = fb.completed_at or datetime.utcnow()
        h = fb_time.hour
        hour_count[h] = hour_count.get(h, 0) + 1

    top_hours = sorted(hour_count, key=hour_count.get, reverse=True)
    best_hour = top_hours[0] if top_hours else None

    # ── 3. Frequency ─────────────────────────────────────────────────────────
    total_days = len(records)
    active_days = sum(1 for r in records if r.completed_count > 0)
    frequency = round(active_days / total_days, 2) if total_days > 0 else 0

    # ── 4. Weekday distribution ──────────────────────────────────────────────
    weekday_completed = {i: 0 for i in range(7)}
    for r in records:
        if r.completed_count > 0:
            wd = r.record_date.weekday()
            weekday_completed[wd] = weekday_completed.get(wd, 0) + 1

    # ── 5. Weekend vs weekday rates ──────────────────────────────────────────
    weekend_total = sum(1 for r in records if r.record_date.weekday() >= 5)
    weekday_total = total_days - weekend_total
    weekend_active = sum(
        1 for r in records if r.record_date.weekday() >= 5 and r.completed_count > 0
    )
    weekday_active = sum(
        1 for r in records if r.record_date.weekday() < 5 and r.completed_count > 0
    )

    data = {
        'average_duration_minutes': avg_duration,
        'common_hours': top_hours[:3],
        'best_hour': best_hour,
        'learning_frequency': frequency,
        'weekday_activity': {str(k): v for k, v in weekday_completed.items()},
        'weekday_rate': round(weekday_active / weekday_total, 2) if weekday_total > 0 else 0,
        'weekend_rate': round(weekend_active / weekend_total, 2) if weekend_total > 0 else 0,
        'total_data_points': total_feedbacks,
    }

    save_insight(user_goal_id, 'habits', data, confidence)
