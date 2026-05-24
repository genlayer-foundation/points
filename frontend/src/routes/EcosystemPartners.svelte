<script>
  import { onMount } from 'svelte';
  import { partnersAPI, validatorsAPI, projectsAPI } from '../lib/api.js';
  import PartnerCard from '../components/portal/partners/PartnerCard.svelte';

  const SECTIONS = [
    {
      id: 'project',
      title: 'Projects',
      description: "High-signal products built on GenLayer, from applications to infrastructure that can grow with intelligent contracts.",
      icon: '/assets/icons/terminal-fill-white.svg',
      iconClass: 'bg-orange-500',
      countClass: 'border-orange-200 bg-orange-50 text-orange-600',
      skeletonCount: 6,
    },
    {
      id: 'validator',
      title: 'Validators',
      description: 'Graduated validators contributing reliable network participation.',
      icon: '/assets/icons/shield-white.svg',
      iconClass: 'bg-gradient-to-br from-[#8f7bff] to-[#6f8cff]',
      countClass: 'border-[#d9d2ff] bg-[#f4f1ff] text-[#6f5ddb]',
      skeletonCount: 6,
    },
    {
      id: 'partner',
      title: 'Partners',
      description: 'Organizations supporting and expanding the GenLayer ecosystem.',
      icon: '/assets/icons/group-white.svg',
      iconClass: 'bg-black',
      countClass: 'border-blue-200 bg-blue-50 text-blue-700',
      skeletonCount: 18,
    },
  ];

  let items = $state([]);
  let loading = $state(true);

  let grouped = $derived({
    partner: items.filter((i) => i.category === 'partner'),
    validator: items.filter((i) => i.category === 'validator'),
    project: items.filter((i) => i.category === 'project'),
  });

  function normalizePartner(p) {
    return {
      id: `partner-${p.id || p.slug}`,
      slug: p.slug,
      name: p.name,
      logo_url: p.logo_url || '',
      href: p.website_url || p.url || '#',
      isExternal: true,
      category: 'partner',
    };
  }

  function normalizeValidator(user) {
    return {
      id: `validator-${user.address || user.id || user.name}`,
      name: user.name || 'Validator',
      logo_url: user.profile_image_url || '',
      href: user.address ? `#/participant/${user.address}` : '#',
      isExternal: false,
      category: 'validator',
    };
  }

  function normalizeProject(b) {
    const link = b.slug ? `#/builders/projects/${b.slug}` : (b.link || b.url || '');
    return {
      id: `project-${b.id || b.title}`,
      name: b.title || b.name || 'Project',
      logo_url: b.featured_profile_image_url || '',
      href: link || '#',
      isExternal: link.startsWith('http'),
      category: 'project',
    };
  }

  function asArray(maybe) {
    if (Array.isArray(maybe)) return maybe;
    if (Array.isArray(maybe?.results)) return maybe.results;
    return [];
  }

  onMount(async () => {
    const [partnersRes, validatorsRes, buildsRes] = await Promise.allSettled([
      partnersAPI.list({ page_size: 200 }),
      validatorsAPI.getAllValidators(),
      projectsAPI.list(),
    ]);

    const partners =
      partnersRes.status === 'fulfilled'
        ? asArray(partnersRes.value?.data).map(normalizePartner)
        : [];

    const validators =
      validatorsRes.status === 'fulfilled'
        ? asArray(validatorsRes.value?.data)
            .map(normalizeValidator)
        : [];

    const projects =
      buildsRes.status === 'fulfilled'
        ? asArray(buildsRes.value?.data).map(normalizeProject)
        : [];

    items = [...partners, ...validators, ...projects];
    loading = false;
  });
</script>

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[300px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <img
      src="/assets/illustrations/welcome-gradient.png"
      alt=""
      class="absolute inset-0 w-full h-full object-cover opacity-70"
    />
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="space-y-2">
      <h1
        class="text-[34px] sm:text-[40px] md:text-[46px] font-semibold font-display text-black leading-none"
        style="letter-spacing: -1px;"
      >
        Ecosystem
      </h1>
      <p class="text-[14px] sm:text-[15px] text-[#3f4b5f]" style="letter-spacing: 0.2px;">
        A thriving network of projects, validators, and partners building the future of the GenLayer ecosystem.
      </p>
    </header>

    <section
      class="rounded-[10px] border border-white/70 bg-white/78 p-5 sm:p-7 md:p-8 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md"
    >
      {#if loading}
        <div class="space-y-8 md:space-y-10">
          {#each SECTIONS as section, index}
            <section class={index > 0 ? 'border-t border-[#e9ecf3] pt-6 md:pt-8' : ''}>
              <div class="flex items-start gap-3">
                <div class="w-10 h-10 rounded-[12px] {section.iconClass} flex flex-shrink-0 items-center justify-center shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
                  <img src={section.icon} alt="" class="w-5 h-5" />
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-3">
                    <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
                      {section.title}
                    </h2>
                    <span class="h-6 w-24 rounded-full bg-[#f2f3f7] animate-pulse"></span>
                  </div>
                  <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">{section.description}</p>
                </div>
              </div>

              <div class="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-4">
                {#each Array(section.skeletonCount) as _}
                  <div class="h-[92px] rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)] animate-pulse"></div>
                {/each}
              </div>
            </section>
          {/each}
        </div>
      {:else if items.length === 0}
        <div class="rounded-[8px] border border-[#e8ebf2] bg-white p-12 text-center shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
          <h3 class="font-heading font-semibold text-black">Nothing here yet</h3>
          <p class="mt-1 text-[14px] text-[#6b6b6b]">Check back soon — we're growing the ecosystem.</p>
        </div>
      {:else}
        <div class="space-y-8 md:space-y-10">
          {#each SECTIONS as section, index}
            {@const sectionItems = grouped[section.id] ?? []}
            {#if sectionItems.length > 0}
              <section class={index > 0 ? 'border-t border-[#e9ecf3] pt-6 md:pt-8' : ''}>
                <div class="flex items-start gap-3">
                  <div class="w-10 h-10 rounded-[12px] {section.iconClass} flex flex-shrink-0 items-center justify-center shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
                    <img src={section.icon} alt="" class="w-5 h-5" />
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-3">
                      <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
                        {section.title}
                      </h2>
                      <span
                        class="inline-flex h-[25px] items-center rounded-full border px-3 text-[12px] font-semibold {section.countClass}"
                      >
                        {sectionItems.length} {section.title}
                      </span>
                    </div>
                    <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">{section.description}</p>
                  </div>
                </div>

                <div class="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-4">
                  {#each sectionItems as item (item.id)}
                    <PartnerCard {item} />
                  {/each}
                </div>
              </section>
            {/if}
          {/each}
        </div>
      {/if}
    </section>
  </div>
</div>
