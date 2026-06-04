"""Resource Cache — caching layer for Resource Engine.

Provides:
    make_cache_key(skill, level, content_id) -> str
    get_cached_resources(cache_key) -> list | None
    save_resource_cache(cache_key, skill_name, resources)
    cleanup_expired_cache() -> int
    enforce_cache_limit()
    get_cache_stats() -> dict
    get_cache_performance() -> dict
"""

import json
from datetime import datetime, timedelta

from models import db, ResourceCache

CACHE_TTL_DAYS = 7
MAX_RESOURCE_CACHE = 100

# In-memory performance counters (reset on restart)
_hits = 0
_misses = 0


def make_cache_key(skill, level, content_id):
    """Build a unique cache key: skill_level_content_id."""
    skill_part = skill.lower().replace(' ', '_') if skill else 'unknown'
    level_map = {'零基础': 'beginner', '初级': 'beginner',
                 '中级': 'intermediate', '高级': 'advanced'}
    level_part = level_map.get(level, 'beginner')
    return f'{skill_part}_{level_part}_{content_id}'


def get_cached_resources(cache_key):
    """Return cached resources for *cache_key* if valid, else None."""
    global _hits, _misses
    now = datetime.utcnow()
    row = ResourceCache.query.filter_by(keyword=cache_key)\
        .filter(ResourceCache.expires_at > now).first()
    if not row:
        _misses += 1
        return None
    _hits += 1
    try:
        return json.loads(row.resource_json)
    except (json.JSONDecodeError, TypeError):
        return None


def save_resource_cache(cache_key, skill_name, resources):
    """Save resources to cache. Overwrites existing entry for same key."""
    now = datetime.utcnow()
    existing = ResourceCache.query.filter_by(keyword=cache_key).first()
    if existing:
        existing.resource_json = json.dumps(resources, ensure_ascii=False)
        existing.skill_name = skill_name
        existing.created_at = now
        existing.expires_at = now + timedelta(days=CACHE_TTL_DAYS)
    else:
        row = ResourceCache(
            keyword=cache_key,
            skill_name=skill_name,
            resource_json=json.dumps(resources, ensure_ascii=False),
            created_at=now,
            expires_at=now + timedelta(days=CACHE_TTL_DAYS),
        )
        db.session.add(row)
    db.session.commit()
    enforce_cache_limit()


def cleanup_expired_cache():
    """Delete all expired cache entries. Returns count deleted."""
    now = datetime.utcnow()
    count = ResourceCache.query.filter(ResourceCache.expires_at < now).delete()
    db.session.commit()
    return count


def enforce_cache_limit():
    """Ensure cache does not exceed MAX_RESOURCE_CACHE entries."""
    total = ResourceCache.query.count()
    if total <= MAX_RESOURCE_CACHE:
        return
    excess = total - MAX_RESOURCE_CACHE
    oldest = ResourceCache.query.order_by(ResourceCache.created_at.asc())\
        .limit(excess).all()
    for row in oldest:
        db.session.delete(row)
    db.session.commit()


def get_cache_stats():
    """Return cache statistics."""
    now = datetime.utcnow()
    total = ResourceCache.query.count()
    expired = ResourceCache.query.filter(ResourceCache.expires_at < now).count()
    return {
        'cache_count': total,
        'expired_count': expired,
        'max_cache': MAX_RESOURCE_CACHE,
        'ttl_days': CACHE_TTL_DAYS,
    }


def get_cache_performance():
    """Return cache hit/miss statistics."""
    total = _hits + _misses
    hit_rate = round(_hits / total, 2) if total > 0 else 0
    return {
        'cache_hits': _hits,
        'cache_misses': _misses,
        'hit_rate': hit_rate,
    }
