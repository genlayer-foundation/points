export const REFERRAL_URL = 'https://portal.genlayer.foundation/';

export function normalizeReferralCode(value) {
  const code = String(value || '').trim().toUpperCase();
  return /^[A-Z0-9]{8}$/.test(code) ? code : '';
}

export function referralCodeFromSources(...sources) {
  for (const source of sources) {
    const code = normalizeReferralCode(source?.referral_code);
    if (code) return code;
  }
  return '';
}

export function buildReferralLink(code) {
  const normalizedCode = normalizeReferralCode(code);
  if (!normalizedCode) return '';

  const url = new URL(REFERRAL_URL);
  url.searchParams.set('ref', normalizedCode);
  return url.toString();
}
