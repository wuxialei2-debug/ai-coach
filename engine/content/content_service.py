"""Content Service — high-level API for the Content Engine.

Exports:
    get_task_content(skill_name, level, kp_name) -> dict
    get_content_by_id(skill_name, level, content_id) -> dict
"""

from .content_loader import load_content, _content_id_for_kp


def get_task_content(skill_name, level, kp_name):
    """Look up content for a knowledge point name.

    Returns (content_id, content_dict) or (None, default_dict).
    """
    content_id = _content_id_for_kp(skill_name, kp_name)
    if content_id:
        return content_id, load_content(skill_name, level, content_id)
    return None, None


def get_content_by_id(skill_name, level, content_id):
    """Load content directly by content_id."""
    return load_content(skill_name, level, content_id)
