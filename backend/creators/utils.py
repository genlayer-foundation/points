from creators.models import Creator


def ensure_creator_status(user):
    if not user or not getattr(user, 'pk', None):
        return None

    creator, _ = Creator.objects.get_or_create(user=user)
    return creator


def ensure_creator_status_for_users(user_ids):
    user_ids = {user_id for user_id in user_ids if user_id}
    if not user_ids:
        return

    existing_user_ids = set(
        Creator.objects.filter(user_id__in=user_ids).values_list('user_id', flat=True)
    )
    missing_user_ids = user_ids - existing_user_ids
    if missing_user_ids:
        Creator.objects.bulk_create(
            [Creator(user_id=user_id) for user_id in missing_user_ids],
            ignore_conflicts=True,
            batch_size=500,
        )
