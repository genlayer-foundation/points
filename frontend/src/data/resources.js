// Builder Resources content. Keep this file as the curated inventory for the
// Resources page; dynamic Gen TV stream details are resolved by slug in the route.

export const pageHeader = {
  title: 'Builder Resources',
  subtitle: 'Agent-first resources for building GenLayer projects with coding assistants.',
};

export const communityLinks = [
  { label: 'Telegram', url: 'https://t.me/genlayer', icon: 'telegram', color: '#26A5E4' },
  { label: 'Discord', url: 'https://discord.gg/8Jm4v89VAu', icon: 'discord', color: '#5865F2' },
  { label: 'X', url: 'https://x.com/GenLayer', icon: 'x', color: '#111111' },
];

export const genLayerContext = {
  eyebrow: 'Agent context',
  title: 'What GenLayer lets you build',
  description:
    'GenLayer is an AI-native blockchain for Intelligent Contracts: Python contracts that run in GenVM, can use LLM reasoning and live web data, and settle their results on-chain through AI-validator consensus.',
  agentRule:
    'Use GenLayer when an implementation needs judgment, external facts, unstructured content, or changing real-world data that a deterministic smart contract cannot verify by itself.',
  capabilities: [
    {
      label: 'LLM reasoning',
      description: 'Interpret text, score outputs, classify events, summarize evidence, and make constrained decisions inside contract logic.',
    },
    {
      label: 'Web access',
      description: 'Read websites and APIs directly from Intelligent Contracts without routing every fact through an oracle first.',
    },
    {
      label: 'Consensus on meaning',
      description: 'Validators compare whether outcomes are equivalent enough to accept, even when AI or web outputs are not byte-identical.',
    },
  ],
  outcomes: [
    'Intelligent oracles',
    'Web-aware agents',
    'Prediction and resolution markets',
    'Quality, reputation, and moderation systems',
    'Data-driven DeFi or DAO automation',
  ],
};

export const agentResources = {
  title: 'GenLayer Skills for coding agents',
  url: 'https://skills.genlayer.com/',
  description:
    'The primary entry point for AI coding agents. Skills package the GenLayer context, docs, API references, linting, testing, and deployment workflows an agent needs to build correctly.',
  highlights: [
    'Task playbooks for writing, testing, linting, and deploying contracts',
    'Prompt-ready docs and API context packaged for agent workflows',
    'Project patterns that steer agents toward existing examples first',
    'Quality gates for iterating without drifting from GenLayer conventions',
  ],
  prompt: `You are a coding agent implementing a GenLayer project. Treat GenLayer as an AI-native blockchain where Intelligent Contracts are Python contracts running in GenVM, with non-deterministic web and LLM operations validated by consensus.

GenLayer context:
- GenLayer is for apps that need judgment, external facts, unstructured content, or changing real-world data to affect on-chain state.
- Intelligent Contracts can call LLMs, fetch web/API data, process natural language, and still settle results through decentralized AI-validator consensus.
- Use GenLayer for intelligent oracles, web-aware agents, prediction and resolution markets, reputation or moderation systems, AI-assisted governance, data-driven DeFi, and workflows where validators must agree on meaning rather than exact bytes.
- Do not model GenLayer as a normal deterministic EVM chain. Design explicit validation/equivalence rules for any LLM or web-dependent result.

Use official GenLayer agent context first:
- Skills site: https://skills.genlayer.com/
- For Claude Code, install: /plugin marketplace add genlayerlabs/skills
- Then install the development plugin: /plugin install genlayer-dev@genlayerlabs
- Use genlayernode only when the task is validator-node operation, not normal app or contract development.

Available GenLayer Skills and when to use them:
- write-contract: use before and during Intelligent Contract implementation. It covers storage rules, runner dependencies, equivalence-principle choice, validator patterns, LLM resilience, web access, cross-contract calls, and anti-patterns.
- genvm-lint: run after every contract change. Use genvm-lint check contracts/<file>.py --json and fix errors before testing or deploying.
- direct-tests: use for fast in-memory unit tests of state transitions, access control, validation, and mocked web or LLM calls. Run with pytest tests/direct/ -v.
- integration-tests: use after direct tests pass when consensus, real web/LLM calls, Studio, GLSim, StudioNet, or Bradbury behavior matters. Run with gltest tests/integration/ -v -s.
- genlayer-cli: use for networks, accounts, deployment, calls, writes, schemas, receipts, traces, and debugging.

Add MCP context when the client supports MCP:
- GenLayer Docs MCP: claude mcp add genlayer-docs --transport sse https://docs-mcp.genlayer.com/sse
- GenLayer MCP: claude mcp add genlayer npx -- -y genlayer-mcp
- Use docs MCP to verify APIs, examples, SDK methods, and current network instructions before writing code. If MCP is unavailable, use https://docs.genlayer.com/full-documentation.txt and https://sdk.genlayer.com/main/_static/ai/api.txt.

Package and tool map:
- CLI and local environment: npm install -g genlayer
- Contract linting: pip install genvm-linter
- Contract tests: pip install genlayer-test, or pip install genlayer-test[sim] when using GLSim
- Frontend or TypeScript app integration: npm install genlayer-js
- Python backend, scripts, or app integration: use genlayer-py and verify the exact API in the SDK reference before coding
- VS Code-compatible editor support: https://marketplace.visualstudio.com/items?itemName=genlayer-labs.genlayer

Build workflow:
1. Clarify whether the task is contract-only, contract plus frontend, backend integration, deployment, or validator-node operation.
2. If creating a project, prefer established starters before inventing structure:
   - GenLayer Gym for web-access sources, benchmarks, and evaluation patterns: https://gym.genlayer.foundation
   - Intelligent Oracle for oracle-style patterns: https://intelligentoracle.com
   - Project boilerplate: https://github.com/genlayerlabs/genlayer-project-boilerplate
3. For contracts, use Python with a pinned GenVM Depends header. Do not use unpinned latest or test runner aliases.
4. Choose the equivalence strategy before writing non-deterministic logic:
   - Use strict_eq only when validators can reproduce exactly the same normalized output.
   - Use custom leader and validator functions for LLM calls, changing web pages, fuzzy scoring, external APIs with unstable fields, and production logic.
   - Mock web and LLM calls in direct tests; use integration tests for full consensus.
5. Use GenLayer storage types for persisted state. Do not store raw Python dict or list as contract storage. Use TreeMap, DynArray, dataclasses with allow_storage, and sized integers for money.
6. Handle LLM output defensively. Request JSON, validate types, handle aliases, sanitize malformed JSON, and classify errors with deterministic prefixes such as EXPECTED, EXTERNAL, TRANSIENT, and LLM_ERROR.
7. Run quality gates in order:
   - genvm-lint check contracts/<file>.py --json
   - pytest tests/direct/ -v
   - gltest tests/integration/ -v -s when consensus, deployment, or real network behavior matters
   - genlayer deploy, genlayer schema, genlayer call, genlayer write, and genlayer receipt for deploy/debug loops

Network and deployment rules:
- Use genlayer network set for built-in networks instead of overriding RPC manually.
- StudioNet is gasless; 0 GEN is expected and okay.
- Bradbury and Asimov testnets require funded accounts. Use https://testnet-faucet.genlayer.foundation/ for testnet GEN. Faucet claiming is browser-based and cannot be fully automated.
- Debug failed transactions with genlayer receipt <txHash> --stdout --stderr, then genlayer schema <address>, genlayer code <address>, and read calls before changing code.

Application integration gap to compensate for:
- The current genlayer-dev skills are strong for contract writing, linting, tests, CLI, and deployment, but they do not fully define frontend/backend integration with genlayer-js or genlayer-py.
- When building a dApp, explicitly consult GenLayerJS or GenLayerPY docs via docs MCP or the SDK reference. Do not invent client method names.
- Generate or inspect the deployed contract schema before wiring UI/backend calls.
- In TypeScript/frontends, use genlayer-js for createClient, chains, readContract, writeContract, transaction status, receipts, and event/status UX. Keep addresses, chain config, and deployed schemas in typed config.
- In Python backends/scripts, use genlayer-py only after verifying the current API surface in the SDK reference.
- Always distinguish read/view calls from write/transaction calls in the UI. Show submitted, pending, finalized, and failed states where relevant.

Deliverable expectations:
- Make the smallest complete implementation that passes lint and tests.
- Prefer direct tests for fast feedback and integration tests for consensus confidence.
- If a tool, network, account, API key, faucet token, Docker environment, or LLM provider is unavailable, say exactly what is blocked and provide the next command or manual step.
- Never leave GenLayer-specific APIs guessed. Verify them in Skills, docs MCP, full docs, or SDK reference before finalizing.`,
  includedReferences: [
    {
      label: 'Full documentation',
      url: 'https://docs.genlayer.com/full-documentation.txt',
      description: 'Plain-text docs for comparing or double-checking agent output.',
    },
    {
      label: 'API documentation',
      url: 'https://sdk.genlayer.com/main/_static/ai/api.txt',
      description: 'Plain-text SDK reference when a skill needs verification.',
    },
  ],
};

export const codingStreams = [
  {
    slug: 'from-zero-to-genlayer',
    title: 'From Zero to GenLayer',
    description: 'The key onboarding session for builders getting started with GenLayer.',
    url: 'https://x.com/i/broadcasts/1jxXgeaLLgRJZ',
    image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/from-zero-to-genlayer.png',
    starts_at: '2026-03-19T11:00:00.000Z',
    ends_at: '2026-03-19T11:30:00.000Z',
  },
  {
    slug: 'vibecoding-ep2',
    title: 'Vibecoding: Our First Intelligent Contract',
    description: 'Creating the first Intelligent Contract, testing it in Studio, and fixing bugs.',
    url: 'https://x.com/i/broadcasts/1eaKbjQdYgrKX',
    image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/vibecoding-ep2.png',
    starts_at: '2025-12-30T14:00:00.000Z',
    ends_at: '2025-12-30T14:30:00.000Z',
  },
  {
    slug: 'vibecoding-bradbury-gym',
    title: 'Vibecoding: Bradbury Gym',
    description: 'Benchmark-oriented GenLayer development and the reference direction for GenLayer Gym.',
    url: 'https://x.com/i/broadcasts/1aKbdbyZdjqJX',
    image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/vibecoding-bradbury-gym.png',
    starts_at: '2026-04-01T16:30:00.000Z',
    ends_at: '2026-04-01T17:00:00.000Z',
  },
  {
    slug: 'gentalks-ep8',
    title: 'GenTalks: Skills Review',
    description: 'A GenTalks session covering Bradbury context and skills.genlayer.com.',
    url: 'https://x.com/i/broadcasts/1wxWjaZPpYnJQ',
    image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/gentalks-ep8.png',
    starts_at: '2026-03-18T14:30:00.000Z',
    ends_at: '2026-03-18T15:00:00.000Z',
  },
];

export const starterProjects = [
  {
    label: 'GenLayer Gym',
    category: 'Primary reference',
    url: 'https://gym.genlayer.foundation',
    codeUrl: '',
    description: 'Reference project for web-access sources, benchmarks, and evaluation patterns.',
    featured: true,
  },
  {
    label: 'Intelligent Oracle',
    category: 'Featured example',
    url: 'https://intelligentoracle.com',
    codeUrl: '',
    description: 'Reference oracle project for agents building with web access and consensus checks.',
  },
  {
    label: 'Project Boilerplate',
    category: 'Starter',
    url: 'https://github.com/genlayerlabs/genlayer-project-boilerplate',
    codeUrl: 'https://github.com/genlayerlabs/genlayer-project-boilerplate',
    description: 'Cloneable project structure for a contract plus frontend workflow.',
  },
  {
    label: 'Bridge Boilerplate',
    category: 'Starter',
    url: 'https://github.com/genlayer-foundation/genlayer-studio-bridge-boilerplate',
    codeUrl: 'https://github.com/genlayer-foundation/genlayer-studio-bridge-boilerplate',
    description: 'Cross-chain bridge starter for testing integrations with GenLayer Studio.',
  },
  {
    label: 'Prediction Market Kit',
    category: 'Open source kit',
    url: 'https://github.com/courtofinternet/pm-kit',
    codeUrl: 'https://github.com/courtofinternet/pm-kit',
    description: 'Prediction-market template for AI consensus and outcome resolution flows.',
  },
];

export const buildTools = [
  {
    label: 'GenLayer Studio',
    url: 'https://studio.genlayer.com',
    description: 'Browser IDE for writing, testing, and deploying Intelligent Contracts.',
    icon: 'studio',
  },
  {
    label: 'GenLayer CLI',
    url: 'https://docs.genlayer.com/developers/intelligent-contracts/tools/genlayer-cli',
    description: 'Scaffold, deploy, and interact with contracts from the terminal.',
    icon: 'cli',
  },
  {
    label: 'JavaScript SDK',
    url: 'https://docs.genlayer.com/developers/decentralized-applications/genlayer-js',
    description: 'Install with npm install genlayer-js.',
    icon: 'js',
  },
  {
    label: 'Python SDK',
    url: 'https://docs.genlayer.com/api-references/genlayer-py',
    description: 'Install with pip install genlayer-py.',
    icon: 'python',
  },
  {
    label: 'GenLayer Test',
    url: 'https://docs.genlayer.com/api-references/genlayer-test',
    description: 'Install with pip install genlayer-test.',
    icon: 'test',
  },
  {
    label: 'VS Code Extension',
    url: 'https://marketplace.visualstudio.com/items?itemName=genlayer-labs.genlayer',
    description: 'Official VS Code extension for GenLayer intelligent contract development.',
    icon: 'vscode',
  },
];

export const networkResources = [
  {
    label: 'Testnet Faucet',
    url: 'https://testnet-faucet.genlayer.foundation/',
    description: 'Claim Bradbury testnet GEN to start building.',
    kind: 'faucet',
  },
  {
    label: 'Bradbury Explorer',
    url: 'https://explorer-bradbury.genlayer.com/',
    description: 'Browse Bradbury testnet activity.',
    kind: 'explorer',
  },
  {
    label: 'Asimov Explorer',
    url: 'https://explorer-asimov.genlayer.com/',
    description: 'Browse Asimov testnet activity.',
    kind: 'explorer',
  },
  {
    label: 'Studio Explorer',
    url: 'https://explorer-studio.genlayer.com/',
    description: 'Inspect Studio network activity.',
    kind: 'explorer',
  },
];

export const deepDiveReferences = [
  {
    label: 'Developer Documentation',
    url: 'https://docs.genlayer.com/developers',
    description: 'Main documentation for builders who want to read beyond the skills.',
  },
  {
    label: 'Equivalence Principle',
    url: 'https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle',
    description: 'Core consensus model for non-deterministic operations.',
  },
  {
    label: 'GenVM SDK',
    url: 'https://sdk.genlayer.com/main/',
    description: 'Generated SDK reference for deep API inspection.',
  },
];
