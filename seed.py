"""Seed predefined skills and roadmap stages."""

from app import create_app
from models import db, Skill, RoadmapStage


SKILLS = [
    {
        'name': 'Python',
        'description': '从零开始学习 Python 编程，掌握基础语法到项目实战',
        'icon': '🐍',
        'category': '编程',
        'stages': [
            ('基础语法', '变量、数据类型、条件判断、循环'),
            ('函数与模块', '函数定义、参数传递、模块导入'),
            ('面向对象', '类、继承、封装、多态'),
            ('项目实战', '综合项目练习，巩固所学知识'),
        ],
    },
    {
        'name': '英语',
        'description': '系统提升英语能力，从基础到流利表达',
        'icon': '🌍',
        'category': '语言',
        'stages': [
            ('基础词汇与发音', '核心词汇积累、音标与发音规则'),
            ('日常会话', '问候、购物、点餐等场景对话'),
            ('语法与阅读', '核心语法、短文阅读理解'),
            ('写作与表达', '邮件写作、观点表达、深入讨论'),
        ],
    },
    {
        'name': '摄影',
        'description': '掌握摄影技巧，用镜头记录美好瞬间',
        'icon': '📷',
        'category': '兴趣',
        'stages': [
            ('相机基础', '曝光三要素、对焦、白平衡'),
            ('构图与光线', '构图法则、自然光与人工光运用'),
            ('后期处理', '调色、裁剪、修图基础'),
            ('主题创作', '人像、风景、街拍等专题练习'),
        ],
    },
    {
        'name': '写作',
        'description': '提升写作能力，清晰表达思想与观点',
        'icon': '✍️',
        'category': '表达',
        'stages': [
            ('基础写作技巧', '遣词造句、段落组织、修辞手法'),
            ('文章结构', '开头、主体、结尾的布局方法'),
            ('不同文体练习', '记叙文、议论文、说明文写作'),
            ('创作与发表', '完成个人作品，获取反馈与改进'),
        ],
    },
]


def seed():
    app = create_app()
    with app.app_context():
        # 检查是否已初始化
        if Skill.query.first():
            print('数据已存在，跳过初始化')
            return

        for skill_data in SKILLS:
            skill = Skill(
                name=skill_data['name'],
                description=skill_data['description'],
                icon=skill_data['icon'],
                category=skill_data['category'],
            )
            db.session.add(skill)
            db.session.flush()

            for order, (name, desc) in enumerate(skill_data['stages'], 1):
                stage = RoadmapStage(
                    skill_id=skill.id,
                    stage_order=order,
                    name=name,
                    description=desc,
                )
                db.session.add(stage)

        db.session.commit()
        print(f'已初始化 {len(SKILLS)} 个技能及其学习阶段')


if __name__ == '__main__':
    seed()
