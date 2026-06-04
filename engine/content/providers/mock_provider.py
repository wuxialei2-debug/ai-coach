"""MockProvider — returns fixed test data for development and testing."""

from .base import SearchProvider

MOCK_RESULTS = [
    {
        'title': 'Mock Python Variables Tutorial',
        'url': 'https://example.com/python-variables',
        'type': 'article',
        'source': 'example.com',
        'score': 80,
    },
    {
        'title': 'Mock Python Variables Video',
        'url': 'https://example.com/python-variables-video',
        'type': 'video',
        'source': 'example.com',
        'score': 70,
    },
    {
        'title': 'Mock Python Variables Docs',
        'url': 'https://docs.python.org/3/variables',
        'type': 'documentation',
        'source': 'docs.python.org',
        'score': 90,
    },
]


class MockProvider(SearchProvider):
    """Return fixed mock data. For development and testing only."""

    def search(self, query, limit=5):
        """Return mock results regardless of query."""
        return MOCK_RESULTS[:limit]
