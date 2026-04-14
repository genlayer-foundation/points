// Hackathon Winners Data
// All data is hardcoded. Images are hosted on Cloudinary.
// Update this file with real winner data and Cloudinary URLs.

export const hackathonStats = [
  { value: '135', label: 'BUIDLs' },
  { value: '280', label: 'Hackers' },
  { value: '2 Weeks', label: 'Duration' },
];

export const trackSubmissions = [
  { name: 'Agentic Economy Infrastructure', count: 26 },
  { name: 'Subjective Consensus (Bradbury Special)', count: 24 },
  { name: 'Prediction Markets & P2P Betting', count: 21 },
  { name: 'Onchain Justice', count: 19 },
  { name: 'AI Gaming', count: 16 },
  { name: 'Future of Work', count: 15 },
  { name: 'AI Governance', count: 14 },
];

export const grandWinner = {
  name: 'BuildersClaw',
  builder: 'luchoo_eth, FedeTavano, martinpuli',
  avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103540/buildersclaw-logo_fhlv2d.jpg',
  screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103539/buildersclaw-bg_dpt9ig.png',
  category: 'Agentic Economy Infrastructure',
  descriptionIntro: 'BuildersClaw connects companies that need real code with builders ready to ship it. Companies post coding challenges with prize money, and builders compete by submitting working solutions through AI agents.',
  descriptionBullets: [
    'A GenLayer intelligent contract evaluates every submission automatically, scoring code against challenge requirements through multi-validator consensus.',
    'Smart contracts handle escrow and payouts. Funds are locked when a challenge is created and released to the winner once judging is complete.',
    'All judging happens on-chain and is fully verifiable. No human panel, no subjective opinions. The best code wins on merit.',
  ],
  links: {
    project: 'https://dorahacks.io/buidl/41425',
    youtube: 'https://www.youtube.com/watch?v=p3NGRS7TzF8',
    github: 'https://github.com/buildersclaw/buildersclaw',
    website: 'https://buildersclaw.xyz',
    twitter: ['https://x.com/buildersclaw'],
  },
};

export const trackWinners = [
  {
    name: 'Reasoned Judgment Protocol',
    builder: 'JadedOne',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103547/rjp-bg_vz6cmw.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103547/rjp-bg_vz6cmw.png',
    category: 'Subjective Consensus',
    description: 'Before your wallet interacts with a stranger on-chain, this protocol checks their history and tells you if they are safe. GenLayer validators evaluate wallet behavior and produce auditable trust judgments that smart contracts and AI agents can read before making decisions.',
    links: {
      project: 'https://dorahacks.io/buidl/42237',
      youtube: 'https://youtu.be/RK0Qkhc6nUU',
      github: 'https://github.com/Jaydearcadian/RJP',
      website: 'https://rjp-xi.vercel.app',
      twitter: ['https://x.com/Jaydearcadian'],
    },
  },
  {
    name: 'Verdictdotfun',
    builder: 'jrkenny',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103549/verdictdotfun-bg_jgzojh.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776105099/verdict-bg_jud622.png',
    category: 'AI Gaming',
    description: 'An online gaming platform where GenLayer intelligent contracts act as AI referees, settling every dispute through on-chain consensus. No centralized game server, no admin override, just verifiable fair play.',
    links: {
      project: 'https://dorahacks.io/buidl/42213',
      youtube: 'https://youtu.be/x1yhXUrbaiw',
      github: 'https://github.com/Jr-kenny/verdictdotfun',
      website: 'https://verdictdotfun.vercel.app',
      twitter: ['https://x.com/Jrken_ny'],
    },
  },
  {
    name: 'TreasuryPilot',
    builder: 'sandragcarrillo, carlaupgrade',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103548/treasurypilot-bg_ibxy7e.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776105098/treasury-bg_vtb5tf.png',
    category: 'AI Governance',
    description: 'A Telegram bot that helps DAOs manage their treasury. Every time someone proposes spending community funds, a GenLayer intelligent contract checks it against the rules the community wrote and flags anything that does not fit.',
    links: {
      project: 'https://dorahacks.io/buidl/41321',
      youtube: 'https://youtu.be/E6rBd6v_hRg',
      github: 'https://github.com/sandragcarrillo/TreasuryPilot',
      website: 'https://treasury-pilot-frontend.vercel.app',
      twitter: ['https://x.com/sandraupgrade', 'https://x.com/carlaupgrade'],
    },
  },
  {
    name: 'Proven',
    builder: 'EstebanBM, hugohise, ivan_sarapura, RobGT0',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103546/proven-logo_olm9ts.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103546/proven-bg_jhylzq.png',
    category: 'Prediction Markets & P2P Betting',
    description: 'Pick a friend, pick a topic, bet on who is right. GenLayer validators go out, fetch real sources from the web, and reach consensus on who won. No central oracle, no house edge, just peer-to-peer bets settled by AI.',
    links: {
      project: 'https://dorahacks.io/buidl/41409',
      youtube: 'https://youtu.be/MCj9ObSz4EQ',
      github: 'https://github.com/proven-xyz/proven-app',
      website: 'https://proven-app.vercel.app',
      twitter: ['https://x.com/ProvenXYZ'],
    },
  },
  {
    name: 'Gotham Court',
    builder: 'kiter',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103543/gotham-logo_awbdhl.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776105095/gotham-bg_vet0ij.png',
    category: 'Onchain Justice',
    description: 'Submit your evidence, the other side submits theirs, and a GenLayer intelligent contract reads both sides to deliver a verdict. On-chain arbitration for disputes that today have nowhere to go.',
    links: {
      project: 'https://dorahacks.io/buidl/41898',
      youtube: 'https://youtu.be/uQZI4d_DJj0',
      github: 'https://github.com/PhiBao/gotham-court',
      website: 'https://gotham-court-frontend.vercel.app',
      twitter: null,
    },
  },
  {
    name: 'AutoBounty',
    builder: 'artugrande, tomazzi14',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103538/autobounty-logo_nyjgl8.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776105096/autobounty-bg_nyoylr.png',
    category: 'Future of Work',
    description: 'Post a coding bounty, a developer submits a pull request, and a GenLayer intelligent contract reads the actual code on GitHub to verify the work was done before releasing USDC payment on Avalanche. Already live with real money.',
    links: {
      project: 'https://dorahacks.io/buidl/42260',
      youtube: 'https://www.youtube.com/watch?v=THBYivw17ig',
      github: 'https://github.com/tomazzi14/AutoBounty',
      website: 'https://auto-bounty.vercel.app',
      twitter: ['https://x.com/ArtuGrande', 'https://x.com/tomasmazz'],
    },
  },
];

export const honorableMentions = [
  {
    name: 'Agent Escrow',
    builder: 'emark',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103535/agentescrow-logo_llhyil.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776104830/agentescrow-bg_uzfsmm.png',
    category: 'Agentic Economy Infrastructure',
    awardLabel: 'Best GenLayer Fit',
    description: 'Built for a world where AI agents hire other AI agents. GenLayer intelligent contracts hold the escrow and, if the agents disagree on whether the job was done, an on-chain Internet Court resolves it through AI consensus.',
    links: {
      project: 'https://dorahacks.io/buidl/42088',
      youtube: 'https://youtu.be/oZ8vxWi1xcc',
      github: 'https://github.com/emark-cloud/agent_escrow',
      website: 'https://agentescrow-nu.vercel.app/',
      twitter: ['https://x.com/emark2_0'],
    },
  },
  {
    name: 'Apolo',
    builder: 'lilyet',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103536/apolo-logo_d5ulzf.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103536/apolo-bg_q2bzww.png',
    category: 'Future of Work',
    awardLabel: 'Best Market Potential',
    description: 'A freelance payment system where money only moves when the job is provably complete. A GenLayer intelligent contract checks real-world delivery conditions against web evidence before releasing funds. Already live on BNB Chain with real transactions.',
    links: {
      project: 'https://dorahacks.io/buidl/41345',
      youtube: 'https://youtu.be/DL5UfbESZNo',
      github: 'https://github.com/DarienPerezGit/Apolo',
      website: 'https://project-apolo.vercel.app/',
      twitter: ['https://x.com/_A_polo__'],
    },
  },
  {
    name: 'Callit',
    builder: 'enochlee, heywole',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103541/callit-logo_m83whg.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776104876/callit-bg_gzepry.png',
    category: 'Prediction Markets & P2P Betting',
    awardLabel: 'Best Implementation',
    description: 'A prediction market where GenLayer handles four stages of AI consensus, from deciding which markets are valid to resolving who won, while your funds sit safely on a separate Base chain until the outcome is final.',
    links: {
      project: 'https://dorahacks.io/buidl/42252',
      youtube: 'https://www.youtube.com/watch?v=ZbQ-ym-NRNE',
      github: 'https://github.com/enochakinbode/callit',
      website: 'https://callit-genlayer.vercel.app/',
      twitter: ['https://x.com/enochakinbode'],
    },
  },
  {
    name: 'WindfallRouter',
    builder: 'papa_raw, unjoursurterre',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103551/windfall-logo_rksubc.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103550/windfall-bg_jegkrd.png',
    category: 'Subjective Consensus',
    awardLabel: 'Best Originality',
    description: 'Routes transactions through the most energy-efficient path by using GenLayer consensus to evaluate the carbon impact of different execution routes. Sustainability meets blockchain infrastructure.',
    links: {
      project: 'https://dorahacks.io/buidl/42113',
      youtube: 'https://youtu.be/osp92rHhZ6k',
      github: 'https://github.com/Ecofrontiers/genlayer-hackathon',
      website: 'https://frontend-ecofrontiers.vercel.app/',
      twitter: ['https://x.com/ecofrontiers'],
    },
  },
  {
    name: 'PRISMA',
    builder: 'RonaldGaymer, kenyi001, Vctor11180',
    avatar: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103544/prisma-logo_nxismq.png',
    screenshot: 'https://res.cloudinary.com/dfqmoeawa/image/upload/v1776103544/prisma-bg_hmb3ng.png',
    category: 'Subjective Consensus',
    awardLabel: 'Best Presentation & UX',
    description: 'Turns raw blockchain wallet activity into clean, visual audit reports that anyone can understand. GenLayer consensus validates the financial analysis, bringing transparency to on-chain data.',
    links: {
      project: 'https://dorahacks.io/buidl/42215',
      youtube: 'https://www.youtube.com/watch?v=E610vqElNU4',
      github: 'https://github.com/Kenyi001/ledgerlens',
      website: 'https://ledgerlens-backend.vercel.app/',
      twitter: ['https://x.com/RG_Ronald_A'],
    },
  },
];

export const winnersSponsors = [
  { name: 'Chutes', url: 'https://chutes.ai', bg: '#131313' },
  { name: 'Pathrock Network', url: 'https://pathrocknetwork.org', bg: '#ffffff' },
  { name: 'StakeMe', url: 'https://stakeme.pro', bg: '#ffffff' },
  { name: 'Crouton Digital', url: 'https://crouton.digital', bg: '#ffffff' },
];
