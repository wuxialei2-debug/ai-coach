"""StaticProvider — reads from the built-in RESOURCE_MAP.

This is the default provider. It returns pre-curated resources
without any network calls, with fallback search links when
the content_id is not found in RESOURCE_MAP.
"""

from .base import SearchProvider
from ..resources import RESOURCE_MAP


class StaticProvider(SearchProvider):
    """Return resources from the static RESOURCE_MAP with fallback."""

    def search(self, query, limit=5, knowledge_point=None, skill_name=None):
        """Look up resources by content_id in RESOURCE_MAP.

        When the content_id is not found (e.g. photography KP names),
        generates fallback search links using the knowledge_point name.

        Args:
            query: content_id (e.g. "variables", "functions")
            limit: max results
            knowledge_point: KP name for fallback generation
            skill_name: skill name for context

        Returns:
            list of standardized resource dicts
        """
        raw = RESOURCE_MAP.get(query, [])
        if not raw:
            return self._generate_fallback(knowledge_point or query, skill_name, limit)

        results = []
        for item in raw[:limit]:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'type': item.get('type', 'article'),
                'source': self._extract_domain(item.get('url', '')),
                'score': 0,
            })
        return results

    def _generate_fallback(self, knowledge_point, skill_name, limit):
        """Generate fallback search links based on KP name.

        Creates links to Baidu Baike, Bilibili, and YouTube search results
        so the user always has actionable resources even without curated content.
        """
        from urllib.parse import quote
        encoded = quote(knowledge_point)

        fallback = []

        # Baidu Baike — Chinese encyclopedia
        fallback.append({
            'title': f'{knowledge_point} — 百度百科',
            'url': f'https://baike.baidu.com/item/{encoded}',
            'type': 'documentation',
            'source': 'baike.baidu.com',
            'score': 70,
        })

        # Bilibili — Chinese video platform
        fallback.append({
            'title': f'{knowledge_point} — Bilibili 视频教程',
            'url': f'https://search.bilibili.com/all?keyword={encoded}',
            'type': 'video',
            'source': 'bilibili.com',
            'score': 65,
        })

        # YouTube — international video platform
        fallback.append({
            'title': f'{knowledge_point} — YouTube 教程',
            'url': f'https://www.youtube.com/results?search_query={encoded}',
            'type': 'video',
            'source': 'youtube.com',
            'score': 60,
        })

        # Google — general search fallback
        fallback.append({
            'title': f'{knowledge_point} — Google 搜索',
            'url': f'https://www.google.com/search?q={encoded}',
            'type': 'article',
            'source': 'google.com',
            'score': 50,
        })

        # Skill-specific extra: add Bing/CN search for Chinese skills
        if skill_name and any(c > '一' for c in skill_name):
            fallback.append({
                'title': f'{knowledge_point} — Bing 搜索',
                'url': f'https://cn.bing.com/search?q={encoded}',
                'type': 'article',
                'source': 'bing.com',
                'score': 45,
            })

        return fallback[:limit]

    @staticmethod
    def _extract_domain(url):
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or ''
            return host[4:] if host.startswith('www.') else host
        except Exception:
            return ''
