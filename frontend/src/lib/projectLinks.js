const discordInviteLabels = new Map([
  ['8jm4v89vau', 'GenLayer Labs'],
  ['genlayerlabs', 'GenLayer Labs'],
  ['frgxqfm3kz', 'Precog Markets'],
  ['vfvghdbmgy', 'Rally'],
  ['84nb4q4h', 'FUD.markets'],
]);

export function parseProjectUrl(rawUrl) {
  if (!rawUrl) return null;
  try {
    return new URL(rawUrl);
  } catch {
    try {
      return new URL(`https://${rawUrl}`);
    } catch {
      return null;
    }
  }
}

export function getProjectLinkType(label, url) {
  const value = `${label || ''} ${url || ''}`.toLowerCase();
  if (value.includes('github.com') || value.includes('github')) return 'github';
  if (value.includes('x.com') || value.includes('twitter.com') || value.includes('twitter') || value.includes(' x')) return 'x';
  if (value.includes('t.me') || value.includes('telegram')) return 'telegram';
  if (value.includes('discord')) return 'discord';
  return 'website';
}

export function getProjectLinkLabel(link) {
  return {
    website: 'Website',
    x: 'X',
    telegram: 'Telegram',
    discord: 'Discord',
    github: 'GitHub',
  }[link?.type] || link?.label || 'Link';
}

export function getProjectLinkDisplayUrl(link, project = null) {
  const rawUrl = link?.url || '';
  if (!rawUrl) return '';

  const url = parseProjectUrl(rawUrl);
  if (url) {
    const host = url.hostname.replace(/^www\./, '');
    const pathParts = url.pathname.split('/').filter(Boolean);

    if (link.type === 'x' || host === 'twitter.com' || host === 'x.com') {
      const handle = pathParts[0] || '';
      return handle && !['i', 'intent', 'share'].includes(handle.toLowerCase()) ? `@${handle}` : host;
    }

    if (link.type === 'telegram' || host === 't.me' || host === 'telegram.me') {
      return pathParts[0] ? `@${pathParts[0]}` : host;
    }

    if (link.type === 'discord') {
      return getDiscordDisplayName(host, pathParts, project);
    }

    if (link.type === 'github') {
      return getGitHubDisplayName(host, pathParts);
    }

    return host;
  }

  return rawUrl.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '');
}

function getGitHubDisplayName(host, pathParts) {
  if (host !== 'github.com') return pathParts[0] || host;

  const owner = cleanGitHubPathPart(pathParts[0]);
  const repo = cleanGitHubPathPart(pathParts[1]);
  return repo || owner || host;
}

function cleanGitHubPathPart(value = '') {
  try {
    return decodeURIComponent(value).replace(/\.git$/i, '');
  } catch {
    return value.replace(/\.git$/i, '');
  }
}

function getDiscordDisplayName(host, pathParts, project) {
  const inviteCode = getDiscordInviteCode(host, pathParts);
  if (inviteCode) {
    const knownServerName = discordInviteLabels.get(inviteCode.toLowerCase());
    if (knownServerName) return knownServerName;

    const projectServerName = getProjectDiscordServerName(project);
    if (projectServerName) return projectServerName;
  }

  if (host.includes('discord.com') && pathParts[0] === 'channels') {
    return getProjectDiscordServerName(project) || 'Discord';
  }

  return getProjectDiscordServerName(project) || pathParts[0] || host;
}

function getDiscordInviteCode(host, pathParts) {
  if (host === 'discord.gg') return pathParts[0] || '';
  if (host.includes('discord.com') && pathParts[0] === 'invite') return pathParts[1] || '';
  return '';
}

function getProjectDiscordServerName(project) {
  return project?.discord_server_name || project?.discord_name || project?.title || '';
}
