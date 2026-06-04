"""Execution analyzer — completion rates, streaks, stage patterns.

Inputs:  LearningRecord (completed_count, total_count, streak_days, total_minutes)
         DailyTask (status, estimated_minutes)
         RoadmapStage (status, name)
Output:  memory_insight type = execution
"""

from collections import defaultdict

from models import db, DailyTask, LearningRecord, RoadmapStage
from .common import data_volume_confidence, save_insight


def analyze_execution(user_goal_id):
    """Analyze and persist execution insight for *user_goal_id*."""
    # ── Gather data ──────────────────────────────────────────────────────────
    records = LearningRecord.query.filter_by(
        user_goal_id=user_goal_id,
    ).order_by(LearningRecord.record_date).all()

    tasks = DailyTask.query.filter_by(user_goal_id=user_goal_id).all()

    record_count = len(records)

    # ── Confidence ───────────────────────────────────────────────────────────
    confidence = data_volume_confidence(record_count)
    if confidence <= 0:
        save_insight(user_goal_id, 'execution', {}, 0.0)
        return

    # ── 1. Average completion rate ───────────────────────────────────────────
    rates = []
    for r in records:
        if r.total_count > 0:
            rates.append(r.completed_count / r.total_count)
    avg_completion = round(sum(rates) / len(rates), 2) if rates else 0

    # ── 2. Streak info ───────────────────────────────────────────────────────
    current_streak = records[-1].streak_days if records else 0
    max_streak = max(r.streak_days for r in records) if records else 0

    # ── 3. Best task duration ────────────────────────────────────────────────
    completion_by_duration = defaultdict(lambda: {'done': 0, 'total': 0})
    for t in tasks:
        bucket = _duration_bucket(t.estimated_minutes or 0)
        completion_by_duration[bucket]['total'] += 1
        if t.status == 'done':
            completion_by_duration[bucket]['done'] += 1

    duration_rates = {}
    best_duration = None
    best_rate = 0
    for bucket, vals in completion_by_duration.items():
        rate = vals['done'] / vals['total'] if vals['total'] > 0 else 0
        duration_rates[bucket] = round(rate, 2)
        if rate > best_rate and vals['total'] >= 2:
            best_rate = rate
            best_duration = bucket

    # ── 4. Break-prone stages ────────────────────────────────────────────────
    stages = RoadmapStage.query.filter_by(user_goal_id=user_goal_id).all()
    stage_analysis = []
    for s in stages:
        stage_tasks = [t for t in tasks if t.stage_id == s.id]
        s_done = sum(1 for t in stage_tasks if t.status == 'done')
        s_skipped = sum(1 for t in stage_tasks if t.status == 'skipped')
        s_total = s_done + s_skipped
        s_rate = round(s_done / s_total, 2) if s_total > 0 else 0
        stage_analysis.append({
            'stage_name': s.name,
            'completion_rate': s_rate,
            'done_count': s_done,
            'skipped_count': s_skipped,
        })

    data = {
        'average_completion_rate': avg_completion,
        'current_streak': current_streak,
        'max_streak': max_streak,
        'best_duration_minutes': best_duration,
        'duration_completion_rates': duration_rates,
        'stage_analysis': stage_analysis,
        'total_study_days': record_count,
        'total_tasks': len(tasks),
    }

    save_insight(user_goal_id, 'execution', data, confidence)


def _duration_bucket(minutes):
    """Bucket a duration into a label for grouping."""
    if minutes <= 10:
        return '≤10'
    if minutes <= 20:
        return '11-20'
    if minutes <= 30:
        return '21-30'
    if minutes <= 45:
        return '31-45'
    if minutes <= 60:
        return '46-60'
    return '>60'
