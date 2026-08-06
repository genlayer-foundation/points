const PROJECT_CONTRIBUTION_TYPE_SLUGS = new Set([
  'projects',
  'projects-and-milestones',
  'projects-milestones',
  'project-milestone',
]);

/**
 * Keep legacy project slugs recognizable while old contribution types remain
 * addressable from historical submissions.
 *
 * @param {{ slug?: string } | null | undefined} contributionType
 */
export function isProjectContributionType(contributionType) {
  return PROJECT_CONTRIBUTION_TYPE_SLUGS.has(contributionType?.slug);
}
