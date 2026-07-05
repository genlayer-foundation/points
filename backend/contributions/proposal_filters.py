from django.db.models import Q

from .models import SubmittedContribution


class ProposalReviewStatusFilterMixin:
    """Shared proposal review status filters for steward and AI review queues."""

    def filter_has_proposal(self, queryset, name, value):
        """Filter submissions that have/don't have a proposal ready for final review."""
        if value is True:
            queryset = queryset.filter(proposed_action__isnull=False)
            if not self.data.get('proposal_review_status'):
                queryset = queryset.filter(
                    Q(proposal_review_status=SubmittedContribution.PROPOSAL_STATUS_PENDING_REVIEW)
                    | Q(proposal_review_status__isnull=True)
                )
            return queryset
        if value is False:
            return queryset.filter(proposed_action__isnull=True)
        return queryset

    def filter_proposal_review_status(self, queryset, name, value):
        """Filter by active proposal review status."""
        status_map = {
            'pending': SubmittedContribution.PROPOSAL_STATUS_PENDING_REVIEW,
            'pending_review': SubmittedContribution.PROPOSAL_STATUS_PENDING_REVIEW,
            'questioned': SubmittedContribution.PROPOSAL_STATUS_QUESTIONED,
        }
        status_value = status_map.get(str(value).lower())
        if status_value:
            return queryset.filter(
                proposed_action__isnull=False,
                proposal_review_status=status_value,
            )
        return queryset.none()
