import re
from urllib.parse import urlparse, urlencode, parse_qs


# Query params to always strip during normalization
TRACKING_PARAMS = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term',
                   'utm_content', 't', 's', 'ref', 'si', 'feature'}

# Query params to preserve during normalization (essential for identity)
ESSENTIAL_PARAMS = {'v', 'import-contract'}


def normalize_url(url):
    """Normalize a URL for duplicate comparison.

    - Lowercase the scheme and host
    - Strip trailing slashes
    - Strip fragment (#...)
    - Remove tracking params (utm_*, t=, s=, ref=, etc.)
    - Preserve essential params (v= for YouTube, import-contract= for Studio)
    """
    if not url:
        return ''
    parsed = urlparse(url)
    scheme = (parsed.scheme or 'https').lower()
    host = (parsed.netloc or '').lower()
    path = parsed.path.rstrip('/')

    # Filter query params
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {}
    for key, values in query_params.items():
        if key in ESSENTIAL_PARAMS:
            filtered[key] = values
        elif key not in TRACKING_PARAMS:
            filtered[key] = values

    query_string = ''
    if filtered:
        # Flatten single-value lists for cleaner output
        flat = {}
        for k, v in sorted(filtered.items()):
            flat[k] = v[0] if len(v) == 1 else v
        query_string = '?' + urlencode(flat, doseq=True)

    return f"{scheme}://{host}{path}{query_string}"


def detect_url_type(url):
    """Detect the EvidenceURLType for a URL by matching against stored patterns.

    Returns the first matching EvidenceURLType, or the generic type if none match.
    Results are cached per-request via the caller; this function always queries the DB.
    """
    from .models import EvidenceURLType

    url_types = EvidenceURLType.objects.filter(is_generic=False).order_by('order')
    for url_type in url_types:
        for pattern in url_type.url_patterns:
            try:
                if re.search(pattern, url, re.IGNORECASE):
                    return url_type
            except re.error:
                continue

    # Fallback to generic type
    generic = EvidenceURLType.objects.filter(is_generic=True).first()
    return generic


def extract_handle(url, evidence_url_type):
    """Extract a handle/owner from a URL using the type's handle_extract_pattern.

    Returns the extracted handle (lowercase) or None if no pattern or no match.
    """
    if not evidence_url_type or not evidence_url_type.handle_extract_pattern:
        return None
    try:
        match = re.search(evidence_url_type.handle_extract_pattern, url, re.IGNORECASE)
        if match:
            return match.group('handle').lower()
    except (re.error, IndexError):
        pass
    return None


def get_user_social_handle(user, social_account_type):
    """Get the user's linked handle for a social account type.

    Returns the platform_username (lowercase) or None if not linked.
    """
    connection_map = {
        'twitter': 'twitterconnection',
        'github': 'githubconnection',
    }
    relation_name = connection_map.get(social_account_type)
    if not relation_name:
        return None
    try:
        connection = getattr(user, relation_name)
        return connection.platform_username.lower() if connection.platform_username else None
    except Exception:
        return None


def validate_handle_ownership(url, evidence_url_type, user):
    """Validate that the handle in the URL matches the user's linked account.

    Returns an error message string if there's a mismatch or account not linked,
    or None if OK.
    Skips validation if:
    - The URL type has no ownership_social_account configured
    """
    if not evidence_url_type or not evidence_url_type.ownership_social_account:
        return None

    platform_labels = {
        'twitter': 'X (Twitter)',
        'github': 'GitHub',
    }
    platform = platform_labels.get(
        evidence_url_type.ownership_social_account,
        evidence_url_type.ownership_social_account,
    )

    user_handle = get_user_social_handle(user, evidence_url_type.ownership_social_account)
    if not user_handle:
        return (
            f"You must link your {platform} account before submitting "
            f"{evidence_url_type.name} evidence."
        )

    url_handle = extract_handle(url, evidence_url_type)
    if not url_handle:
        # Could not extract handle from URL -- skip check
        return None

    if url_handle != user_handle:
        return (
            f"The {platform} handle in this URL (@{url_handle}) does not match "
            f"your linked account (@{user_handle})."
        )

    return None


def check_duplicate_url(url, exclude_submission_id=None):
    """Check if a normalized URL already exists in evidence for active submissions.

    Checks against submissions with state: pending, accepted, more_info_needed.
    Also checks against accepted contributions (Evidence linked to Contribution).

    Uses the indexed normalized_url field for fast lookups.

    Returns a description string if duplicate found, or None.
    """
    from .models import Evidence

    normalized = normalize_url(url)
    if not normalized:
        return None

    # Check evidence on submitted contributions (pending/accepted/more_info_needed)
    submission_qs = Evidence.objects.filter(
        normalized_url=normalized,
        submitted_contribution__isnull=False,
        submitted_contribution__state__in=['pending', 'accepted', 'more_info_needed'],
    )

    if exclude_submission_id:
        submission_qs = submission_qs.exclude(
            submitted_contribution__id=exclude_submission_id,
        )

    if submission_qs.exists():
        return "This URL has already been submitted."

    # Check evidence on accepted contributions
    if Evidence.objects.filter(
        normalized_url=normalized,
        contribution__isnull=False,
        contribution__frozen_global_points__gt=0,
    ).exists():
        return "This URL has already been submitted in an accepted contribution."

    return None
