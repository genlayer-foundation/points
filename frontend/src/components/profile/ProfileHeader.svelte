<script>
  import { push } from "svelte-spa-router";
  import { showSuccess } from "../../lib/toastStore";
  import Avatar from "../Avatar.svelte";
  import CategoryIcon from "../portal/CategoryIcon.svelte";
  import SocialLink from "../SocialLink.svelte";

  let {
    participant = null,
    isOwnProfile = false,
    isValidatorOnly = false,
    onParticipantUpdated = () => {},
  } = $props();

  let solidColor = $derived(
    participant?.steward
      ? "bg-green-500"
      : participant?.validator
        ? "bg-sky-500"
        : participant?.builder
          ? "bg-orange-500"
          : participant?.has_validator_waitlist
            ? "bg-sky-400"
            : participant?.has_builder_welcome
              ? "bg-orange-400"
              : "bg-purple-500",
  );

  let hasAnyRole = $derived(
    participant &&
      (participant.steward ||
        participant.validator ||
        participant.builder ||
        participant.creator ||
        participant.has_validator_waitlist ||
        participant.has_builder_welcome),
  );

  // UI state for copy-to-clipboard feedback
  let copiedAddress = $state(false);
</script>

<div
  class="bg-white rounded-[16px] overflow-hidden border border-[#f7f7f7] shadow-[0px_4px_12px_rgba(0,0,0,0.02)] mb-6"
>
  <!-- Banner Image -->
  <div
    class="h-32 md:h-48 relative overflow-hidden {participant?.banner_image_url ? '' : 'bg-gradient-to-r from-purple-600 via-indigo-500 to-sky-400'}"
  >
    {#if participant?.banner_image_url}
      <img
        src={participant.banner_image_url}
        alt="Profile banner"
        class="w-full h-full object-cover"
      />
    {/if}
  </div>

  <!-- Profile Info Section (Figma 1:3164 implementation) -->
  <div class="p-[12px] bg-white rounded-bl-[8px] rounded-br-[8px]">
    <div class="flex items-center">
      <div class="flex gap-[12px] items-center w-full">
        <!-- Avatar Wrapper -->
        <div
          class="bg-black border-[2.5px] border-[#e9f9fe] rounded-full w-[96px] h-[96px] overflow-hidden flex-shrink-0 relative flex items-center justify-center"
        >
          <Avatar user={participant} size="full" showBorder={false} />
        </div>

        <!-- Info Content -->
        <div class="flex flex-col gap-[8px] justify-center flex-1">
          <div class="flex gap-[12px] items-center">
            <h1
              class="text-[40px] font-semibold text-black leading-[40px]"
              style="letter-spacing: -0.8px; font-family: 'F37 Lineca', 'Geist', sans-serif;"
            >
              {participant?.name ||
                (isValidatorOnly ? "Validator" : "Participant")}
            </h1>

            <div class="flex items-start gap-[5px] mt-1">
              <!-- GenLayer badge (always shown) -->
              <div class="flex-shrink-0 relative badge-tooltip-wrap">
                <CategoryIcon category="genlayer" mode="hexagon" size={32} />
                <div class="badge-tooltip">
                  <span class="badge-tooltip-title">GenLayer Member</span>
                  <span class="badge-tooltip-desc">Part of the GenLayer ecosystem</span>
                </div>
              </div>
              <!-- Steward badge -->
              {#if participant?.steward || participant?.working_groups?.length > 0}
                <div class="flex-shrink-0 relative badge-tooltip-wrap">
                  <CategoryIcon category="steward" mode="hexagon" size={32} />
                  <div class="badge-tooltip">
                    <span class="badge-tooltip-title">Ecosystem Steward</span>
                    <span class="badge-tooltip-desc">{participant?.working_groups?.length > 0 ? 'Working Group Member' : 'Admin'}</span>
                  </div>
                </div>
              {/if}
              <!-- Community -->
              {#if participant?.creator}
                <div class="flex-shrink-0 relative badge-tooltip-wrap">
                  <CategoryIcon category="community" mode="hexagon" size={32} />
                  <div class="badge-tooltip">
                    <span class="badge-tooltip-title">Community</span>
                    <span class="badge-tooltip-desc">Growing the community through referrals</span>
                  </div>
                </div>
              {/if}
              <!-- Builder -->
              {#if participant?.builder || participant?.has_builder_welcome}
                <div class="flex-shrink-0 relative badge-tooltip-wrap">
                  <CategoryIcon category="builder" mode="hexagon" size={32} />
                  <div class="badge-tooltip">
                    <span class="badge-tooltip-title">Builder</span>
                    <span class="badge-tooltip-desc">{participant?.builder ? 'Deploying contracts and contributing code' : 'Builder journey in progress'}</span>
                  </div>
                </div>
              {/if}
              <!-- Validator -->
              {#if participant?.validator || participant?.has_validator_waitlist}
                <div class="flex-shrink-0 relative badge-tooltip-wrap">
                  <CategoryIcon category="validator" mode="hexagon" size={32} />
                  <div class="badge-tooltip">
                    <span class="badge-tooltip-title">Validator</span>
                    <span class="badge-tooltip-desc">{participant?.validator ? 'Securing the network through consensus' : 'On the validator waitlist'}</span>
                  </div>
                </div>
              {/if}
            </div>
          </div>

          <!-- Address -->
          <div class="flex items-center gap-[12px]">
            <p
              class="text-[14px] text-[#5e6671] font-medium leading-[18px] whitespace-nowrap"
            >
              {participant?.address
                ? participant.address.substring(0, 6) +
                  "..." +
                  participant.address.substring(participant.address.length - 4)
                : "0x000...0000"}
            </p>
            {#if participant?.address}
              <button
                onclick={() => {
                  navigator.clipboard.writeText(participant.address);
                  showSuccess("Address copied to clipboard!");
                  copiedAddress = true;
                  setTimeout(() => (copiedAddress = false), 1200);
                }}
                title="Copy address"
                class="hover:text-black transition-colors"
                aria-label="Copy Address"
              >
                {#if copiedAddress}
                  <svg
                    class="w-5 h-5 text-green-600 transition-transform duration-200 scale-110"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    ><path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z"/></svg
                  >
                {:else}
                  <svg
                    class="w-5 h-5 opacity-70 hover:opacity-100"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    ><path
                      d="M7 6V3C7 2.44772 7.44772 2 8 2H21C21.5523 2 22 2.44772 22 3V16C22 16.5523 21.5523 17 21 17H18V20C18 20.5523 17.5523 21 17 21H4C3.44772 21 3 20.5523 3 20V7C3 6.44772 3.44772 6 4 6H7ZM7 17V8H5V19H16V17H7ZM9 4V15H20V4H9Z"
                    /></svg
                  >
                {/if}
              </button>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- Social Connections & Actions Row -->
    <div class="flex items-center justify-between w-full mt-6">
      <div class="flex gap-[8px] items-center text-[14px] flex-wrap">
        {#if isOwnProfile}
          <!-- Own profile: show interactive social link pills -->
          <SocialLink
            platform="github"
            platformLabel="GitHub"
            connection={participant?.github_connection}
            initiateUrl="/api/auth/github/"
            onLinked={onParticipantUpdated}
            compact={true}
          />
          <SocialLink
            platform="twitter"
            platformLabel="X"
            connection={participant?.twitter_connection}
            initiateUrl="/api/auth/twitter/"
            onLinked={onParticipantUpdated}
            compact={true}
          />
          <SocialLink
            platform="discord"
            platformLabel="Discord"
            connection={participant?.discord_connection}
            initiateUrl="/api/auth/discord/"
            onLinked={onParticipantUpdated}
            compact={true}
          />
        {:else}
          <!-- Other user's profile: show read-only linked accounts -->
          {#if participant?.github_connection?.platform_username}
            <a
              href={`https://github.com/${participant.github_connection.platform_username}`}
              target="_blank"
              rel="noopener noreferrer"
              class="flex gap-[4px] items-center justify-center p-[4px] px-[8px] rounded-[6px] bg-white border border-[#f0f0f0] hover:bg-gray-50 transition-colors"
            >
              <svg class="w-4 h-4 opacity-80 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"/></svg>
              <span class="font-medium text-black tracking-[0.28px]">{participant.github_connection.platform_username}</span>
            </a>
          {/if}
          {#if participant?.twitter_connection?.platform_username}
            <a
              href={`https://x.com/${participant.twitter_connection.platform_username}`}
              target="_blank"
              rel="noopener noreferrer"
              class="flex gap-[4px] items-center justify-center p-[4px] px-[8px] rounded-[6px] bg-white border border-[#f0f0f0] hover:bg-gray-50 transition-colors"
            >
              <svg class="w-4 h-4 opacity-80 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              <span class="font-medium text-black tracking-[0.28px]">{participant.twitter_connection.platform_username}</span>
            </a>
          {/if}
          {#if participant?.discord_connection?.platform_username}
            <div class="flex gap-[4px] items-center justify-center p-[4px] px-[8px] rounded-[6px] bg-white border border-[#f0f0f0]">
              <svg class="w-4 h-4 opacity-80 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/></svg>
              <span class="font-medium text-black tracking-[0.28px]">{participant.discord_connection.platform_username}</span>
            </div>
          {/if}
        {/if}
      </div>

      <div class="flex gap-[10px] items-center">
        {#if isOwnProfile}
          <button
            onclick={() => push("/profile")}
            class="flex items-center gap-[8px] px-[14px] py-[10px] bg-white border border-[#f5f5f5] rounded-[6px] text-[13px] font-medium text-black hover:bg-gray-50 transition-colors"
          >
            <svg
              class="w-5 h-5 opacity-70"
              viewBox="0 0 24 24"
              fill="currentColor"
              ><path
                d="M16.7574 2.99666L14.7574 4.99666H5V18.9967H19V9.2393L21 7.2393V19.9967C21 20.5489 20.5523 20.9967 20 20.9967H4C3.44772 20.9967 3 20.5489 3 19.9967V3.99666C3 3.44438 3.44772 2.99666 4 2.99666H16.7574ZM20.4853 2.09717L21.8995 3.51138L12.7071 12.7038L11.2954 12.7063L11.2929 11.2896L20.4853 2.09717Z"
              /></svg
            >
            Edit profile
          </button>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .badge-tooltip-wrap .badge-tooltip {
    display: none;
    position: absolute;
    left: 50%;
    top: calc(100% + 8px);
    transform: translateX(-50%);
    background: #1a1a1a;
    border-radius: 8px;
    padding: 8px 12px;
    white-space: nowrap;
    z-index: 50;
    flex-direction: column;
    gap: 2px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .badge-tooltip-wrap .badge-tooltip::before {
    content: '';
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    border: 5px solid transparent;
    border-bottom-color: #1a1a1a;
  }

  .badge-tooltip-wrap:hover .badge-tooltip {
    display: flex;
  }

  .badge-tooltip-title {
    font-size: 13px;
    font-weight: 600;
    color: #ffffff;
    line-height: 1.2;
  }

  .badge-tooltip-desc {
    font-size: 12px;
    color: #999;
    line-height: 1.3;
  }
</style>
