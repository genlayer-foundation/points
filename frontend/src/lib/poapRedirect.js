export function clearPoapClaimRedirect(token) {
  if (typeof window === 'undefined' || !token) return;
  const redirectPath = sessionStorage.getItem('redirectAfterLogin');
  const claimPaths = new Set([
    `/claim/poap/${token}`,
    `/claim/poap/${encodeURIComponent(token)}`,
  ]);
  if (redirectPath && claimPaths.has(redirectPath)) {
    sessionStorage.removeItem('redirectAfterLogin');
  }
}
