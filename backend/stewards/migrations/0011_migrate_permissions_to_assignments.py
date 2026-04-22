"""
Collapse StewardPermission rows into StewardAssignment rows.

Collapsing rules (per steward):
  1. If the steward has the full action set
     {'accept','reject','request_more_info','propose'} on every ContributionType
     in the DB -> one global `full_review` assignment (scope null/null).
  2. Else, for each Category: if the steward has the full action set on every
     ContributionType in that category -> one `full_review` assignment scoped
     to the category.
  3. For any remaining types with the full action set -> one `full_review`
     assignment per type.
  4. For any remaining types where only `propose` is present (after removing
     rows consumed above) -> `propose` assignments, collapsed the same way
     (category-wide first, then per-type).

Partial combinations (e.g. `accept` without `reject`) are dropped with a
summary print so they can be reviewed manually before the old table is
deleted in the next migration.
"""
from collections import defaultdict

from django.db import migrations


FULL_ACTIONS = frozenset({'accept', 'reject', 'request_more_info', 'propose'})


def _build_assignments(steward_id, actions_by_type, all_type_ids_by_category):
    """Return (list of assignment dicts, set of unhandled (type_id, action))."""
    assignments = []
    unhandled = set()

    types_with_full = {
        ct_id for ct_id, acts in actions_by_type.items() if FULL_ACTIONS.issubset(acts)
    }
    types_with_propose_only = {
        ct_id for ct_id, acts in actions_by_type.items()
        if acts == {'propose'}
    }
    for ct_id, acts in actions_by_type.items():
        if ct_id in types_with_full or ct_id in types_with_propose_only:
            continue
        for a in acts:
            unhandled.add((ct_id, a))

    all_type_ids = set().union(*all_type_ids_by_category.values()) if all_type_ids_by_category else set()

    if all_type_ids and types_with_full >= all_type_ids:
        assignments.append({
            'steward_id': steward_id,
            'role': 'full_review',
            'scope_category_id': None,
            'scope_type_id': None,
        })
    else:
        covered_full = set()
        for cat_id, type_ids in all_type_ids_by_category.items():
            if type_ids and type_ids <= types_with_full:
                assignments.append({
                    'steward_id': steward_id,
                    'role': 'full_review',
                    'scope_category_id': cat_id,
                    'scope_type_id': None,
                })
                covered_full |= type_ids
        for ct_id in sorted(types_with_full - covered_full):
            assignments.append({
                'steward_id': steward_id,
                'role': 'full_review',
                'scope_category_id': None,
                'scope_type_id': ct_id,
            })

    propose_targets = set(types_with_propose_only)
    if propose_targets:
        if all_type_ids and propose_targets >= all_type_ids:
            assignments.append({
                'steward_id': steward_id,
                'role': 'propose',
                'scope_category_id': None,
                'scope_type_id': None,
            })
        else:
            covered_propose = set()
            for cat_id, type_ids in all_type_ids_by_category.items():
                if type_ids and type_ids <= propose_targets:
                    assignments.append({
                        'steward_id': steward_id,
                        'role': 'propose',
                        'scope_category_id': cat_id,
                        'scope_type_id': None,
                    })
                    covered_propose |= type_ids
            for ct_id in sorted(propose_targets - covered_propose):
                assignments.append({
                    'steward_id': steward_id,
                    'role': 'propose',
                    'scope_category_id': None,
                    'scope_type_id': ct_id,
                })

    return assignments, unhandled


def forwards(apps, schema_editor):
    StewardPermission = apps.get_model('stewards', 'StewardPermission')
    StewardAssignment = apps.get_model('stewards', 'StewardAssignment')
    ContributionType = apps.get_model('contributions', 'ContributionType')

    all_type_ids_by_category = defaultdict(set)
    for ct_id, cat_id in ContributionType.objects.values_list('id', 'category_id'):
        if cat_id is not None:
            all_type_ids_by_category[cat_id].add(ct_id)

    perms_by_steward = defaultdict(lambda: defaultdict(set))
    for steward_id, ct_id, action_name in StewardPermission.objects.values_list(
        'steward_id', 'contribution_type_id', 'action'
    ):
        perms_by_steward[steward_id][ct_id].add(action_name)

    to_create = []
    total_unhandled = []
    for steward_id, actions_by_type in perms_by_steward.items():
        assignments, unhandled = _build_assignments(
            steward_id, actions_by_type, all_type_ids_by_category
        )
        to_create.extend(assignments)
        if unhandled:
            total_unhandled.append((steward_id, unhandled))

    # ignore_conflicts keeps reruns idempotent against the unique constraint.
    StewardAssignment.objects.bulk_create(
        [StewardAssignment(**row) for row in to_create],
        ignore_conflicts=True,
    )

    print(
        f"\n  Migrated {StewardPermission.objects.count()} StewardPermission rows "
        f"into {len(to_create)} StewardAssignment rows "
        f"({len(perms_by_steward)} stewards)."
    )
    if total_unhandled:
        print("  Dropped partial permission combinations (manual review needed):")
        for steward_id, unhandled in total_unhandled:
            print(f"    steward_id={steward_id}: {sorted(unhandled)}")


def backwards(apps, schema_editor):
    StewardAssignment = apps.get_model('stewards', 'StewardAssignment')
    StewardAssignment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('stewards', '0010_stewardassignment'),
        ('contributions', '0052_contributiontype_required_evidence_url_types'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
