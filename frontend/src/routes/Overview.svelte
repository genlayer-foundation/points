<script>
  import ReferralSection from '../components/ReferralSection.svelte';
  import Icon from '../components/Icons.svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';

  function handleConnectWallet() {
    // Trigger the auth button click
    const authButton = document.querySelector('[data-auth-button]');
    if (authButton) authButton.click();
  }
</script>

<div class="max-w-4xl mx-auto space-y-8">
  <!-- Header -->
  <div class="space-y-4">
    <h1 class="text-3xl font-bold text-gray-900">GenLayer’s Incentivized Builder Program</h1>
    <p class="text-base text-gray-700 leading-relaxed">

      The GenLayer Testnet Incentives Program rewards early contributors who
help build the foundation of the GenLayer ecosystem across code,
infrastructure, and community growth. <b>Participation is open to everyone.</b> Direct
coding is not required to participate.
    </p>
    <p class="text-base text-gray-700 leading-relaxed">
    Community members can earn points by referring builders. The referral
points will show as “Builder Points” in the <b>Supporters</b> section as soon
as the referred Builders complete the Builders Welcome Journey or their first
contribution. 
    </p>
    <p class="text-base text-gray-700 leading-relaxed">
      All contributions are tracked through the wallet address, which is required to receive points and maintain contribution records. Contributors can view their rank and track points in real time through the leaderboards and individual profile pages. Apart from the builders program, GenLayer also incentivizes validator contributions.
    </p>
  </div>

  <!-- Referral Program -->
  <div class="bg-purple-50 rounded-lg shadow-sm border border-purple-200">
    <!-- Header -->
    <div class="bg-purple-100 px-5 py-3 border-b border-purple-200">
      <h2 class="text-lg font-semibold text-purple-700 uppercase tracking-wider flex items-center">
        <svg class="w-5 h-5 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
        </svg>
        Referral Program
      </h2>
    </div>

    <!-- Content -->
    <div class="flex flex-col lg:flex-row">
      <!-- Image -->
      <div class="w-full lg:w-1/2">
        <img src="/assets/builders_program.png" alt="Builder Program" class="w-full h-full object-cover lg:rounded-bl-lg" />
      </div>

      <!-- Text and Action -->
      <div class="w-full lg:w-1/2 p-6 space-y-4">
        <p class="text-gray-700">
          For each builder referred who submits at least one contribution, the referrer receives 10% of the points that builder earns permanently. In addition, referrers receive 500 Discord XP for each valid referral.
        </p>
        <p class="text-gray-700 font-bold italic">
          Share the image with your referral link on X to be eligible for the $1000 raffle.
        </p>
        {#if $authState.isAuthenticated}
          <div class="flex items-center justify-center pt-2">
            <ReferralSection />
          </div>
        {:else}
          <div class="flex items-center justify-center pt-2">
            <button
              onclick={handleConnectWallet}
              class="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-md font-medium transition-colors"
            >
              Connect Wallet to Get Referral Code
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- Contributor Categories -->
  <div class="space-y-6">
    <h2 class="text-2xl font-bold text-gray-900">Contributor Categories</h2>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Builders -->
    <div class="bg-orange-50 rounded-lg shadow-sm border border-orange-200 overflow-hidden">
      <!-- Header -->
      <div class="bg-orange-100 px-5 py-3 border-b border-orange-200">
        <h2 class="text-lg font-semibold text-orange-700 uppercase tracking-wider flex items-center">
          <svg class="w-5 h-5 mr-2 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
            <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
          </svg>
          Builders
        </h2>
      </div>
      <!-- Content -->
      <div class="p-6 space-y-3">
        <p class="text-gray-700">
          Contribute by writing Intelligent Contracts, launching dApps, creating educational
          resources, or building developer tools.
        </p>
        <button
          onclick={() => push('/builders/contributions')}
          class="inline-flex items-center text-orange-600 hover:text-orange-700 font-medium"
        >
          → View Builder Contribution opportunities
        </button>
      </div>
    </div>

    <!-- Supporters -->
    <div class="bg-purple-50 rounded-lg shadow-sm border border-purple-200 overflow-hidden">
      <!-- Header -->
      <div class="bg-purple-100 px-5 py-3 border-b border-purple-200">
        <h2 class="text-lg font-semibold text-purple-700 uppercase tracking-wider flex items-center">
          <Icon name="participants" size="md" className="text-purple-600 mr-2" />
          Supporters
        </h2>
      </div>
      <!-- Content -->
      <div class="p-6 space-y-3">
        <p class="text-gray-700">
          Non-technical contributors who grow the community. Currently earn points through
          referring builders and validators. Additional opportunities will become available in
          future phases.
        </p>
        <p class="text-sm text-gray-600 italic">
          Note: Supporter activity does not currently influence Discord roles or points.
        </p>
      </div>
    </div>

    <!-- Validators -->
    <div class="bg-sky-50 rounded-lg shadow-sm border border-sky-200 overflow-hidden">
      <!-- Header -->
      <div class="bg-sky-100 px-5 py-3 border-b border-sky-200">
        <h2 class="text-lg font-semibold text-sky-700 uppercase tracking-wider flex items-center">
          <svg class="w-5 h-5 mr-2 text-sky-600" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L4 7v5c0 5 3.5 9.5 8 10.5 4.5-1 8-5.5 8-10.5V7L12 2z"/>
          </svg>
          Validators
        </h2>
      </div>
      <!-- Content -->
      <div class="p-6 space-y-3">
        <p class="text-gray-700">
          Help scale and secure the GenLayer network. Points can be earned through contributions like documentation, protocol testing, infrastructure tooling, security research, and regional validator deployment.
        </p>
        <div class="flex flex-col space-y-2">
          <button
            onclick={() => push('/validators/contributions')}
            class="inline-flex items-center text-sky-600 hover:text-sky-700 font-medium"
          >
            → View Validator Contributions opportunities
          </button>
          <button
            onclick={() => push('/validators/waitlist')}
            class="inline-flex items-center text-sky-600 hover:text-sky-700 font-medium"
          >
            → Join Validator Waitlist
          </button>
        </div>
      </div>
    </div>

    <!-- Stewards -->
    <div class="bg-green-50 rounded-lg shadow-sm border border-green-200 overflow-hidden">
      <!-- Header -->
      <div class="bg-green-100 px-5 py-3 border-b border-green-200">
        <h2 class="text-lg font-semibold text-green-700 uppercase tracking-wider flex items-center">
          <span class="mr-2">🌱</span>
          Stewards
        </h2>
      </div>
      <!-- Content -->
      <div class="p-6 space-y-3">
        <p class="text-gray-700">
          Stewards review submited contributions, evaluating them on technical quality, originality, and ecosystem impact. Stewards assign points transparently and may request revisions or offer feedback to improve contributions. Their role ensures fairness, consistency, and alignment with GenLayer's long-term vision as the ecosystem grows.
        </p>
        <button
          onclick={() => push('/stewards')}
          class="inline-flex items-center text-green-600 hover:text-green-700 font-medium"
        >
          → Learn more about Stewards
        </button>
      </div>
    </div>
    </div>
  </div>
</div>
