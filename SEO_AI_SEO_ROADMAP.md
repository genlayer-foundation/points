# SEO and AI SEO Roadmap

This document tracks the remaining SEO and AI-search work for GenLayer Portal after the first pass of metadata, canonical URL, crawl-file, sitemap, structured-data, and `llms.txt` improvements.

## Current State

The platform is a Vite/Svelte client-rendered SPA using hash routing through `svelte-spa-router`. That means the first HTML response is still mostly an app shell. Search engines that execute JavaScript can discover hydrated content, but the setup is weaker than SSR/SSG for:

- initial HTML content extraction
- social preview bots that do not execute JavaScript
- faster and more reliable indexing of dynamic public pages
- AI answer systems that rely on crawled/indexed page text

Already improved:

- default title, description, canonical, robots, Open Graph, Twitter, and JSON-LD tags
- route-level metadata for public routes
- `noindex,nofollow` fallback for unknown/protected app routes
- dynamic client-side metadata for project, POAP, and startup request detail pages
- `robots.txt`
- static `sitemap.xml`
- `llms.txt`
- tests for canonical normalization and metadata helpers

These changes are useful, but they do not replace server-rendered or pre-rendered page HTML.

## Core Principle

AI SEO is not a separate bag of tricks. Google says AI features in Search are still grounded in Search systems, and Bing’s guidelines describe discovery, crawl, indexing, and content quality across Bing search experiences, Copilot, and grounding APIs. The platform should optimize for clear, crawlable, useful, original, well-structured public content.

Do not create hidden “AI-only” content. Do not add structured data that does not match visible page content. Do not rely on `llms.txt` as a substitute for indexable HTML, sitemaps, internal links, and high-quality pages.

## Highest Priority: Rendering and Routing

### 1. Move Public Pages To SSR Or SSG

This is the biggest remaining SEO gap.

Recommended target architecture:

- Public content routes use SSR or SSG.
- Authenticated dashboards and workflow-heavy app routes can remain client-rendered.
- Public pages return meaningful HTML before JavaScript runs.
- Path URLs are canonical, not hash URLs.

Good candidates for SSR/SSG:

- `/`
- `/how-it-works`
- `/builders/resources`
- `/builders/projects/:slug`
- `/builders/startup-requests/:id`
- `/community/poaps`
- `/community/poaps/:slug`
- `/ecosystem-partners`
- `/gen-news`
- `/gen-tv`
- `/hackathon`
- `/hackathon-winners`
- `/referral-program`
- `/validators/participants`
- `/validators/waitlist/join`
- `/genesis/*`
- legal pages

Best implementation options:

1. Migrate the public site to SvelteKit hybrid rendering.
   - Use SSR for dynamic public pages.
   - Use prerendering for stable docs/marketing pages.
   - Keep protected dashboard views as client-heavy app pages.

2. Add static pre-rendering as an intermediate step.
   - Generate HTML for the public route set at build time.
   - Generate dynamic static pages from API data for projects, POAPs, and resources.
   - Keep SPA fallback only for authenticated/internal routes.

3. Use Vite SSR only if a SvelteKit migration is too large.
   - Vite supports SSR, but SvelteKit gives cleaner routing, data loading, and deployment conventions.

Avoid using dynamic rendering as the long-term answer. Google describes dynamic rendering as a workaround, not a recommended solution, because it adds complexity and operational risk.

### 2. Replace Hash Routing For Public Pages

Current canonical URLs are path-based, but the app still internally routes through hashes. Long term:

- public links should be normal path URLs
- internal links should use `/builders/resources`, not `/#/builders/resources`
- server/CDN rewrites should serve the right page or SSR handler
- legacy path aliases should 301 to canonical paths where possible
- hash-fragment legacy URLs cannot be redirected by the server, so the client should continue normalizing them

## Crawl and Indexation

### 3. Generate Dynamic Sitemaps

The current sitemap is static and covers important top-level public routes. It should become generated from real data.

Include:

- public project pages
- POAP pages that are public and not draft/private
- Gen TV stream pages if stream detail pages are exposed
- news/announcement pages if created
- partner pages if detail pages are exposed
- docs/foundation pages

Each sitemap entry should include:

- canonical URL
- reliable `lastmod`
- only indexable, public pages

If the URL count grows, split into sitemap indexes:

- `sitemap-static.xml`
- `sitemap-projects.xml`
- `sitemap-poaps.xml`
- `sitemap-content.xml`
- `sitemap.xml` as the index

### 4. Submit And Monitor Search Engines

Set up or verify:

- Google Search Console
- Bing Webmaster Tools
- sitemap submission in both
- index coverage reports
- URL inspection for key pages
- crawl stats
- structured data enhancement reports
- Bing/Copilot visibility reporting where available

Monitor:

- pages discovered but not indexed
- duplicate canonical issues
- soft 404s
- blocked resources
- mobile usability
- Core Web Vitals
- top queries and pages

### 5. Keep Robots Policy Intentional

Current `robots.txt` is a reasonable start. Revisit when SSR/SSG lands.

Rules:

- allow public pages and assets
- do not block JS/CSS/images needed to render public pages
- block internal/API/OAuth/account routes from crawling
- use `noindex` headers or meta tags for pages that can be crawled but should not be indexed
- decide separately whether AI training bots should be allowed or disallowed

Important distinction:

- `robots.txt` controls crawler access.
- `noindex` controls indexing.
- `Google-Extended` is a policy control for some Google model usage, not ordinary Google Search indexing.
- `llms.txt` is useful as an AI-readable orientation file, but it is not a replacement for `robots.txt`, sitemaps, or indexable content.

## Content Strategy For Search And AI Answers

### 6. Create Public, Answerable Content Pages

The platform needs more crawlable, non-gated explanatory content. AI answer systems tend to cite pages that answer specific questions clearly.

Recommended pages:

- What is GenLayer?
- What are Intelligent Contracts?
- What is Optimistic Democracy?
- What is GenVM?
- How GenLayer consensus works
- How to build on GenLayer
- GenLayer builder quickstart
- GenLayer validator guide
- GenLayer testnets: Asimov vs Bradbury
- GenLayer ecosystem projects
- GenLayer POAPs and community participation
- AI-native apps built on GenLayer
- GenLayer glossary

Each page should have:

- one clear H1
- short direct answer near the top
- descriptive sections with H2/H3 structure
- original examples, diagrams, screenshots, or code snippets
- links to docs, GitHub, explorer, resources, and related portal pages
- visible dates where freshness matters
- author or organization attribution where appropriate
- concise definitions that can be quoted or cited

Avoid:

- thin pages generated only to target keywords
- pages that require login to understand the main content
- AI-generated filler
- hidden blocks made only for crawlers

### 7. Strengthen Project And POAP Pages

Public detail pages should be useful as standalone pages.

For builder projects:

- server-render title, one-liner, long description, project links, screenshots, contributors, related contributions
- expose canonical project image and social preview image
- add visible project category/tags
- add “built with GenLayer” context
- add related resources and internal links

For POAP pages:

- server-render title, description, artwork, event date, claim status, collection count
- include event context and links back to community/GenLayer pages
- avoid indexing draft/private/expired pages unless there is durable public value

### 8. Add News/Content Detail Pages

If `gen-news` and `gen-tv` are important acquisition channels, list pages are not enough.

Add detail URLs for:

- announcements
- builder spotlights
- hackathon recaps
- stream episodes
- workshops

These pages can support `Article`, `VideoObject`, and `BreadcrumbList` structured data when the visible content supports it.

## Structured Data

### 9. Expand Schema Carefully

Keep the current base schema, then add page-specific schema only where it matches visible content.

Useful additions:

- `BreadcrumbList` for public routes
- `Article` or `BlogPosting` for news and essays
- `VideoObject` for Gen TV stream detail pages
- `Event` for hackathons, live workshops, and POAP-related events
- `SoftwareApplication` or `WebApplication` only for actual app/product pages
- `Organization` with complete logo, sameAs, legal name, and contact links if available
- `FAQPage` only when the page visibly contains FAQs

Validation requirements:

- run Google Rich Results Test for supported schema
- run Schema.org validator for all JSON-LD
- keep JSON-LD generated from the same source data as visible content
- add tests for required schema fields on key templates

## Social And Link Preview SEO

### 10. Server-Render Open Graph For Dynamic Pages

Client-side metadata helps browsers after hydration, but many social crawlers and link unfurlers read only initial HTML.

Needed:

- SSR/SSG metadata for dynamic public pages
- dynamic OG images for projects, POAPs, streams, announcements, and hackathon recaps
- stable image dimensions, preferably 1200x630
- absolute image URLs
- fallback image when a page lacks media

## Performance And Core Web Vitals

### 11. Reduce Client Bundle Size

Current production build reports a large main JS chunk. This matters for users and can affect crawl/render efficiency.

Priorities:

- route-level code splitting
- lazy-load protected dashboard routes
- lazy-load charting, wallet, blockchain, and steward-only code
- lazy-load reCAPTCHA only on pages/forms that need it
- split public marketing/content routes from authenticated app routes
- remove dead code and unused dependencies

### 12. Improve Image, Font, And Layout Performance

Checklist:

- set width/height or aspect-ratio on important images
- use modern formats and responsive image sizes
- preload only critical fonts
- use `font-display: swap`
- avoid layout shifts in cards, hero media, and route transitions
- defer non-critical analytics/scripts
- measure Lighthouse and CrUX/Search Console Core Web Vitals

## Semantic HTML And Accessibility

### 13. Fix Existing A11y And Semantic Warnings

The current Svelte build emits many accessibility warnings. These are not purely accessibility concerns; they also affect content structure and machine readability.

Fix:

- labels associated with controls
- icon-only buttons with accessible names
- clickable `div`s converted to buttons/links
- one logical H1 per public page
- meaningful link text
- useful alt text for content images
- empty alt text only for decorative images
- heading order
- landmark elements where appropriate

## Analytics And Measurement

### 14. Define SEO And AI SEO KPIs

Track:

- indexed public pages
- sitemap submitted/discovered URLs
- organic impressions/clicks/CTR/position
- branded vs non-branded queries
- rich result eligibility/errors
- AI/Bing/Copilot referrals where reported
- ChatGPT/Perplexity/Claude referral traffic where available in analytics
- backlinks to public project/resources pages
- crawl errors and server logs for major bots

### 15. Add Server Log Or Edge Log Review

Once public pages are SSR/SSG:

- inspect Googlebot, Bingbot, and social crawler requests
- confirm bots receive 200s for canonical public URLs
- confirm protected/internal URLs are not indexed
- identify high-value pages crawled but not indexed

## Governance

### 16. Add A Route SEO Registry

Every public route should have an owner and expected SEO behavior.

Track:

- route path
- index/noindex
- canonical URL
- title pattern
- description pattern
- schema type
- sitemap inclusion
- source of `lastmod`
- whether route is SSR, SSG, or CSR

### 17. Add SEO Checks To CI

Automated checks should prevent regressions:

- sitemap URLs are canonical and unique
- sitemap only contains indexable routes
- public routes have title and description
- protected routes are `noindex`
- JSON-LD is parseable
- canonical URL does not contain hash fragments
- no accidental `robots.txt` blocking of assets
- build output contains crawl files

## Suggested Execution Plan

### Phase 1: Short-Term Cleanup

Effort: 1-3 days

- submit current sitemap to Google Search Console and Bing Webmaster Tools
- validate current JSON-LD and rich result eligibility
- expand route metadata for any public routes missed in the first pass
- add route SEO registry
- add CI checks for sitemap/canonical/noindex behavior
- update internal public links to prefer path URLs where possible

### Phase 2: Rendering Migration

Effort: 1-3 weeks depending on deployment constraints

- choose SvelteKit SSR/SSG or Vite SSR path
- SSR/SSG public pages
- keep authenticated app routes client-heavy
- replace hash routing for public routes
- generate dynamic sitemaps from API data
- server-render Open Graph tags for dynamic pages

### Phase 3: Content And Schema Expansion

Effort: ongoing, first useful batch in 1-2 weeks

- publish the core GenLayer explanatory pages
- add detail pages for news/streams
- enrich project and POAP pages
- add BreadcrumbList, Article, VideoObject, Event, and FAQ schema where appropriate
- build dynamic OG images

### Phase 4: Performance And Monitoring

Effort: ongoing

- split large JS bundles
- fix Core Web Vitals issues
- resolve Svelte accessibility warnings
- monitor Search Console/Bing coverage weekly
- review crawl logs monthly

## References

- Google Search Central: [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)
- Google Search Central: [JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- Google Search Central: [Dynamic rendering as a workaround](https://developers.google.com/search/docs/crawling-indexing/javascript/dynamic-rendering)
- Google Search Central: [Structured data introduction](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data)
- Google Search Central: [Title links](https://developers.google.com/search/docs/appearance/title-link)
- Google Search Console: [Search Console tools](https://search.google.com/search-console/about)
- Bing: [Webmaster Guidelines](https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a)
- Bing Webmaster Blog: [Sitemaps in AI-powered search](https://blogs.bing.com/webmaster/July-2025/Keeping-Content-Discoverable-with-Sitemaps-in-AI-Powered-Search)
- SvelteKit docs: [Single-page apps](https://svelte.dev/docs/kit/single-page-apps)
- SvelteKit docs: [Static site generation](https://svelte.dev/docs/kit/adapter-static)
- Vite docs: [Server-side rendering](https://vite.dev/guide/ssr)
- `llms.txt` proposal: [llmstxt.org](https://llmstxt.org/)
