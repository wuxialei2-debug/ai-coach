"""BraveProvider — real web search via Brave Search API.

Requires BRAVE_API_KEY environment variable.
Falls back to StaticProvider on any failure.
"""

import os
import json
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from .base import SearchProvider

# ── Skill-specific search templates ──────────────────────────────────────

_SEARCH_QUERIES = {
    'Python': {
        'default': '{kp} Python tutorial',
        'article': '{kp} Python tutorial beginner guide',
        'video': '{kp} Python tutorial video',
        'documentation': '{kp} Python official documentation',
    },
    '英语': {
        'default': 'English {kp} lesson',
        'article': 'English {kp} grammar tutorial',
        'video': 'English {kp} video lesson',
        'documentation': 'English {kp} reference',
    },
    '摄影': {
        'default': 'Photography {kp} tutorial',
        'article': 'Photography {kp} guide',
        'video': 'Photography {kp} tutorial video',
        'documentation': 'Photography {kp} reference',
    },
    '写作': {
        'default': 'Writing {kp} guide',
        'article': 'Writing {kp} tutorial',
        'video': 'Writing {kp} video lesson',
        'documentation': 'Writing {kp} reference',
    },
}

# ── Domain whitelist (per skill) ─────────────────────────────────────────

_DOMAIN_WHITELIST = {
    'Python': [
        'python.org', 'docs.python.org', 'realpython.com',
        'w3schools.com', 'freecodecamp.org', 'runoob.com',
        'liaoxuefeng.com',
    ],
    '英语': [
        'bbc.com', 'cambridge.org', 'oxfordlearnersdictionaries.com',
        'engvid.com', 'w3schools.com',
    ],
    '摄影': [
        'photographylife.com', 'fstoppers.com',
        'digital-photography-school.com',
    ],
    '写作': [
        'grammarly.com', 'hubspot.com', 'copyblogger.com',
    ],
}

# General fallback whitelist
_GENERAL_WHITELIST = [
    'python.org', 'docs.python.org', 'w3schools.com',
    'freecodecamp.org', 'realpython.com', 'developer.mozilla.org',
    'coursera.org', 'edx.org', 'khanacademy.org', 'youtube.com',
    'runoob.com', 'liaoxuefeng.com',
]


class BraveProvider(SearchProvider):
    """Search resources using Brave Search API."""

    def __init__(self):
        self.api_key = os.environ.get('BRAVE_API_KEY', '')

    def search(self, query, limit=5, knowledge_point=None, skill_name=None):
        """Search Brave for resources matching *query*.

        Args:
            query: content_id (e.g. "variables")
            limit: max results
            knowledge_point: KP name for fallback
            skill_name: skill name for context

        Returns:
            list of standardized resource dicts
        """
        if not self.api_key:
            print('[BraveProvider] API Key missing, fallback → StaticProvider')
            return self._fallback_static(query, limit, knowledge_point, skill_name)

        # Build search query
        search_query = self._build_query(query)
        print(f'[BraveProvider] Search query: {search_query}')

        try:
            raw_results = self._call_api(search_query, limit * 2)
        except Exception as e:
            print(f'[BraveProvider] Search failed: {e}, fallback → StaticProvider')
            return self._fallback_static(query, limit, knowledge_point, skill_name)

        # Normalize, classify, filter
        results = []
        for item in raw_results:
            normalized = self._normalize(item)
            normalized['type'] = self._classify_type(normalized['url'])
            results.append(normalized)

        # Whitelist scoring
        results = self._apply_whitelist(results, query)

        print(f'[BraveProvider] Results: {len(results)}')
        return results[:limit]

    def _build_query(self, content_id):
        """Build a search query from content_id."""
        kp = content_id.replace('_', ' ')
        return f'{kp} Python tutorial'

    def _call_api(self, query, count):
        """Call Brave Search API. Returns list of raw result dicts."""
        url = f'https://api.search.brave.com/res/v1/web/search?q={query}&count={count}'
        req = Request(url, headers={
            'Accept': 'application/json',
            'X-Subscription-Token': self.api_key,
        })
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        return data.get('web', {}).get('results', [])

    def _normalize(self, raw):
        """Normalize a Brave result to standard format."""
        url = raw.get('url', '')
        return {
            'title': raw.get('title', ''),
            'url': url,
            'type': 'article',
            'source': self._extract_domain(url),
            'score': 0,
        }

    @staticmethod
    def _extract_domain(url):
        try:
            host = urlparse(url).hostname or ''
            return host[4:] if host.startswith('www.') else host
        except Exception:
            return ''

    @staticmethod
    def _classify_type(url):
        """Classify resource type by URL domain."""
        domain = urlparse(url).hostname or ''
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'video'
        if 'docs' in domain or 'official' in domain:
            return 'documentation'
        return 'article'

    def _apply_whitelist(self, results, content_id):
        """Boost whitelisted domains, penalize non-whitelisted."""
        # Determine skill from content_id context
        skill = 'Python'  # Default
        for s in _SEARCH_QUERIES:
            if s.lower() in content_id.lower():
                skill = s
                break

        whitelist = _DOMAIN_WHITELIST.get(skill, _GENERAL_WHITELIST)

        for r in results:
            domain = r['source']
            if any(w in domain for w in whitelist):
                r['score'] = 80
            else:
                r['score'] = 20  # Penalize but don't remove
        return results

    @staticmethod
    def _fallback_static(query, limit, knowledge_point=None, skill_name=None):
        """Fall back to StaticProvider."""
        from .static_provider import StaticProvider
        return StaticProvider().search(query, limit, knowledge_point, skill_name)
