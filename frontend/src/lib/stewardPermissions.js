import { writable, get } from 'svelte/store';
import { stewardAPI } from './api.js';

const permissions = writable({});

let loaded = false;

async function load() {
  try {
    const response = await stewardAPI.getMyPermissions();
    permissions.set(response.data || {});
    loaded = true;
  } catch (err) {
    permissions.set({});
  }
}

function hasPermission(contributionTypeId, action) {
  const perms = get(permissions);
  const actions = perms[String(contributionTypeId)] || [];
  return actions.includes(action);
}

function getActions(contributionTypeId) {
  const perms = get(permissions);
  return perms[String(contributionTypeId)] || [];
}

function isLoaded() {
  return loaded;
}

export const stewardPermissions = {
  subscribe: permissions.subscribe,
  load,
  hasPermission,
  getActions,
  isLoaded,
};
