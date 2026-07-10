export function isMissionEnded(mission) {
  return !!mission?.end_date && new Date(mission.end_date).getTime() <= Date.now();
}

export function compareMissions(a, b) {
  const aEnded = isMissionEnded(a);
  const bEnded = isMissionEnded(b);
  if (aEnded !== bEnded) return aEnded ? 1 : -1;

  const aEnd = a.end_date ? new Date(a.end_date).getTime() : 0;
  const bEnd = b.end_date ? new Date(b.end_date).getTime() : 0;
  return bEnd - aEnd;
}
