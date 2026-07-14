from django.db.models import Exists, OuterRef

from .models import SubmissionNote, SubmissionStateTransition


def more_info_request_notes():
    """Recorded requests rendered by the submission card's history blocks."""
    return SubmissionNote.objects.filter(
        submitted_contribution_id=OuterRef('pk'),
        is_proposal=False,
        data__action='more_info',
    )


def more_info_resubmission_transitions():
    """Transitions that prove a submitter reopened a more-info request."""
    return SubmissionStateTransition.objects.filter(
        submitted_contribution_id=OuterRef('pk'),
        event=SubmissionStateTransition.EVENT_EDITED,
        from_state='more_info_needed',
        to_state='pending',
    )


def annotate_more_info_flags(queryset):
    """Expose request-history and durable transition flags without N+1 queries."""
    return queryset.annotate(
        has_more_info_request_flag=Exists(more_info_request_notes()),
        more_info_resubmitted_flag=Exists(more_info_resubmission_transitions()),
    )


class SubmissionLifecycleFilterMixin:
    """Shared history filters for steward and DAI submission queues."""

    def filter_has_more_info_request(self, queryset, name, value):
        request_exists = Exists(more_info_request_notes())
        if value is True:
            return queryset.filter(request_exists)
        if value is False:
            return queryset.exclude(request_exists)
        return queryset

    def filter_is_more_info_resubmitted(self, queryset, name, value):
        transition_exists = Exists(more_info_resubmission_transitions())
        if value is True:
            return queryset.filter(transition_exists)
        if value is False:
            return queryset.exclude(transition_exists)
        return queryset
