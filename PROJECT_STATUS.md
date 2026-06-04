# AI Coach — PROJECT_STATUS.md

> 生成日期：2026-06-02
> 版本：MVP Release 1.0

---

## 一、当前功能列表

### 已实现功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **首页** | AI 教练问候（时间自适应） | ✅ |
| | 推荐技能展示（4 个技能） | ✅ |
| | 搜索框 | ✅ |
| | 当前成长目标卡片 | ✅ |
| | 今日学习任务卡片（含 Adjuster 调整横幅） | ✅ |
| | 空状态处理（无目标/无任务） | ✅ |
| **向导** | 5 步创建目标：选择技能 → 水平 → 周期 → 时长 → 生成 | ✅ |
| | URL 预选技能 | ✅ |
| | 生成中动画 | ✅ |
| **路线图** | 目标信息头部（图标/等级/时长） | ✅ |
| | 总体进度条 | ✅ |
| | 阶段列表（完成/当前/待开始） | ✅ |
| | 知识点列表（当前阶段） | ✅ |
| **任务详情** | 学习内容展示 | ✅ |
| | 练习任务展示 | ✅ |
| | 4 个反馈按钮（完成/太难/太简单/跳过） | ✅ |
| | 笔记和实际时长输入 | ✅ |
| | 反馈后自动刷新 | ✅ |
| **学习记录** | 30 天学习日历（绿/黄/灰/红 状态） | ✅ |
| | 学习统计（总时长/本周/本月/完成/跳过/平均时长） | ✅ |
| | 趋势分析（7 天 + 30 天 SVG 折线图） | ✅ |
| | 最近 20 条任务记录 | ✅ |
| | AI 成长总结（含趋势和建议） | ✅ |
| **成长画像** | 执行力卡片 | ✅ |
| | 成长趋势卡片 | ✅ |
| | 学习偏好卡片 | ✅ |
| | 学习习惯卡片 | ✅ |
| | 推荐节奏卡片 | ✅ |
| | 完成概率卡片 | ✅ |
| | AI 当前策略卡片 | ✅ |
| | 置信度横幅（低数据提醒） | ✅ |
| **Adjuster** | 规则 1：低完成率 → 降低难度+复习 | ✅ |
| | 规则 2：连续太难 → 降低难度+复习 | ✅ |
| | 规则 3：连续太简单 → 增加挑战 | ✅ |
| | 规则 4：长期未学习 → 大幅降低门槛 | ✅ |
| | 规则 5：高表现 → 增加挑战 | ✅ |
| | 默认：无调整 | ✅ |
| **Memory Engine** | 学习习惯分析 | ✅ |
| | 学习偏好分析 | ✅ |
| | 执行力分析 | ✅ |
| | 成长画像（趋势/节奏/概率） | ✅ |
| | 置信度计算（基于数据量 + 时间衰减） | ✅ |
| **导航** | 底部 4 标签导航（首页/路线图/记录/画像） | ✅ |
| | 当前页高亮 | ✅ |

### 未实现功能（V2 规划）

- 技能搜索（搜索框为占位符）
- 阶段点击查看详情（显示"功能开发中"）
- 学习资料自动推荐
- 每周/每月成长报告
- 浏览器/手机推送提醒
- AI 语音教练
- 多目标并行管理
- 数据导出

---

## 二、数据库结构

### 表清单

| 表名 | 用途 | 行数（测试） | 关键索引 |
|------|------|-------------|---------|
| `skills` | 预定义技能 | 4 | PK(id) |
| `user_goals` | 用户成长目标 | 2 | PK(id), FK(skill_id) |
| `roadmap_stages` | 路线图阶段 | 8 | PK(id), FK(skill_id), FK(user_goal_id) |
| `daily_tasks` | 每日任务 | 6 | PK(id), FK(user_goal_id), FK(stage_id), **UQ(user_goal_id, date)**, **IX(goal_date)** |
| `task_feedback` | 任务反馈 | 6 | PK(id), FK(task_id), **cascade delete** |
| `learning_records` | 每日学习汇总 | 6 | PK(id), FK(user_goal_id), **IX(goal_date)** |
| `memory_insights` | AI 记忆分析结果 | 4 | PK(id), FK(user_goal_id) |
| `user_profiles` | 用户个人资料（预留） | 0 | PK(id) |

### 外键关系

```
skills ──< user_goals ──< roadmap_stages
                        ──< daily_tasks ──< task_feedback
                        ──< learning_records
                        ──< memory_insights
```

### 级联删除

- 删除 `user_goals` → 自动删除关联的 `daily_tasks`, `task_feedback`, `learning_records`, `memory_insights`, `roadmap_stages`
- 删除 `daily_tasks` → 自动删除关联的 `task_feedback`

---

## 三、API 列表

| 方法 | 路径 | 用途 | 请求体 | 返回 |
|------|------|------|--------|------|
| GET | `/` | 首页 | - | HTML |
| GET | `/roadmap` | 路线图页 | - | HTML |
| GET | `/history` | 学习记录页 | - | HTML |
| GET | `/portrait` | 成长画像页 | - | HTML |
| GET | `/wizard` | 创建目标向导 | - | HTML |
| GET | `/task/<id>` | 任务详情页 | - | HTML |
| POST | `/api/goals/create` | 创建目标 | `{skill_id, level, daily_minutes, target_months}` | `{ok, goal_id}` |
| POST | `/api/tasks/<id>/feedback` | 提交反馈 | `{action, notes?, actual_minutes?}` | `{ok}` |
| GET | `/api/goals/<id>/insights` | 获取画像数据 | - | `{ok, insights}` |
| GET | `/api/goals/<id>/adjustments` | 获取调整策略 | - | `{ok, adjustments}` |
| GET | `/api/goals/<id>/history` | 获取学习记录 | - | `{ok, calendar, stats, trends, recent_tasks, summary}` |

### History API 返回结构

```json
{
  "ok": true,
  "has_data": true,
  "calendar": { "days": [...], "current_streak": 2, "max_streak": 5 },
  "stats": { "total_hours": 5.0, "week_minutes": 120, "month_minutes": 300, "done_count": 10, "skipped_count": 2, "avg_duration_minutes": 25.0 },
  "trends": { "days7": [{"date":"...", "rate":0.8, "label":"06/01"}, ...], "days30": [...] },
  "recent_tasks": [{"id":1, "title":"...", "date":"...", "status":"done", "difficulty":"just_right", "completed_minutes":15, "estimated_minutes":20}],
  "summary": { "week_completion_rate": 0.8, "week_avg_minutes": 20, "current_streak": 2, "growth_trend": "保持稳定", "suggestion": "..." }
}
```

---

## 四、项目目录结构

```
AI  Coach/
├── app.py                    # Flask 应用主文件（路由 + API + 数据库初始化）
├── config.py                 # 应用配置
├── models.py                 # SQLAlchemy 数据模型（8 个表）
├── roadmap_generator.py      # 路线图生成器（预置模板）
├── task_generator.py         # 每日任务生成器（含 Adjuster 集成）
├── seed.py                   # 初始数据填充
├── requirements.txt          # Python 依赖
├── PROJECT.md                # 原始项目文档
├── test_adjuster.py          # Adjuster 单元测试（6 个用例）
├── test_memory_engine.py     # Memory Engine 端到端测试
│
├── engine/
│   ├── __init__.py
│   ├── coach/
│   │   ├── __init__.py
│   │   └── adjuster.py       # 5 条规则动态调整器
│   └── memory/
│       ├── __init__.py
│       ├── common.py          # 共享工具（置信度、保存）
│       ├── engine.py          # 统一入口（update / get_insights）
│       ├── execution.py       # 执行力分析器
│       ├── growth_profile.py  # 成长画像分析器
│       ├── habits.py          # 学习习惯分析器
│       └── preferences.py     # 学习偏好分析器
│
├── static/
│   ├── css/
│   │   └── style.css         # 所有样式（1525+ 行）
│   └── js/
│       └── app.js            # 向导 + 导航交互
│
├── templates/
│   ├── base.html             # 基础模板（底部导航）
│   ├── index.html            # 首页
│   ├── wizard.html           # 创建目标向导
│   ├── roadmap.html          # 路线图页
│   ├── history.html          # 学习记录页
│   ├── portrait.html         # 成长画像页
│   └── task_detail.html      # 任务详情页
│
└── instance/
    └── app.db                # SQLite 数据库
```

---

## 五、已知问题

### 中等
1. **Windows 终端 GBK 编码**：测试输出的中文显示为乱码。不影响应用本身（HTML 页面渲染正常），仅影响 `test_adjuster.py` 和 `test_memory_engine.py` 的控制台输出可读性。
2. **搜索框为占位**：首页搜索框为 `readonly`，尚未接入搜索逻辑，仅作为 UI 占位。

### 低
3. **路线图阶段详情**：点击阶段卡片显示"功能开发中"，尚未实现阶段详情查看。
4. **UserProfile 表未使用**：`user_profiles` 表已定义但未接入功能，属于预留模型。
5. **Seed 数据 RoadmapStage 无 user_goal_id**：`seed.py` 创建的预设阶段有 `skill_id` 但无 `user_goal_id`，可能和用户生成的阶段在查询时混淆。

---

## 六、下一阶段规划

### Phase 9（建议）：功能增强
- 任务回顾与反馈编辑
- 阶段详情查看（点击展开知识点进度）
- 多目标切换功能
- 数据导出（CSV / JSON）

### Phase 10（建议）：AI 能力升级
- 接入 LLM API（Claude / OpenAI）生成个性化内容
- 智能学习资料推荐
- 每周/每月成长报告
- 自然语言学习建议

### V2（长期）
- 任意技能自动生成路线图（不限于预置模板）
- 跨目标长期记忆
- AI 语音教练
- 浏览器 / 手机推送提醒
- 多角色共享记忆（Coach / Assistant / Companion）

---

## 七、测试状态

| 测试套件 | 用例数 | 通过 | 状态 |
|---------|--------|------|------|
| Adjuster 单元测试 | 6 | 6 | ✅ 全部通过 |
| Memory Engine 端到端测试 | 8 个验证点 | 8 | ✅ 全部通过 |
| 全流程验收（手动） | 7 个页面路由 + 5 个 API | 12 | ✅ 全部通过 |

---

*MVP Release 1.0 — 2026-06-02*
