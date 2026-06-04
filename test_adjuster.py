"""Adjuster end-to-end self-test.

Run with: python test_adjuster.py
Requires: the app's working directory as CWD.
"""

import sys
import os
from datetime import date, timedelta, datetime

PROJECT_DIR = r"C:\Users\luojinfa\Desktop\AI  Coach"
sys.path.insert(0, PROJECT_DIR)

from app import create_app
from models import db, Skill, UserGoal, RoadmapStage, DailyTask, TaskFeedback, \
    LearningRecord
from engine.coach.adjuster import get_adjustments


def _clean_data():
    for model in (TaskFeedback, LearningRecord, DailyTask, RoadmapStage, UserGoal):
        model.query.delete()
    db.session.commit()


def _create_goal(app):
    """Create a minimal goal with one stage."""
    skill = Skill.query.first()
    if not skill:
        skill = Skill(name='Python', description='Test', icon='PY', category='编程')
        db.session.add(skill)
        db.session.commit()

    goal = UserGoal(
        skill_id=skill.id, level='零基础',
        daily_minutes=20, target_months=3, status='active',
    )
    db.session.add(goal)
    db.session.flush()

    stage = RoadmapStage(
        user_goal_id=goal.id, skill_id=skill.id,
        stage_order=1, name='基础语法', status='current',
        knowledge_points='["变量","数据类型","运算符"]',
    )
    db.session.add(stage)
    db.session.commit()
    return goal.id


def _add_feedback(goal_id, difficulty, days_ago=0, completed_minutes=15):
    """Add a DailyTask + TaskFeedback pair."""
    d = date.today() - timedelta(days=days_ago)
    task = DailyTask(
        user_goal_id=goal_id,
        stage_id=1,
        date=d,
        title='Test task',
        content='test',
        practice='test',
        estimated_minutes=20,
        status='done',
    )
    db.session.add(task)
    db.session.flush()

    fb = TaskFeedback(
        task_id=task.id,
        difficulty=difficulty,
        completed_minutes=completed_minutes,
        completed_at=datetime.now() - timedelta(days=days_ago),
    )
    db.session.add(fb)

    # Add accompanying learning record
    record = LearningRecord(
        user_goal_id=goal_id,
        record_date=d,
        completed_count=1,
        total_count=1,
        total_minutes=completed_minutes,
        streak_days=1,
    )
    db.session.add(record)
    db.session.commit()


def _add_learning_records(goal_id, days_data):
    """Add multiple learning records from a list of (days_ago, completed, total, streak)."""
    for days_ago, completed, total, streak in days_data:
        d = date.today() - timedelta(days=days_ago)
        record = LearningRecord(
            user_goal_id=goal_id,
            record_date=d,
            completed_count=completed,
            total_count=total,
            total_minutes=20 if completed > 0 else 0,
            streak_days=streak,
        )
        db.session.add(record)
    db.session.commit()


# ── Test scenarios ────────────────────────────────────────────────────────────

def test_rule1_low_completion():
    """Rule 1: Last 7 days completion rate < 40%."""
    print("\n[Test 1] Low completion rate (< 40%)...", end=' ')
    _clean_data()
    gid = _create_goal(app)
    # 5 records, only 1 completed
    _add_learning_records(gid, [
        (0, 1, 1, 1),
        (1, 0, 1, 0),
        (2, 1, 1, 1),  # the 40% line — 2/5 = 0.4, not < 0.4
        (3, 0, 1, 0),
        (4, 0, 1, 0),
    ])
    adj = get_adjustments(gid)
    # 2/5 = 0.4, which is NOT < 0.4
    # Need a lower rate
    print(f"multiplier={adj['task_multiplier']} (need < 1)", end=' ')
    # This one won't trigger since 2/5 = 0.4
    # Let me add worse data
    _add_learning_records(gid, [(5, 0, 1, 0)])
    adj = get_adjustments(gid)
    # Now 2/6 ≈ 0.33 < 0.4
    passed = (adj['task_multiplier'] < 1 and adj['review_mode'] is True
              and adj['difficulty'] == 'easy')
    print(f"multiplier={adj['task_multiplier']} review={adj['review_mode']} diff={adj['difficulty']}",
          'PASS' if passed else 'FAIL')
    return passed


def test_rule2_too_hard():
    """Rule 2: Last 3 feedbacks all too_hard."""
    print("\n[Test 2] Last 3 feedbacks all too_hard...", end=' ')
    _clean_data()
    gid = _create_goal(app)
    # Add 3 recent feedbacks all too_hard
    for i in range(3):
        _add_feedback(gid, 'too_hard', days_ago=i, completed_minutes=10)

    adj = get_adjustments(gid)
    passed = (adj['task_multiplier'] == 0.7 and adj['difficulty'] == 'easy'
              and adj['review_mode'] is True)
    print(f"multiplier={adj['task_multiplier']} diff={adj['difficulty']} review={adj['review_mode']}",
          'PASS' if passed else 'FAIL')
    return passed


def test_rule3_too_easy():
    """Rule 3: Last 3 feedbacks all too_easy."""
    print("\n[Test 3] Last 3 feedbacks all too_easy...", end=' ')
    _clean_data()
    gid = _create_goal(app)
    for i in range(3):
        _add_feedback(gid, 'too_easy', days_ago=i, completed_minutes=5)

    adj = get_adjustments(gid)
    passed = (adj['task_multiplier'] == 1.3 and adj['difficulty'] == 'hard'
              and adj['challenge_mode'] is True)
    print(f"multiplier={adj['task_multiplier']} diff={adj['difficulty']} challenge={adj['challenge_mode']}",
          'PASS' if passed else 'FAIL')
    return passed


def test_rule4_inactivity():
    """Rule 4: No learning record in 5+ days."""
    print("\n[Test 4] 5+ days inactivity...", end=' ')
    _clean_data()
    gid = _create_goal(app)
    # Add a record from 6 days ago
    d = date.today() - timedelta(days=6)
    record = LearningRecord(
        user_goal_id=gid, record_date=d,
        completed_count=1, total_count=1,
        total_minutes=20, streak_days=1,
    )
    db.session.add(record)
    db.session.commit()

    adj = get_adjustments(gid)
    passed = (adj['task_multiplier'] == 0.5 and adj['difficulty'] == 'easy')
    print(f"multiplier={adj['task_multiplier']} diff={adj['difficulty']} days_since=6",
          'PASS' if passed else 'FAIL')
    return passed


def test_rule5_high_performance():
    """Rule 5: Long-term completion rate > 90% and streak >= 7."""
    print("\n[Test 5] High performance (rate>90%, streak>=7)...", end=' ')
    _clean_data()
    gid = _create_goal(app)
    # 10 records, all completed, streak increases
    days_data = []
    for i in range(10):
        days_data.append((i, 1, 1, 10 - i))
    _add_learning_records(gid, days_data)
    # Update final record's streak to 10
    latest = LearningRecord.query.filter_by(user_goal_id=gid).order_by(
        LearningRecord.record_date.desc()).first()
    if latest:
        latest.streak_days = 10
        db.session.commit()

    adj = get_adjustments(gid)
    passed = (adj['task_multiplier'] == 1.5 and adj['difficulty'] == 'hard'
              and adj['challenge_mode'] is True)
    print(f"multiplier={adj['task_multiplier']} diff={adj['difficulty']} challenge={adj['challenge_mode']}",
          'PASS' if passed else 'FAIL')
    return passed


def test_default_no_adjustment():
    """Default: no rule matches, returns neutral."""
    print("\n[Test 6] No rule matches (neutral default)...", end=' ')
    _clean_data()
    gid = _create_goal(app)
    # 3 records with mixed completion
    _add_learning_records(gid, [
        (0, 1, 1, 2),
        (1, 1, 1, 1),
        (2, 0, 1, 0),
    ])
    adj = get_adjustments(gid)
    passed = (adj['task_multiplier'] == 1.0 and adj['difficulty'] == 'normal'
              and adj['review_mode'] is False and adj['challenge_mode'] is False
              and adj['reason'] == '')
    print(f"multiplier={adj['task_multiplier']} diff={adj['difficulty']}",
          'PASS' if passed else 'FAIL')
    return passed


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = create_app()
    ctx = app.app_context()
    ctx.push()
    db.create_all()

    print("=" * 60)
    print("AI COACH ADJUSTER - SELF-TEST")
    print("=" * 60)

    tests = [
        test_rule1_low_completion,
        test_rule2_too_hard,
        test_rule3_too_easy,
        test_rule4_inactivity,
        test_rule5_high_performance,
        test_default_no_adjustment,
    ]

    results = []
    for t in tests:
        try:
            results.append(t())
        except Exception as e:
            print(f"ERROR: {e}")
            results.append(False)

    print(f"\n{'=' * 60}")
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"RESULT: {passed}/{total} passed")
    if passed < total:
        for i, r in enumerate(results):
            if not r:
                print(f"  Test {i+1}: FAILED")
    print(f"{'=' * 60}")

    ctx.pop()
    sys.exit(0 if passed == total else 1)
