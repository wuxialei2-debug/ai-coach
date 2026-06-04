"""Growth profile — comprehensive analysis combining all dimensions.

Inputs:  All other memory insights (habits, preferences, execution)
         LearningRecord (completed_count, total_count, streak_days)
Output:  memory_insight type = growth_profile

CAUTION: All labels here are *dynamic analytical conclusions*, NOT fixed
user types. They change automatically as new data arrives and must never
be used as permanent user tags.
"""

from models import db, DailyTask, TaskFeedback, LearningRecord, MemoryInsight
from .common import save_insight


def analyze_growth_profile(user_goal_id):
    """Analyze and persist growth profile for *user_goal_id*."""
    # ── Gather supporting insights ───────────────────────────────────────────
    exec_insight = MemoryInsight.query.filter_by(
        user_goal_id=user_goal_id, insight_type='execution',
    ).first()
    pref_insight = MemoryInsight.query.filter_by(
        user_goal_id=user_goal_id, insight_type='preferences',
    ).first()

    total_feedbacks = TaskFeedback.query.join(DailyTask).filter(
        DailyTask.user_goal_id == user_goal_id,
    ).count()

    # ── Minimal data guard ───────────────────────────────────────────────────
    records = LearningRecord.query.filter_by(
        user_goal_id=user_goal_id,
    ).order_by(LearningRecord.record_date).all()

    if total_feedbacks < 3:
        save_insight(user_goal_id, 'growth_profile', {}, 0.0)
        return

    # ── Confidence: average of available sub-insights ────────────────────────
    confidences = []
    for ins in (exec_insight, pref_insight):
        if ins and ins.confidence > 0:
            confidences.append(ins.confidence)
    confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.3

    # ── 1. Execution level ───────────────────────────────────────────────────
    rates = []
    for r in records:
        if r.total_count > 0:
            rates.append(r.completed_count / r.total_count)
    avg_completion = round(sum(rates) / len(rates), 2) if rates else 0

    current_streak = records[-1].streak_days if records else 0
    max_streak = max(r.streak_days for r in records) if records else 0

    if avg_completion >= 0.8 and current_streak >= 5:
        execution_level = '优秀'
    elif avg_completion >= 0.6 and current_streak >= 3:
        execution_level = '良好'
    elif avg_completion >= 0.4:
        execution_level = '一般'
    else:
        execution_level = '需要加强'

    # ── 2. Growth trend (first half vs second half) ──────────────────────────
    mid = len(rates) // 2
    if mid >= 1 and len(rates) > mid:
        first_half = sum(rates[:mid]) / mid
        second_half = sum(rates[mid:]) / (len(rates) - mid)
        if second_half > first_half + 0.1:
            trend = '持续进步'
        elif second_half < first_half - 0.1:
            trend = '需要关注'
        else:
            trend = '保持稳定'
    else:
        trend = '数据不足'

    # ── 3. Recommended pace ──────────────────────────────────────────────────
    if avg_completion >= 0.8 and current_streak >= 7:
        recommended_pace = '可适当增加学习量'
    elif avg_completion <= 0.4:
        recommended_pace = '建议减少单次学习量'
    else:
        recommended_pace = '保持当前节奏'

    # ── 4. Completion probability ― a heuristic estimate ─────────────────
    if max_streak >= 14:
        probability = '很高'
    elif max_streak >= 7:
        probability = '较高'
    elif max_streak >= 3:
        probability = '一般'
    elif max_streak >= 1:
        probability = '较低'
    else:
        probability = '暂无数据'

    data = {
        'execution_level': execution_level,
        'growth_trend': trend,
        'recommended_pace': recommended_pace,
        'completion_probability': probability,
        'average_completion_rate': avg_completion,
        'current_streak': current_streak,
        'max_streak': max_streak,
        'total_study_days': len(records),
        'total_feedbacks': total_feedbacks,
    }

    save_insight(user_goal_id, 'growth_profile', data, confidence)
