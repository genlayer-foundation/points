<script>
  // Props for the Avatar component
  let { 
    user = null,           // User object with profile_image_url, name, address
    size = 'md',          // Size: 'xs', 'sm', 'md', 'lg', 'xl', '2xl'
    showBorder = false,   // Show white border (useful for overlapping)
    clickable = false,    // Make avatar clickable
    showStatus = false,   // Show online/offline status dot
    className = ''        // Additional CSS classes
  } = $props();
  
  // Determine role-based color theme
  let roleColorTheme = $derived(
    user?.steward ? 'green' :
    user?.validator ? 'sky' :
    user?.builder ? 'orange' :
    user?.has_validator_waitlist ? 'sky' :
    user?.has_builder_welcome ? 'orange' :
    'purple'
  );
  
  // Check if user is in transition (waitlist/welcome) - removed striping
  
  // Size mappings
  const sizeClasses = {
    'xs': 'w-6 h-6 text-xs',
    'sm': 'w-8 h-8 text-sm',
    'md': 'w-10 h-10 text-base',
    'lg': 'w-12 h-12 text-lg',
    'xl': 'w-16 h-16 text-xl',
    '2xl': 'w-20 h-20 text-2xl',
    '3xl': 'w-24 h-24 sm:w-32 sm:h-32 text-3xl sm:text-4xl'
  };
  
  const borderWidths = {
    'xs': 'ring-1',
    'sm': 'ring-2',
    'md': 'ring-2',
    'lg': 'ring-3',
    'xl': 'ring-3',
    '2xl': 'ring-4',
    '3xl': 'ring-4 ring-white'
  };
  
  // Color mappings for backgrounds
  const colorMap = {
    'green': 'bg-green-500',
    'sky': 'bg-sky-500',
    'orange': 'bg-orange-500',
    'purple': 'bg-purple-500'
  };
  
  // Get initials from name or address
  function getInitials() {
    if (user?.name) {
      const names = user.name.split(' ');
      if (names.length >= 2) {
        return names[0][0] + names[names.length - 1][0];
      }
      return user.name.substring(0, 2).toUpperCase();
    } else if (user?.address) {
      return user.address.substring(2, 4).toUpperCase();
    }
    return '??';
  }
  
  // Handle click if clickable
  function handleClick() {
    if (clickable && user?.address) {
      import('svelte-spa-router').then(({ push }) => {
        push(`/participant/${user.address}`);
      });
    }
  }
</script>

<div 
  class="relative inline-block {className}"
  class:cursor-pointer={clickable}
  onclick={clickable ? handleClick : undefined}
>
  <div 
    class="
      {sizeClasses[size]} 
      rounded-full 
      overflow-hidden 
      {showBorder ? `${borderWidths[size]} ring-white` : ''}
      flex items-center justify-center
      {clickable ? 'hover:opacity-90 transition-opacity' : ''}
    "
  >
    {#if user?.profile_image_url}
      <img 
        src={user.profile_image_url} 
        alt={user.name || 'User avatar'}
        class="w-full h-full object-cover"
      />
    {:else}
      <!-- Default avatar with role-based color -->
      <div 
        class="
          w-full h-full 
          {colorMap[roleColorTheme.replace('-waitlist', '').replace('-welcome', '')]}
          flex items-center justify-center
          font-semibold text-white
          relative
        "
      >
        <span>{getInitials()}</span>
      </div>
    {/if}
  </div>
  
  {#if showStatus}
    <span 
      class="
        absolute bottom-0 right-0 
        block h-2.5 w-2.5 
        rounded-full 
        bg-green-400 
        ring-2 ring-white
      "
    ></span>
  {/if}
</div>