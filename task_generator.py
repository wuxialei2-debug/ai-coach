"""Generate daily tasks from current roadmap stage and knowledge points.

Integrates with AI Coach adjuster to personalise tasks based on
the learner's recent performance and long-term patterns.
"""

import json
from datetime import date, timedelta
from models import db, DailyTask, RoadmapStage
from engine.coach.adjuster import get_adjustments
from engine.content.content_service import get_task_content
from engine.content.resources import get_resources

CONTENT_TEMPLATES = {
    'Python': {
        'content': '学习{stage}中的"{kp}"，掌握其语法规则和核心概念，理解在实际开发中的应用场景。',
        'practice': '编写一段 Python 代码练习"{kp}"，通过实践加深理解，注意代码规范和常见错误。',
    },
    '英语': {
        'content': '学习{stage}中的"{kp}"，掌握相关词汇、句型和表达方式，结合实际场景进行练习。',
        'practice': '完成"{kp}"相关的听、说、读、写练习，尝试在实际对话中运用所学内容。',
    },
    '摄影': {
        'content': '学习{stage}中的"{kp}"，理解核心概念和实用技巧，分析优秀作品中的运用。',
        'practice': '运用"{kp}"的知识进行实际拍摄练习，拍摄至少 5 张照片并分析效果。',
    },
    '写作': {
        'content': '学习{stage}中的"{kp}"，掌握写作技巧和方法，通过范文理解其应用。',
        'practice': '针对"{kp}"完成一段写作练习，注重技巧的运用和自我修改改进。',
    },
}

DEFAULT_CONTENT = '学习{stage}中的"{kp}"，掌握核心概念与应用方法。'
DEFAULT_PRACTICE = '完成关于"{kp}"的练习，巩固所学知识。'

REVIEW_TEMPLATE = '复习"{kp}"，巩固之前学习的内容，查漏补缺。'
CHALLENGE_TEMPLATE = (
    '【拓展练习】\n'
    '运用{stage}所学知识完成一个综合性练习，尝试解决更复杂的问题。\n\n'
    '【进阶阅读】\n'
    '查阅相关资料，深入了解该知识点的进阶应用。'
)


def generate_daily_task(goal):
    """Generate one daily task for the active goal.

    Returns the existing task if already generated for today,
    or creates a new one from the current stage's knowledge points,
    adjusted by the AI Coach adjuster.
    """
    today = date.today()

    # Check if task already exists for today
    existing = DailyTask.query.filter_by(
        user_goal_id=goal.id,
        date=today
    ).first()
    if existing:
        return existing

    # Get current stage
    current_stage = RoadmapStage.query.filter_by(
        user_goal_id=goal.id,
        status='current'
    ).first()
    if not current_stage:
        return None

    # Parse knowledge points
    kp_list = json.loads(
        current_stage.knowledge_points
    ) if current_stage.knowledge_points else []
    if not kp_list:
        return None

    # ── Read AI Coach adjustments ─────────────────────────────────────────
    adjustments = get_adjustments(goal.id)
    multiplier = adjustments['task_multiplier']
    difficulty = adjustments['difficulty']

    # Determine KP count based on difficulty
    kp_count = {'easy': 1, 'normal': 2, 'hard': 3}.get(difficulty, 2)

    # Cycle through knowledge points based on completed task count
    done_count = DailyTask.query.filter(
        DailyTask.user_goal_id == goal.id,
        DailyTask.stage_id == current_stage.id,
        DailyTask.status == 'done'
    ).count()

    kp_index = done_count % len(kp_list)
    kps = []
    for i in range(kp_count):
        kps.append(kp_list[(kp_index + i) % len(kp_list)])

    # ── Generate content from templates ───────────────────────────────────
    skill_name = goal.skill.name
    level = goal.level
    templates = CONTENT_TEMPLATES.get(skill_name, {})
    content_tpl = templates.get('content', DEFAULT_CONTENT)
    practice_tpl = templates.get('practice', DEFAULT_PRACTICE)

    content_parts = []
    practice_parts = []
    first_content_id = None

    # Review mode: add review section
    if adjustments['review_mode']:
        review_kps = _get_review_kps(goal.id, current_stage.id)
        if review_kps:
            review_content = '\n'.join(
                '[复习] ' + REVIEW_TEMPLATE.format(kp=rk)
                for rk in review_kps
            )
            content_parts.append(review_content)

    # Main content — use Content Engine, fall back to template
    for kp in kps:
        content_id, rich = get_task_content(skill_name, level, kp)
        if rich:
            if not first_content_id:
                first_content_id = content_id
            content_parts.append(json.dumps(rich, ensure_ascii=False))
            if rich.get('practice'):
                practice_parts.append(json.dumps(rich['practice'], ensure_ascii=False))
            else:
                practice_parts.append(practice_tpl.format(stage=current_stage.name, kp=kp))
        else:
            content_parts.append(content_tpl.format(stage=current_stage.name, kp=kp))
            practice_parts.append(practice_tpl.format(stage=current_stage.name, kp=kp))

    # Challenge mode: add challenge section
    if adjustments['challenge_mode']:
        practice_parts.append(
            CHALLENGE_TEMPLATE.format(stage=current_stage.name)
        )

    content = '\n\n'.join(content_parts)
    practice = '\n\n'.join(practice_parts)

    # Build title
    if first_content_id and len(kps) == 1:
        title = rich.get('title', f'理解{kps[0]}') if rich else f'理解{kps[0]}'
    elif len(kps) == 1:
        title = f'理解{kps[0]}'
    else:
        title = f'学习{"、".join(kps)}'

    # Adjust estimated minutes
    if first_content_id and rich and rich.get('estimated_minutes'):
        adjusted_minutes = max(5, int(rich['estimated_minutes'] * multiplier))
    else:
        adjusted_minutes = max(5, int(goal.daily_minutes * multiplier))

    # Collect resources from content engine
    # Use content_id if available, otherwise search by first KP name
    resources = []
    search_key = first_content_id
    if not search_key and kps:
        search_key = kps[0]
    if search_key:
        resources = get_resources(search_key, skill_name, level)

    task = DailyTask(
        user_goal_id=goal.id,
        stage_id=current_stage.id,
        date=today,
        title=title,
        content=content,
        practice=practice,
        content_id=first_content_id,
        resources=json.dumps(resources, ensure_ascii=False) if resources else None,
        estimated_minutes=adjusted_minutes,
        status='pending',
    )
    db.session.add(task)
    db.session.commit()

    return task


def _get_review_kps(goal_id, stage_id):
    """Get knowledge points to review: yesterday's KP + any from too-hard tasks."""
    kps = []

    # Yesterday's task KP
    yesterday = date.today() - timedelta(days=1)
    yesterday_task = DailyTask.query.filter_by(
        user_goal_id=goal_id,
        date=yesterday,
    ).first()
    if yesterday_task:
        # Extract KP from title (strip "理解" prefix)
        title = yesterday_task.title
        if title.startswith('理解'):
            kps.append(title[2:])

    return kps
