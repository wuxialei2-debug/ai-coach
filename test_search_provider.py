"""Search Provider self-test.

Run with: python test_search_provider.py
"""

import sys
sys.path.insert(0, r"C:\Users\luojinfa\Desktop\AI  Coach")

from engine.content.providers.base import SearchProvider
from engine.content.providers.static_provider import StaticProvider
from engine.content.providers.mock_provider import MockProvider
from engine.content.providers import get_provider


def test_static_provider():
    """Test 1: StaticProvider returns resources."""
    print('[Test 1] StaticProvider returns resources...', end=' ')
    p = StaticProvider()
    results = p.search('variables', limit=3)
    passed = len(results) > 0 and 'title' in results[0] and 'url' in results[0]
    print(f'found={len(results)}', 'PASS' if passed else 'FAIL')
    return passed


def test_mock_provider():
    """Test 2: MockProvider returns resources."""
    print('[Test 2] MockProvider returns resources...', end=' ')
    p = MockProvider()
    results = p.search('anything', limit=3)
    passed = len(results) == 3 and 'Mock' in results[0]['title']
    print(f'found={len(results)}', 'PASS' if passed else 'FAIL')
    return passed


def test_factory():
    """Test 3: Factory returns correct provider."""
    print('[Test 3] Factory returns correct provider...', end=' ')
    p = get_provider('static')
    passed_static = isinstance(p, StaticProvider)
    p2 = get_provider('mock')
    passed_mock = isinstance(p2, MockProvider)
    passed = passed_static and passed_mock
    print(f'static={passed_static} mock={passed_mock}', 'PASS' if passed else 'FAIL')
    return passed


def test_search_engine_uses_provider():
    """Test 4: Search Engine calls Provider."""
    print('[Test 4] Search Engine calls Provider...', end=' ')
    # Reset provider to static
    import engine.content.providers as prov
    prov._current_provider = None

    from engine.content.search import search_resources
    results = search_resources('Python', '零基础', 'variables')
    passed = len(results) > 0 and 'title' in results[0]
    print(f'found={len(results)}', 'PASS' if passed else 'FAIL')
    return passed


def test_resource_engine_compatible():
    """Test 5: Resource Engine compatible."""
    print('[Test 5] Resource Engine compatible...', end=' ')
    from app import create_app
    app = create_app()
    with app.app_context():
        from engine.content.resources import get_resources
        results = get_resources('variables', 'Python', '零基础')
        passed = len(results) > 0
    print(f'found={len(results)}', 'PASS' if passed else 'FAIL')
    return passed


if __name__ == '__main__':
    print('=' * 60)
    print('PHASE 13.1 - SEARCH PROVIDER SELF-TEST')
    print('=' * 60)

    results = [
        test_static_provider(),
        test_mock_provider(),
        test_factory(),
        test_search_engine_uses_provider(),
        test_resource_engine_compatible(),
    ]

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f'\n{"=" * 60}')
    print(f'RESULT: {passed}/{total} passed')
    print(f'{"=" * 60}')
    sys.exit(0 if passed == total else 1)
