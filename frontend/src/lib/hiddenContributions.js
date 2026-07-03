const HIDDEN_WELCOME_CONTRIBUTION_SLUGS = new Set([
  'builder-welcome',
  'builder_welcome',
  'community-welcome',
  'community_welcome',
]);

const HIDDEN_WELCOME_CONTRIBUTION_NAMES = [
  'builder welcome',
  'community welcome',
];

export function getContributionTypeSlug(contribution) {
  return String(
    contribution?.contribution_type_details?.slug ||
      contribution?.contribution_type_slug ||
      contribution?.contribution_type?.slug ||
      contribution?.contribution?.contribution_type_details?.slug ||
      contribution?.contribution?.contribution_type_slug ||
      contribution?.contribution?.contribution_type?.slug ||
      ''
  ).toLowerCase();
}

export function getContributionTypeName(contribution) {
  return String(
    contribution?.contribution_type_details?.name ||
      contribution?.contribution_type_name ||
      contribution?.contribution_type?.name ||
      contribution?.contribution?.contribution_type_details?.name ||
      contribution?.contribution?.contribution_type_name ||
      contribution?.contribution?.contribution_type?.name ||
      ''
  ).toLowerCase();
}

export function isHiddenWelcomeContribution(contribution) {
  const slug = getContributionTypeSlug(contribution);
  if (slug && HIDDEN_WELCOME_CONTRIBUTION_SLUGS.has(slug)) return true;

  const name = getContributionTypeName(contribution);
  return Boolean(name && HIDDEN_WELCOME_CONTRIBUTION_NAMES.some((hiddenName) => name.includes(hiddenName)));
}

export function visibleContributions(contributions) {
  return (contributions || []).filter((contribution) => !isHiddenWelcomeContribution(contribution));
}
