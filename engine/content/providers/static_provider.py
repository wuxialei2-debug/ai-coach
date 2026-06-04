"""StaticProvider — reads from the built-in RESOURCE_MAP.

This is the default provider. It returns pre-curated resources
without any network calls.
"""

from .base import SearchProvider
from ..resources import RESOURCE_MAP


class StaticProvider(SearchProvider):
    """Return resources from the static RESOURCE_MAP."""

    def search(self, query, limit=5):
        """Look up resources by content_id in RESOURCE_MAP.

        Args:
            query: content_id (e.g. "variables", "functions")
            limit: max results

        Returns:
            list of standardized resource dicts
        """
        raw = RESOURCE_MAP.get(query, [])
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

    @staticmethod
    def _extract_domain(url):
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or ''
            return host[4:] if host.startswith('www.') else host
        except Exception:
            return ''
