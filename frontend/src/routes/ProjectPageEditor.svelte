<script>
  // @ts-nocheck
  import { push } from 'svelte-spa-router';
  import { contributionsAPI, projectsAPI, usersAPI } from '../lib/api.js';
  import { isHiddenWelcomeContribution } from '../lib/hiddenContributions.js';
  import {
    getMarkdownTextLength,
    validateProjectMarkdownMedia,
  } from '../lib/projectPageTemplate.js';

  /** @type {{ params?: { slug?: string } }} */
  let { params = {} } = $props();

  /** @type {any} */
  let project = $state(null);
  let loading = $state(true);
  let saving = $state(false);
  /** @type {string | null} */
  let error = $state(null);
  /** @type {string | null} */
  let notice = $state(null);
  let lastRequestedSlug = '';

  let profileForm = $state({
    description: '',
    details: '',
    url: '',
    github_url: '',
    x_url: '',
    telegram_url: '',
    discord_url: '',
    demo_url: '',
    hero_image_url: '',
    hero_image_url_tablet: '',
    hero_image_url_mobile: '',
    user_profile_image_url: '',
  });
  let selectedParticipants = $state([]);
  let participantSearch = $state('');
  let participantResults = $state([]);
  let participantSearching = $state(false);
  let participantSearchError = $state('');
  let selectedContributions = $state([]);
  let contributionOptions = $state([]);
  let contributionSearch = $state('');
  let contributionPickerOpen = $state(false);
  let contributionsLoading = $state(false);
  let contributionsError = $state('');
  let contributionLoadKey = '';
  let imageUrlEditors = $state({});
  let imageUploading = $state({});
  let imageUploadErrors = $state({});
  let imagePreviewUrls = $state({});

  let fieldIssues = $derived(getFieldIssues());
  let filteredContributionOptions = $derived(getFilteredContributionOptions());
  let canSubmit = $derived(!saving && fieldIssues.length === 0);

  const linkFields = [
    { key: 'url', type: 'website', label: 'Website', prefix: 'https://', placeholder: 'example.com' },
    { key: 'demo_url', type: 'demo', label: 'Demo video', prefix: 'https://', placeholder: 'youtube.com/watch?v=...' },
    { key: 'x_url', type: 'x', label: 'X', prefix: 'x.com/', placeholder: 'X handle, e.g. genlayer' },
    { key: 'telegram_url', type: 'telegram', label: 'Telegram', prefix: 't.me/', placeholder: 'Group/channel name, e.g. genlayer' },
    { key: 'discord_url', type: 'discord', label: 'Discord', prefix: 'discord.gg/', placeholder: 'Invite code, e.g. abc123' },
    { key: 'github_url', type: 'github', label: 'GitHub', prefix: 'github.com/', placeholder: 'Org/repo, e.g. genlayer/project' },
  ];

  const imageFields = [
    { key: 'user_profile_image_url', type: 'logo', label: 'Logo', dimensions: '512 x 512 px', previewClass: 'rounded-full', placeholder: 'https://...' },
    { key: 'hero_image_url', type: 'desktop', label: 'Desktop banner', dimensions: '1600 x 520 px · 40:13', previewClass: 'rounded-[7px]', placeholder: 'https://...' },
    { key: 'hero_image_url_tablet', type: 'tablet', label: 'iPad banner', dimensions: '1200 x 560 px · 15:7', previewClass: 'rounded-[7px]', placeholder: 'https://...' },
    { key: 'hero_image_url_mobile', type: 'mobile', label: 'Mobile banner', dimensions: '900 x 1200 px · 3:4', previewClass: 'rounded-[7px]', placeholder: 'https://...' },
  ];

  $effect(() => {
    const slug = params.slug;
    if (slug && slug !== lastRequestedSlug) {
      lastRequestedSlug = slug;
      loadEditor(slug);
    }
  });

  $effect(() => {
    const query = participantSearch.trim();
    participantSearchError = '';
    if (query.length < 2) {
      participantResults = [];
      participantSearching = false;
      return;
    }

    participantSearching = true;
    const timeout = setTimeout(async () => {
      try {
        const response = await usersAPI.searchUsers(query);
        const data = response.data?.results || response.data || [];
        participantResults = data.filter((user) => !hasMatchingParticipant(selectedParticipants, user)).slice(0, 8);
      } catch (err) {
        participantResults = [];
        participantSearchError = 'Could not search users right now.';
      } finally {
        participantSearching = false;
      }
    }, 220);

    return () => clearTimeout(timeout);
  });

  $effect(() => {
    const key = selectedParticipants.map((user) => getParticipantKeys(user).join(',')).filter(Boolean).join('|');
    if (key === contributionLoadKey) return;
    contributionLoadKey = key;
    loadParticipantContributions();
  });

  /** @param {string} slug */
  async function loadEditor(slug) {
    try {
      loading = true;
      error = null;
      notice = null;
      const projectResponse = await projectsAPI.get(slug);
      const loadedProject = projectResponse.data;
      if (!loadedProject?.can_edit) {
        project = null;
        error = 'You do not have permission to edit this project.';
        return;
      }
      project = loadedProject;
      selectedParticipants = getProjectParticipantsForEditing(project);
      selectedContributions = [...(project.related_contributions || [])];
      hydrateForm(loadedProject);
    } catch (err) {
      const requestError = /** @type {{ response?: { data?: { detail?: string } }, message?: string }} */ (err);
      error = requestError.response?.data?.detail || requestError.message || 'Failed to load project editor';
    } finally {
      loading = false;
    }
  }

  function hydrateForm(projectData) {
    const nextProfileForm = {
      description: projectData.description || '',
      details: projectData.details || '',
      url: projectData.url || '',
      github_url: projectData.github_url || '',
      x_url: projectData.x_url || '',
      telegram_url: projectData.telegram_url || '',
      discord_url: projectData.discord_url || '',
      demo_url: projectData.demo_url || '',
      hero_image_url: projectData.hero_image_url || '',
      hero_image_url_tablet: projectData.hero_image_url_tablet || '',
      hero_image_url_mobile: projectData.hero_image_url_mobile || '',
      user_profile_image_url: projectData.user_profile_image_url || projectData.featured_profile_image_url || '',
    };
    profileForm = nextProfileForm;
  }

  function getFieldIssues() {
    const issues = [];
    if (!profileForm.details.trim()) issues.push('About is required.');
    const aboutTextLength = getMarkdownTextLength(profileForm.details);
    if (profileForm.details.trim() && aboutTextLength < 120) issues.push('About must include at least 120 text characters.');
    for (const [label, value] of [
      ['Website URL', profileForm.url],
      ['GitHub URL', profileForm.github_url],
      ['X URL', profileForm.x_url],
      ['Telegram URL', profileForm.telegram_url],
      ['Discord URL', profileForm.discord_url],
      ['Demo video URL', profileForm.demo_url],
      ['Desktop banner image URL', profileForm.hero_image_url],
      ['iPad banner image URL', profileForm.hero_image_url_tablet],
      ['Mobile banner image URL', profileForm.hero_image_url_mobile],
      ['Logo image URL', profileForm.user_profile_image_url],
    ]) {
      if (value.trim() && !isHttpUrl(value)) {
        issues.push(`${label} must start with http:// or https://.`);
      }
    }
    if (profileForm.description.length > 100) issues.push('One-liner must be 100 characters or fewer.');
    if (aboutTextLength > 1000) issues.push('About must be 1000 text characters or fewer.');
    if (profileForm.details.length > 4000) issues.push('About media markup is too long.');
    issues.push(...validateProjectMarkdownMedia(profileForm.details, 'About'));
    return issues;
  }

  async function loadParticipantContributions() {
    const participantsWithAddress = selectedParticipants.filter(getParticipantAddress);
    selectedContributions = selectedContributions.filter((contribution) => {
      const user = getContributionUser(contribution);
      return hasMatchingParticipant(selectedParticipants, user);
    });

    if (!participantsWithAddress.length) {
      contributionOptions = [];
      contributionSearch = '';
      contributionPickerOpen = false;
      contributionsLoading = false;
      contributionsError = '';
      return;
    }

    try {
      contributionsLoading = true;
      contributionsError = '';
      const responses = await Promise.all(
        participantsWithAddress.map((user) =>
          contributionsAPI.getContributions({
            user_address: getParticipantAddress(user),
            page_size: 50,
            ordering: '-frozen_global_points',
            exclude_onboarding: 'true',
          })
        )
      );
      const seen = new Set();
      contributionOptions = responses
        .flatMap((response) => response.data?.results || response.data || [])
        .filter((contribution) => {
          if (!contribution?.id || seen.has(contribution.id) || isHiddenWelcomeContribution(contribution)) return false;
          seen.add(contribution.id);
          return true;
        })
        .sort((a, b) => getPoints(b) - getPoints(a));
    } catch (err) {
      contributionOptions = [];
      contributionsError = 'Could not load contributions for the selected participants.';
    } finally {
      contributionsLoading = false;
    }
  }

  async function saveChanges() {
    if (!canSubmit) {
      error = 'Complete the required fields and fix URL formatting before saving.';
      return;
    }
    if (!params.slug) return;

    try {
      saving = true;
      error = null;
      notice = null;

      const profileResponse = await projectsAPI.updateProfile(params.slug, {
        description: profileForm.description.trim(),
        details: profileForm.details.trim(),
        url: profileForm.url.trim(),
        github_url: profileForm.github_url.trim(),
        x_url: profileForm.x_url.trim(),
        telegram_url: profileForm.telegram_url.trim(),
        discord_url: profileForm.discord_url.trim(),
        demo_url: profileForm.demo_url.trim(),
        hero_image_url: profileForm.hero_image_url.trim(),
        hero_image_url_tablet: profileForm.hero_image_url_tablet.trim(),
        hero_image_url_mobile: profileForm.hero_image_url_mobile.trim(),
        user_profile_image_url: profileForm.user_profile_image_url.trim(),
        participant_ids: getSelectedParticipantIds(),
        related_contribution_ids: selectedContributions.map((contribution) => contribution.id).filter(Boolean),
      });
      project = profileResponse.data;
      selectedContributions = [...(project.related_contributions || selectedContributions)];
      notice = 'Changes saved.';
    } catch (err) {
      const requestError = /** @type {{ response?: { data?: any }, message?: string }} */ (err);
      const data = requestError.response?.data;
      error = data?.detail || firstFieldError(data) || requestError.message || 'Failed to save project page';
    } finally {
      saving = false;
    }
  }

  function resetToProjectDefaults() {
    if (!project) return;
    profileForm = {
      description: project.description || '',
      details: project.details || '',
      url: project.url || '',
      github_url: project.github_url || '',
      x_url: project.x_url || '',
      telegram_url: project.telegram_url || '',
      discord_url: project.discord_url || '',
      demo_url: project.demo_url || '',
      hero_image_url: project.hero_image_url || '',
      hero_image_url_tablet: project.hero_image_url_tablet || '',
      hero_image_url_mobile: project.hero_image_url_mobile || '',
      user_profile_image_url: project.user_profile_image_url || project.featured_profile_image_url || '',
    };
    selectedParticipants = getProjectParticipantsForEditing(project);
    selectedContributions = [...(project.related_contributions || [])];
    participantSearch = '';
    contributionSearch = '';
    contributionPickerOpen = false;
  }

  /** @param {any} user */
  function addParticipant(user) {
    if (!getParticipantId(user) || hasMatchingParticipant(selectedParticipants, user)) return;
    selectedParticipants = [...selectedParticipants, user];
    participantSearch = '';
    participantResults = [];
  }

  /** @param {any} participantToRemove */
  function removeParticipant(participantToRemove) {
    const removed = selectedParticipants.find((user) => isSameParticipant(user, participantToRemove));
    selectedParticipants = selectedParticipants.filter((user) => !isSameParticipant(user, participantToRemove));
    if (removed) {
      selectedContributions = selectedContributions.filter((contribution) => {
        const user = getContributionUser(contribution);
        return !isSameParticipant(user, removed);
      });
    }
  }

  function selectContribution(contribution) {
    if (!contribution?.id || isContributionSelected(contribution)) return;
    selectedContributions = [...selectedContributions, contribution].sort((a, b) => getPoints(b) - getPoints(a));
    contributionSearch = '';
    contributionPickerOpen = false;
  }

  function removeContribution(contributionId) {
    selectedContributions = selectedContributions.filter((item) => item.id !== contributionId);
  }

  function getFilteredContributionOptions() {
    const selectedIds = new Set(selectedContributions.map((contribution) => contribution.id));
    const query = contributionSearch.trim().toLowerCase();
    return contributionOptions
      .filter((contribution) => !selectedIds.has(contribution.id))
      .filter((contribution) => {
        if (!query) return true;
        const haystack = [
          getContributionTitle(contribution),
          getContributionTypeName(contribution),
          getParticipantName(getContributionUser(contribution)),
        ].join(' ').toLowerCase();
        return haystack.includes(query);
      })
      .slice(0, 8);
  }

  function getProjectParticipantsForEditing(projectData) {
    const seen = new Set();
    const people = [];
    for (const participant of [
      getProjectOwner(projectData),
      ...(projectData?.participants || []),
      ...(projectData?.related_contributions || []).map(getContributionUser),
    ]) {
      const keys = getParticipantKeys(participant);
      if (!keys.length) continue;
      if (keys.some((key) => seen.has(key))) {
        keys.forEach((key) => seen.add(key));
        continue;
      }
      keys.forEach((key) => seen.add(key));
      people.push(participant);
    }
    return people;
  }

  function getProjectOwner(projectData) {
    if (!projectData?.user && !projectData?.user_name && !projectData?.user_address) return null;
    return {
      id: projectData.user,
      name: projectData.user_name || projectData.author || '',
      address: projectData.user_address || '',
      profile_image_url: projectData.owner_profile_image_url || projectData.user_profile_image_url || '',
    };
  }

  function updateProfileField(key, value) {
    profileForm = { ...profileForm, [key]: value };
  }

  function toggleImageUrlEditor(key) {
    imageUrlEditors = { ...imageUrlEditors, [key]: !imageUrlEditors[key] };
  }

  function getImagePreviewUrl(field) {
    return imagePreviewUrls[field.key] || profileForm[field.key] || '';
  }

  function updateImageUrlField(key, value) {
    imagePreviewUrls = { ...imagePreviewUrls, [key]: '' };
    updateProfileField(key, value);
  }

  async function uploadProjectImage(event, field) {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (!file || !params.slug) return;

    if (!file.type?.startsWith('image/')) {
      imageUploadErrors = { ...imageUploadErrors, [field.key]: 'Only image files are supported.' };
      return;
    }

    if (typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function') {
      imagePreviewUrls = { ...imagePreviewUrls, [field.key]: URL.createObjectURL(file) };
    }

    const formData = new FormData();
    formData.append('image', file);
    formData.append('image_type', field.type);

    try {
      imageUploading = { ...imageUploading, [field.key]: true };
      imageUploadErrors = { ...imageUploadErrors, [field.key]: '' };
      const response = await projectsAPI.uploadImage(params.slug, formData);
      const uploadedUrl = response.data?.url || '';
      updateProfileField(field.key, uploadedUrl);
      imagePreviewUrls = { ...imagePreviewUrls, [field.key]: uploadedUrl };
      notice = `${field.label} uploaded.`;
    } catch (err) {
      imageUploadErrors = {
        ...imageUploadErrors,
        [field.key]: err.response?.data?.error || `Could not upload ${field.label.toLowerCase()}.`,
      };
    } finally {
      imageUploading = { ...imageUploading, [field.key]: false };
    }
  }

  function updateLinkFieldFromInput(key, type, value) {
    const input = String(value || '').trim();
    updateProfileField(key, input ? normalizeLinkValue(input, type) : '');
  }

  function getLinkEditorValue(key, type) {
    const value = String(profileForm[key] || '').trim();
    if (!value) return '';
    const withoutProtocol = value.replace(/^https?:\/\//i, '');
    if (type === 'website' || type === 'demo') return withoutProtocol;
    return stripKnownSocialHost(withoutProtocol, type).replace(/^@+/, '').replace(/^\/+/, '');
  }

  function normalizeLinkField(key, type) {
    const value = String(profileForm[key] || '').trim();
    if (!value) {
      updateProfileField(key, '');
      return;
    }
    updateProfileField(key, normalizeLinkValue(value, type));
  }

  function normalizeLinkValue(value, type) {
    const raw = value.trim();
    if (/^https?:\/\//i.test(raw)) return raw;
    if (type === 'website' || type === 'demo') return `https://${raw.replace(/^\/+/, '')}`;

    const withoutProtocol = raw.replace(/^https?:\/\//i, '');
    const hostless = stripKnownSocialHost(withoutProtocol, type).replace(/^@+/, '').replace(/^\/+/, '');
    if (type === 'x') return `https://x.com/${hostless}`;
    if (type === 'telegram') return `https://t.me/${hostless}`;
    if (type === 'discord') return `https://discord.gg/${hostless.replace(/^invite\//i, '')}`;
    if (type === 'github') return `https://github.com/${hostless}`;
    return raw;
  }

  function stripKnownSocialHost(value, type) {
    const normalized = value.replace(/^www\./i, '');
    const hostPatterns = {
      x: /^(x\.com|twitter\.com)\//i,
      telegram: /^(t\.me|telegram\.me)\//i,
      discord: /^(discord\.gg|discord\.com\/invite)\//i,
      github: /^github\.com\//i,
    };
    return normalized.replace(hostPatterns[type] || /^$/, '');
  }

  function isContributionSelected(contribution) {
    return selectedContributions.some((item) => item.id === contribution.id);
  }

  function getParticipantName(user) {
    if (user?.name || user?.user_name) return user.name || user.user_name;
    const address = getParticipantAddress(user);
    if (address) return `${address.slice(0, 6)}...${address.slice(-4)}`;
    return 'Portal user';
  }

  function getContributionUser(contribution) {
    return contribution?.user_details || contribution?.user || {};
  }

  function getParticipantId(user) {
    if (typeof user === 'number') return user;
    if (typeof user === 'string' && /^\d+$/.test(user)) return Number(user);
    const id = user?.id ?? user?.user_id;
    if (typeof id === 'number') return id;
    if (typeof id === 'string' && /^\d+$/.test(id)) return Number(id);
    return null;
  }

  function getParticipantAddress(user) {
    return String(user?.address || user?.user_address || '').trim();
  }

  function getParticipantKeys(user) {
    if (!user && user !== 0) return [];
    const keys = [];
    const id = getParticipantId(user);
    if (id) keys.push(`id:${id}`);

    const address = getParticipantAddress(user).toLowerCase();
    if (address) keys.push(`address:${address}`);

    if (!keys.length) {
      const fallback = typeof user === 'string' || typeof user === 'number' ? user : user?.name || user?.user_name;
      const name = normalizeTitle(fallback);
      if (name) keys.push(`name:${name}`);
    }
    return keys;
  }

  function isSameParticipant(left, right) {
    const leftKeys = new Set(getParticipantKeys(left));
    return getParticipantKeys(right).some((key) => leftKeys.has(key));
  }

  function hasMatchingParticipant(participants, user) {
    return participants.some((participant) => isSameParticipant(participant, user));
  }

  function getSelectedParticipantIds() {
    const seen = new Set();
    return selectedParticipants
      .map(getParticipantId)
      .filter((id) => {
        if (!id || seen.has(id)) return false;
        seen.add(id);
        return true;
      });
  }

  function getContributionTitle(contribution) {
    return contribution.title || contribution.mission?.name || contribution.contribution_type_name || contribution.contribution_type?.name || 'Contribution';
  }

  function getContributionTypeName(contribution) {
    return contribution.contribution_type_name || contribution.contribution_type_details?.name || contribution.contribution_type?.name || 'Contribution';
  }

  function getPoints(contribution) {
    return Number(contribution.frozen_global_points ?? contribution.points ?? 0);
  }

  function formatDate(value) {
    if (!value) return '';
    try {
      return new Date(value).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return value;
    }
  }

  function isHttpUrl(value) {
    try {
      const url = new URL(value);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  }

  function normalizeTitle(value) {
    return String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
  }

  function firstFieldError(data) {
    if (!data || typeof data !== 'object') return '';
    const first = Object.values(data)[0];
    return Array.isArray(first) ? first[0] : '';
  }
</script>

<div class="relative -mx-3 -my-3 min-h-full overflow-hidden bg-[#f6f7f9] px-3 py-6 sm:px-5 sm:py-8 md:px-8">
  <div
    class="pointer-events-none absolute inset-x-0 top-0 h-[360px] overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_16%_10%,rgba(238,133,33,0.42),transparent_32%),linear-gradient(180deg,#fff1df_0%,rgba(255,248,239,0.72)_48%,rgba(246,247,249,0)_100%)]"></div>
  </div>

  <div class="relative mx-auto max-w-[1040px]">
    {#if loading}
      <div class="min-h-[70vh] rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.12)] sk-shimmer"></div>
    {:else if error && !project}
      <div class="rounded-[10px] border border-rose-200 bg-rose-50 p-6 text-rose-700">
        <p class="text-sm font-semibold">Project editor unavailable</p>
        <p class="mt-1 text-sm">{error}</p>
      </div>
    {:else if project}
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div class="min-w-0">
          <button
            type="button"
            onclick={() => window.history.length > 1 ? window.history.back() : push(`/builders/projects/${project.slug}`)}
            class="inline-flex min-h-11 items-center gap-2 text-[13px] font-semibold text-[#667085] transition hover:text-black"
          >
            <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="h-4 w-4" />
            Back
          </button>
          <h1 class="mt-1 text-[30px] font-semibold leading-tight text-black">Edit project profile</h1>
        </div>

        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            onclick={resetToProjectDefaults}
            disabled={saving}
            class="h-10 rounded-[7px] border border-[#dfe3eb] bg-white px-4 text-[14px] font-semibold text-black transition hover:border-[#f1bd82] disabled:opacity-50"
          >
            Reset fields
          </button>
          <button
            type="button"
            onclick={saveChanges}
            disabled={!canSubmit}
            class="h-10 rounded-[7px] bg-[#ee8521] px-4 text-[14px] font-semibold text-white transition hover:bg-[#d87519] disabled:cursor-not-allowed disabled:bg-[#d7dce5]"
          >
            Save changes
          </button>
        </div>
      </div>

      {#if notice}
        <div class="mb-4 rounded-[8px] border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>
      {/if}
      {#if error}
        <div class="mb-4 rounded-[8px] border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
      {/if}

      <section class="rounded-[10px] border border-white/70 bg-white/88 shadow-[0_18px_55px_rgba(38,48,75,0.12)] backdrop-blur-md">
        <div class="border-b border-[#edf0f5] p-4 sm:p-5">
          <div class="mb-3 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 class="text-[18px] font-semibold text-black">Project images</h2>
              <p class="mt-1 text-[13px] leading-5 text-[#667085]">Upload Cloudinary assets or use a hosted URL fallback.</p>
            </div>
          </div>

          <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {#each imageFields as field}
              <div class="rounded-[8px] border border-[#edf0f5] bg-[#fbfcfe] p-3">
                <div class="mb-2 flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-[13px] font-semibold text-black">{field.label}</p>
                    <p class="mt-0.5 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#98a2b3]">{field.dimensions}</p>
                  </div>
                  {#if imageUploading[field.key]}
                    <span class="shrink-0 rounded-full bg-[#fff2e2] px-2 py-1 text-[10px] font-semibold uppercase text-[#ee8521]">Uploading</span>
                  {/if}
                </div>

                <div class="flex items-center gap-3">
                  <div class="flex h-14 w-16 shrink-0 items-center justify-center overflow-hidden border border-[#edf0f5] bg-white text-[10px] font-semibold uppercase text-[#98a2b3] {field.previewClass}">
                    {#if getImagePreviewUrl(field)}
                      <img src={getImagePreviewUrl(field)} alt={`${field.label} preview`} class="h-full w-full object-cover" />
                    {:else}
                      Empty
                    {/if}
                  </div>

                  <div class="min-w-0 flex-1">
                    <input
                      id={`project-upload-${field.key}`}
                      type="file"
                      accept="image/*"
                      aria-label={`${field.label} upload`}
                      class="sr-only"
                      onchange={(event) => uploadProjectImage(event, field)}
                    />
                    <div class="flex gap-2">
                      <label
                        for={`project-upload-${field.key}`}
                        class="inline-flex h-8 cursor-pointer items-center justify-center rounded-[7px] bg-[#111827] px-3 text-[12px] font-semibold text-white transition hover:bg-black"
                      >
                        Upload
                      </label>
                      <button
                        type="button"
                        onclick={() => toggleImageUrlEditor(field.key)}
                        class="h-8 rounded-[7px] border border-[#dfe3eb] bg-white px-3 text-[12px] font-semibold text-black transition hover:border-[#f1bd82]"
                      >
                        URL
                      </button>
                    </div>
                    {#if imageUploadErrors[field.key]}
                      <p class="mt-1 text-[11px] leading-4 text-rose-700">{imageUploadErrors[field.key]}</p>
                    {/if}
                  </div>
                </div>

                {#if imageUrlEditors[field.key]}
                  <div class="mt-3">
                    <label for={`project-${field.key}`} class="sr-only">{field.label} URL</label>
                    <input
                      id={`project-${field.key}`}
                      value={profileForm[field.key]}
                      oninput={(event) => updateImageUrlField(field.key, event.currentTarget.value)}
                      type="url"
                      class="h-9 w-full rounded-[7px] border border-[#dfe3eb] bg-white px-2 text-[12px] text-black outline-none transition placeholder:text-[#98a2b3] focus:border-[#ee8521] focus:ring-3 focus:ring-[#ee8521]/10"
                      placeholder={field.placeholder}
                    />
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>

        <div class="space-y-4 p-4 sm:p-5">
          <div class="grid gap-4 lg:grid-cols-[minmax(0,0.55fr)_minmax(0,1.45fr)]">
            <div class="space-y-1.5">
              <div class="flex items-center justify-between gap-3">
                <label for="project-description" class="text-[13px] font-semibold text-black">One-liner</label>
                <span class="text-[11px] font-semibold text-[#98a2b3]">{profileForm.description.length}/100</span>
              </div>
              <textarea
                id="project-description"
                bind:value={profileForm.description}
                rows="2"
                maxlength="100"
                class="h-[76px] w-full resize-none rounded-[8px] border border-[#dfe3eb] bg-white px-3 py-2.5 text-[14px] leading-5 text-black outline-none transition placeholder:text-[#98a2b3] focus:border-[#ee8521] focus:ring-4 focus:ring-[#ee8521]/10"
                placeholder="Short summary shown under the project title."
              ></textarea>
            </div>

            <div class="space-y-1.5">
              <div class="flex items-center justify-between gap-3">
                <label for="project-about" class="text-[13px] font-semibold text-black">About</label>
                <span class="text-[12px] font-semibold {getMarkdownTextLength(profileForm.details) >= 120 && getMarkdownTextLength(profileForm.details) <= 1000 ? 'text-emerald-700' : 'text-amber-700'}">{getMarkdownTextLength(profileForm.details)}/1000 text · min 120</span>
              </div>
              <textarea
                id="project-about"
                bind:value={profileForm.details}
                rows="4"
                class="h-[132px] w-full resize-y rounded-[8px] border border-[#dfe3eb] bg-white px-3 py-2.5 text-[14px] leading-6 text-black outline-none transition placeholder:text-[#98a2b3] focus:border-[#ee8521] focus:ring-4 focus:ring-[#ee8521]/10"
                placeholder={`What the project does, who it is for, and why it matters.\n\n<Image src="https://..." caption="Optional caption" />\n\n<Video url="https://..." title="Optional title" />`}
              ></textarea>
            </div>
          </div>

          <div class="rounded-[8px] border border-[#edf0f5] bg-[#fbfcfe] p-3">
            <div class="mb-3 flex items-center justify-between gap-3">
              <h3 class="text-[14px] font-semibold text-black">Project links</h3>
              <p class="hidden text-[12px] text-[#667085] sm:block">Optional links appear on the banner when filled.</p>
            </div>
            <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {#each linkFields as field}
                <div class="space-y-1.5">
                  <label for={`project-${field.key}`} class="text-[12px] font-semibold text-black">{field.label}</label>
                  <div class="flex h-10 overflow-hidden rounded-[8px] border border-[#dfe3eb] bg-white transition focus-within:border-[#ee8521] focus-within:ring-4 focus:ring-[#ee8521]/10">
                    <span class="hidden shrink-0 items-center border-r border-[#edf0f5] bg-[#f7f8fb] px-2.5 text-[12px] font-semibold text-[#667085] sm:inline-flex">{field.prefix}</span>
                    <input
                      id={`project-${field.key}`}
                      value={getLinkEditorValue(field.key, field.type)}
                      oninput={(event) => updateLinkFieldFromInput(field.key, field.type, event.currentTarget.value)}
                      onblur={() => normalizeLinkField(field.key, field.type)}
                      type="text"
                      class="min-w-0 flex-1 border-0 bg-transparent px-3 text-[14px] text-black outline-none placeholder:text-[#98a2b3]"
                      placeholder={field.placeholder}
                    />
                  </div>
                </div>
              {/each}
            </div>
          </div>

          <div class="grid gap-4 lg:grid-cols-2">
            <div class="rounded-[8px] border border-[#edf0f5] bg-[#fbfcfe] p-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <h3 class="text-[14px] font-semibold text-black">Participants</h3>
                  <p class="mt-1 text-[12px] leading-5 text-[#667085]">Search Portal users connected to this project.</p>
                </div>
                <span class="rounded-full bg-white px-2.5 py-1 text-[12px] font-semibold text-[#667085] shadow-sm">{selectedParticipants.length}</span>
              </div>

              <div class="mt-4">
                <label for="participant-search" class="sr-only">Search participants</label>
                <input
                  id="participant-search"
                  bind:value={participantSearch}
                  type="search"
                  class="h-10 w-full rounded-[8px] border border-[#dfe3eb] bg-white px-3 text-[14px] text-black outline-none transition placeholder:text-[#98a2b3] focus:border-[#ee8521] focus:ring-4 focus:ring-[#ee8521]/10"
                  placeholder="Search participants by name or address"
                />
                {#if participantSearching}
                  <p class="mt-2 text-[12px] text-[#667085]">Searching users...</p>
                {:else if participantSearchError}
                  <p class="mt-2 text-[12px] text-rose-700">{participantSearchError}</p>
                {:else if participantResults.length}
                  <div class="mt-2 overflow-hidden rounded-[8px] border border-[#edf0f5] bg-white shadow-[0_14px_34px_rgba(38,48,75,0.12)]">
                    {#each participantResults as user}
                      <button
                        type="button"
                        onclick={() => addParticipant(user)}
                        class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition hover:bg-[#fff8ef]"
                      >
                        <span class="min-w-0">
                          <span class="block truncate text-[13px] font-semibold text-black">{getParticipantName(user)}</span>
                          <span class="block truncate text-[12px] text-[#667085]">{getParticipantAddress(user) || 'Portal user'}</span>
                        </span>
                        <span class="shrink-0 text-[12px] font-semibold text-[#ee8521]">Add</span>
                      </button>
                    {/each}
                  </div>
                {/if}
              </div>

              {#if selectedParticipants.length}
                <div class="mt-3 flex max-h-[88px] flex-wrap gap-2 overflow-y-auto pr-1">
                  {#each selectedParticipants as user}
                    <span class="inline-flex max-w-full items-center gap-2 rounded-full border border-[#f1bd82] bg-white px-2.5 py-1.5 text-[12px] font-semibold text-black">
                      <span class="max-w-[170px] truncate">{getParticipantName(user)}</span>
                      <button type="button" onclick={() => removeParticipant(user)} class="text-[#98a2b3] transition hover:text-rose-600" aria-label={`Remove ${getParticipantName(user)}`}>x</button>
                    </span>
                  {/each}
                </div>
              {:else}
                <p class="mt-3 rounded-[8px] border border-dashed border-[#dfe3eb] bg-white p-3 text-[12px] leading-5 text-[#667085]">No participants added yet.</p>
              {/if}
            </div>

            <div class="rounded-[8px] border border-[#edf0f5] bg-[#fbfcfe] p-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <h3 class="text-[14px] font-semibold text-black">Related submissions</h3>
                  <p class="mt-1 text-[12px] leading-5 text-[#667085]">Search accepted contributions from selected participants.</p>
                </div>
                <span class="rounded-full bg-white px-2.5 py-1 text-[12px] font-semibold text-[#667085] shadow-sm">{selectedContributions.length}</span>
              </div>

              {#if !selectedParticipants.length}
                <p class="mt-4 rounded-[8px] border border-dashed border-[#dfe3eb] bg-white p-3 text-[12px] leading-5 text-[#667085]">Add participants first to select their submissions.</p>
              {:else if contributionsLoading}
                <p class="mt-4 rounded-[8px] border border-[#edf0f5] bg-white p-3 text-[12px] leading-5 text-[#667085]">Loading participant submissions...</p>
              {:else if contributionsError}
                <p class="mt-4 rounded-[8px] border border-rose-200 bg-rose-50 p-3 text-[12px] leading-5 text-rose-700">{contributionsError}</p>
              {:else if contributionOptions.length}
                <div class="relative mt-4">
                  <label for="submission-search" class="sr-only">Search submissions</label>
                  <input
                    id="submission-search"
                    bind:value={contributionSearch}
                    onfocus={() => contributionPickerOpen = true}
                    type="search"
                    class="h-10 w-full rounded-[8px] border border-[#dfe3eb] bg-white px-3 text-[14px] text-black outline-none transition placeholder:text-[#98a2b3] focus:border-[#ee8521] focus:ring-4 focus:ring-[#ee8521]/10"
                    placeholder="Search submissions by title, type, or participant"
                  />

                  {#if contributionPickerOpen}
                    <div class="absolute left-0 right-0 top-[46px] z-20 max-h-[288px] overflow-y-auto rounded-[8px] border border-[#edf0f5] bg-white shadow-[0_18px_45px_rgba(38,48,75,0.16)]">
                      {#if filteredContributionOptions.length}
                        {#each filteredContributionOptions as contribution}
                          {@const contributionUser = getContributionUser(contribution)}
                          <button
                            type="button"
                            onclick={() => selectContribution(contribution)}
                            class="flex w-full items-start justify-between gap-3 px-3 py-2.5 text-left transition hover:bg-[#fff8ef]"
                          >
                            <span class="min-w-0">
                              <span class="line-clamp-1 text-[13px] font-semibold text-black">{getContributionTitle(contribution)}</span>
                              <span class="mt-0.5 block truncate text-[12px] text-[#667085]">{getParticipantName(contributionUser)} · {getContributionTypeName(contribution)} · {formatDate(contribution.contribution_date)}</span>
                            </span>
                            <span class="shrink-0 rounded-full bg-[#fff2e2] px-2 py-1 text-[12px] font-semibold text-[#ee8521]">{getPoints(contribution)} pts</span>
                          </button>
                        {/each}
                      {:else}
                        <p class="p-3 text-[12px] leading-5 text-[#667085]">No matching submissions.</p>
                      {/if}
                    </div>
                  {/if}
                </div>

                {#if selectedContributions.length}
                  <div class="mt-3 flex max-h-[88px] flex-wrap gap-2 overflow-y-auto pr-1">
                    {#each selectedContributions as contribution}
                      <span class="inline-flex max-w-full items-center gap-2 rounded-full border border-[#f1bd82] bg-white px-2.5 py-1.5 text-[12px] font-semibold text-black">
                        <span class="max-w-[260px] truncate">{getContributionTitle(contribution)}</span>
                        <button
                          type="button"
                          onclick={() => removeContribution(contribution.id)}
                          class="text-[#98a2b3] transition hover:text-rose-600"
                          aria-label={`Remove ${getContributionTitle(contribution)}`}
                        >
                          x
                        </button>
                      </span>
                    {/each}
                  </div>
                {:else}
                  <p class="mt-3 rounded-[8px] border border-dashed border-[#dfe3eb] bg-white p-3 text-[12px] leading-5 text-[#667085]">No submissions selected yet.</p>
                {/if}
              {:else}
                <p class="mt-4 rounded-[8px] border border-dashed border-[#dfe3eb] bg-white p-3 text-[12px] leading-5 text-[#667085]">No accepted submissions found for the selected participants.</p>
              {/if}
            </div>
          </div>

          {#if fieldIssues.length}
            <div class="rounded-[8px] border border-amber-200 bg-amber-50 p-3 text-[13px] leading-5 text-amber-800">
              {#each fieldIssues.slice(0, 5) as issue}
                <p>{issue}</p>
              {/each}
            </div>
          {/if}
        </div>
      </section>
    {/if}
  </div>
</div>
