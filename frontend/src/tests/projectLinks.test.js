import { describe, expect, it } from 'vitest';
import {
  getProjectLinkDisplayUrl,
  getProjectLinkType,
} from '../lib/projectLinks.js';

describe('project link display labels', () => {
  it('shows GitHub repository names when a repository URL is given', () => {
    const link = {
      type: getProjectLinkType('GitHub', 'https://github.com/example/cognocracy'),
      url: 'https://github.com/example/cognocracy',
    };

    expect(getProjectLinkDisplayUrl(link)).toBe('cognocracy');
  });

  it('shows GitHub usernames when only a profile URL is given', () => {
    const link = {
      type: getProjectLinkType('GitHub', 'https://github.com/example'),
      url: 'https://github.com/example',
    };

    expect(getProjectLinkDisplayUrl(link)).toBe('example');
  });

  it('does not throw on malformed GitHub percent escapes', () => {
    const link = {
      type: getProjectLinkType('GitHub', 'https://github.com/example/%zz'),
      url: 'https://github.com/example/%zz',
    };

    expect(getProjectLinkDisplayUrl(link)).toBe('%zz');
  });

  it('shows Discord server names instead of random invite codes', () => {
    const link = {
      type: getProjectLinkType('Discord', 'https://discord.gg/abc123'),
      url: 'https://discord.gg/abc123',
    };

    expect(getProjectLinkDisplayUrl(link, { title: 'Cognocracy' })).toBe('Cognocracy');
  });

  it('uses known Discord server names for existing project invites', () => {
    const link = {
      type: getProjectLinkType('Discord', 'https://discord.gg/frgXQfM3KZ'),
      url: 'https://discord.gg/frgXQfM3KZ',
    };

    expect(getProjectLinkDisplayUrl(link, { title: 'Different Project Name' })).toBe('Precog Markets');
  });
});
