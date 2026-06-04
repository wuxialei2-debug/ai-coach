import os
import json
from datetime import date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from config import Config
from models import db, Skill, UserGoal, RoadmapStage, DailyTask, TaskFeedback, \
    LearningRecord, MemoryInsight, ResourceClick
from roadmap_generator import generate_roadmap
from task_generator import generate_daily_task
from engine.memory.engine import update as memory_update, get_insights as memory_get_insights
from engine.coach.adjuster import get_adjustments


def _seed_skills():
    """Seed predefined skills if table is empty."""
    skills = [
        {'name': 'Python', 'description': '从零开始学习 Python 编程，掌握基础语法到项目实战', 'icon': '🐍', 'category': '编程'},
        {'name': '英语', 'description': '系统提升英语能力，从基础到流利表达', 'icon': '🌍', 'category': '语言'},
        {'name': '摄影', 'description': '掌握摄影技巧，用镜头记录美好瞬间', 'icon': '📷', 'category': '兴趣'},
        {'name': '写作', 'description': '提升写作能力，清晰表达思想与观点', 'icon': '✍️', 'category': '表达'},
    ]
    for s in skills:
        db.session.add(Skill(**s))
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        # Auto-seed skills if table is empty
        if not Skill.query.first():
            _seed_skills()
            print('[Seed] Initialized 4 skills')
        # Auto-cleanup expired cache on startup
        from engine.content.cache import cleanup_expired_cache
        cleaned = cleanup_expired_cache()
        if cleaned:
            print(f'[Cache] cleaned {cleaned} expired items')

    # ── Template Filters ──────────────────────────────────────────────────

    @app.template_filter('parse_content_blocks')
    def parse_content_blocks(content_str):
        """Parse task.content into renderable blocks."""
        if not content_str:
            return []
        blocks = []
        for segment in content_str.split('\n\n'):
            segment = segment.strip()
            if not segment:
                continue
            if segment.startswith('[复习]'):
                blocks.append({'type': 'review', 'text': segment})
            elif segment.startswith('{'):
                try:
                    data = json.loads(segment)
                    blocks.append({'type': 'rich', 'data': data})
                except json.JSONDecodeError:
                    blocks.append({'type': 'plain', 'text': segment})
            else:
                blocks.append({'type': 'plain', 'text': segment})
        return blocks

    @app.template_filter('parse_practice_blocks')
    def parse_practice_blocks(practice_str):
        """Parse task.practice into renderable blocks."""
        if not practice_str:
            return []
        blocks = []
        for segment in practice_str.split('\n\n'):
            segment = segment.strip()
            if not segment:
                continue
            if segment.startswith('{') or segment.startswith('['):
                try:
                    items = json.loads(segment)
                    if isinstance(items, list):
                        blocks.append({'type': 'exercises', 'items': items})
                    else:
                        blocks.append({'type': 'plain', 'text': segment})
                except json.JSONDecodeError:
                    blocks.append({'type': 'plain', 'text': segment})
            elif segment.startswith('【'):
                blocks.append({'type': 'challenge', 'text': segment})
            else:
                blocks.append({'type': 'plain', 'text': segment})
        return blocks

    @app.template_filter('extract_quiz')
    def extract_quiz(content_str):
        """Extract quiz items from task.content blocks."""
        if not content_str:
            return []
        quizzes = []
        for segment in content_str.split('\n\n'):
            segment = segment.strip()
            if not segment or not segment.startswith('{'):
                continue
            try:
                data = json.loads(segment)
                if isinstance(data, dict) and data.get('quiz'):
                    quizzes.extend(data['quiz'])
            except json.JSONDecodeError:
                continue
        return quizzes

    @app.template_filter('parse_json')
    def parse_json(text):
        """Parse a JSON string, return empty list on failure."""
        if not text:
            return []
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return []

    # ── Page Routes ────────────────────────────────────────────────────────

    @app.route('/')
    def index():
        active_goal = UserGoal.query.filter_by(status='active')\
            .order_by(UserGoal.created_at.desc()).first()
        skills = Skill.query.all()

        # Generate today's task if needed
        today_task = None
        adjustments = None
        if active_goal:
            today_task = generate_daily_task(active_goal)
            adjustments = get_adjustments(active_goal.id)

        return render_template('index.html', goal=active_goal,
                               skills=skills, today_task=today_task,
                               adjustments=adjustments)

    @app.route('/roadmap')
    def roadmap():
        active_goal = UserGoal.query.filter_by(status='active')\
            .order_by(UserGoal.created_at.desc()).first()
        if active_goal:
            stages = RoadmapStage.query\
                .filter_by(user_goal_id=active_goal.id)\
                .order_by(RoadmapStage.stage_order).all()
            for s in stages:
                if s.knowledge_points:
                    s.kp_list = json.loads(s.knowledge_points)
                else:
                    s.kp_list = []
        else:
            stages = []
        return render_template('roadmap.html', goal=active_goal, stages=stages)

    @app.route('/history')
    def history():
        active_goal = UserGoal.query.filter_by(status='active')\
            .order_by(UserGoal.created_at.desc()).first()
        return render_template('history.html', goal=active_goal)

    @app.route('/portrait')
    def portrait():
        active_goal = UserGoal.query.filter_by(status='active')\
            .order_by(UserGoal.created_at.desc()).first()
        return render_template('portrait.html', goal=active_goal)

    @app.route('/wizard')
    def wizard():
        skills = Skill.query.all()
        return render_template('wizard.html', skills=skills)

    @app.route('/task/<int:task_id>')
    def task_detail(task_id):
        task = DailyTask.query.get_or_404(task_id)
        feedback = TaskFeedback.query.filter_by(task_id=task_id).first()
        return render_template('task_detail.html', task=task, feedback=feedback)

    # ── API Routes ─────────────────────────────────────────────────────────

    @app.route('/api/goals/create', methods=['POST'])
    def api_create_goal():
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'error': '无效的请求数据'}), 400

        skill_id = data.get('skill_id')
        level = data.get('level')
        daily_minutes = data.get('daily_minutes')
        target_months = data.get('target_months')

        if not all([skill_id, level, daily_minutes, target_months]):
            return jsonify({'ok': False, 'error': '请填写完整信息'}), 400

        skill = Skill.query.get(skill_id)
        if not skill:
            return jsonify({'ok': False, 'error': '技能不存在'}), 404

        goal = UserGoal(
            skill_id=skill.id,
            level=level,
            daily_minutes=int(daily_minutes),
            target_months=int(target_months),
            status='active',
        )
        db.session.add(goal)
        db.session.flush()

        try:
            generate_roadmap(goal)
        except Exception as e:
            db.session.rollback()
            return jsonify({'ok': False, 'error': f'路线图生成失败: {str(e)}'}), 500

        UserGoal.query.filter(UserGoal.id != goal.id,
                              UserGoal.status == 'active')\
            .update({'status': 'paused'})
        db.session.commit()

        return jsonify({'ok': True, 'goal_id': goal.id})

    @app.route('/api/tasks/<int:task_id>/feedback', methods=['POST'])
    def api_task_feedback(task_id):
        task = DailyTask.query.get_or_404(task_id)
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'error': '无效的请求数据'}), 400

        action = data.get('action')  # done / too_hard / too_easy / skipped
        notes = data.get('notes', '')
        actual_minutes = data.get('actual_minutes')

        valid_actions = ('done', 'too_hard', 'too_easy', 'skipped')
        if action not in valid_actions:
            return jsonify({'ok': False, 'error': '无效的操作'}), 400

        if action == 'skipped':
            task.status = 'skipped'
        else:
            task.status = 'done'
            difficulty = None
            if action == 'too_hard':
                difficulty = 'too_hard'
            elif action == 'too_easy':
                difficulty = 'too_easy'

            fb = TaskFeedback(
                task_id=task.id,
                difficulty=difficulty,
                completed_minutes=actual_minutes,
                note=notes,
            )
            db.session.add(fb)

        db.session.commit()

        # Update today's learning record
        _update_learning_record(task.user_goal_id)

        # Update memory insights
        memory_update(task.user_goal_id)

        return jsonify({'ok': True})

    @app.route('/api/goals/<int:goal_id>/insights', methods=['GET'])
    def api_goal_insights(goal_id):
        goal = UserGoal.query.get_or_404(goal_id)
        insights = memory_get_insights(goal.id)
        return jsonify({'ok': True, 'goal_id': goal.id, 'insights': insights})

    @app.route('/api/goals/<int:goal_id>/adjustments', methods=['GET'])
    def api_goal_adjustments(goal_id):
        goal = UserGoal.query.get_or_404(goal_id)
        adj = get_adjustments(goal.id)
        return jsonify({'ok': True, 'goal_id': goal.id, 'adjustments': adj})

    @app.route('/api/goals/<int:goal_id>/history', methods=['GET'])
    def api_goal_history(goal_id):
        """Return comprehensive history data for a goal."""
        goal = UserGoal.query.get_or_404(goal_id)
        today = date.today()

        all_records = LearningRecord.query.filter_by(
            user_goal_id=goal.id,
        ).order_by(LearningRecord.record_date).all()

        has_data = len(all_records) > 0

        # ── Calendar: last 30 days (using date-indexed lookup) ─────────────────
        record_by_date = {r.record_date: r for r in all_records}
        calendar_days = []
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            record = record_by_date.get(d)
            if record and record.total_count > 0:
                rate = record.completed_count / record.total_count
                if rate >= 0.8:
                    status = 'completed'
                elif rate >= 0.3:
                    status = 'partial'
                else:
                    status = 'low'
            else:
                status = 'none'
            calendar_days.append({
                'date': d.isoformat(),
                'day': d.day,
                'weekday': d.weekday(),
                'status': status,
            })

        current_streak = all_records[-1].streak_days if all_records else 0
        max_streak = max(r.streak_days for r in all_records) if all_records else 0

        # ── Stats ──────────────────────────────────────────────────────────────
        total_minutes = sum(r.total_minutes for r in all_records)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        week_minutes = sum(r.total_minutes for r in all_records
                           if r.record_date >= week_start)
        month_minutes = sum(r.total_minutes for r in all_records
                            if r.record_date >= month_start)
        done_tasks = DailyTask.query.filter_by(
            user_goal_id=goal.id, status='done',
        ).count()
        skipped_tasks = DailyTask.query.filter_by(
            user_goal_id=goal.id, status='skipped',
        ).count()
        fb_with_minutes = TaskFeedback.query.join(DailyTask).filter(
            DailyTask.user_goal_id == goal.id,
            TaskFeedback.completed_minutes.isnot(None),
        ).all()
        avg_duration = 0
        if fb_with_minutes:
            avg_duration = sum(fb.completed_minutes
                               for fb in fb_with_minutes) / len(fb_with_minutes)

        stats = {
            'total_hours': round(total_minutes / 60, 1),
            'week_minutes': week_minutes,
            'month_minutes': month_minutes,
            'done_count': done_tasks,
            'skipped_count': skipped_tasks,
            'avg_duration_minutes': round(avg_duration, 1),
        }

        # ── Trends: 7-day & 30-day completion rates (using memoized lookup) ──
        def _build_trend(days):
            result = []
            for i in range(days - 1, -1, -1):
                d = today - timedelta(days=i)
                rec = record_by_date.get(d)
                rate = round(rec.completed_count / rec.total_count, 2) if (
                    rec and rec.total_count > 0) else 0
                result.append({'date': d.isoformat(), 'rate': rate,
                               'label': d.strftime('%m/%d')})
            return result

        trends = {
            'days7': _build_trend(7),
            'days30': _build_trend(30),
        }

        # ── Recent 20 tasks (eager-load feedback to avoid N+1) ────────────────
        recent_tasks_data = DailyTask.query.filter_by(
            user_goal_id=goal.id,
        ).outerjoin(TaskFeedback).add_columns(
            TaskFeedback.difficulty,
            TaskFeedback.completed_minutes,
        ).order_by(DailyTask.date.desc(), DailyTask.id.desc()).limit(20).all()

        recent_tasks = []
        for t, diff, cmin in recent_tasks_data:
            recent_tasks.append({
                'id': t.id,
                'title': t.title,
                'date': t.date.isoformat(),
                'status': t.status,
                'difficulty': diff,
                'completed_minutes': cmin,
                'estimated_minutes': t.estimated_minutes,
            })

        # ── AI Weekly Summary ──────────────────────────────────────────────────
        week_records = [r for r in all_records
                        if r.record_date >= today - timedelta(days=7)]
        week_with_total = [r for r in week_records if r.total_count > 0]
        week_rate = round(
            sum(1 for r in week_with_total if r.completed_count > 0)
            / len(week_with_total), 2,
        ) if week_with_total else 0
        week_avg_min = round(
            sum(r.total_minutes for r in week_records) / len(week_records), 1,
        ) if week_records else 0

        growth_insight = MemoryInsight.query.filter_by(
            user_goal_id=goal.id, insight_type='growth_profile',
        ).first()
        growth_trend = '数据不足'
        if growth_insight and growth_insight.data:
            gdata = json.loads(growth_insight.data)
            growth_trend = gdata.get('growth_trend', '数据不足')

        if week_rate >= 0.8 and current_streak >= 5:
            suggestion = '继续保持当前节奏，学习状态非常稳定！'
        elif week_rate >= 0.6:
            suggestion = '学习状态良好，坚持每天完成学习任务！'
        elif week_rate >= 0.4:
            suggestion = '适当调整计划，确保每天完成基本任务，逐步建立习惯。'
        elif week_rate > 0:
            suggestion = '可以尝试降低单次学习量，从每天少量开始，逐步建立规律。'
        else:
            suggestion = '开始建立学习习惯，从每天少量学习开始吧！'

        summary = {
            'week_completion_rate': week_rate,
            'week_avg_minutes': week_avg_min,
            'current_streak': current_streak,
            'growth_trend': growth_trend,
            'suggestion': suggestion,
        }

        return jsonify({
            'ok': True,
            'has_data': has_data,
            'calendar': {'days': calendar_days, 'current_streak': current_streak,
                         'max_streak': max_streak},
            'stats': stats,
            'trends': trends,
            'recent_tasks': recent_tasks,
            'summary': summary,
        })

    @app.route('/api/resources/click', methods=['POST'])
    def api_resource_click():
        """Record a resource click."""
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'error': '无效的请求数据'}), 400

        task_id = data.get('task_id')
        url = data.get('url')
        title = data.get('title', '')
        res_type = data.get('type', 'article')

        if not url:
            return jsonify({'ok': False, 'error': '缺少 url'}), 400

        # Get goal_id from task
        task = DailyTask.query.get(task_id) if task_id else None
        if not task:
            active_goal = UserGoal.query.filter_by(status='active')\
                .order_by(UserGoal.created_at.desc()).first()
            goal_id = active_goal.id if active_goal else None
        else:
            goal_id = task.user_goal_id

        if not goal_id:
            return jsonify({'ok': False, 'error': '无活跃目标'}), 400

        click = ResourceClick(
            user_goal_id=goal_id,
            task_id=task_id,
            resource_url=url,
            resource_title=title,
            resource_type=res_type,
            resource_score=data.get('score', 0),
            position=data.get('position'),
        )
        db.session.add(click)
        db.session.commit()

        return jsonify({'ok': True, 'click_id': click.id})

    @app.route('/api/resources/complete', methods=['POST'])
    def api_resource_complete():
        """Mark a resource click as completed."""
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'error': '无效的请求数据'}), 400

        click_id = data.get('click_id')
        duration = data.get('duration_seconds', 0)

        click = ResourceClick.query.get(click_id)
        if not click:
            return jsonify({'ok': False, 'error': '记录不存在'}), 404

        click.duration_seconds = duration
        click.completed = True
        db.session.commit()

        return jsonify({'ok': True})

    @app.route('/api/cache/stats', methods=['GET'])
    def api_cache_stats():
        """Return cache statistics."""
        from engine.content.cache import get_cache_stats
        stats = get_cache_stats()
        return jsonify({'ok': True, **stats})

    @app.route('/api/cache/cleanup', methods=['POST'])
    def api_cache_cleanup():
        """Manually cleanup expired cache entries."""
        from engine.content.cache import cleanup_expired_cache
        deleted = cleanup_expired_cache()
        return jsonify({'ok': True, 'deleted': deleted})

    @app.route('/api/cache/performance', methods=['GET'])
    def api_cache_performance():
        """Return cache hit/miss performance."""
        from engine.content.cache import get_cache_performance
        perf = get_cache_performance()
        return jsonify({'ok': True, **perf})

    @app.route('/api/goals/<int:goal_id>/resources', methods=['GET'])
    def api_goal_resources(goal_id):
        """Get recommended resources for the goal's current task."""
        goal = UserGoal.query.get_or_404(goal_id)
        today = date.today()
        task = DailyTask.query.filter_by(
            user_goal_id=goal.id, date=today,
        ).first()

        if not task or not task.resources:
            return jsonify({'ok': True, 'cache_hit': False, 'resources': []})

        import json
        try:
            resources = json.loads(task.resources)
        except (json.JSONDecodeError, TypeError):
            resources = []

        return jsonify({
            'ok': True,
            'cache_hit': True,
            'resources': resources,
        })

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _update_learning_record(user_goal_id):
        """Update or create today's aggregated learning record."""
        today = date.today()

        tasks = DailyTask.query.filter_by(
            user_goal_id=user_goal_id, date=today
        ).all()
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == 'done')

        total_minutes = 0
        for t in tasks:
            if t.status == 'done':
                fb = TaskFeedback.query.filter_by(task_id=t.id).first()
                if fb and fb.completed_minutes:
                    total_minutes += fb.completed_minutes
                else:
                    total_minutes += t.estimated_minutes or 0

        # Calculate streak: consecutive days ending with today that have > 0 done tasks
        streak = 0
        check_date = today
        while True:
            day_tasks = DailyTask.query.filter_by(
                user_goal_id=user_goal_id, date=check_date
            ).all()
            if any(t.status == 'done' for t in day_tasks):
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        record = LearningRecord.query.filter_by(
            user_goal_id=user_goal_id, record_date=today
        ).first()

        if record:
            record.completed_count = completed
            record.total_count = total
            record.total_minutes = total_minutes
            record.streak_days = streak
        else:
            record = LearningRecord(
                user_goal_id=user_goal_id,
                record_date=today,
                completed_count=completed,
                total_count=total,
                total_minutes=total_minutes,
                streak_days=streak,
            )
            db.session.add(record)

        db.session.commit()

    return app


if __name__ == '__main__':
    app = create_app()
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
