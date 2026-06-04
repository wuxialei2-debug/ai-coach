"""Provider Factory — unified entry point for search providers.

Usage:
    from engine.content.providers import get_provider
    provider = get_provider()
    results = provider.search("variables", limit=5)
"""

from .static_provider import StaticProvider
from .mock_provider import MockProvider
from .brave_provider import BraveProvider

DEFAULT_PROVIDER_TYPE = 'static'

_PROVIDER_MAP = {
    'static': StaticProvider,
    'mock': MockProvider,
    'brave': BraveProvider,
}

_current_provider = None


def get_provider(provider_type=None):
    """Return a SearchProvider instance.

    Auto-fallback: if brave is selected but API key is missing,
    falls back to StaticProvider.
    """
    global _current_provider

    if provider_type is None:
        try:
            from config import Config
            provider_type = getattr(Config, 'PROVIDER_TYPE', DEFAULT_PROVIDER_TYPE)
        except Exception:
            provider_type = DEFAULT_PROVIDER_TYPE

    # Auto-fallback: brave without API key → static
    if provider_type == 'brave':
        import os
        if not os.environ.get('BRAVE_API_KEY', ''):
            try:
                from config import Config
                if not getattr(Config, 'BRAVE_API_KEY', ''):
                    print('[BraveProvider] API Key missing, fallback → StaticProvider')
                    provider_type = 'static'
            except Exception:
                provider_type = 'static'

    if _current_provider is not None and provider_type == getattr(_current_provider, '_provider_type', None):
        return _current_provider

    cls = _PROVIDER_MAP.get(provider_type, StaticProvider)
    provider = cls()
    provider._provider_type = provider_type
    _current_provider = provider

    print(f'[Provider] Using {cls.__name__}')
    return provider
