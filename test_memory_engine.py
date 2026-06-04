"""Memory Engine end-to-end self-test.

Run with: python test_memory_engine.py
Requires: the app's working directory as CWD.
"""

import json
import sys
import os

# Ensure the project directory is on sys.path
PROJECT_DIR = r"C:\Users\luojinfa\Desktop\AI  Coach"
sys.path.insert(0, PROJECT_DIR)

from app import create_app
from models import db, Skill, UserGoal, RoadmapStage, DailyTask, TaskFeedback, \
    LearningRecord, MemoryInsight


def run_tests():
    app = create_app()
    ctx = app.app_context()
    ctx.push()

    db.create_all()
    setup_skills()

    # Clear previous test data
    for model in (MemoryInsight, TaskFeedback, LearningRecord, DailyTask, RoadmapStage, UserGoal):
        model.query.delete()
    db.session.commit()

    print("=" * 60)
    print("MEMORY ENGINE - SELF-TEST")
    print("=" * 60)

    with app.test_client() as client:
        # Step 1: Create a goal
        goal_id = create_goal(client)

        # Step 2: Before any feedback, check insights (should be all empty/0)
        print("\n--- Before any feedback ---")
        check_insights(client, goal_id)

        # Step 3: Generate a task and submit first feedback
        task1 = get_today_task(client, goal_id)
        assert task1, "Task must be generated"
        submit_feedback(client, task1.id, 'done', minutes=15, notes='第一天学习')

        # Step 4: Create more historical feedback directly (simulating previous days)
        goal_obj = db.session.get(UserGoal, goal_id)
        stage = RoadmapStage.query.filter_by(user_goal_id=goal_id, status='current').first()
        from datetime import date, timedelta, datetime

        for days_ago in range(1, 5):
            d = date.today() - timedelta(days=days_ago)
            task = DailyTask(
                user_goal_id=goal_id,
                stage_id=stage.id,
                date=d,
                title=f'历史任务 {days_ago}',
                content='历史学习内容',
                practice='历史练习内容',
                estimated_minutes=goal_obj.daily_minutes,
                status='done',
            )
            db.session.add(task)
            db.session.flush()

            # Alternate difficulties for variety
            diff = 'just_right'
            if days_ago % 3 == 1:
                diff = 'too_easy'
            elif days_ago % 3 == 2:
                diff = 'too_hard'
            minutes = 15 + days_ago * 5

            fb = TaskFeedback(
                task_id=task.id,
                difficulty=diff,
                completed_minutes=minutes,
                note=f'第{days_ago}天学习笔记',
                completed_at=datetime.now() - timedelta(days=days_ago),
            )
            db.session.add(fb)

            lr = LearningRecord(
                user_goal_id=goal_id,
                record_date=d,
                completed_count=1,
                total_count=1,
                total_minutes=minutes,
                streak_days=days_ago,
            )
            db.session.add(lr)

        db.session.commit()
        print(f"\n[SETUP] Created 4 historical task+feedback+record entries")

        # Step 5: Manually trigger memory engine update with 5 data points
        from engine.memory.engine import update as memory_update
        memory_update(goal_id)

        # Step 6: Now check insights -- should have data with confidence > 0
        print("\n--- After 5 feedback entries ---")
        result = check_insights(client, goal_id)

        # Step 7: Verify database state
        verify_db()

        # Step 8: Verify minimum requirements
        insights = result['insights']
        all_have_data = all(
            insights[t]['confidence'] > 0
            for t in ('habits', 'preferences', 'execution', 'growth_profile')
        )

        print(f"\n{'=' * 60}")
        print(f"RESULT: {'ALL PASS' if all_have_data else 'SOME FAILURES'}")
        print(f"{'=' * 60}")

        if not all_have_data:
            for t in ('habits', 'preferences', 'execution', 'growth_profile'):
                c = insights[t]['confidence']
                d = bool(insights[t]['data'])
                print(f"  {t}: confidence={c}, has_data={d}")
            ctx.pop()
            sys.exit(1)

        # Print all insight data for manual verification
        print("\nFull insights data:")
        for itype, ins in insights.items():
            print(f"\n--- {itype} (confidence={ins['confidence']}) ---")
            print(json.dumps(ins['data'], ensure_ascii=False, indent=2))

    ctx.pop()
    print("\nMemory Engine self-test complete")


# ── Helpers ────────────────────────────────────────────────────────────────────

def setup_skills():
    """Create MVP skills if not present."""
    if Skill.query.first():
        return
    skills = [
        Skill(name='Python', description='Python 编程语言', icon='PY', category='编程'),
        Skill(name='英语',   description='英语语言学习',   icon='EN', category='语言'),
        Skill(name='摄影',   description='摄影技巧与艺术', icon='PH', category='艺术'),
        Skill(name='写作',   description='写作能力提升',   icon='WR', category='写作'),
    ]
    for s in skills:
        db.session.add(s)
    db.session.commit()
    print(f"[SETUP] Created {len(skills)} skills")


def create_goal(client, skill_id=1, level='零基础', minutes=20, months=3):
    """Create a goal via the API."""
    resp = client.post('/api/goals/create', json={
        'skill_id': skill_id,
        'level': level,
        'daily_minutes': minutes,
        'target_months': months,
    })
    data = resp.get_json()
    print(f"[CREATE GOAL] status={resp.status_code}, ok={data['ok']}, goal_id={data.get('goal_id')}")
    return data['goal_id']


def submit_feedback(client, task_id, action, minutes=None, notes=''):
    """Submit feedback for a task."""
    body = {'action': action, 'notes': notes, 'actual_minutes': minutes}
    resp = client.post(f'/api/tasks/{task_id}/feedback', json=body)
    data = resp.get_json()
    ok = 'OK' if data['ok'] else 'FAIL'
    print(f"[FEEDBACK] task={task_id} action={action} minutes={minutes} -> {ok}")
    return data['ok']


def get_today_task(client, goal_id):
    """Get the task generated for today."""
    client.get('/')  # trigger generation
    from datetime import date
    task = DailyTask.query.filter_by(user_goal_id=goal_id, date=date.today()).first()
    if task:
        print(f"[TASK] id={task.id} title={task.title} status={task.status} minutes={task.estimated_minutes}")
    else:
        print(f"[TASK] No task for today")
    return task


def check_insights(client, goal_id):
    """Call the insights API and print results."""
    resp = client.get(f'/api/goals/{goal_id}/insights')
    data = resp.get_json()
    print(f"\n[INSIGHTS API] status={resp.status_code}, ok={data['ok']}")

    insights = data['insights']
    for itype in ('habits', 'preferences', 'execution', 'growth_profile'):
        ins = insights[itype]
        conf = ins['confidence']
        has_data = bool(ins['data'])
        status = 'HAS DATA' if conf > 0 else '(no data - conf=0)'
        print(f"  {itype}: confidence={conf} {status}")
        if conf > 0 and has_data:
            print(f"    => {json.dumps(ins['data'], ensure_ascii=False, indent=4)}")

    return data


def verify_db():
    """Verify database records."""
    print(f"\n[DB] MemoryInsight count: {MemoryInsight.query.count()}")
    print(f"[DB] TaskFeedback count: {TaskFeedback.query.count()}")
    print(f"[DB] LearningRecord count: {LearningRecord.query.count()}")
    print(f"[DB] DailyTask count: {DailyTask.query.count()}")

    records = LearningRecord.query.order_by(LearningRecord.record_date).all()
    for r in records:
        print(f"  LearningRecord {r.record_date}: completed={r.completed_count}/{r.total_count} streak={r.streak_days}")


if __name__ == '__main__':
    run_tests()
