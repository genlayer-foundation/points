import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { categories, categoryTheme, currentCategory } from '../stores/category.js';

describe('categoryTheme', () => {
  it('keeps the app shell background white for every category', () => {
    const originalCategory = get(currentCategory);

    try {
      for (const category of categories) {
        currentCategory.set(category.id);
        expect(get(categoryTheme).bg).toBe('bg-white');
      }
    } finally {
      currentCategory.set(originalCategory);
    }
  });
});
