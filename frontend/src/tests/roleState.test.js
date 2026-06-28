import { describe, it, expect } from 'vitest';
import {
  roleFunnelState,
  rolePath,
  journeyPath,
  roleForCategory,
  hasAnyRoleOrJourney,
} from '../lib/roleState.js';

describe('roleState.roleFunnelState', () => {
  it('is unauthenticated regardless of user', () => {
    expect(roleFunnelState(false, null, 'builder')).toBe('unauthenticated');
    expect(roleFunnelState(false, { builder: {} }, 'builder')).toBe('unauthenticated');
  });

  it('is earned when the role profile is present', () => {
    expect(roleFunnelState(true, { builder: {} }, 'builder')).toBe('earned');
    expect(roleFunnelState(true, { validator: {} }, 'validator')).toBe('earned');
    expect(roleFunnelState(true, { creator: {} }, 'community')).toBe('earned');
  });

  it('is started when the journey marker is set but role not earned', () => {
    expect(roleFunnelState(true, { has_builder_welcome: true }, 'builder')).toBe('started');
    expect(roleFunnelState(true, { has_validator_welcome: true }, 'validator')).toBe('started');
    expect(roleFunnelState(true, { has_validator_waitlist: true }, 'validator')).toBe('started');
    expect(roleFunnelState(true, { has_community_welcome: true }, 'community')).toBe('started');
    expect(roleFunnelState(true, { has_community_link_discord: true }, 'community')).toBe('started');
  });

  it('does not treat a GitHub link alone as a started builder journey', () => {
    expect(roleFunnelState(true, { github_connection: {} }, 'builder')).toBe('none');
  });

  it('is none when authenticated with no role and no progress', () => {
    expect(roleFunnelState(true, {}, 'builder')).toBe('none');
    expect(roleFunnelState(true, { name: 'x' }, 'community')).toBe('none');
  });

  it('treats earned as higher priority than a started signal', () => {
    expect(roleFunnelState(true, { builder: {}, github_connection: {} }, 'builder')).toBe('earned');
  });
});

describe('roleState path helpers', () => {
  it('maps roles to their main and journey routes', () => {
    expect(rolePath('builder')).toBe('/builders');
    expect(rolePath('validator')).toBe('/validators');
    expect(rolePath('community')).toBe('/community');
    expect(journeyPath('builder')).toBe('/builders/journey');
    expect(journeyPath('community')).toBe('/community/journey');
  });

  it('maps non-role categories to community for onboarding preselect', () => {
    expect(roleForCategory('builder')).toBe('builder');
    expect(roleForCategory('validator')).toBe('validator');
    expect(roleForCategory('community')).toBe('community');
    expect(roleForCategory('global')).toBe('community');
    expect(roleForCategory('steward')).toBe('community');
  });
});

describe('hasAnyRoleOrJourney (gates first-run UI away from new accounts)', () => {
  it('is false for a brand-new / not-yet-engaged account', () => {
    expect(hasAnyRoleOrJourney(null)).toBe(false);
    expect(hasAnyRoleOrJourney({})).toBe(false);
    expect(hasAnyRoleOrJourney({ name: 'x', email: 'a@b.com' })).toBe(false);
    expect(hasAnyRoleOrJourney({ github_connection: {} })).toBe(false);
  });

  it('is true once a role is earned or a journey started', () => {
    expect(hasAnyRoleOrJourney({ builder: {} })).toBe(true);
    expect(hasAnyRoleOrJourney({ has_builder_welcome: true })).toBe(true);
    expect(hasAnyRoleOrJourney({ has_validator_waitlist: true })).toBe(true);
    expect(hasAnyRoleOrJourney({ has_validator_welcome: true })).toBe(true);
    expect(hasAnyRoleOrJourney({ has_community_welcome: true })).toBe(true);
    expect(hasAnyRoleOrJourney({ creator: {} })).toBe(true);
    expect(hasAnyRoleOrJourney({ has_community_link_discord: true })).toBe(true);
    expect(hasAnyRoleOrJourney({ steward: {} })).toBe(true);
    expect(hasAnyRoleOrJourney({ working_groups: [{ id: 1 }] })).toBe(true);
  });
});
