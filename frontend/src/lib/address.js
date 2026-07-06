// Wallet-address display helpers.
//
// The API only returns truncated addresses (0x1234...abcd) for OTHER users;
// full addresses exist client-side only for the logged-in user's own wallet.
// truncateAddress is idempotent, so it is safe on already-truncated values.

export function truncateAddress(address) {
  if (!address) return '';
  const value = String(address);
  return value.length > 10 ? `${value.slice(0, 6)}...${value.slice(-4)}` : value;
}

export function isFullAddress(value) {
  return /^0x[0-9a-fA-F]{40}$/.test(String(value || '').trim());
}

// Preferred key for /participant/ links: user id when present, else whatever
// address form we have (a pasted full address still resolves server-side).
export function participantPath(user) {
  const key = user?.id ?? user?.address;
  return key != null && key !== '' ? `/participant/${key}` : null;
}
