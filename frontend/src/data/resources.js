// Resources page data — single source of truth
// Edit this file to update content across the Resources page

export const pageHeader = {
  title: 'Resources for Builders',
  subtitle: 'Everything you need to build on GenLayer — docs, tools, SDKs, and ecosystem projects in one place.',
};

export const sections = [
  { id: 'getting-started', label: 'Getting Started' },
  { id: 'documentation', label: 'Docs' },
  { id: 'ai-development', label: 'AI Tools' },
  { id: 'bradbury-links', label: 'Bradbury Dev Links' },
  { id: 'ecosystem', label: 'Ecosystem' },
  { id: 'hackathon', label: 'Hackathon' },
  { id: 'how-it-works', label: 'How It Works' },
  { id: 'tracks', label: 'Tracks & Ideas' },
];

export const gettingStarted = {
  tag: 'Recommended',
  title: 'GenLayer Boilerplate',
  description: 'The fastest way to start building on GenLayer. Clone the boilerplate, deploy your first Intelligent Contract, and connect a frontend — all in under 10 minutes.',
  url: 'https://github.com/yeagerai/genlayer-boilerplate',
  ctaLabel: 'View on GitHub',
};

export const documentation = [
  {
    tag: 'Docs',
    title: 'Equivalence Principle',
    description: 'Understand the core concept behind Intelligent Contracts — how GenLayer achieves deterministic results from non-deterministic AI outputs through validator consensus.',
    url: 'https://docs.genlayer.com/concepts/equivalence-principle',
    ctaLabel: 'Read documentation',
  },
  {
    tag: 'Docs',
    title: 'Development Setup & Quickstart',
    description: 'Set up your local environment, install the GenLayer CLI, deploy your first contract, and connect it to a frontend application step by step.',
    url: 'https://docs.genlayer.com/getting-started/setup',
    ctaLabel: 'Read documentation',
  },
];

export const aiDevelopment = [
  {
    tag: 'AI Tooling',
    title: 'Claude Code Skills',
    description: 'Pre-built Claude Code skills that understand GenLayer\'s architecture. Get AI-assisted contract development with context-aware suggestions and best practices.',
    url: 'https://github.com/yeagerai/genlayer-claude-code-skills',
    ctaLabel: 'View on GitHub',
    installSteps: [
      {
        label: 'Install skills',
        command: 'claude install-skills https://github.com/yeagerai/genlayer-claude-code-skills',
      },
    ],
  },
  {
    tag: 'AI Tooling',
    title: 'GenLayer MCP Server',
    description: 'Model Context Protocol server for GenLayer. Connect any MCP-compatible AI assistant to GenLayer\'s documentation, contract templates, and deployment tools.',
    url: 'https://github.com/yeagerai/genlayer-mcp-server',
    ctaLabel: 'View on GitHub',
    installSteps: [
      {
        label: 'Install via npx',
        command: 'npx @anthropic-ai/claude-code mcp add genlayer -- npx -y genlayer-mcp-server',
      },
    ],
  },
];

export const bradburyLinks = {
  network: {
    title: 'Network',
    items: [
      { label: 'JSON-RPC Endpoint', value: 'https://studio-api.genlayer.com/api', copyable: true },
      { label: 'WebSocket', value: 'wss://studio-api.genlayer.com/ws', copyable: true },
      { label: 'Chain ID', value: '61_999', copyable: false },
    ],
  },
  explorers: {
    title: 'Explorers & Tools',
    items: [
      { label: 'GenLayer Explorer', url: 'https://explorer.genlayer.com' },
      { label: 'GenLayer Studio', url: 'https://studio.genlayer.com' },
      { label: 'GenLayer Simulator', url: 'https://simulator.genlayer.com' },
    ],
  },
  sdks: {
    title: 'SDKs & CLI',
    items: [
      {
        label: 'GenLayer JS SDK',
        package: 'genlayer-js',
        version: 'latest',
        installCommand: 'npm install genlayer-js',
        url: 'https://www.npmjs.com/package/genlayer-js',
      },
      {
        label: 'GenLayer Python SDK',
        package: 'genlayer',
        version: 'latest',
        installCommand: 'pip install genlayer',
        url: 'https://pypi.org/project/genlayer/',
      },
      {
        label: 'GenLayer CLI',
        package: 'genlayer-cli',
        version: 'latest',
        installCommand: 'npm install -g genlayer-cli',
        url: 'https://www.npmjs.com/package/genlayer-cli',
      },
    ],
  },
};

export const ecosystemProjects = [
  {
    title: 'Internet Court',
    description: 'Decentralized arbitration platform for dispute resolution with AI-evaluated evidence.',
    url: 'https://internetcourt.org',
    track: 'Onchain Justice',
  },
  {
    title: 'MergeProof',
    description: 'Verified code contribution tracking and proof-of-work for open source developers.',
    url: 'https://mergeproof.com',
    track: 'Future of Work',
  },
  {
    title: 'Molly.fun',
    description: 'Social AI agent platform exploring agent-to-agent economic interactions.',
    url: 'https://molly.fun',
    track: 'Agentic Economy',
  },
  {
    title: 'COFI Bets',
    description: 'On-chain prediction market with AI-resolved outcomes through validator consensus.',
    url: 'https://bet.courtofinternet.com/',
    track: 'Prediction Markets',
  },
  {
    title: 'Rally.fun',
    description: 'Collaborative funding platform for community-driven initiatives and bounties.',
    url: 'https://rally.fun',
    track: 'Future of Work',
  },
  {
    title: 'Argue.fun',
    description: 'Structured debate platform with AI-judged arguments and community voting.',
    url: 'https://argue.fun',
    track: 'AI Governance',
  },
  {
    title: 'P2P Betting',
    description: 'Peer-to-peer betting platform with trustless settlement via Intelligent Contracts.',
    url: 'https://p2p-betting-mu.vercel.app/create',
    track: 'Prediction Markets',
  },
  {
    title: 'Prediction Market Kit',
    description: 'Open-source toolkit for building custom prediction markets on GenLayer.',
    url: 'https://pmkit.courtofinternet.com/',
    track: 'Prediction Markets',
  },
  {
    title: 'Unstoppable',
    description: 'Multiplayer coordination game exploring social dynamics and consensus mechanisms.',
    url: 'https://unstoppable.fun/',
    track: 'AI Gaming',
  },
  {
    title: 'Mochi Quest',
    description: 'Interactive AI game where players navigate consensus-based challenges together.',
    url: 'https://guess-picture.onrender.com/mochi-quest',
    track: 'AI Gaming',
  },
  {
    title: 'Bridge Boilerplate',
    description: 'Connect GenLayer Intelligent Contracts with EVM chains via LayerZero V2. Offload AI reasoning to GenLayer while keeping users and liquidity on Base/Ethereum.',
    url: 'https://github.com/genlayer-foundation/genlayer-studio-bridge-boilerplate',
    track: 'Infrastructure',
  },
  {
    title: 'PM Kit',
    description: 'Fully on-chain prediction market kit with cross-chain bridging, escrow, and trustless resolution via GenLayer validator consensus. Like Limitless, but decentralized.',
    url: 'https://github.com/courtofinternet/pm-kit',
    track: 'Prediction Markets',
  },
];

export const hackathon = {
  title: 'Testnet Bradbury Hackathon',
  subtitle: 'Build Intelligent Contracts with AI consensus',
  highlights: [
    'Builder Points + $5,000 in prizes',
    '6 tracks to choose from',
    'Mentorship & funding opportunities',
  ],
  ctaLabel: 'View Hackathon Details',
  ctaPath: '/hackathon',
};

export const portalInfo = [
  {
    step: 1,
    title: 'Sign Up',
    description: 'Connect your wallet and create your builder profile on the GenLayer Portal.',
    color: 'from-[#f8b93d] to-[#ee8d24]', // orange
  },
  {
    step: 2,
    title: 'Build & Deploy',
    description: 'Write Intelligent Contracts, deploy to Bradbury testnet, and build your frontend.',
    color: 'from-[#6da7f3] to-[#387de8]', // blue
  },
  {
    step: 3,
    title: 'Submit',
    description: 'Submit your contributions through the portal to earn points and climb the leaderboard.',
    color: 'from-[#a77fee] to-[#7f52e1]', // purple
  },
  {
    step: 4,
    title: 'Earn & Rank',
    description: 'Accumulate points, unlock contributions, and rise through the builder ranks.',
    color: 'from-[#3eb359] to-[#2d9a46]', // green
  },
];

export const tracksAndIdeas = [
  {
    title: 'Agentic Economy Infrastructure',
    description: 'Build the infrastructure for AI agents to interact, transact, and coordinate autonomously.',
    gradient: 'from-[#f8b93d] to-[#ee8d24]',
  },
  {
    title: 'AI Governance',
    description: 'AI-driven decisions and coordination between humans and autonomous agents.',
    gradient: 'from-[#6da7f3] to-[#387de8]',
  },
  {
    title: 'Prediction Markets & P2P Betting',
    description: 'Bet, predict, and trade on future outcomes with on-chain markets powered by AI consensus.',
    gradient: 'from-[#a77fee] to-[#7f52e1]',
  },
  {
    title: 'AI Gaming',
    description: 'Multiplayer games exploring coordination, social dynamics, and consensus mechanics.',
    gradient: 'from-[#e85d75] to-[#c94058]',
  },
  {
    title: 'Future of Work',
    description: 'AI-verified deliverables, reputation tracking, and outcome-based payment systems.',
    gradient: 'from-[#3eb359] to-[#2d9a46]',
  },
  {
    title: 'Onchain Justice',
    description: 'Decentralized arbitration with AI-evaluated evidence and fair dispute resolution.',
    gradient: 'from-[#f0923b] to-[#d6721e]',
  },
];
