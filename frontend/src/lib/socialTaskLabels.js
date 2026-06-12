// Display labels for the task surface per category. Backend keeps a single
// "SocialTask" model + "/social-tasks" API; the UI just relabels the surface.

const LABELS = {
  community: {
    title: 'Social tasks',
    subtitle: 'Quick wins to support the GenLayer community.',
    listPath: '/community/tasks',
  },
  builder: {
    title: 'Builder tasks',
    subtitle: 'Quick wins to grow the builder ecosystem.',
    listPath: '/builders/tasks',
  },
  validator: {
    title: 'Validator tasks',
    subtitle: 'Quick wins to support the validator network.',
    listPath: '/validators/tasks',
  },
};

const DEFAULT_LABEL = LABELS.community;

export function getTaskLabels(category) {
  return LABELS[category] || DEFAULT_LABEL;
}
