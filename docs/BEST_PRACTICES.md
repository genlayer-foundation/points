# Developer Best Practices

This document outlines best practices for developing and maintaining the GenLayer Points system.

## Table of Contents

- [Code Organization](#code-organization)
- [Django Best Practices](#django-best-practices)
- [Svelte 5 Best Practices](#svelte-5-best-practices)
- [API Design](#api-design)
- [Database Optimization](#database-optimization)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Performance](#performance)

## Code Organization

### Directory Structure

Follow the existing project structure:

```
backend/
├── app_name/
│   ├── models.py      # Data models
│   ├── views.py       # ViewSets and views
│   ├── serializers.py # DRF serializers
│   ├── permissions.py # Custom permissions
│   ├── admin.py       # Admin configuration
│   ├── urls.py        # URL routing
│   └── tests/         # Test files
```

### File Naming

- Use lowercase with underscores for Python files
- Use PascalCase for Svelte components
- Keep file names descriptive but concise

## Django Best Practices

### Models

1. **Use abstract base models for common fields**:
   ```python
   from utils.models import BaseModel
   
   class MyModel(BaseModel):
       # Inherits created_at, updated_at
       name = models.CharField(max_length=100)
   ```

2. **Add proper help_text and verbose names**:
   ```python
   class Contribution(models.Model):
       points = models.PositiveIntegerField(
           help_text="Base points before multiplier"
       )
       
       class Meta:
           verbose_name = "Contribution"
           verbose_name_plural = "Contributions"
   ```

3. **Use database constraints**:
   ```python
   class Meta:
       constraints = [
           models.UniqueConstraint(
               fields=['user', 'contribution_type'],
               name='unique_user_contribution_type'
           )
       ]
   ```

### Views

1. **Use select_related and prefetch_related**:
   ```python
   def get_queryset(self):
       return Contribution.objects.select_related(
           'user', 'contribution_type'
       ).prefetch_related(
           'evidence_items'
       )
   ```

2. **Return appropriate HTTP status codes**:
   ```python
   from rest_framework import status
   
   return Response(data, status=status.HTTP_201_CREATED)
   ```

3. **Use DRF decorators for actions**:
   ```python
   @action(detail=True, methods=['post'])
   def approve(self, request, pk=None):
       instance = self.get_object()
       # ...
   ```

### Serializers

1. **Use nested serializers carefully**:
   ```python
   # Use SerializerMethodField for complex logic
   class ContributionSerializer(serializers.ModelSerializer):
       user_details = serializers.SerializerMethodField()
       
       def get_user_details(self, obj):
           return LightUserSerializer(obj.user).data
   ```

2. **Implement validation in validate() method**:
   ```python
   def validate(self, data):
       if data['min_points'] > data['max_points']:
           raise serializers.ValidationError(
               "min_points cannot exceed max_points"
           )
       return data
   ```

## Svelte 5 Best Practices

### State Management

1. **Use runes properly**:
   ```svelte
   <script>
     // State
     let count = $state(0);
     
     // Derived values
     let doubled = $derived(count * 2);
     
     // Effects
     $effect(() => {
       console.log(`Count changed to ${count}`);
     });
   </script>
   ```

2. **Avoid unnecessary reactivity**:
   ```svelte
   <!-- Good: Only updates when needed -->
   let filtered = $derived(
     items.filter(item => item.active)
   );
   
   <!-- Avoid: Recalculates on every render -->
   {#each items.filter(item => item.active) as item}
   ```

### Component Design

1. **Use props with defaults**:
   ```svelte
   <script>
     let {
       value = '',
       disabled = false,
       onchange = () => {}
     } = $props();
   </script>
   ```

2. **Keep components focused**:
   - One responsibility per component
   - Extract reusable logic to lib/

### API Integration

1. **Handle loading and error states**:
   ```svelte
   <script>
     let data = $state(null);
     let loading = $state(true);
     let error = $state(null);
     
     onMount(async () => {
       try {
         const response = await api.get('/endpoint/');
         data = response.data;
       } catch (err) {
         error = err.message;
       } finally {
         loading = false;
       }
     });
   </script>
   
   {#if loading}
     <Spinner />
   {:else if error}
     <ErrorMessage {error} />
   {:else}
     <Content {data} />
   {/if}
   ```

## API Design

### URL Patterns

- Use nouns, not verbs: `/contributions/` not `/getContributions/`
- Use plural names: `/users/` not `/user/`
- Nest resources logically: `/users/{id}/contributions/`

### Response Format

```json
{
  "count": 100,
  "next": "http://api/v1/items/?page=2",
  "previous": null,
  "results": [...]
}
```

### Error Responses

```json
{
  "error": "Validation failed",
  "details": {
    "field_name": ["Error message"]
  }
}
```

## Database Optimization

### Query Optimization

1. **Use database indexes**:
   ```python
   class Meta:
       indexes = [
           models.Index(fields=['created_at']),
           models.Index(fields=['user', 'contribution_type']),
       ]
   ```

2. **Avoid N+1 queries**:
   ```python
   # Bad: N+1 query
   for contribution in Contribution.objects.all():
       print(contribution.user.name)
   
   # Good: Single query with join
   for contribution in Contribution.objects.select_related('user'):
       print(contribution.user.name)
   ```

3. **Use `only()` and `defer()` for partial selects**:
   ```python
   User.objects.only('id', 'name', 'address')
   ```

### Caching

Consider caching for:
- Leaderboard rankings
- Contribution type statistics
- User profile data

## Error Handling

### Backend

```python
from rest_framework.exceptions import ValidationError, PermissionDenied

def my_view(request):
    try:
        # operation
    except Model.DoesNotExist:
        raise ValidationError("Resource not found")
    except PermissionError:
        raise PermissionDenied("Not authorized")
```

### Frontend

```javascript
try {
  const response = await api.post('/endpoint/', data);
  showSuccess('Success!');
} catch (error) {
  if (error.response?.status === 400) {
    showError(error.response.data.error || 'Validation failed');
  } else if (error.response?.status === 403) {
    showError('Permission denied');
  } else {
    showError('An unexpected error occurred');
  }
}
```

## Testing

### Backend Tests

```python
from django.test import TestCase
from rest_framework.test import APITestCase

class ContributionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(...)
        self.client.force_authenticate(user=self.user)
    
    def test_create_contribution(self):
        response = self.client.post('/api/v1/contributions/', {...})
        self.assertEqual(response.status_code, 201)
```

### Frontend Tests

```javascript
import { render, fireEvent } from '@testing-library/svelte';
import Component from './Component.svelte';

test('handles click', async () => {
  const { getByRole } = render(Component);
  const button = getByRole('button');
  await fireEvent.click(button);
  // assertions
});
```

## Performance

### Backend

1. Use database connection pooling in production
2. Implement pagination for list endpoints
3. Use async views for I/O-bound operations
4. Cache expensive computations

### Frontend

1. Lazy load routes and large components
2. Debounce search inputs
3. Use virtual scrolling for large lists
4. Optimize images and assets

### Monitoring

- Log slow queries (>100ms)
- Monitor API response times
- Track frontend performance metrics
