"""Smart Resource Search — provider-based resource discovery with scoring.

Architecture:
    search_resources() → get_provider() → Provider.search() → results

Provides:
    search_resources(skill_name, level, content_id, knowledge_point) -> list
    rank_resources(resources, user_preference) -> list
    calculate_resource_score(resource, user_preference) -> int

Future:
    search_with_llm() -> raise NotImplementedError
"""

from .providers import get_provider

# ── Allowed domains ──────────────────────────────────────────────────────

ALLOWED_DOMAINS = [
    'python.org',
    'docs.python.org',
    'w3schools.com',
    'freecodecamp.org',
    'realpython.com',
    'developer.mozilla.org',
    'coursera.org',
    'edx.org',
    'khanacademy.org',
    'youtube.com',
    'runoob.com',
    'liaoxuefeng.com',
]

# ── Search templates (for future web search) ─────────────────────────────

SEARCH_TEMPLATES = {
    'Python': {
        'article': ['{kp} Python tutorial', '{kp} Python 菜鸟教程'],
        'video': ['{kp} Python tutorial youtube'],
        'documentation': ['{kp} Python official documentation'],
    },
    '英语': {
        'article': ['English {kp} lesson', '英语{kp}教程'],
        'video': ['English {kp} video lesson'],
        'documentation': ['English {kp} grammar reference'],
    },
    '摄影': {
        'article': ['Photography {kp} tutorial', '摄影{kp}教程'],
        'video': ['Photography {kp} tutorial youtube'],
        'documentation': [],
    },
    '写作': {
        'article': ['Writing {kp} guide', '写作{kp}技巧'],
        'video': ['Writing {kp} tutorial youtube'],
        'documentation': [],
    },
}


def search_resources(skill_name, level, content_id, knowledge_point=''):
    """Search for resources via the configured Provider.

    Delegates to the active SearchProvider (static, mock, or future API).
    Returns list of resource dicts with title, url, type, source, score.
    """
    provider = get_provider()
    return provider.search(content_id, limit=5)


def calculate_resource_score(resource, user_preference=None):
    """Calculate a 0-100 score for a resource.

    Dimensions:
    - Base score by type (documentation +30, article +20, video +15)
    - User preference bonus (+20 if matches preferred type)
    - Domain authority bonus (+10 for official docs)
    """
    score = 0

    res_type = resource.get('type', 'article')
    type_scores = {'documentation': 30, 'article': 20, 'video': 15, 'course': 15}
    score += type_scores.get(res_type, 10)

    if user_preference:
        preferred = user_preference.get('preferred_resource_type', '')
        if preferred and res_type == preferred:
            score += 20

    source = resource.get('source', '')
    official_domains = ['python.org', 'docs.python.org', 'developer.mozilla.org']
    if any(d in source for d in official_domains):
        score += 10

    return min(score, 100)


def rank_resources(resources, user_preference=None, top_n=5):
    """Score and rank resources, return top N."""
    for res in resources:
        res['score'] = calculate_resource_score(res, user_preference)
    ranked = sorted(resources, key=lambda r: r['score'], reverse=True)
    return ranked[:top_n]


def search_with_llm(skill_name, level, content_id, knowledge_point):
    """Future: LLM-powered resource search. Not implemented yet."""
    raise NotImplementedError(
        'LLM search not implemented. Use search_resources() instead.'
    )
