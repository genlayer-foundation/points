const ROLE_ORDER = [
  {
    key: "builder",
    label: "Builder",
    category: "builder",
    isActive: (participant) =>
      participant?.builder || participant?.has_builder_welcome,
  },
  {
    key: "validator",
    label: "Validator",
    waitlistLabel: "Validator Waitlist",
    category: "validator",
    isActive: (participant) =>
      participant?.validator || participant?.has_validator_waitlist,
  },
  {
    key: "community",
    label: "Community",
    category: "community",
    isActive: (participant) => participant?.creator,
  },
];

function toNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function getRoleLabel(role, participant) {
  if (
    role.key === "validator" &&
    participant?.has_validator_waitlist &&
    !participant?.validator
  ) {
    return role.waitlistLabel;
  }

  return role.label;
}

function toRoleBadge(role, participant) {
  return {
    key: role.key,
    label: getRoleLabel(role, participant),
    category: role.category,
  };
}

/**
 * Derive a profile headline from role-specific activity instead of summing
 * points across categories with different reward scales.
 */
export function getTopRole(
  participant,
  { builderStats = {}, validatorStats = {}, communityStats = {} } = {},
) {
  const statsByRole = {
    builder: builderStats,
    validator: validatorStats,
    community: communityStats,
  };

  const activeRoles = ROLE_ORDER.filter((role) => role.isActive(participant));

  const contributionScores = activeRoles.map((role) => ({
    ...role,
    label: getRoleLabel(role, participant),
    score: toNumber(statsByRole[role.key]?.totalContributions),
  }));

  const bestContributionScore = Math.max(
    0,
    ...contributionScores.map((role) => role.score),
  );

  if (bestContributionScore > 0) {
    const winners = contributionScores.filter(
      (role) => role.score === bestContributionScore,
    );

    if (winners.length > 1) {
      return {
        label: "Balanced",
        category: "genlayer",
        badges: winners.map((role) => toRoleBadge(role, participant)),
      };
    }

    return {
      label: winners[0].label,
      category: winners[0].category,
      badges: [toRoleBadge(winners[0], participant)],
    };
  }

  const pointScores = activeRoles.map((role) => ({
    ...role,
    label: getRoleLabel(role, participant),
    score: toNumber(statsByRole[role.key]?.totalPoints),
  }));

  const bestPointScore = Math.max(0, ...pointScores.map((role) => role.score));

  if (bestPointScore > 0) {
    const winners = pointScores.filter((role) => role.score === bestPointScore);

    if (winners.length > 1) {
      return {
        label: "Balanced",
        category: "genlayer",
        badges: winners.map((role) => toRoleBadge(role, participant)),
      };
    }

    return {
      label: winners[0].label,
      category: winners[0].category,
      badges: [toRoleBadge(winners[0], participant)],
    };
  }

  if (activeRoles.length === 1) {
    return {
      label: getRoleLabel(activeRoles[0], participant),
      category: activeRoles[0].category,
      badges: [toRoleBadge(activeRoles[0], participant)],
    };
  }

  if (activeRoles.length > 1) {
    return {
      label: "Multi-role",
      category: "genlayer",
      badges: activeRoles.map((role) => toRoleBadge(role, participant)),
    };
  }

  if (participant?.steward || participant?.working_groups?.length > 0) {
    return {
      label: "Steward",
      category: "steward",
      badges: [
        {
          key: "steward",
          label: "Steward",
          category: "steward",
        },
      ],
    };
  }

  return {
    label: "Member",
    category: "genlayer",
    badges: [],
  };
}
