"""SearchProvider — abstract base class for resource search providers.

All providers must implement search(query, limit) and return a list of
standardized resource dicts:
    [{"title", "url", "type", "source", "score"}]
"""


class SearchProvider:
    """Base class for search providers. Subclasses must implement search()."""

    def search(self, query, limit=5):
        """Search for resources matching *query*.

        Args:
            query: search keyword or content_id
            limit: max results to return (default 5)

        Returns:
            list of {"title", "url", "type", "source", "score"} dicts
        """
        raise NotImplementedError
