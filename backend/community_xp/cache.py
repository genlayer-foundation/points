"""
Short-lived caches for the shared, non-personalized community aggregates.

The community ranking queryset annotates every visible user with correlated
subqueries and then filters and orders on the computed alias, so no index can
serve it and every request that touches it scans the whole population. The
objects cached here take no request input and contain no per-user data: the
ranking snapshot is a list of (user_id, total_points), and the stats summary is
a set of member ids plus a points total. Everything personalized (search,
user_rank, profile_context, hydration) is still computed per request from the
cached snapshot.

The project configures no CACHES backend, so this is Django's per-process
LocMemCache: each Gunicorn worker on each container keeps its own copy. That
caps ranking scans at roughly (workers x containers) per TTL rather than one per
request, which helps most at steady state and least at maximum fan-out. Making
the relief independent of container count would need a shared cache tier.

Staleness is bounded rather than invalidated: MEE6 XP already lags by hours, so
a 60 second lag on ranks sits well inside the existing freshness envelope.
"""

from django.core.cache import cache


# Bump the version suffix whenever the score semantics, the ranking floor, or
# the cached value's shape changes, so old entries cannot be misread.
COMMUNITY_RANKING_CACHE_KEY = 'community:ranking:v1'
COMMUNITY_STATS_SUMMARY_CACHE_KEY = 'community:stats-summary:v1'
COMMUNITY_CACHE_TTL_SECONDS = 60


def cached_or_compute(key, compute, ttl=COMMUNITY_CACHE_TTL_SECONDS):
    """
    Return a cached value, computing and storing it on a miss.

    An empty result is a legitimate value, so misses are detected with
    ``is None`` rather than truthiness. A raising ``compute`` propagates and
    caches nothing.
    """
    if not ttl:
        return compute()

    cached = cache.get(key)
    if cached is not None:
        return cached

    value = compute()
    cache.set(key, value, ttl)
    return value


def clear_community_caches():
    """Drop both entries. Intended for tests and management commands."""
    cache.delete(COMMUNITY_RANKING_CACHE_KEY)
    cache.delete(COMMUNITY_STATS_SUMMARY_CACHE_KEY)
