/**
 * `wrap()` — drop-in replacement for `svelte-spa-router/wrap`.
 *
 * Marks a route component with auth/preconditions, static props and userData.
 * The portal only ever uses `{ component, conditions }` (see App.svelte
 * `protectedRoute`), so this is the minimal subset; the async-component /
 * loading-component features of the original are intentionally dropped.
 * ponytail: no asyncComponent/loadingComponent — unused; add back if a route
 * ever needs code-splitting.
 */
export function wrap(args) {
  if (!args || !args.component) {
    throw Error('wrap() requires a component');
  }
  if (args.conditions && !Array.isArray(args.conditions)) {
    args.conditions = [args.conditions];
  }
  return {
    component: args.component,
    conditions: args.conditions || [],
    userData: args.userData,
    props: args.props || {},
    _sveltesparouter: true,
  };
}

export default wrap;
