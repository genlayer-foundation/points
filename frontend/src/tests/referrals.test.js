import { describe, expect, it } from 'vitest';
import {
  buildReferralLink,
  normalizeReferralCode,
  referralCodeFromSources,
} from '../lib/referrals.js';

describe('referral helpers', () => {
  it('normalizes valid referral codes', () => {
    expect(normalizeReferralCode(' ab12cd34 ')).toBe('AB12CD34');
  });

  it('rejects missing or malformed referral codes', () => {
    expect(normalizeReferralCode('')).toBe('');
    expect(normalizeReferralCode('ABC')).toBe('');
    expect(normalizeReferralCode('ABCDEF!@')).toBe('');
  });

  it('builds a complete referral link only when a valid code exists', () => {
    expect(buildReferralLink('ab12cd34')).toBe('https://portal.genlayer.foundation/?ref=AB12CD34');
    expect(buildReferralLink('')).toBe('');
  });

  it('uses the first valid code from available user sources', () => {
    expect(referralCodeFromSources(
      { referral_code: '' },
      { referral_code: 'xy98za76' },
    )).toBe('XY98ZA76');
  });
});
