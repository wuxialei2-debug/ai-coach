from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Skill(db.Model):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(10))
    category = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    goals = db.relationship('UserGoal', backref='skill', lazy='dynamic')
    stages = db.relationship('RoadmapStage', backref='skill', lazy='dynamic',
                             order_by='RoadmapStage.stage_order')


class UserGoal(db.Model):
    __tablename__ = 'user_goals'

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    level = db.Column(db.String(20), nullable=False)  # 零基础/初级/中级/高级
    daily_minutes = db.Column(db.Integer, nullable=False)
    target_months = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='active')  # active/paused/completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    tasks = db.relationship('DailyTask', backref='goal', lazy='dynamic',
                            cascade='all, delete-orphan')
    records = db.relationship('LearningRecord', backref='goal', lazy='dynamic',
                              cascade='all, delete-orphan')
    stages = db.relationship('RoadmapStage', backref='goal', lazy='dynamic',
                              order_by='RoadmapStage.stage_order',
                              cascade='all, delete-orphan')
    insights = db.relationship('MemoryInsight', backref='goal', lazy='dynamic',
                               cascade='all, delete-orphan')
    resource_clicks = db.relationship('ResourceClick', backref='goal', lazy='dynamic',
                                      cascade='all, delete-orphan')


class RoadmapStage(db.Model):
    __tablename__ = 'roadmap_stages'

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=True)
    user_goal_id = db.Column(db.Integer, db.ForeignKey('user_goals.id'),
                             nullable=True)
    stage_order = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    knowledge_points = db.Column(db.Text)  # JSON array of knowledge point strings
    status = db.Column(db.String(20), default='pending')  # pending/current/completed

    tasks = db.relationship('DailyTask', backref='stage', lazy='dynamic')


class DailyTask(db.Model):
    __tablename__ = 'daily_tasks'
    __table_args__ = (
        db.UniqueConstraint('user_goal_id', 'date', name='uq_goal_date'),
        db.Index('ix_daily_tasks_goal_date', 'user_goal_id', 'date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_goal_id = db.Column(db.Integer, db.ForeignKey('user_goals.id'),
                             nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('roadmap_stages.id'),
                         nullable=True)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)       # learning content
    practice = db.Column(db.Text)      # practice exercise
    content_id = db.Column(db.String(100))  # content library reference
    resources = db.Column(db.Text)  # JSON array of recommended resources
    estimated_minutes = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending')  # pending/done/skipped
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    feedback = db.relationship('TaskFeedback', backref='task', uselist=False,
                               cascade='all, delete-orphan')


class TaskFeedback(db.Model):
    __tablename__ = 'task_feedback'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('daily_tasks.id'), nullable=False)
    difficulty = db.Column(db.String(20))  # too_easy/just_right/too_hard
    completed_minutes = db.Column(db.Integer)
    note = db.Column(db.Text)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)


class LearningRecord(db.Model):
    __tablename__ = 'learning_records'
    __table_args__ = (
        db.Index('ix_learning_record_goal_date', 'user_goal_id', 'record_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_goal_id = db.Column(db.Integer, db.ForeignKey('user_goals.id'),
                             nullable=False)
    record_date = db.Column(db.Date, nullable=False)
    completed_count = db.Column(db.Integer, default=0)
    total_count = db.Column(db.Integer, default=0)
    total_minutes = db.Column(db.Integer, default=0)
    streak_days = db.Column(db.Integer, default=0)


class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), default='学习者')
    avatar = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


class MemoryInsight(db.Model):
    __tablename__ = 'memory_insights'

    id = db.Column(db.Integer, primary_key=True)
    user_goal_id = db.Column(db.Integer, db.ForeignKey('user_goals.id'),
                             nullable=False)
    insight_type = db.Column(db.String(50), nullable=False)
    data = db.Column(db.Text)  # JSON
    confidence = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


class ResourceClick(db.Model):
    __tablename__ = 'resource_clicks'

    id = db.Column(db.Integer, primary_key=True)
    user_goal_id = db.Column(db.Integer, db.ForeignKey('user_goals.id'),
                             nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('daily_tasks.id'), nullable=True)
    resource_url = db.Column(db.String(500), nullable=False)
    resource_title = db.Column(db.String(200))
    resource_type = db.Column(db.String(20))  # article/video/documentation
    resource_score = db.Column(db.Integer, default=0)  # 0-100 ranking score
    position = db.Column(db.Integer)  # position in recommendation list (1-based)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)
    duration_seconds = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)


class ResourceCache(db.Model):
    __tablename__ = 'resource_cache'

    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(200), nullable=False)
    skill_name = db.Column(db.String(100))
    resource_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
