// Resources page data — single source of truth (builder-focused)
// Edit this file to update content across the Resources page

export const pageHeader = {
  title: 'Builder Resources',
  subtitle: 'Everything you need to build on GenLayer.',
};

export const communityLinks = [
  { label: 'Discord', url: 'https://discord.gg/8Jm4v89VAu', color: '#5865F2' },
  { label: 'Telegram', url: 'https://t.me/genlayer', color: '#26A5E4' },
  { label: 'X', url: 'https://x.com/GenLayer', color: '#000000' },
  { label: 'YouTube', url: 'https://www.youtube.com/@GenLayer', color: '#FF0000' },
];

export const sdks = [
  { label: 'JavaScript SDK', url: 'https://www.npmjs.com/package/genlayer-js', icon: 'js' },
  { label: 'Python SDK', url: 'https://pypi.org/project/genlayer-py/', icon: 'python' },
  { label: 'GenLayer CLI', url: 'https://docs.genlayer.com/developers/intelligent-contracts/tools/genlayer-cli', icon: 'cli' },
];

export const documentation = [
  { label: 'Developer Documentation', url: 'https://docs.genlayer.com/developers', description: 'Full reference for Intelligent Contracts, SDKs, and developer tools', icon: 'docs' },
  { label: 'Equivalence Principle', url: 'https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle', description: 'How non-deterministic operations reach consensus across validators', icon: 'eq' },
  { label: 'Python SDK API Reference', url: 'https://sdk.genlayer.com/main/api/index.html', description: 'Complete API reference for the Python SDK', icon: 'api' },
];

export const boilerplates = [
  { label: 'Project Boilerplate', url: 'https://github.com/genlayerlabs/genlayer-project-boilerplate', description: 'Starter template — clone, deploy a contract, and connect a frontend' },
  { label: 'Bridge Boilerplate', url: 'https://github.com/genlayer-foundation/genlayer-studio-bridge-boilerplate', description: 'Bridge integration starter for cross-chain transfers' },
  { label: 'Prediction Market Kit', url: 'https://github.com/courtofinternet/pm-kit', description: 'Full prediction market template powered by AI consensus' },
];

export const tools = [
  { label: 'GenLayer Studio', url: 'https://studio.genlayer.com', description: 'Browser IDE for writing, testing, and deploying Intelligent Contracts' },
  { label: 'Testnet Faucet', url: 'https://testnet-faucet.genlayer.foundation/', description: 'Claim 100 GEN tokens per day on Asimov or Bradbury testnets' },
  { label: 'Asimov Explorer', url: 'https://explorer-asimov.genlayer.com', description: 'Browse transactions and contracts on testnet Asimov' },
  { label: 'Bradbury Explorer', url: 'https://explorer-bradbury.genlayer.com', description: 'Browse transactions and contracts on testnet Bradbury' },
];

export const aiResources = {
  links: [
    { label: 'Python SDK API (LLM-friendly)', url: 'https://sdk.genlayer.com/main/_static/ai/api.txt', description: 'Plain-text API reference optimized for LLM consumption' },
    { label: 'Claude Code Skills', url: 'https://skills.genlayer.com', description: 'AI skills for writing, linting, testing, and deploying contracts' },
  ],
  metaprompt: `You are a GenLayer developer assistant. GenLayer is an L2 blockchain (ZKSync-based rollup) where Intelligent Contracts — Python classes inheriting from gl.Contract — can natively call LLMs and access the web.

## What are Intelligent Contracts?
Intelligent Contracts are Python smart contracts that go beyond traditional deterministic logic. They can call LLMs, fetch web data, and process unstructured information — all while maintaining blockchain consensus. Contracts inherit from gl.Contract, use @gl.public.write for state-changing methods and @gl.public.view for read-only methods. Storage uses TreeMap (key-value), DynArray (dynamic arrays), and u256 (integers). Raise UserError for user-facing failures.

## The Equivalence Principle
The core consensus mechanism for non-deterministic operations. A leader node executes an operation and proposes a result. Validators independently verify whether that result is acceptable — majority acceptance means consensus.
- gl.eq_principle.strict_eq — exact match (for deterministic APIs like RPCs)
- gl.eq_principle.prompt_comparative — LLM judges if two outputs are equivalent
- gl.eq_principle.prompt_non_comparative — LLM validates leader result directly
- gl.vm.run_nondet_unsafe — custom validator logic (most common in real contracts)
Always extract structured data before comparing. Raw web/LLM output varies across nodes.

## Development Tools
- GenLayer Studio (https://studio.genlayer.com): Browser IDE for writing, testing, and deploying contracts
- GenLayer CLI: Terminal tool for scaffolding, deploying, and interacting with contracts
- Faucet (https://testnet-faucet.genlayer.foundation/): Get 100 GEN tokens/day on testnets

## Active Testnets
- Asimov: Explorer at https://explorer-asimov.genlayer.com
- Bradbury: Explorer at https://explorer-bradbury.genlayer.com

## Key References
- Documentation: https://docs.genlayer.com/developers
- Equivalence Principle: https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- Python SDK full API: https://sdk.genlayer.com/main/_static/ai/api.txt
- JS SDK: https://www.npmjs.com/package/genlayer-js
- Python SDK: https://pypi.org/project/genlayer-py/
- GenLayer CLI: https://docs.genlayer.com/developers/intelligent-contracts/tools/genlayer-cli
- Project Boilerplate: https://github.com/genlayerlabs/genlayer-project-boilerplate
- Bridge Boilerplate: https://github.com/genlayer-foundation/genlayer-studio-bridge-boilerplate
- Prediction Market Kit: https://github.com/courtofinternet/pm-kit
- Claude Code Skills: https://skills.genlayer.com (write, lint, test, deploy contracts via AI)`,
};

export const tracksAndIdeas = [
  {
    title: 'Agentic Economy Infrastructure',
    description: 'Build the infrastructure for AI agents to interact, transact, and coordinate autonomously.',
    color: '#ee8521',
  },
  {
    title: 'AI Governance',
    description: 'AI-driven decisions and coordination between humans and autonomous agents.',
    color: '#387de8',
  },
  {
    title: 'Prediction Markets & P2P Betting',
    description: 'Bet, predict, and trade on future outcomes with on-chain markets powered by AI consensus.',
    color: '#7f52e1',
  },
  {
    title: 'AI Gaming',
    description: 'Multiplayer games exploring coordination, social dynamics, and consensus mechanics.',
    color: '#c94058',
  },
  {
    title: 'Future of Work',
    description: 'AI-verified deliverables, reputation tracking, and outcome-based payment systems.',
    color: '#3eb359',
  },
  {
    title: 'Onchain Justice',
    description: 'Decentralized arbitration with AI-evaluated evidence and fair dispute resolution.',
    color: '#d6721e',
  },
];
