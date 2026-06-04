"""Brave Provider self-test.

Run with: python test_brave_provider.py
"""

import sys
import os
sys.path.insert(0, r"C:\Users\luojinfa\Desktop\AI  Coach")

from engine.content.providers.brave_provider import BraveProvider
from engine.content.providers.static_provider import StaticProvider
from engine.content.providers.mock_provider import MockProvider
from engine.content.providers import get_provider


def test1_init():
    """BraveProvider 初始化成功."""
    print('[Test 1] BraveProvider init...', end=' ')
    p = BraveProvider()
    passed = isinstance(p, BraveProvider)
    print('PASS' if passed else 'FAIL')
    return passed


def test2_search_without_key():
    """搜索无 API Key 时回退到 StaticProvider."""
    print('[Test 2] Search without API key (fallback)...', end=' ')
    # Ensure no API key
    os.environ.pop('BRAVE_API_KEY', None)
    p = BraveProvider()
    results = p.search('variables', limit=3)
    passed = len(results) > 0  # Should get static results
    print(f'found={len(results)}', 'PASS' if passed else 'FAIL')
    return passed


def test3_normalize():
    """结果标准化."""
    print('[Test 3] Normalize result...', end=' ')
    raw = {'title': 'Test', 'url': 'https://docs.python.org/3/tutorial'}
    p = BraveProvider()
    result = p._normalize(raw)
    passed = all(k in result for k in ['title', 'url', 'type', 'source', 'score'])
    print(f'source={result["source"]}', 'PASS' if passed else 'FAIL')
    return passed


def test4_classify_type():
    """资源分类."""
    print('[Test 4] Classify type...', end=' ')
    p = BraveProvider()
    t1 = p._classify_type('https://youtube.com/watch?v=abc')
    t2 = p._classify_type('https://docs.python.org/3/')
    t3 = p._classify_type('https://realpython.com/python-variables/')
    passed = t1 == 'video' and t2 == 'documentation' and t3 == 'article'
    print(f'youtube={t1} docs={t2} article={t3}', 'PASS' if passed else 'FAIL')
    return passed


def test5_cache_write():
    """缓存写入."""
    print('[Test 5] Cache write...', end=' ')
    sys.path.insert(0, r"C:\Users\luojinfa\Desktop\AI  Coach")
    from app import create_app
    from models import db, ResourceCache
    from engine.content.cache import save_resource_cache, get_cached_resources
    app = create_app()
    with app.app_context():
        save_resource_cache('test_brave_cache', 'Python', [{'title': 'test'}])
        cached = get_cached_resources('test_brave_cache')
        passed = cached is not None and len(cached) == 1
    print('PASS' if passed else 'FAIL')
    return passed


def test6_cache_hit():
    """缓存命中."""
    print('[Test 6] Cache hit...', end=' ')
    from engine.content.cache import get_cached_resources
    from app import create_app
    app = create_app()
    with app.app_context():
        cached = get_cached_resources('test_brave_cache')
        passed = cached is not None
    print('PASS' if passed else 'FAIL')
    return passed


def test7_api_key_missing_fallback():
    """API Key 缺失自动回退."""
    print('[Test 7] API Key missing auto-fallback...', end=' ')
    os.environ.pop('BRAVE_API_KEY', None)
    import engine.content.providers as prov
    prov._current_provider = None
    p = get_provider('brave')
    passed = isinstance(p, StaticProvider)
    print(f'type={type(p).__name__}', 'PASS' if passed else 'FAIL')
    return passed


def test8_search_failure_fallback():
    """搜索失败自动回退."""
    print('[Test 8] Search failure fallback...', end=' ')
    p = BraveProvider()
    p.api_key = 'invalid-key-12345'
    results = p.search('variables', limit=3)
    passed = len(results) > 0  # Should fallback to static
    print(f'found={len(results)}', 'PASS' if passed else 'FAIL')
    return passed


def test9_factory_brave():
    """Factory 返回 BraveProvider."""
    print('[Test 9] Factory returns BraveProvider...', end=' ')
    os.environ['BRAVE_API_KEY'] = 'test-key'
    import engine.content.providers as prov
    prov._current_provider = None
    p = get_provider('brave')
    passed = isinstance(p, BraveProvider)
    os.environ.pop('BRAVE_API_KEY', None)
    prov._current_provider = None
    print(f'type={type(p).__name__}', 'PASS' if passed else 'FAIL')
    return passed


def test10_resource_engine_compatible():
    """Resource Engine 兼容."""
    print('[Test 10] Resource Engine compatible...', end=' ')
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
    print('PHASE 13.2 - BRAVE PROVIDER SELF-TEST')
    print('=' * 60)

    results = [
        test1_init(),
        test2_search_without_key(),
        test3_normalize(),
        test4_classify_type(),
        test5_cache_write(),
        test6_cache_hit(),
        test7_api_key_missing_fallback(),
        test8_search_failure_fallback(),
        test9_factory_brave(),
        test10_resource_engine_compatible(),
    ]

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f'\n{"=" * 60}')
    print(f'RESULT: {passed}/{total} passed')
    print(f'{"=" * 60}')
    sys.exit(0 if passed == total else 1)
