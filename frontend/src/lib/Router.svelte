<script module>
  // Re-export the navigation API so `import Router, { push, location, ... }
  // from 'svelte-spa-router'` (aliased to this file) keeps working unchanged.
  import {
    push, pop, replace, location, querystring, params, link, loc,
  } from './router.js';
  export { push, pop, replace, location, querystring, params, link, loc };
</script>

<script>
  import { onDestroy } from 'svelte';
  // loc and params are already in scope from the module script above.
  import { buildRoutes, matchRoute } from './router.js';

  // onRouteLoaded / onConditionsFailed replace svelte-spa-router's
  // on:routeLoaded / on:conditionsFailed events (callback props are the
  // Svelte 5 idiom and avoid event-forwarding deprecation warnings).
  let { routes = {}, onRouteLoaded, onConditionsFailed } = $props();

  const routesList = buildRoutes(routes);

  let Component = $state(null);
  let componentParams = $state(null);
  let componentProps = $state({});
  let lastLoc = null;

  const unsubscribe = loc.subscribe(async (newLoc) => {
    lastLoc = newLoc;
    const hit = matchRoute(routesList, newLoc.location);
    if (!hit) {
      // No match (the '*' catch-all normally prevents this) — render nothing.
      Component = null;
      params.set(undefined);
      return;
    }

    const { route, params: matched } = hit; // `params` (the store) stays in scope
    const hasParams = Object.keys(matched).length > 0;
    const detail = {
      route: route.path,
      location: newLoc.location,
      querystring: newLoc.querystring,
      userData: route.userData,
      params: hasParams ? matched : null,
    };

    // Run auth/preconditions in order; first falsy result aborts the route.
    for (const cond of route.conditions) {
      if (!(await cond(detail))) {
        if (newLoc !== lastLoc) return; // user navigated away mid-await
        Component = null;
        onConditionsFailed?.(detail);
        return;
      }
    }
    if (newLoc !== lastLoc) return;

    Component = route.component;
    componentParams = hasParams ? matched : null;
    componentProps = route.props;
    params.set(componentParams);
    onRouteLoaded?.({ ...detail, component: Component });
  });

  onDestroy(unsubscribe);
</script>

{#if Component}
  {#if componentParams}
    <Component params={componentParams} {...componentProps} />
  {:else}
    <Component {...componentProps} />
  {/if}
{/if}
