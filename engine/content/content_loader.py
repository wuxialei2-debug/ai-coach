"""Content Loader — loads content JSON files from the content/ directory.

Exports:
    load_content(skill, level, content_id) -> dict
    get_default_content(content_id) -> dict
"""

import json
import os

_CONTENT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'content')

# { (skill, level): {content_id: data} }
_cache = {}


def load_content(skill, level, content_id):
    """Load a content file by skill, level, and content_id.

    Returns the parsed JSON dict, or a default placeholder if not found.
    """
    level_map = {
        '零基础': 'beginner',
        '初级': 'beginner',
        '中级': 'intermediate',
        '高级': 'advanced',
    }
    eng_level = level_map.get(level, 'beginner')

    skill_map = {
        'Python': 'python',
        '英语': 'english',
        '摄影': 'photography',
        '写作': 'writing',
    }
    eng_skill = skill_map.get(skill, skill)

    key = (eng_skill, eng_level)
    if key not in _cache:
        _load_level(eng_skill, eng_level)

    data = _cache.get(key, {}).get(content_id)
    if data:
        return data

    # Fallback: try beginner level
    if eng_level != 'beginner':
        fallback_key = (eng_skill, 'beginner')
        if fallback_key not in _cache:
            _load_level(eng_skill, 'beginner')
        data = _cache.get(fallback_key, {}).get(content_id)
        if data:
            return data

    return get_default_content(content_id)


def get_default_content(content_id):
    """Return a placeholder content dict when real content is unavailable."""
    title = content_id.replace('_', ' ').title() if content_id else '未知知识点'
    return {
        'id': content_id or 'unknown',
        'title': title,
        'estimated_minutes': 15,
        'summary': '该知识点的内容正在建设中。',
        'content': [
            f'关于 {title} 的详细学习内容正在编写中。',
            '请先完成其他已有内容的学习任务。',
        ],
        'examples': [],
        'practice': ['请结合学习内容自行练习。'],
        'quiz': [],
        'next': None,
    }


def _load_level(skill_dir, level_dir):
    """Load all content files for a given skill/level into cache."""
    dir_path = os.path.join(_CONTENT_DIR, skill_dir, level_dir)
    key = (skill_dir, level_dir)
    _cache[key] = {}

    if not os.path.isdir(dir_path):
        return

    for fname in os.listdir(dir_path):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(dir_path, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            content_id = data.get('id', fname[:-5])
            _cache[key][content_id] = data
        except (json.JSONDecodeError, IOError):
            continue


def _content_id_for_kp(skill_name, kp_name):
    """Map a knowledge point name to a content_id.

    Tries exact match, then title substring match, then keyword overlap.
    Returns None if no mapping found.
    """
    level_map = {
        'Python': 'python',
        '英语': 'english',
        '摄影': 'photography',
        '写作': 'writing',
    }
    skill_dir = level_map.get(skill_name, skill_name)

    all_cached = {}
    for level in ('beginner', 'intermediate', 'advanced'):
        key = (skill_dir, level)
        if key not in _cache:
            _load_level(skill_dir, level)
        all_cached.update(_cache.get(key, {}))

    # Exact match on content_id
    if kp_name in all_cached:
        return kp_name

    # Title substring match
    for cid, data in all_cached.items():
        title = data.get('title', '')
        if kp_name in title or title in kp_name:
            return cid

    # Keyword overlap: check if any 2+ char substring is shared
    def _keywords(s):
        """Extract significant substrings from Chinese/English text."""
        words = set()
        # Split by common delimiters
        cleaned = s
        for delim in ('、', '与', '和', '（', '）', '的', '语句', '操作', '处理', '定义', '调用'):
            cleaned = cleaned.replace(delim, ' ')
        for w in cleaned.split():
            if len(w) >= 2:
                words.add(w)
        return words

    kp_words = _keywords(kp_name)
    best_cid = None
    best_overlap = 0
    for cid, data in all_cached.items():
        title = data.get('title', '')
        title_words = _keywords(title)
        overlap = len(kp_words & title_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_cid = cid

    if best_overlap >= 1:
        return best_cid

    # Fallback: direct substring check with 2-char minimum
    for cid, data in all_cached.items():
        title = data.get('title', '')
        for i in range(len(kp_name) - 1):
            substr = kp_name[i:i+2]
            if substr.isalnum() and not substr.isascii() and substr in title:
                return cid

    return None
