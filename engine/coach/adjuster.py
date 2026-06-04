"""AI Coach adjuster — generates dynamic adjustment strategies.

Reads from Memory Engine insights and raw learning data to produce
task-generation adjustments that personalize each day's learning plan.

Exports:
    get_adjustments(goal_id) -> dict
"""

from datetime import date, timedelta
from models import DailyTask, TaskFeedback, LearningRecord


def get_adjustments(goal_id):
    """Generate adjustment strategy for *goal_id*.

    Checks rules in priority order and returns the first match.
    If no rule matches, returns a neutral (no-adjustment) strategy.

    Returns:
        dict with keys:
            task_multiplier (float):  multiplier for daily task duration
            difficulty (str):         "easy" | "normal" | "hard"
            review_mode (bool):       include review content
            challenge_mode (bool):    include challenge content
            reason (str):             human-readable explanation
    """
    default = {
        'task_multiplier': 1.0,
        'difficulty': 'normal',
        'review_mode': False,
        'challenge_mode': False,
        'reason': '',
    }

    # ── Gather data ──────────────────────────────────────────────────────

    # Recent feedback (up to 3 most recent, newest first)
    recent_feedbacks = TaskFeedback.query.join(DailyTask).filter(
        DailyTask.user_goal_id == goal_id,
    ).order_by(TaskFeedback.completed_at.desc()).limit(3).all()

    # Learning records from the last 7 days
    last_week = date.today() - timedelta(days=7)
    recent_records = LearningRecord.query.filter(
        LearningRecord.user_goal_id == goal_id,
        LearningRecord.record_date >= last_week,
    ).order_by(LearningRecord.record_date).all()

    # All records (newest first) for streak and long-term rate
    all_records = LearningRecord.query.filter_by(
        user_goal_id=goal_id,
    ).order_by(LearningRecord.record_date.desc()).all()

    # ── Rule 4: Long inactivity (highest priority) ───────────────────────
    if all_records:
        days_since = (date.today() - all_records[0].record_date).days
    else:
        days_since = 999

    if days_since >= 5:
        return {
            'task_multiplier': 0.5,
            'difficulty': 'easy',
            'review_mode': False,
            'challenge_mode': False,
            'reason': '长时间未学习，降低重新开始门槛。',
        }

    # ── Rule 2: Last 3 feedbacks all too_hard ────────────────────────────
    if len(recent_feedbacks) >= 3:
        difficulties = [fb.difficulty for fb in recent_feedbacks]
        if all(d == 'too_hard' for d in difficulties):
            return {
                'task_multiplier': 0.7,
                'difficulty': 'easy',
                'review_mode': True,
                'challenge_mode': False,
                'reason': '近期任务偏难，拆分知识点并增加讲解。',
            }

    # ── Rule 3: Last 3 feedbacks all too_easy ────────────────────────────
    if len(recent_feedbacks) >= 3:
        difficulties = [fb.difficulty for fb in recent_feedbacks]
        if all(d == 'too_easy' for d in difficulties):
            return {
                'task_multiplier': 1.3,
                'difficulty': 'hard',
                'review_mode': False,
                'challenge_mode': True,
                'reason': '近期任务过于简单，增加挑战内容。',
            }

    # ── Rule 1: Low completion rate last 7 days ──────────────────────────
    if recent_records:
        with_work = [r for r in recent_records if r.total_count > 0]
        if with_work:
            done_ratio = sum(1 for r in with_work if r.completed_count > 0) / len(with_work)
            if done_ratio < 0.4:
                return {
                    'task_multiplier': 0.5,
                    'difficulty': 'easy',
                    'review_mode': True,
                    'challenge_mode': False,
                    'reason': '最近学习压力较大，先降低任务量并增加复习。',
                }

    # ── Rule 5: High long-term performance ───────────────────────────────
    if all_records:
        with_work = [r for r in all_records if r.total_count > 0]
        if with_work:
            done_ratio = sum(1 for r in with_work if r.completed_count > 0) / len(with_work)
            current_streak = all_records[0].streak_days

            if done_ratio > 0.9 and current_streak >= 7:
                return {
                    'task_multiplier': 1.5,
                    'difficulty': 'hard',
                    'review_mode': False,
                    'challenge_mode': True,
                    'reason': '学习状态优秀，增加挑战任务。',
                }

    return default
