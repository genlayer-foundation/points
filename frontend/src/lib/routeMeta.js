export const SITE_URL = 'https://portal.genlayer.foundation';
export const SITE_NAME = 'GenLayer Portal';
export const TWITTER_SITE = '@GenLayer';

const ogImage = (fileName) => ({
  src: `${SITE_URL}/assets/og/${fileName}`,
  width: '1200',
  height: '630',
});

export const OG_IMAGES = {
  portal: ogImage('portal.png'),
  howItWorks: ogImage('how-it-works.png'),
  referral: ogImage('referral-program.png'),
  hackathon: ogImage('hackathon.png'),
  hackathonWinners: ogImage('hackathon-winners.png'),
  genesis: ogImage('genesis.png'),
  genesisManifesto: ogImage('genesis-manifesto.png'),
  genesisWhitepaper: ogImage('genesis-whitepaper.png'),
  genesisCompass: ogImage('genesis-compass.png'),
  genTv: ogImage('gen-tv.png'),
  genNews: ogImage('gen-news.png'),
  ecosystemPartners: ogImage('ecosystem-partners.png'),
  buildersResources: ogImage('builders-resources.png'),
  builderProject: ogImage('builder-project.png'),
  communityPoaps: ogImage('community-poaps.png'),
  participants: ogImage('participants.png'),
  validatorsParticipants: ogImage('validators-participants.png'),
  validatorsWaitlist: ogImage('validators-waitlist.png'),
  validatorsWallOfShame: ogImage('validators-wall-of-shame.png'),
  termsOfUse: ogImage('terms-of-use.png'),
  privacyPolicy: ogImage('privacy-policy.png'),
};

export const DEFAULT_META = {
  title: 'GenLayer Portal',
  description:
    'Track GenLayer contributions, points, validators, builders, community activity, events, and ecosystem programs.',
  image: OG_IMAGES.portal.src,
  imageWidth: OG_IMAGES.portal.width,
  imageHeight: OG_IMAGES.portal.height,
  url: `${SITE_URL}/`,
};

export const ROUTE_META = {
  '/': DEFAULT_META,
  '/how-it-works': {
    title: 'How GenLayer Portal Works',
    description:
      'Learn how GenLayer Portal connects builders, validators, and community contributors through points, missions, referrals, and ecosystem programs.',
    image: OG_IMAGES.howItWorks.src,
    imageWidth: OG_IMAGES.howItWorks.width,
    imageHeight: OG_IMAGES.howItWorks.height,
  },
  '/referral-program': {
    title: 'GenLayer Referral Program',
    description:
      'Invite builders and validators to GenLayer. Earn 10% of eligible builder and validator contribution points forever, with no cap.',
    image: OG_IMAGES.referral.src,
    imageWidth: OG_IMAGES.referral.width,
    imageHeight: OG_IMAGES.referral.height,
  },
  '/hackathon': {
    title: 'Testnet Bradbury Hackathon',
    description:
      'Build on GenLayer Testnet Bradbury. Compete for prizes and Builder Points by shipping AI-native applications and Intelligent Contracts.',
    image: OG_IMAGES.hackathon.src,
    imageWidth: OG_IMAGES.hackathon.width,
    imageHeight: OG_IMAGES.hackathon.height,
  },
  '/hackathon-winners': {
    title: 'Hackathon Winners - Testnet Bradbury',
    description:
      "Meet the winners of GenLayer's Testnet Bradbury Hackathon: 135 BUIDLs, 280 hackers, and two weeks of AI-native building.",
    image: OG_IMAGES.hackathonWinners.src,
    imageWidth: OG_IMAGES.hackathonWinners.width,
    imageHeight: OG_IMAGES.hackathonWinners.height,
  },
  '/genesis': {
    title: 'GenLayer Genesis',
    description:
      'Explore the GenLayer Genesis essays on trust, AI-mediated judgment, and the infrastructure needed for commerce between humans and machines.',
    image: OG_IMAGES.genesis.src,
    imageWidth: OG_IMAGES.genesis.width,
    imageHeight: OG_IMAGES.genesis.height,
  },
  '/genesis/manifesto': {
    title: 'GenLayer Manifesto',
    description:
      'Read the GenLayer manifesto on trust, decentralization, and why AI-native adjudication needs open infrastructure.',
    image: OG_IMAGES.genesisManifesto.src,
    imageWidth: OG_IMAGES.genesisManifesto.width,
    imageHeight: OG_IMAGES.genesisManifesto.height,
  },
  '/genesis/whitepaper': {
    title: 'GenLayer Whitepaper',
    description:
      'Read the GenLayer whitepaper and technical framing for AI-powered smart contracts, subjective consensus, and decentralized judgment.',
    image: OG_IMAGES.genesisWhitepaper.src,
    imageWidth: OG_IMAGES.genesisWhitepaper.width,
    imageHeight: OG_IMAGES.genesisWhitepaper.height,
  },
  '/genesis/compass': {
    title: 'GenLayer Compass',
    description:
      'A strategic map of the agentic-commerce stack and the trust infrastructure GenLayer is building for AI-native coordination.',
    image: OG_IMAGES.genesisCompass.src,
    imageWidth: OG_IMAGES.genesisCompass.width,
    imageHeight: OG_IMAGES.genesisCompass.height,
  },
  '/gen-tv': {
    title: 'GenTV',
    description:
      'Watch GenLayer streams, ecosystem conversations, builder sessions, and community programming from the GenLayer network.',
    image: OG_IMAGES.genTv.src,
    imageWidth: OG_IMAGES.genTv.width,
    imageHeight: OG_IMAGES.genTv.height,
  },
  '/gen-news': {
    title: 'GenLayer News',
    description:
      'Follow GenLayer updates, ecosystem news, builder highlights, and community announcements from across the network.',
    image: OG_IMAGES.genNews.src,
    imageWidth: OG_IMAGES.genNews.width,
    imageHeight: OG_IMAGES.genNews.height,
  },
  '/ecosystem-partners': {
    title: 'GenLayer Ecosystem Partners',
    description:
      'Discover projects, validators, partners, and builders contributing to the GenLayer ecosystem.',
    image: OG_IMAGES.ecosystemPartners.src,
    imageWidth: OG_IMAGES.ecosystemPartners.width,
    imageHeight: OG_IMAGES.ecosystemPartners.height,
  },
  '/builders/resources': {
    title: 'GenLayer Builder Resources',
    description:
      'Find GenLayer builder resources, references, tools, and examples for shipping AI-native applications and Intelligent Contracts.',
    image: OG_IMAGES.buildersResources.src,
    imageWidth: OG_IMAGES.buildersResources.width,
    imageHeight: OG_IMAGES.buildersResources.height,
  },
  '/builders/projects/:slug': {
    title: 'GenLayer Builder Project',
    description:
      'Explore a builder project in the GenLayer ecosystem, including its overview, milestones, media, and accepted contributions.',
    image: OG_IMAGES.builderProject.src,
    imageWidth: OG_IMAGES.builderProject.width,
    imageHeight: OG_IMAGES.builderProject.height,
  },
  '/community/poaps': {
    title: 'GenLayer Community POAPs',
    description:
      'Explore GenLayer community POAPs, badges, and collectible moments from events, campaigns, and ecosystem participation.',
    image: OG_IMAGES.communityPoaps.src,
    imageWidth: OG_IMAGES.communityPoaps.width,
    imageHeight: OG_IMAGES.communityPoaps.height,
  },
  '/participants': {
    title: 'GenLayer Participants',
    description:
      'Browse GenLayer participants, validator operators, and ecosystem contributors across the Portal.',
    image: OG_IMAGES.participants.src,
    imageWidth: OG_IMAGES.participants.width,
    imageHeight: OG_IMAGES.participants.height,
  },
  '/validators/participants': {
    title: 'GenLayer Validator Participants',
    description:
      'Browse validator participants and operators contributing to GenLayer testnets and network reliability.',
    image: OG_IMAGES.validatorsParticipants.src,
    imageWidth: OG_IMAGES.validatorsParticipants.width,
    imageHeight: OG_IMAGES.validatorsParticipants.height,
  },
  '/validators/waitlist/join': {
    title: 'Join the GenLayer Validator Waitlist',
    description:
      'Apply to join the GenLayer validator waitlist and prepare to contribute to testnet operations and network reliability.',
    image: OG_IMAGES.validatorsWaitlist.src,
    imageWidth: OG_IMAGES.validatorsWaitlist.width,
    imageHeight: OG_IMAGES.validatorsWaitlist.height,
  },
  '/validators/wall-of-shame': {
    title: 'GenLayer Validator Wall of Shame',
    description:
      'Track validator uptime issues and reliability signals from GenLayer testnet participation.',
    image: OG_IMAGES.validatorsWallOfShame.src,
    imageWidth: OG_IMAGES.validatorsWallOfShame.width,
    imageHeight: OG_IMAGES.validatorsWallOfShame.height,
  },
  '/terms-of-use': {
    title: 'GenLayer Portal Terms of Use',
    description:
      'Review the terms that govern access to and use of GenLayer Portal and related services.',
    image: OG_IMAGES.termsOfUse.src,
    imageWidth: OG_IMAGES.termsOfUse.width,
    imageHeight: OG_IMAGES.termsOfUse.height,
  },
  '/privacy-policy': {
    title: 'GenLayer Portal Privacy Policy',
    description:
      'Review how GenLayer Portal handles privacy, personal information, and related data practices.',
    image: OG_IMAGES.privacyPolicy.src,
    imageWidth: OG_IMAGES.privacyPolicy.width,
    imageHeight: OG_IMAGES.privacyPolicy.height,
  },
};

export const ROUTE_META_ALIASES = {
  '/foundations': '/genesis',
  '/foundations/manifesto': '/genesis/manifesto',
  '/foundations/whitepaper': '/genesis/whitepaper',
  '/foundations/compass': '/genesis/compass',
  '/manifesto': '/genesis/manifesto',
};

export const STATIC_OG_ROUTES = [
  '/how-it-works',
  '/referral-program',
  '/hackathon',
  '/hackathon-winners',
  '/genesis',
  '/genesis/manifesto',
  '/genesis/whitepaper',
  '/genesis/compass',
  '/gen-tv',
  '/gen-news',
  '/ecosystem-partners',
  '/builders/resources',
  '/community/poaps',
  '/participants',
  '/validators/participants',
  '/validators/waitlist/join',
  '/validators/wall-of-shame',
  '/terms-of-use',
  '/privacy-policy',
];

function normalizeRoutePath(path) {
  const raw = path || '/';
  const withoutQuery = raw.split('?')[0].split('#')[0] || '/';
  if (withoutQuery.length > 1) {
    return withoutQuery.replace(/\/+$/, '');
  }
  return withoutQuery;
}

export function resolveRouteMeta(path = '/') {
  const normalized = normalizeRoutePath(path);
  const aliasTarget = ROUTE_META_ALIASES[normalized];
  const key = aliasTarget || normalized;

  if (ROUTE_META[key]) {
    return {
      ...DEFAULT_META,
      ...ROUTE_META[key],
      url: ROUTE_META[key].url || `${SITE_URL}${key === '/' ? '/' : key}`,
    };
  }

  if (normalized.startsWith('/builders/projects/')) {
    return {
      ...DEFAULT_META,
      ...ROUTE_META['/builders/projects/:slug'],
      url: `${SITE_URL}${normalized}`,
    };
  }

  return DEFAULT_META;
}
