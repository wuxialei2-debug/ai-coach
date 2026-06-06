"""Static resource mapping — maps content_ids to recommended learning resources.

Each content_id maps to a list of resources with title, url, and type.
Types: article, video, documentation

Resources are real, publicly available learning materials.
"""

RESOURCE_MAP = {
    # ── Python Beginner ──────────────────────────────────────────────────
    'variables': [
        {
            'title': 'Python 变量和数据类型 — 菜鸟教程',
            'url': 'https://www.runoob.com/python/python-variable-types.html',
            'type': 'article',
        },
        {
            'title': 'Python Variables — W3Schools',
            'url': 'https://www.w3schools.com/python/python_variables.asp',
            'type': 'article',
        },
        {
            'title': 'Python 变量 — 廖雪峰教程',
            'url': 'https://www.liaoxuefeng.com/wiki/1016959663602400/1017000000606130',
            'type': 'article',
        },
    ],
    'data_types': [
        {
            'title': 'Python 数据类型 — 菜鸟教程',
            'url': 'https://www.runoob.com/python/python-data-types.html',
            'type': 'article',
        },
        {
            'title': 'Python Numbers, Type Conversion — W3Schools',
            'url': 'https://www.w3schools.com/python/python_numbers.asp',
            'type': 'article',
        },
        {
            'title': 'Built-in Types — Python 官方文档',
            'url': 'https://docs.python.org/3/library/stdtypes.html',
            'type': 'documentation',
        },
    ],
    'input_output': [
        {
            'title': 'Python 输入和输出 — 菜鸟教程',
            'url': 'https://www.runoob.com/python/python-io.html',
            'type': 'article',
        },
        {
            'title': 'Python User Input — W3Schools',
            'url': 'https://www.w3schools.com/python/python_user_input.asp',
            'type': 'article',
        },
        {
            'title': 'Python print() 函数 — 菜鸟教程',
            'url': 'https://www.runoob.com/python/python-func-print.html',
            'type': 'article',
        },
    ],
    'if_else': [
        {
            'title': 'Python 条件判断 — 廖雪峰教程',
            'url': 'https://www.liaoxuefeng.com/wiki/1016959663602400/1017001535168864',
            'type': 'article',
        },
        {
            'title': 'Python if...else — W3Schools',
            'url': 'https://www.w3schools.com/python/python_conditions.asp',
            'type': 'article',
        },
        {
            'title': 'Python If Else 视频教程 — freeCodeCamp',
            'url': 'https://www.youtube.com/watch?v=Zp5MuPOtsSY',
            'type': 'video',
        },
    ],
    'loops': [
        {
            'title': 'Python 循环 — 廖雪峰教程',
            'url': 'https://www.liaoxuefeng.com/wiki/1016959663602400/1017002016462656',
            'type': 'article',
        },
        {
            'title': 'Python For Loops — W3Schools',
            'url': 'https://www.w3schools.com/python/python_for_loops.asp',
            'type': 'article',
        },
        {
            'title': 'Python 循环语句 — 菜鸟教程',
            'url': 'https://www.runoob.com/python/python-loops.html',
            'type': 'article',
        },
    ],
    'functions': [
        {
            'title': 'Python 函数 — 廖雪峰教程',
            'url': 'https://www.liaoxuefeng.com/wiki/1016959663602400/1017042800030560',
            'type': 'article',
        },
        {
            'title': 'Python Functions — W3Schools',
            'url': 'https://www.w3schools.com/python/python_functions.asp',
            'type': 'article',
        },
        {
            'title': 'Python 函数视频教程 — freeCodeCamp',
            'url': 'https://www.youtube.com/watch?v=NE97ylAnrz4',
            'type': 'video',
        },
    ],
    'lists': [
        {
            'title': 'Python 列表 — 廖雪峰教程',
            'url': 'https://www.liaoxuefeng.com/wiki/1016959663602400/1017000000602650',
            'type': 'article',
        },
        {
            'title': 'Python Lists — W3Schools',
            'url': 'https://www.w3schools.com/python/python_lists.asp',
            'type': 'article',
        },
        {
            'title': 'Python 列表和元组 — 菜鸟教程',
            'url': 'https://www.runoob.com/python/python-lists.html',
            'type': 'article',
        },
    ],
    'dictionaries': [
        {
            'title': 'Python 字典 — 廖雪峰教程',
            'url': 'https://www.liaoxuefeng.com/wiki/1016959663602400/1017000000602682',
            'type': 'article',
        },
        {
            'title': 'Python Dictionaries — W3Schools',
            'url': 'https://www.w3schools.com/python/python_dictionaries.asp',
            'type': 'article',
        },
        {
            'title': 'Python 字典 — 菜鸟教程',
            'url': 'https://www.runoob.com/python/python-dictionary.html',
            'type': 'article',
        },
    ],
}

# Type icons for frontend display
RESOURCE_TYPE_ICONS = {
    'article': '📄',
    'video': '▶',
    'documentation': '🌐',
}

RESOURCE_TYPE_LABELS = {
    'article': '文章',
    'video': '视频',
    'documentation': '官方文档',
}


def get_resources(content_id, skill_name=None, level=None):
    """Get recommended resources for a content_id.

    Uses Smart Search + Cache with unique key.
    Returns a list of resource dicts, or empty list if none found.
    """
    from .cache import get_cached_resources, save_resource_cache, make_cache_key
    from .search import search_resources, rank_resources

    cache_key = make_cache_key(skill_name, level, content_id)

    # 1. Check cache
    cached = get_cached_resources(cache_key)
    if cached is not None:
        return cached

    # 2. Search (currently static mapping, future: web search)
    raw = search_resources(skill_name or '', level or '', content_id, knowledge_point=content_id)

    # 3. Rank and return top 5
    resources = rank_resources(raw)

    # 4. Save to cache
    try:
        save_resource_cache(cache_key, skill_name, resources)
    except Exception:
        pass  # Cache failure is non-fatal

    return resources
