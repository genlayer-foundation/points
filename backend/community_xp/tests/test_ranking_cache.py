"""Semantics of the short-lived community aggregate cache."""

from django.core.cache import cache
from django.test import TestCase, override_settings

from community_xp.cache import (
    COMMUNITY_RANKING_CACHE_KEY,
    cached_or_compute,
    clear_community_caches,
)


LOCMEM = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'community-ranking-cache-tests',
    },
    'other': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'community-ranking-cache-tests-other',
    },
}


@override_settings(CACHES=LOCMEM)
class CachedOrComputeTest(TestCase):
    def setUp(self):
        cache.clear()
        clear_community_caches()
        self.calls = 0

    def counting(self, value):
        def compute():
            self.calls += 1
            return value
        return compute

    def test_miss_computes_and_stores(self):
        result = cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(1, 10)]))

        self.assertEqual(result, [(1, 10)])
        self.assertEqual(self.calls, 1)
        self.assertEqual(cache.get(COMMUNITY_RANKING_CACHE_KEY), [(1, 10)])

    def test_hit_does_not_recompute(self):
        cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(1, 10)]))
        result = cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(2, 20)]))

        self.assertEqual(result, [(1, 10)])
        self.assertEqual(self.calls, 1)

    def test_empty_result_is_cached_not_treated_as_a_miss(self):
        cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([]))
        result = cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(9, 90)]))

        self.assertEqual(result, [])
        self.assertEqual(self.calls, 1)

    def test_expiry_recomputes(self):
        cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(1, 10)]), ttl=1)
        cache.delete(COMMUNITY_RANKING_CACHE_KEY)  # stands in for the TTL elapsing

        result = cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(2, 20)]), ttl=1)

        self.assertEqual(result, [(2, 20)])
        self.assertEqual(self.calls, 2)

    def test_zero_ttl_bypasses_the_cache_entirely(self):
        cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(1, 10)]), ttl=0)
        cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(1, 10)]), ttl=0)

        self.assertEqual(self.calls, 2)
        self.assertIsNone(cache.get(COMMUNITY_RANKING_CACHE_KEY))

    def test_exception_propagates_and_caches_nothing(self):
        def boom():
            self.calls += 1
            raise ValueError('compute failed')

        with self.assertRaises(ValueError):
            cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, boom)

        self.assertIsNone(cache.get(COMMUNITY_RANKING_CACHE_KEY))

        # The next call must retry rather than serve a poisoned entry.
        result = cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(3, 30)]))
        self.assertEqual(result, [(3, 30)])
        self.assertEqual(self.calls, 2)

    def test_clear_community_caches_forces_a_recompute(self):
        cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(1, 10)]))
        clear_community_caches()
        result = cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(2, 20)]))

        self.assertEqual(result, [(2, 20)])
        self.assertEqual(self.calls, 2)

    def test_entry_is_isolated_to_the_default_alias(self):
        from django.core.cache import caches

        cached_or_compute(COMMUNITY_RANKING_CACHE_KEY, self.counting([(1, 10)]))

        self.assertIsNone(caches['other'].get(COMMUNITY_RANKING_CACHE_KEY))
