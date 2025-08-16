<script>
  import { currentCategory, categories, categoryTheme } from '../stores/category.js';
  import Icon from './Icons.svelte';
  
  function selectCategory(categoryId) {
    currentCategory.set(categoryId);
  }
  
  // Category-specific colors
  const categoryColors = {
    global: {
      active: 'bg-white text-gray-900 shadow-sm',
      inactive: 'text-gray-600 hover:text-gray-900 hover:bg-gray-100',
      icon: ''
    },
    builder: {
      active: 'bg-orange-500 text-white shadow-sm',
      inactive: 'text-orange-600 hover:bg-orange-100',
      icon: 'text-orange-500'
    },
    validator: {
      active: 'bg-sky-500 text-white shadow-sm',
      inactive: 'text-sky-600 hover:bg-sky-100',
      icon: 'text-sky-500'
    }
  };
</script>

<div class="flex items-center space-x-1 bg-gray-200 rounded-lg p-1">
  {#each categories as category}
    {@const colors = categoryColors[category.id] || categoryColors.global}
    <button
      onclick={() => selectCategory(category.id)}
      class="flex items-center px-3 py-2 rounded-md text-sm font-medium transition-all duration-200
             {$currentCategory === category.id 
               ? colors.active
               : colors.inactive}"
    >
      <Icon 
        name={category.id === 'global' ? 'genlayer' : category.id} 
        size="sm" 
        className="mr-2 {$currentCategory === category.id ? (category.id === 'global' ? 'text-black' : '') : (category.id === 'global' ? 'text-gray-600' : colors.icon)}" 
      />
      {category.name}
    </button>
  {/each}
</div>