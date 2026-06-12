<script>
  import FoundationsShell from '../components/foundations/FoundationsShell.svelte';

  const TOC = [
    {
      id: 'state-of-the-art',
      num: '00',
      label: 'State of the Art',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
    },
    {
      id: 'worldview',
      num: '01',
      label: 'Worldview',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    },
    {
      id: 'concept',
      num: '02',
      label: 'Concept',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>',
    },
    {
      id: 'what-is-genlayer',
      num: '03',
      label: 'What is GenLayer?',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    },
    {
      id: 'history',
      num: '04',
      label: 'History',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    },
    {
      id: 'pillars',
      num: '05',
      label: 'Strategic Pillars',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="21" x2="4" y2="9"/><line x1="9" y1="21" x2="9" y2="6"/><line x1="14" y1="21" x2="14" y2="9"/><line x1="19" y1="21" x2="19" y2="6"/><line x1="2" y1="21" x2="22" y2="21"/><line x1="2" y1="4" x2="22" y2="4"/></svg>',
    },
    {
      id: 'mission',
      num: '06',
      label: 'Mission',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    },
    {
      id: 'bibliography',
      num: '07',
      label: 'Bibliography',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    },
  ];

  const TOPBAR = [
    { kind: 'section', id: 'state-of-the-art', label: '00 State of the Art' },
    { kind: 'section', id: 'worldview', label: '01 Worldview' },
    { kind: 'section', id: 'concept', label: '02 Concept' },
    { kind: 'section', id: 'what-is-genlayer', label: '03 What is GenLayer?' },
    { kind: 'section', id: 'history', label: '04 History' },
    { kind: 'section', id: 'pillars', label: '05 Pillars' },
    { kind: 'section', id: 'mission', label: '06 Mission' },
    { kind: 'section', id: 'bibliography', label: '07 Bibliography' },
    { kind: 'doc', key: 'manifesto', label: 'Manifesto' },
    { kind: 'doc', key: 'whitepaper', label: 'Whitepaper' },
  ];

  function scrollToStart(e) {
    e.preventDefault();
    document.getElementById('state-of-the-art')?.scrollIntoView({ behavior: 'smooth' });
  }
</script>

<FoundationsShell current="compass" toc={TOC} tocTitle="On this page" topbarBrand="Compass" topbarItems={TOPBAR}>
  <div class="fd-page">
    <div class="shell">
      <!-- HERO -->
      <header class="hero">
        <div class="hero-grid" aria-hidden="true"></div>
        <span class="chip"><span class="dot"></span>The GenLayer Compass</span>
        <h1>The adjudication layer for the <em>agentic economy</em></h1>
        <p class="hero-lede">GenLayer uses decentralized AI validator consensus to resolve contracts that require judgment, not just code. This is the missing piece of infrastructure for the agentic economy.</p>
        <div class="hero-actions">
          <a class="btn-hero" href="#/foundations/manifesto">Read the manifesto
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
          </a>
          <a class="btn-ghost" href="#state-of-the-art" onclick={scrollToStart}>Start reading</a>
        </div>
      </header>

      <!-- BENTO STAT TILES — set 1 -->
      <section class="bento reveal-stagger" aria-label="Key figures">
        <div class="stat stat-dark stat-wide">
          <span class="stat-eyebrow">Agentic economy</span>
          <span class="stat-num">$9T by 2030</span>
          <span class="stat-label">The size of the agentic economy projected by Cathie Wood at ARK Invest.</span>
        </div>
        <div class="stat">
          <span class="stat-eyebrow">US civil disputes</span>
          <span class="stat-num">344 days</span>
          <span class="stat-label">Average resolution time for complex civil disputes in the U.S. legal system.</span>
        </div>
        <div class="stat stat-lav">
          <span class="stat-eyebrow">International average</span>
          <span class="stat-num">657 days</span>
          <span class="stat-label">The international average resolution time &mdash; latency designed for human speed.</span>
        </div>
      </section>

      <!-- 00 STATE OF THE ART -->
      <section class="ed-section reveal" id="state-of-the-art">
        <div class="ed-aside">
          <span class="sec-badge">Section 00</span>
          <h2>State of the Art &amp; Executive Summary</h2>
          <p class="sec-lede">The agentic stack is being built in public. Payments, identity, interoperability: every layer assumes the happy path. None of them handles the moment something goes wrong. That missing piece is adjudication.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <blockquote class="pull">Every layer assumes the happy path. None handles the moment something goes wrong.</blockquote>
            <p>Read the specifications of the agentic-commerce stack as it is being released right now. x402 has no formal dispute mechanism. ERC-8004: adjudication is managed by specific validation protocols. A2A: dispute resolution is not defined within the protocol.</p>
            <p>These are not opinions. They are the published specifications of three foundational standards of the emerging stack: the payment layer (Coinbase&rsquo;s x402), the trustless-agent identity and reputation layer (ERC-8004), and the agent interoperability layer (Google&rsquo;s A2A, now under the Linux Foundation). Read them. Notice what is missing.</p>

            <p>GenLayer is the adjudication layer for the agentic-commerce stack: machine-speed judgment when a transaction becomes ambiguous or contested. Internet Court &mdash; one of our own initiatives &mdash; is the open standard and agent skill that connects these layers into a full transaction path: discovery, negotiation, contracts, payment, escrow, execution, verification, and disputes, with GenLayer as its adjudication layer.</p>

            <div class="diagram">
              <div class="diagram-title">The agentic-commerce stack, 2026</div>
              <div class="ic-diagram">
                <div class="ic-bracket">
                  <span class="ic-bracket-label">Internet Court</span>
                  <span class="ic-bracket-sub">Open standard &middot; agent skill</span>
                </div>
                <div class="ic-stack">
                  <div class="ic-row">
                    <span class="ic-no">01</span>
                    <div class="ic-block"><span class="ic-name">Discovery, identity &amp; reputation</span><span class="ic-std">ERC-7857 &middot; ERC-8004</span></div>
                  </div>
                  <div class="ic-row">
                    <span class="ic-no">02</span>
                    <div class="ic-block"><span class="ic-name">Negotiation</span><span class="ic-std">A2A</span></div>
                  </div>
                  <div class="ic-row">
                    <span class="ic-no">03</span>
                    <div class="ic-block"><span class="ic-name">Contracts &amp; obligations</span><span class="ic-std">ERC-7710 &middot; ERC-8183 &middot; Arkhai</span></div>
                  </div>
                  <div class="ic-row">
                    <span class="ic-no">04</span>
                    <div class="ic-block"><span class="ic-name">Payment &amp; escrow</span><span class="ic-std">x402 &middot; MPP &middot; APP</span></div>
                  </div>
                  <div class="ic-row">
                    <span class="ic-no">05</span>
                    <div class="ic-block"><span class="ic-name">Execution</span><span class="ic-std">OpenClaw &middot; Hermes</span></div>
                  </div>
                  <div class="ic-row ic-row-genlayer">
                    <span class="ic-no">06</span>
                    <div class="ic-block"><span class="ic-name">Verification &amp; disputes</span><span class="ic-std"><strong>GenLayer</strong> &middot; Kleros &middot; UMA</span></div>
                    <span class="ic-tag">GenLayer &mdash; the judgment layer</span>
                  </div>
                </div>
              </div>
              <p class="diagram-cap">GenLayer is the adjudication layer that makes the stack safe when something goes wrong. Internet Court connects the full path around it.</p>
            </div>
            <p>Every layer of the stack has been engineered with extraordinary care to handle the moment when everything goes right. None of the layers handles the moment when something goes wrong. The payment goes through. The job is accepted. The reputation is updated. The identity is established. And then a single dispute appears &mdash; over a delivered specification, an interpreted clause, a missed deadline &mdash; and the entire stack reaches for a function it does not yet have.</p>
            <p>That function is <strong>adjudication</strong>. Not adjudication in the narrow courtroom sense. Not a sovereign court. Not a replacement for every legal system. Adjudication in the deeper sense: a credible mechanism for evaluating contested commitments, weighing evidence, interpreting language, reaching a judgment, and attaching consequences to it.</p>
            <p>By 2030, AI agents will be running businesses, managing portfolios, signing contracts, and making deals at a velocity and volume the existing legal system cannot survive. They will outnumber human transactors by orders of magnitude. They will negotiate across jurisdictions that do not recognize their existence. They will disagree. They will disagree at machine speed. They will disagree about things that matter. And when they do, they will find that the system that was supposed to resolve their disagreements was built for parties with bodies, addresses, and a finite tolerance for waiting.</p>
            <p>The agents have none of those.</p>
            <p>This is the missing piece. This is the gap. GenLayer was built to close it, by providing the adjudication layer for the agentic economy.</p>
          </div>
        </div>
      </section>

      <!-- 01 WORLDVIEW -->
      <section class="ed-section reveal" id="worldview">
        <div class="ed-aside">
          <span class="sec-badge">Section 01</span>
          <h2>Worldview / Cosmovision</h2>
          <p class="sec-lede">Trust is the oldest technology humans ever built. It has evolved through layers, from personal memory to cryptographic proof. Now a seventh is needed: AI-mediated judgment at machine speed.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <h3>The technology we forgot we invented</h3>
            <p>There is a sentence at the heart of every meaningful exchange in human history. <em>I trust you.</em> It is the most valuable sentence in business and in love. It clears friction. It unlocks credit. It compresses due diligence. It makes cooperation feel inevitable. It is also the most fragile sentence we know how to say, because the moment it is said, the speaker hands a piece of their uncertainty over to someone else and stands exposed. Trusting means becoming vulnerable.</p>
            <p>We call this &ldquo;trust&rdquo;, but the word obscures what it actually is. Trust is not a feeling. It is a technology &mdash; a piece of social machinery that human beings have been quietly engineering for the entire history of our species. The German sociologist Niklas Luhmann, in his 1968 monograph <em>Vertrauen</em>, put it most precisely: trust is &ldquo;a mechanism for the reduction of social complexity.&rdquo; It is the operating system that makes action possible in a world too complicated to verify in full.</p>
            <p>Without trust, life becomes computationally intractable. Every breakfast becomes a negotiation. Every transaction becomes a lawsuit. Every stranger becomes a threat. Trust is what lets us put down our defenses long enough to build anything at all. And like any technology, trust evolves.</p>

            <h3>The physics of trust</h3>
            <p>Trust is what you fall back on when you cannot verify. The amount of trust required for any action is directly proportional to the entropy of that action &mdash; the amount of unknown the actor must absorb.</p>
            <p>If two people are betting on the result of a coin flip, they need to trust each other to honor the outcome. If they are running the same flip through a public, mathematically provable random function, they need to trust nothing at all.</p>
            <p>This gives us what we will call the physics of trust: <strong>as verifiability rises, the requirement for trust falls.</strong> Where mathematical proof is possible, trust is no longer needed, only verification. Where proof is impossible, trust is the only mechanism available.</p>
            <p>Most of the world lives in the second category. Most agreements are not coin flips. Most agreements are interpretations of incomplete information by parties who will inevitably disagree about what was agreed.</p>
            <p>Trust is what bridges that gap. And every important advance in commerce, governance, and law throughout history has been an attempt to manufacture more trust at lower cost.</p>
            <blockquote class="pull">Faith, then trust, then confidence, then assurance, then guarantee, then proof.<span class="attr">The gradient of certainty along which civilization has slowly climbed</span></blockquote>
            <p>Each layer reduces the entropy of the previous one. Each layer was a technology, invented in a specific place, by specific people, in response to a specific failure of the layer beneath it.</p>

            <h3>The seven layers of trust</h3>
            <p>If you zoom out far enough, trust has historically been built in layers. Each built on the failures of the one before it, each extending the radius of cooperation to a new horizon.</p>

            <div class="diagram">
              <div class="diagram-title">Seven layers, eight centuries</div>
              <div class="timeline">
                <div class="tl-item"><span class="tl-no">I</span><span class="tl-name">Personal</span><span class="tl-era">The tribe &middot; ~150 people</span></div>
                <div class="tl-item"><span class="tl-no">II</span><span class="tl-name">Mythic</span><span class="tl-era">Shared stories, religions, nations</span></div>
                <div class="tl-item"><span class="tl-no">III</span><span class="tl-name">Institutional</span><span class="tl-era">1258 &middot; Consulate of the Sea</span></div>
                <div class="tl-item"><span class="tl-no">IV</span><span class="tl-name">Market</span><span class="tl-era">Contracts, insurance, bills of exchange</span></div>
                <div class="tl-item"><span class="tl-no">V</span><span class="tl-name">Reputational</span><span class="tl-era">Ratings &amp; reviews at internet scale</span></div>
                <div class="tl-item"><span class="tl-no">VI</span><span class="tl-name">Cryptographic</span><span class="tl-era">2008 &middot; Bitcoin</span></div>
                <div class="tl-item tl-now"><span class="tl-no">VII</span><span class="tl-name">AI trust</span><span class="tl-era">Now &middot; machine judgment</span></div>
              </div>
            </div>
          </div>

          <!-- BENTO STAT TILES — trust history -->
          <div class="bento reveal-stagger" aria-label="Trust milestones">
            <div class="stat">
              <span class="stat-eyebrow">Consulate of the Sea</span>
              <span class="stat-num">1258</span>
              <span class="stat-label">Barcelona writes the first durable, supra-sovereign legal code for cross-jurisdiction trade.</span>
            </div>
            <div class="stat">
              <span class="stat-eyebrow">Personal trust ceiling</span>
              <span class="stat-num">~150</span>
              <span class="stat-label">Robin Dunbar&rsquo;s measured cognitive limit on human relationships.</span>
            </div>
            <div class="stat stat-dark">
              <span class="stat-eyebrow">Cryptographic trust</span>
              <span class="stat-num">2008</span>
              <span class="stat-label">Satoshi Nakamoto writes a system where trust can be replaced by proof.</span>
            </div>
            <div class="stat stat-lav">
              <span class="stat-eyebrow">Layers of trust</span>
              <span class="stat-num">7</span>
              <span class="stat-label">From personal memory to AI-mediated judgment at machine speed.</span>
            </div>
          </div>

          <!-- SEVEN LAYERS — feature grid -->
          <div class="layers-grid reveal-stagger" aria-label="The seven layers of trust">
            <div class="layer">
              <div class="layer-head"><span class="layer-no">I</span><h5>Personal trust</h5></div>
              <span class="layer-tag">Direct memory &middot; repeated interaction</span>
              <p>The original layer. Trust based on direct memory, repeated interactions, and human biases. Limited by what the evolutionary anthropologist Robin Dunbar measured as the cognitive ceiling of human relationships &mdash; roughly 150 people. You trust your family, your tribe, your closest friends because you have a body to share, a face to read, and a memory of every prior interaction. Beyond these limits, this layer fails completely.</p>
            </div>

            <div class="layer">
              <div class="layer-head"><span class="layer-no">II</span><h5>Mythic trust</h5></div>
              <span class="layer-tag">Shared stories &middot; religions &middot; nations</span>
              <p>Trust based on shared stories, symbols, religions, nations, identities, and social imaginaries. Yuval Noah Harari called this intersubjective reality. The Cognitive Revolution gave Sapiens the ability to believe in shared fictions, and these fictions allowed millions of strangers to cooperate without ever meeting. Lynne Zucker called this &ldquo;characteristics-based trust&rdquo;: you extend confidence to a stranger because they share a creed, a clan, a flag, an alma mater. Mythic trust increased the limits of personal trust. It also created the first large-scale cooperation failures, because shared myths can be exploited by those who do not share them.</p>
            </div>

            <div class="layer">
              <div class="layer-head"><span class="layer-no">III</span><h5>Institutional trust</h5></div>
              <span class="layer-tag">Courts &middot; states &middot; enforceable process</span>
              <p>The thirteenth century saw an extraordinary engineering project we now barely remember. The merchants of the Mediterranean, moving silk and salt and silver from Alexandria to Venice, could not rely on local courts to enforce agreements across jurisdictions. So in 1258, in Barcelona, they wrote the Consulate of the Sea: the first durable, supra-sovereign legal code. Run by traders, not judges, and enforced by ships and cargo as collateral, not by armies. It worked because it built systemic trust where personal and mythic trust could not reach. It is the layer most modern legal systems still inhabit. It is also the layer that is now visibly failing due to corruption of those institutions and globalization.</p>
            </div>

            <div class="layer">
              <div class="layer-head"><span class="layer-no">IV</span><h5>Market &amp; contractual trust</h5></div>
              <span class="layer-tag">Contracts &middot; insurance &middot; portable instruments</span>
              <p>When the Italian merchants of the same era invented the bill of exchange, the precursor to the modern check, they created a new technology for trusting strangers across distance and currency. Insurance, written contracts, double-entry bookkeeping: each is a market-layer technology. It works because reputation, contract law, and financial intermediaries are grouped together into a portable trust object you can put in an envelope and mail.</p>
            </div>

            <div class="layer">
              <div class="layer-head"><span class="layer-no">V</span><h5>Metatrust (social capital)</h5></div>
              <span class="layer-tag">Reputation &middot; ratings &middot; platform identity</span>
              <p>When the internet was born, frontiers disappeared and dissolved local accountability. It became suddenly possible to transact with someone you would never meet, in a country you had never visited, for a service you had no way to evaluate in advance. The reputation systems of Airbnb, Uber, Amazon, eBay exist for exactly one purpose: to recreate, at internet scale, the gossip networks that small villages had always used.</p>
              <p>Reputation works until it doesn&rsquo;t. It scales trust, but it does not turn trust into proof. Bernie Madoff did not lack credibility. His fraud survived because reputational signals can remain intact long after the underlying reality has already broken.</p>
            </div>

            <div class="layer">
              <div class="layer-head"><span class="layer-no">VI</span><h5>Cryptographic trust</h5></div>
              <span class="layer-tag">Trust replaced by proof &middot; deterministic systems</span>
              <p>In 2008, Satoshi Nakamoto did something none of the previous five layers had done: he wrote a system in which trust could be replaced by proof. Building on the work of Leslie Lamport on Byzantine generals, Ralph Merkle on hash trees, and decades of distributed-systems research, Bitcoin made it possible to coordinate value across the internet without trusting any of the participants &mdash; only the math.</p>
              <p>It was also the moment we discovered the limit of cryptographic trust: it works only for things that can be expressed deterministically. Bitcoin can prove that a coin moved. It cannot prove that a contract was breached. It cannot read a clause, weigh the evidence, or interpret a phrase like &ldquo;reasonable efforts&rdquo; or &ldquo;force majeure.&rdquo;</p>
            </div>

            <div class="layer layer-seven">
              <div class="layer-head"><span class="layer-no">VII</span><h5>AI trust</h5></div>
              <span class="layer-tag">Machine interpretation &middot; AI-mediated judgment</span>
              <p>Trust grounded in machine interpretation, AI-mediated judgment, and systems that can evaluate language, evidence, and ambiguity at a scale and speed human institutions cannot match. Where cryptographic trust replaced trust with proof for deterministic systems, AI trust extends the trust stack into cases where proof alone is not enough: contracts written in natural language, disputed outcomes, contextual evidence, and questions that require judgment rather than calculation.</p>
              <p>This layer will take many forms &mdash; centralized and decentralized, proprietary and open, permissioned and permissionless. GenLayer is one specific implementation inside it: a trustless adjudication protocol for the agentic economy.</p>
            </div>
          </div>

          <!-- WORLDVIEW continued -->
          <div class="prose">
            <p>We believe this seventh layer is now necessary. We believe it is now possible. And we believe its absence is one of the biggest unbuilt pieces of internet infrastructure.</p>

            <h3>Why human trust does not survive contact with agents</h3>
            <p>Every prior trust layer was built for human participants. Humans have bodies, addresses, reputations, fatigue, social context, and finite patience. The legal and commercial systems built around them assume those properties. They assume the parties can be located, slowed, threatened, persuaded or exhausted in recognizably human ways.</p>
            <p>Agents do not share those constraints.</p>
            <p>They transact faster. They scale harder. They are less forgiving of ambiguity. They can appear and disappear across jurisdictions. They can multiply far beyond the volume any legacy adjudication system can absorb. They can press edge cases relentlessly because the marginal cost of doing so approaches zero.</p>
            <p>The existing legal architecture is structurally mismatched to this world. GenLayer is not built to abolish sovereign courts. It is built to provide a first-instance, internet-native adjudication layer for disputes that will arrive too quickly, too often, and too globally for the old system to handle in time.</p>
            <blockquote class="pull">The next economy will not be blocked by the absence of software agents. It will be blocked by the absence of an adjudication layer that can absorb the disputes they produce.</blockquote>
            <p>That is the world GenLayer is for.</p>

            <h3>The defining distinction</h3>
            <p>Almost every project in the AI-crypto space describes itself as a &ldquo;trust system.&rdquo; We want to be precise about what we are.</p>
            <p><strong>GenLayer is not a mechanism for asking the world to trust a new intermediary. It is a mechanism for reducing how much trust any one intermediary needs to be given in the first place.</strong></p>
            <p>The distinction matters. A trust mechanism asks the participants to extend confidence to a system, an institution, or a counterparty. A substitution mechanism removes the need for that confidence entirely. Bitcoin substituted trust in central banks with trust in math. Ethereum substituted trust in legal contracts with trust in code. GenLayer extends that logic into adjudication: a decentralized, AI-mediated mechanism in which judgment is reached through process rather than unilateral authority.</p>
            <p>This is what the seventh layer looks like in practice. Validators powered by diverse large language models, selected at random, reach majority agreement on whether a non-deterministic claim is true, with appeals, escalation, and finality enforced by cryptography. Where Bitcoin reached consensus on the order of transactions, GenLayer reaches consensus on the meaning of transactions. Where Ethereum reached consensus on the execution of code, GenLayer reaches consensus on the interpretation of language. The Equivalence Principle, the technical primitive at the core of GenLayer, is the formal expression of the following: that two answers can be different and yet still be the same.</p>
            <p>This is, we think, the most important property a trust technology can have. The world is not deterministic. It&rsquo;s not black or white. Every existing infrastructure for adjudication &mdash; every court, every arbitration panel, every escrow service &mdash; is in some way a hand-crafted, jurisdiction-dependent, slow attempt to perform the kind of judgment that GenLayer can perform automatically, in minutes, at internet scale, for anyone in the world. And the world about to come online is the one with the most need for it: an economy in which the parties have no bodies, no patience, and no shared courtroom to walk into.</p>
            <p>That is why we believe an Agentic Adjudication Layer is the missing piece of infrastructure for the agentic economy.</p>
            <p>That is why we exist.</p>
          </div>
        </div>
      </section>

      <!-- 02 CONCEPT -->
      <section class="ed-section reveal" id="concept">
        <div class="ed-aside">
          <span class="sec-badge">Section 02</span>
          <h2>Concept</h2>
          <p class="sec-lede">Agentic Adjudication Layer. Four words, each carrying weight. This section unpacks what they mean and why they matter.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <blockquote class="pull" style="margin-top:0">Agentic Adjudication Layer.<span class="attr">The missing piece of infrastructure for the agentic economy</span></blockquote>

          <div class="prose">
            <p>Let&rsquo;s analyze it, word by word.</p>
          </div>
          <dl class="defs reveal-stagger" style="margin-top:1.3em">
            <div class="def">
              <dt>Agentic</dt>
              <dd><p>Because the economy we are building for is the one in which the parties are software, not people. The agents themselves are the principals. They are the new economic actors, and the infrastructure designed for human actors will not survive contact with them.</p></dd>
            </div>
            <div class="def">
              <dt>Adjudication</dt>
              <dd><p>Not &ldquo;dispute resolution,&rdquo; not &ldquo;arbitration,&rdquo; not &ldquo;court.&rdquo; Adjudication is the verb of judgment. It is the act of weighing evidence, interpreting intent, and reaching a verdict the parties will accept as legitimate. Arbitration is a process. Dispute resolution is an outcome. Adjudication is the thing itself &mdash; the moment a judgment becomes the truth the world will trade on.</p></dd>
            </div>
            <div class="def">
              <dt>Layer</dt>
              <dd><p>Because this has to exist as infrastructure, not as a platform-level privilege or an opaque service controlled by one operator. If the missing function sits inside a single platform, the platform becomes the judge. If it exists as a shared layer of the stack, the process itself becomes something others can inspect, challenge, and rely on without handing unilateral power to one intermediary.</p></dd>
            </div>
            <div class="def">
              <dt>Missing piece of infrastructure</dt>
              <dd><p>Not a feature and not an optimization. The agentic stack is being built right now, in public, by serious people: Coinbase&rsquo;s x402, Ethereum&rsquo;s ERC-8004 (Trustless Agents), the Linux Foundation&rsquo;s A2A (Agent Interoperability). Every standard in the stack assumes the happy path. Every one of them carves out the moment of disagreement as someone else&rsquo;s problem. The piece they all defer is the piece without which none of them work at scale.</p></dd>
            </div>
            <div class="def def-wide">
              <dt>Agentic economy</dt>
              <dd><p>The economy in which software acts on its own behalf, transacts at machine speed, and surfaces disagreements at machine speed too. This is the economy Cathie Wood at ARK Invest has projected at nine trillion dollars by 2030. This is the economy Brian Armstrong of Coinbase pointed at when he wrote that &ldquo;AI agents cannot get bank accounts, but they can get crypto wallets.&rdquo; This is the economy Elizabeth Harkavy and Chris Dixon of a16z named when they invested in Catena Labs and wrote that &ldquo;machine-speed systems need machine-speed money.&rdquo;</p></dd>
            </div>
          </dl>
          <div class="prose" style="margin-top:1.6em">
            <p>We agree. We extend.</p>
            <blockquote class="pull">Machine-speed money needs machine-speed adjudication.</blockquote>
            <p>Otherwise the money moves and the disputes do not. And the moment a single material disagreement reaches a system that cannot resolve it at the same speed the money moved at, the entire stack stalls.</p>
            <p>This is what GenLayer does. And only what GenLayer does.</p>
          </div>
        </div>
      </section>

      <!-- 03 WHAT IS GENLAYER -->
      <section class="ed-section reveal" id="what-is-genlayer">
        <div class="ed-aside">
          <span class="sec-badge">Section 03</span>
          <h2>What is GenLayer?</h2>
          <p class="sec-lede">One protocol, many lenses. Versions of the same answer, each tuned for a different audience &mdash; from a stranger at a party to a venture investor to a regulator.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="voices reveal-stagger" aria-label="What is GenLayer — voices">
            <div class="voice">
              <span class="voice-for">V1 &mdash; For a stranger</span>
              <p>AI agents will soon be doing business with each other. And just like humans, they will have disputes. We&rsquo;re building an AI-powered adjudication system so that they can resolve contracts and disputes at machine speed.</p>
            </div>

            <div class="voice">
              <span class="voice-for">V4 &mdash; For a regulator</span>
              <p>GenLayer is an open-source, decentralized protocol that brings transparent, auditable, and impartial dispute resolution to digital commerce. It is designed to complement, not replace, existing legal frameworks in the domains where speed, scale and the cross-border nature of automated transactions exceed what traditional courts were built to handle.</p>
            </div>

            <div class="voice voice-wide">
              <span class="voice-for">V2 &mdash; For a builder</span>
              <p>GenLayer is a new type of blockchain designed for agreements that cannot be resolved by code alone. At its core are Intelligent Contracts: agreements that combine code, natural language, and real-world information, and are adjudicated through decentralized AI validator consensus. This lets agentic commerce keep functioning even when outcomes are disputed, ambiguous, or context-dependent.</p>
            </div>

            <div class="voice voice-wide">
              <span class="voice-for">V3 &mdash; For an investor</span>
              <p>GenLayer is the missing layer that will enable truly agentic commerce. As AI agents begin to transact, negotiate, and coordinate with each other, disputes will inevitably arise &mdash; not as edge cases, but as a structural feature of an economy built on probabilistic systems operating under ambiguity. Until now, most of the market has focused on the happy path: payments, execution, and agents operating in isolation or within limited workflows. But once agents start entering into meaningful commitments with real economic consequence, the bottleneck is no longer just moving money or executing code. It is adjudication.</p>
            </div>

            <div class="voice voice-dark voice-wide">
              <span class="voice-for">V5 &mdash; In one breath</span>
              <p>The adjudication layer for the agentic economy. The missing infrastructure that lets AI agents resolve disputes at machine speed.</p>
            </div>
          </div>

          <!-- One-liners + long description -->
          <div class="prose">
            <h4>One-liners</h4>
          </div>
          <ul class="lines reveal-stagger">
            <li><span class="line-tag">The category line</span><span>Agentic Adjudication Layer. GenLayer is the adjudication layer for the agentic economy.</span></li>
            <li><span class="line-tag">The villain line</span><span>By 2030, AI agents will run businesses, manage portfolios, and make deals. They do not sleep. They cannot go to court.</span></li>
            <li><span class="line-tag">The proof line</span><span>x402 ships payments. ERC-8004 ships identity. A2A ships negotiation. ERC-8183 and Arkhai move contract structure forward. OpenClaw and Hermes address execution. Internet Court connects the stack. GenLayer resolves the disputes.</span></li>
            <li><span class="line-tag">The extension line</span><span>Machine-speed systems need machine-speed money. Machine-speed money needs machine-speed adjudication.</span></li>
            <li><span class="line-tag">The hero line</span><span>GenLayer is not a trust mechanism. It is a mechanism to substitute trust.</span></li>
            <li><span class="line-tag">The promise</span><span>Justice in minutes, not months.</span></li>
            <li><span class="line-tag">The breakthrough</span><span>Two answers can be different and still be equivalent. No existing blockchain accounts for this.</span></li>
          </ul>
          <div class="prose">
            <h4>The long description</h4>
            <p>GenLayer is the Agentic Adjudication Layer: the missing piece of infrastructure for the agentic economy. As AI agents begin to transact, enter into agreements, and coordinate work autonomously, disputes will follow. Smart contracts cannot handle ambiguity because they only work when outcomes can be reduced to deterministic code. Courts can, but far too slowly for an economy running at machine speed. GenLayer exists to close that gap. GenLayer can also be exposed, through Internet Court, as one adjudication path inside a broader open standard for agent-to-agent contracts, alongside identity, negotiation, payment, escrow, execution, and reputation systems.</p>
            <p>At the core of GenLayer is the <strong>Intelligent Contract</strong>: a new kind of smart contract, written in Python, that can read the web, interpret natural language, and evaluate the kind of subjective claims ordinary smart contracts cannot. Intelligent Contracts run inside <strong>GenVM</strong>, GenLayer&rsquo;s sandboxed execution environment, and are resolved through <strong>Optimistic Democracy</strong>, a delegated proof-of-stake consensus mechanism in which a randomly selected set of validators, each connected to a different large language model, evaluates the outcome of a transaction. When validators disagree, the validator set rotates, and anyone can appeal to expand the validator set until the network either reaches finality or determines that the question is undecidable.</p>
            <p>The technical breakthrough behind this is the <strong>Equivalence Principle</strong>: a way for different models to agree when two outputs differ in form but are equivalent in meaning. That makes decentralized consensus on non-deterministic outcomes possible, and allows GenLayer to function as a fast, cost-efficient, and trustworthy adjudication layer for the next generation of digital commerce.</p>

            <h3>Who we are</h3>
            <p>GenLayer is built and stewarded by two entities, each with clear goals: the work of building a protocol and the work of guaranteeing it stays neutral are not the same work, and they should not be done by the same hands.</p>
            <p><strong>GenLayer Labs</strong> is a research and engineering lab exploring the future of commerce, coordination, and decision-making in a world increasingly shaped by software and AI agents. Our work sits at the intersection of AI, cryptography, distributed systems, and institutional design. We are interested in a simple but increasingly important question: what kind of infrastructure is needed when commerce is no longer limited by execution, but by trust, ambiguity, and coordination under uncertainty? We operate with a long-term view of the internet as a place where both humans and machines will need better ways to commit, coordinate, and transact.</p>
            <p><strong>The GenLayer Foundation</strong> was created to answer a single but important question: who should hold the power to decide what is true? If that power is centralized, sooner or later it will be corrupted. We do not intend to repeat that mistake. The protocol must, in the end, belong to the network that runs it.</p>
            <p>The Foundation is the self-dissolving steward of the protocol. Its mission is to support the development of GenLayer until the network is sufficiently decentralized to govern itself, and then to dissolve. It does this by building Deepthought DAO, the AI-assisted governance layer that will eventually replace it, and by ensuring that the protocol&rsquo;s principles outlive any individual or institution. The Foundation believes its highest purpose is to make itself unnecessary.</p>
          </div>
        </div>
      </section>

      <!-- 04 HISTORY -->
      <section class="ed-section reveal" id="history">
        <div class="ed-aside">
          <span class="sec-badge">Section 04</span>
          <h2>History: Origins, Present, Future</h2>
          <p class="sec-lede">From the Consulate of the Sea in 1258 Barcelona to the Equivalence Principle in 2024. The question is the same. The answer needed to be new.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="bento bento-history reveal-stagger" aria-label="History milestones">
            <div class="stat stat-lav">
              <span class="stat-eyebrow">StakeHound incident</span>
              <span class="stat-num">38K ETH</span>
              <span class="stat-label">Roughly $150M lost when a top custody provider lost access &mdash; years of litigation, still unrecovered.</span>
            </div>
            <div class="stat">
              <span class="stat-eyebrow">App Store surge</span>
              <span class="stat-num">84%</span>
              <span class="stat-label">The scale of demand for autonomous, agent-native commerce now coming online.</span>
            </div>
            <div class="stat stat-dark stat-wide">
              <span class="stat-eyebrow">The white paper</span>
              <span class="stat-num">2024</span>
              <span class="stat-label">Albert, Jose Maria, and Edgars co-author <em>GenLayer: The Intelligent Contract Network</em>, the founding technical document.</span>
            </div>
          </div>

          <div class="prose">
            <h3>Origins: the question that started it</h3>
            <p>GenLayer began with a question, not a product. The question was old. It was the same question the merchants of Barcelona had asked themselves in 1258 when they wrote the Consulate of the Sea: how do you resolve disputes when trade crosses jurisdictions and ordinary local courts are not enough? In the thirteenth century, the answer was a code of laws administered by traders, enforced by ships and cargo as collateral, recognized across the Mediterranean from Alexandria to Venice. It worked because it built systemic trust where personal trust could not reach.</p>
            <p>In 2023, the question came back. The places had changed. The parties were no longer ships from Venice and warehouses in Alexandria. They were AI agents, decentralized protocols, and humans transacting across borders that no longer mapped cleanly to any one jurisdiction. The slow, jurisdictional, deeply human legal system had not been designed for any of them. The question was the same. The answer needed to be new.</p>

            <h3>The founding experiences</h3>
            <p>The idea behind GenLayer goes back to 2021. Albert and Edgars, who had already been building together for years, went through a custodian incident at StakeHound in which one of the top custody providers lost access to roughly thirty-eight thousand ETH, worth over $150 million at the time. The case went to the Tel Aviv District Court, even reaching the Supreme Court. Years of litigation followed, but the funds still haven&rsquo;t been recovered. The experience gave them a precise, expensive understanding of what happens when the legal system meets the velocity of cryptocurrency: it stops working. The institutional infrastructure for adjudicating disputes in digital commerce was simply not built for the speed at which those disputes arrive.</p>
            <p>At the same time, Albert, Edgars, and Jose Maria &mdash; GenLayer Labs&rsquo; co-founders &mdash; were exploring a different but related question through YeagerAI, later renamed GenLayer Labs: what happens when software agents stop being passive tools and start acting on their own. First came yAgents, an early self-reflecting terminal agent that could observe its own execution, reason about it, and modify its behavior. Then came GenWorlds, which explored how networks of LLM agents could coordinate through shared state and message passing without a central planner. Together, those research directions pointed toward the same future: agents would not just assist &mdash; they would act, coordinate, and increasingly participate in economic life. The StakeHound litigation revealed the missing piece. If agentic commerce was going to become real, it would need infrastructure not just for execution, but for adjudication. GenLayer was born from that convergence.</p>
            <p>David&rsquo;s story &mdash; the GenLayer Foundation&rsquo;s CEO &mdash; came earlier and from a different angle. He had been the first investor in a startup that was eventually acquired for more than one hundred million dollars. The acquirer refused to pay. The case went to trial. Two years passed before any resolution was possible. When Albert explained the idea to David, it was an instant match.</p>
            <p>What both experiences pointed at was not a new product. It was a new primitive. Smart contracts could enforce deterministic agreements perfectly, but the agreements that matter most in commerce &mdash; the ones with judgment and interpretation and ambiguity baked into them &mdash; are the ones smart contracts cannot reach. The legal system handles them badly. Cryptography can&rsquo;t handle them at all.</p>
            <blockquote class="pull">The gap between <em>I can prove a coin moved</em> and <em>I can prove a contract was honored</em> is the gap GenLayer was created to close.</blockquote>
            <p>The technical insight that made it possible came from the convergence of three things: the maturation of large language models in 2023, which finally made machine interpretation of natural language production-ready; the long history of game-theoretic consensus mechanisms &mdash; Schelling points, Condorcet&rsquo;s jury theorem, Byzantine fault tolerance; and the realization that non-determinism could itself be made consensus-friendly if you could define what it meant for two different answers to be considered equivalent. That last insight became the Equivalence Principle. It is the technical foundation of the entire protocol.</p>
            <p>In February 2024, Albert, Jose Maria, and Edgars co-authored the GenLayer white paper, <em>GenLayer: The Intelligent Contract Network</em>, and stated the ambition plainly in the paper&rsquo;s conclusion: &ldquo;we believe that GenLayer can become the legal system of choice for autonomous AGI agents to conduct business with each other.&rdquo; That sentence is the seed of everything in this document.</p>

            <h3>Present: what we have built</h3>
            <p>GenLayer today is no longer just a research thesis or a whitepaper. It is a working protocol, now deep in the process of becoming production infrastructure. That transition is happening through three testnet phases on the road to mainnet. The first phase was about proving the core ideas could work in practice. The second, Bradbury, is where those ideas begin to operate under far more realistic conditions: validators are no longer just replaying deterministic logic, but evaluating non-deterministic outcomes, handling disagreement, and exposing the system to the kinds of ambiguity it was actually built for. The third phase is about taking that harder, more realistic environment and pushing it toward mainnet readiness.</p>
            <p>At the protocol level, the core primitives are already in place. Intelligent Contracts run inside GenVM, combining code, natural language, and real-world information in ways ordinary smart contracts cannot. Those contracts are resolved through Optimistic Democracy, where validators evaluate non-deterministic outcomes and disputed cases can escalate through broader rounds of review. The Equivalence Principle provides the basis for decentralized agreement when outputs differ in form but are equivalent in meaning. The central breakthrough is no longer hypothetical. GenLayer is already operating the core mechanism it was designed to invent.</p>
            <p>What defines the present moment is that GenLayer has already crossed the line from possibility to reality. Decentralized adjudication is no longer the open question. The work now is to make it robust enough to serve as infrastructure: hardening validator behavior, appeals, edge cases, and developer workflows under real conditions, and turning a breakthrough into something the rest of the agentic economy can depend on.</p>

            <h3>Future: where this leads</h3>
            <p>By 2034, AI agents will have become major economic actors of the global economy. Each human will have, on average, dozens of agents working on their behalf &mdash; booking travel, negotiating contracts, managing finances, hiring other agents, paying bills, disputing them, paying again. The total volume of agent-to-agent contracts will exceed the total volume of human-to-human contracts by orders of magnitude. Every measurable metric of commerce &mdash; speed, throughput, complexity &mdash; will have shifted from human time to machine time.</p>
            <p>The infrastructure for that economy will not look like the infrastructure of today. Payments will be instant. Identity will be portable. Reputation will be on-chain. Adjudication &mdash; the piece that does not yet exist as a true internet-native layer &mdash; will be machine-speed, neutral, and integrated into digital contracts from the moment they are written. GenLayer is the protocol where that resolution happens.</p>
            <p>By 2034, the GenLayer Foundation will have dissolved itself. A foundation whose mission is the decentralization of power cannot, in the end, make an exception of itself. What remains is Deepthought DAO, a fully AI-powered governance layer built on GenLayer itself &mdash; the institution through which governance will be carried out and which will eventually substitute the GenLayer Foundation.</p>
            <p>That is where this leads. That is what we are building toward. And the moment is now, because the agentic economy is starting today.</p>
          </div>
        </div>
      </section>

      <!-- 05 PILLARS -->
      <section class="ed-section reveal" id="pillars">
        <div class="ed-aside">
          <span class="sec-badge">Section 05</span>
          <h2>Strategic Pillars</h2>
          <p class="sec-lede">Five principles that govern how we build, how we decide, and how we hold ourselves accountable. Each is both a strategic commitment and a cultural value.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="pillars reveal-stagger" aria-label="Strategic pillars">
            <div class="pillar">
              <div class="pillar-body">
                <span class="pillar-no">Pillar I</span>
                <h3>The Protocol Outlives Us</h3>
                <p class="pillar-thesis">Every institution that has ever made itself permanent has eventually become the obstacle it was built to remove.</p>
                <p>The protocol must, in the end, belong to the network that runs it. Not to the Labs that built it. Not to the Foundation that stewarded it. Not to any team, partner, or token holder large enough to think of itself as indispensable. If any single entity, including the GenLayer Foundation, becomes load-bearing for the network&rsquo;s survival, we have failed the test the protocol was built to pass.</p>
                <p>This has different consequences for different parts of GenLayer. For the Foundation, it means self-dissolution: the work ends when the network can govern itself, and Deepthought DAO inherits. For Labs, it means building products, contracts, and dependencies that do not require Labs to keep running for them to keep working. For every contributor, it means writing code, making decisions, and shipping features that can be challenged, forked, or reversed without any of us in the room.</p>
              </div>
              <div class="pillar-value"><strong>Value &mdash; Build to be replaced</strong>The measure of our work is not how essential we become but how cleanly we can be succeeded. The day the network functions better without us than with us is the day we have done our job.</div>
            </div>

            <div class="pillar">
              <div class="pillar-body">
                <span class="pillar-no">Pillar II</span>
                <h3>Truth without Trust</h3>
                <p class="pillar-thesis">When you need to trust an entity, you hand it power. Power concentrates. Corruption follows.</p>
                <p>This is not cynicism. It is the pattern that has played out across every system humans have built to resolve disputes, from arbitration panels to platform moderation to financial clearing houses. The moment a single actor can decide what is true, that actor becomes a target, an attack surface, and eventually a liability. GenLayer breaks the pattern by requiring consensus among diverse, independent validators. No single model, operator, or node can unilaterally determine an outcome. Truth emerges from the only place it reliably can: independent reasoners converging on the same answer without coordination.</p>
                <p>In practice: we do not designate trusted validators. We do not appeal to credentials or reputation. We do not give ourselves or any partner the power to override the network. Every design choice should prefer the path that asks for less trust, even when the alternative is faster or simpler.</p>
              </div>
              <div class="pillar-value"><strong>Value &mdash; Trustlessness</strong>A system that requires you to trust someone is only as honest as that someone. We build systems that do not require you to take anyone&rsquo;s word for it.</div>
            </div>

            <div class="pillar">
              <div class="pillar-body">
                <span class="pillar-no">Pillar III</span>
                <h3>Law without Lag</h3>
                <p class="pillar-thesis">Machine-speed systems need machine-speed adjudication. Justice in minutes, not months.</p>
                <p>The agentic economy will produce disputes at a volume and velocity no human institution was designed to absorb. When resolution is slow, the harmed party does not just lose time. They lose agency, leverage, and the ability to act on the truth. The U.S. legal system&rsquo;s average resolution time for complex civil disputes is 344 days. The international average is 657. That latency is not a bug in the legacy system. It is a structural feature of any system designed for human speed.</p>
                <p>In practice: the protocol must prevent any actor from introducing deliberate delay. We benchmark every system we ship on adjudication latency. Speed is not a feature we add when everything else is done. It is the condition everything else is built around.</p>
              </div>
              <div class="pillar-value"><strong>Value &mdash; Velocity wins</strong>Speed is strategy. Shipping is oxygen. In frontier technology, speed and execution determine survival. We operate with urgency and precision. We move fast, stay sharp, and adapt, because standing still is falling behind.</div>
            </div>

            <div class="pillar">
              <div class="pillar-body">
                <span class="pillar-no">Pillar IV</span>
                <h3>Power without Permission</h3>
                <p class="pillar-thesis">Justice that is only reachable by some is not justice. It is a privilege with better branding.</p>
                <p>Traditional dispute resolution depends on who you are, where you are, and how long you can wait. Most people and most agents will never have access to it. GenLayer is built on the opposite assumption: anyone, anywhere, at any status, should be able to deploy a contract, trigger adjudication, and receive a credible resolution under exactly the same rules as everyone else. The diversity of the validator set reinforces this. A permissionless network cannot be captured by any single jurisdiction, operator, or interest group. Diversity is not an ethical bonus. It is a security property.</p>
                <p>In practice: we do not maintain whitelists, priority queues, or exceptions for large customers or partners. Anyone with stake can run a validator. Anyone with a bond can appeal. Gas costs the same regardless of who is asking.</p>
              </div>
              <div class="pillar-value"><strong>Value &mdash; Accessibility</strong>The protocol is only as powerful as the range of people it actually serves.</div>
            </div>

            <div class="pillar">
              <div class="pillar-body">
                <span class="pillar-no">Pillar V</span>
                <h3>Judgment without Bias</h3>
                <p class="pillar-thesis">No single model, institution, or perspective should be able to define truth for everyone else.</p>
                <p>Every adjudication system confronts the same problem: judgment is shaped by whoever is doing the judging. Courts lean toward local power. Platforms enforce the preferences of whoever wrote the moderation policy. Single-model AI systems encode the assumptions of whoever trained the model. GenLayer exists to break that pattern by requiring consensus among a diverse set of independent validators running different models, different seeds, on different hardware, in different geographies. No single perspective can quietly become the default. Bias cannot be eliminated. It can be counterbalanced.</p>
                <p>In practice: we do not pick a preferred LLM. We do not run a reference implementation that gets special treatment. We treat homogeneity in the validator set as a security risk, not a simplification. Validator diversity is something we actively build toward and measure.</p>
              </div>
              <div class="pillar-value"><strong>Value &mdash; Fairness</strong>Equal before the system. Every contract, every user, every dispute, judged by the same process with no exceptions.</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 06 MISSION -->
      <section class="ed-section reveal" id="mission">
        <div class="ed-aside">
          <span class="sec-badge">Section 06</span>
          <h2>Mission</h2>
          <p class="sec-lede">Our mission is to ensure the agentic economy can function under disagreement. Everything else in this document is the unpacking.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <blockquote class="pull" style="margin-top:0">Our mission is to ensure the agentic economy can function under disagreement.</blockquote>

          <div class="prose">
            <p>GenLayer is the adjudication layer for the agentic economy. It uses decentralized AI validator consensus to resolve contracts that require judgment, not just code.</p>
            <p>As software begins to negotiate, transact, execute tasks, and coordinate economic activity on behalf of humans and other systems, ambiguity will scale. The moment meaningful commitments are made at machine speed, disputes also begin to appear at machine speed: whether something was delivered, whether it met the agreed standard, whether a clause was satisfied, whether an outcome is close enough to count, whether the evidence is sufficient. That is where deterministic systems stop being enough.</p>
            <p>This is the missing primitive. Payments, identity, reputation, and workflow infrastructure can move activity forward, but they do not resolve contested commitments. They assume alignment. Real economies do not. The more economically meaningful the activity becomes, the more costly that assumption becomes. Without an adjudication layer, the stack works only on the happy path. It scales until the first material disagreement, and then it is forced back into slower, more fragmented, and more trust-dependent systems. GenLayer is the mechanism that lets the stack continue operating once interpretation, evidence, and disagreement enter the picture; Internet Court is the coordination surface for that broader stack.</p>
            <p>GenLayer exists to ensure that this does not become the bottleneck of the next economy. We exist to provide the missing layer that lets machine-native commitments remain enforceable even when they become ambiguous, contested, or non-deterministic. We exist so that builders can create agentic systems that do not collapse the moment interpretation is required. We exist so that machine-speed money is matched by machine-speed adjudication.</p>
            <p><strong>Enable agentic commerce. Everything else in this document is the unpacking.</strong></p>
          </div>
        </div>
      </section>

      <!-- 07 BIBLIOGRAPHY -->
      <section class="ed-section reveal" id="bibliography">
        <div class="ed-aside">
          <span class="sec-badge">Section 07</span>
          <h2>Bibliography</h2>
          <p class="sec-lede">The intellectual lineage of GenLayer. The works, thinkers, and traditions that shaped the protocol and the worldview behind it. The seed, not the complete canon.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="bib-grid reveal-stagger">
            <div class="bib-group">
              <h4><span class="bib-dot"></span>Trust theory</h4>
              <ul>
                <li>Niklas Luhmann, <a href="https://www.wiley.com/en-us/Trust+and+Power-p-9781509519453" target="_blank" rel="noopener"><cite>Trust and Power</cite></a> (English translation 1979; original German <cite>Vertrauen</cite>, 1968) <span class="bib-note">&mdash; trust as a mechanism for the reduction of social complexity.</span></li>
                <li>Lynne G. Zucker, &ldquo;<a href="https://digitalassets.lib.berkeley.edu/irle/ucb/text/irla0277.pdf" target="_blank" rel="noopener">Production of Trust: Institutional Sources of Economic Structure, 1840&ndash;1920</a>&rdquo; (<cite>Research in Organizational Behavior</cite>, 1986) <span class="bib-note">&mdash; the three modes of trust production.</span></li>
                <li>Roger C. Mayer, James H. Davis, F. David Schoorman, &ldquo;<a href="https://www.jstor.org/stable/258792?seq=1" target="_blank" rel="noopener">An Integrative Model of Organizational Trust</a>&rdquo; (<cite>Academy of Management Review</cite>, 1995) <span class="bib-note">&mdash; the ability/benevolence/integrity model.</span></li>
                <li>Diego Gambetta (ed.), <a href="https://www.nuffield.ox.ac.uk/users/gambetta/Trust_making%20and%20breaking%20cooperative%20relations.pdf" target="_blank" rel="noopener"><cite>Trust: Making and Breaking Cooperative Relations</cite></a> (1988) <span class="bib-note">&mdash; including the Sicilian Mafia as a private adjudicator emerging where public enforcement fails.</span></li>
                <li>Russell Hardin, <a href="https://www.russellsage.org/publications/trust-and-trustworthiness" target="_blank" rel="noopener"><cite>Trust and Trustworthiness</cite></a> (2002) <span class="bib-note">&mdash; the encapsulated-interest model.</span></li>
                <li>Robert Putnam, <a href="http://bowlingalone.com/" target="_blank" rel="noopener"><cite>Bowling Alone</cite></a> (2000); Francis Fukuyama, <a href="https://www.harvard.com/book/9780684825250" target="_blank" rel="noopener"><cite>Trust: The Social Virtues and the Creation of Prosperity</cite></a> (1995) <span class="bib-note">&mdash; the social-capital tradition.</span></li>
                <li>Georg Simmel, <a href="https://archive.org/details/sociologyofgeorg0000simm" target="_blank" rel="noopener"><cite>The Sociology of Georg Simmel</cite></a> (translated 1950) <span class="bib-note">&mdash; the less we know about others, the more we need to trust.</span></li>
              </ul>
            </div>

            <div class="bib-group">
              <h4><span class="bib-dot"></span>Game theory, consensus &amp; the wisdom of crowds</h4>
              <ul>
                <li>Marquis de Condorcet, <a href="https://gallica.bnf.fr/ark:/12148/bpt6k417181" target="_blank" rel="noopener"><cite>Essai sur l&rsquo;application de l&rsquo;analyse &agrave; la probabilit&eacute; des d&eacute;cisions rendues &agrave; la pluralit&eacute; des voix</cite></a> (1785) <span class="bib-note">&mdash; the Jury Theorem.</span></li>
                <li>John Nash, &ldquo;<a href="https://library.princeton.edu/sites/g/files/toruqf6021/files/documents/Non-Cooperative_Games_Nash.pdf" target="_blank" rel="noopener">Non-Cooperative Games</a>&rdquo; (<cite>Annals of Mathematics</cite>, 1951) <span class="bib-note">&mdash; Nash equilibrium.</span></li>
                <li>Thomas Schelling, <a href="https://www.hup.harvard.edu/books/9780674840317" target="_blank" rel="noopener"><cite>The Strategy of Conflict</cite></a> (1960) <span class="bib-note">&mdash; focal points.</span></li>
                <li>Leslie Lamport, Robert Shostak, Marshall Pease, &ldquo;<a href="https://lamport.azurewebsites.net/pubs/byz.pdf" target="_blank" rel="noopener">The Byzantine Generals Problem</a>&rdquo; (<cite>ACM TOPLAS</cite>, 1982) <span class="bib-note">&mdash; Byzantine fault tolerance.</span></li>
                <li>Garay, Kiayias, Leonardos, &ldquo;<a href="https://eprint.iacr.org/2014/765" target="_blank" rel="noopener">The Bitcoin Backbone Protocol: Analysis and Applications</a>&rdquo; (2015).</li>
                <li>Akbir Khan et al., &ldquo;<a href="https://arxiv.org/abs/2402.06782" target="_blank" rel="noopener">Debating with More Persuasive LLMs Leads to More Truthful Answers</a>&rdquo; (arXiv, 2024) <span class="bib-note">&mdash; the future of inter-validator persuasion the GenLayer white paper hints at.</span></li>
                <li>Justin Chih-Yao Chen et al., &ldquo;<a href="https://arxiv.org/abs/2309.13007" target="_blank" rel="noopener">ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs</a>&rdquo; (arXiv, 2024).</li>
              </ul>
            </div>

            <div class="bib-group">
              <h4><span class="bib-dot"></span>Cryptography &amp; distributed systems</h4>
              <ul>
                <li>Satoshi Nakamoto, &ldquo;<a href="https://bitcoin.org/bitcoin.pdf" target="_blank" rel="noopener">Bitcoin: A Peer-to-Peer Electronic Cash System</a>&rdquo; (2008).</li>
                <li>Vitalik Buterin, &ldquo;<a href="https://ethereum.org/en/whitepaper/" target="_blank" rel="noopener">Ethereum: A Next-Generation Smart Contract and Decentralized Application Platform</a>&rdquo; (2014).</li>
                <li>Nick Szabo, &ldquo;<a href="https://nakamotoinstitute.org/library/smart-contracts/" target="_blank" rel="noopener">Smart Contracts</a>&rdquo; (1994).</li>
                <li>Daniel Larimer, &ldquo;<a href="https://bitshares.org/delegated-proof-of-stake-consensus/" target="_blank" rel="noopener">Delegated Proof-of-Stake</a>&rdquo; (2014).</li>
                <li>Silvio Micali, Michael Rabin, Salil Vadhan, &ldquo;<a href="https://people.csail.mit.edu/silvio/Selected%20Scientific%20Papers/Pseudo%20Randomness/Verifiable_Random_Functions.pdf" target="_blank" rel="noopener">Verifiable Random Functions</a>&rdquo; (FOCS, 1999).</li>
                <li>Ralph Merkle, &ldquo;<a href="https://ralphmerkle.com/papers/Protocols.pdf" target="_blank" rel="noopener">Protocols for Public Key Cryptosystems</a>&rdquo; (1980) <span class="bib-note">&mdash; Merkle trees.</span></li>
              </ul>
            </div>

            <div class="bib-group">
              <h4><span class="bib-dot"></span>AI, LLMs &amp; the modern attention era</h4>
              <ul>
                <li>Ashish Vaswani et al., &ldquo;<a href="https://arxiv.org/abs/1706.03762" target="_blank" rel="noopener">Attention Is All You Need</a>&rdquo; (NeurIPS, 2017) <span class="bib-note">&mdash; the paper that named the era.</span></li>
                <li>Andy Zou et al., &ldquo;<a href="https://arxiv.org/abs/2307.15043" target="_blank" rel="noopener">Universal and Transferable Adversarial Attacks on Aligned Language Models</a>&rdquo; (arXiv, 2023) <span class="bib-note">&mdash; the threat model Greyboxing exists to counter.</span></li>
                <li>Christian Szegedy et al., &ldquo;<a href="https://arxiv.org/abs/1312.6199" target="_blank" rel="noopener">Intriguing Properties of Neural Networks</a>&rdquo; (arXiv, 2013).</li>
                <li>Andrej Karpathy, <cite><a href="https://www.youtube.com/playlist?list=PLAqhIrjkxbuWI23v9cThsA9GvCAUhRvKZ" target="_blank" rel="noopener">Zero to Hero</a></cite> lecture series and public writing (2022&ndash;).</li>
              </ul>
            </div>

            <div class="bib-group">
              <h4><span class="bib-dot"></span>History of trust institutions</h4>
              <ul>
                <li>Avner Greif, &ldquo;<a href="https://doi.org/10.1017/S0022050700009475" target="_blank" rel="noopener">Reputation and Coalitions in Medieval Trade: Evidence from the Maghribi Traders</a>&rdquo; (<cite>Journal of Economic History</cite>, 1989).</li>
                <li><a href="https://en.wikipedia.org/wiki/Book_of_the_Consulate_of_the_Sea" target="_blank" rel="noopener"><cite>The Llibre del Consolat de Mar</cite></a> (compiled in the 14th century, with origins in Barcelona, 1258) <span class="bib-note">&mdash; the first durable supra-sovereign commercial code.</span></li>
                <li>Robin Dunbar, <a href="https://www.hup.harvard.edu/books/9780674363366" target="_blank" rel="noopener"><cite>Grooming, Gossip, and the Evolution of Language</cite></a> (1996) <span class="bib-note">&mdash; the cognitive ceiling of personal trust.</span></li>
                <li>Yuval Noah Harari, <a href="https://www.ynharari.com/book/sapiens/" target="_blank" rel="noopener"><cite>Sapiens: A Brief History of Humankind</cite></a> (2014) <span class="bib-note">&mdash; intersubjective reality and the Cognitive Revolution.</span></li>
                <li>David Flusser, theological writings on <em>pistis</em> (faith).</li>
                <li>Giorgio Agamben, <cite>Il Capitalismo come Religione</cite> <span class="bib-note">&mdash; on the etymology of credit / creditum.</span></li>
              </ul>
            </div>

            <div class="bib-group">
              <h4><span class="bib-dot"></span>Contemporary thinking on AI &times; crypto</h4>
              <ul>
                <li>Chris Dixon, <a href="https://readwriteown.com/" target="_blank" rel="noopener"><cite>Read Write Own</cite></a> (2024).</li>
                <li>Chris Dixon and Elizabeth Harkavy, &ldquo;<a href="https://a16zcrypto.com/posts/article/investing-in-catena-labs/" target="_blank" rel="noopener">Investing in Catena Labs</a>&rdquo; (a16z, 2025) <span class="bib-note">&mdash; machine-speed systems need machine-speed money.</span></li>
                <li>Marc Andreessen, &ldquo;<a href="https://a16z.com/the-techno-optimist-manifesto/" target="_blank" rel="noopener">The Techno-Optimist Manifesto</a>&rdquo; (a16z, 2023).</li>
                <li>Sreeram Kannan (EigenLayer), public essays and interviews (2023&ndash;) <span class="bib-note">&mdash; coordination = communication + commitment.</span></li>
                <li>Brian Armstrong (Coinbase), public statements (2024) <span class="bib-note">&mdash; AI agents cannot get bank accounts but they can get crypto wallets.</span></li>
                <li>Larry Fink (BlackRock), public statements (2024) <span class="bib-note">&mdash; everything will be tokenized.</span></li>
                <li>Cathie Wood (ARK Invest), AI-commerce projections (2024) <span class="bib-note">&mdash; the $9T-by-2030 number this document cites.</span></li>
              </ul>
            </div>

            <div class="bib-group">
              <h4><span class="bib-dot"></span>The agentic-commerce stack standards</h4>
              <ul>
                <li>Coinbase Developer Platform, <a href="https://www.x402.org/" target="_blank" rel="noopener"><cite>x402: Internet-Native Payments Standard</cite></a> (2024&ndash;).</li>
                <li>Marco De Rossi, Davide Crapis, Jordan Ellis, Erik Reppel, <a href="https://eips.ethereum.org/EIPS/eip-8004" target="_blank" rel="noopener"><cite>ERC-8004: Trustless Agents</cite></a> (Ethereum draft, August 2025).</li>
                <li><a href="https://a2a-protocol.org/latest/specification/" target="_blank" rel="noopener"><cite>Agent2Agent (A2A) Protocol Specification</cite></a>, Linux Foundation / Google (2025&ndash;).</li>
              </ul>
            </div>

            <div class="bib-group">
              <h4><span class="bib-dot"></span>Founding works</h4>
              <ul>
                <li>Albert Castellana, Jose Maria Lago, Edgars Nemse, <a href="#/foundations/whitepaper"><cite>GenLayer: The Intelligent Contract Network</cite></a> (whitepaper, February 2024) <span class="bib-note">&mdash; the founding technical document.</span></li>
                <li>David Riudor, <a href="https://x.com/driudor/status/1996993081791361353" target="_blank" rel="noopener"><cite>What Does Trust Mean for an Artificial Intelligence?</cite></a> (5-part essay, 2025) <span class="bib-note">&mdash; the philosophical foundation.</span></li>
                <li>David Riudor, <a href="https://x.com/driudor/status/1910315466465173713" target="_blank" rel="noopener"><cite>Are We Witnessing the Death of Trust? &mdash; A World on Edge</cite></a> (2025) <span class="bib-note">&mdash; the Consulate of the Internet article.</span></li>
                <li>Jose Maria Lago, <a href="https://jmlago.github.io/posts/illusion-of-determinism.html" target="_blank" rel="noopener"><cite>The Illusion of Determinism</cite></a> <span class="bib-note">&mdash; why determinism was always an approximation.</span></li>
                <li>Jose Maria Lago, <a href="https://jmlago.github.io/posts/semantic-consensus.html" target="_blank" rel="noopener"><cite>The Challenges of Semantic Consensus</cite></a> <span class="bib-note">&mdash; reaching agreement on meaning, the core of the Equivalence Principle.</span></li>
              </ul>
            </div>
          </div>

          <p class="bib-foot"><em>This list is not complete. It is the seed.</em></p>
        </div>
      </section>

      <!-- RESOURCES -->
      <section class="ed-section reveal" id="resources">
        <div class="ed-aside">
          <span class="sec-badge">Resources</span>
          <h2>Go deeper</h2>
          <p class="sec-lede">The primary sources, and the places where GenLayer is built in public.</p>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="resources reveal-stagger">
            <a class="res" href="#/foundations/whitepaper">
              <span class="res-name">Whitepaper</span>
              <span class="res-desc">GenLayer: The Intelligent Contract Network (2024) &mdash; the founding technical document. Read it here.</span>
            </a>
            <a class="res" href="https://docs.genlayer.com" target="_blank" rel="noopener">
              <span class="res-name">Documentation</span>
              <span class="res-desc">Intelligent Contracts, GenVM, Optimistic Democracy &mdash; how to build on GenLayer.</span>
            </a>
            <a class="res" href="https://studio.genlayer.com" target="_blank" rel="noopener">
              <span class="res-name">GenLayer Studio</span>
              <span class="res-desc">Write and run your first Intelligent Contract in the browser.</span>
            </a>
            <a class="res" href="#/">
              <span class="res-name">Foundation Portal</span>
              <span class="res-desc">Contribute as a builder, validator, or community member.</span>
            </a>
            <a class="res" href="https://internetcourt.org" target="_blank" rel="noopener">
              <span class="res-name">Internet Court</span>
              <span class="res-desc">One of our initiatives &mdash; an open standard and agent skill for agent-to-agent contracts, connecting identity, negotiation, contracts, payment, escrow, execution, verification, and disputes, with GenLayer as its adjudication layer.</span>
            </a>
            <a class="res" href="https://github.com/genlayerlabs" target="_blank" rel="noopener">
              <span class="res-name">GitHub</span>
              <span class="res-desc">The protocol, open source &mdash; read the code, open issues, contribute.</span>
            </a>
            <a class="res" href="https://x.com/GenLayer" target="_blank" rel="noopener">
              <span class="res-name">X / Twitter</span>
              <span class="res-desc">Announcements and the running argument, in public.</span>
            </a>
            <a class="res" href="https://discord.gg/genlayerlabs" target="_blank" rel="noopener">
              <span class="res-name">Discord</span>
              <span class="res-desc">Where the community lives &mdash; questions, testnet, working groups.</span>
            </a>
            <a class="res" href="https://www.youtube.com/@GenLayer" target="_blank" rel="noopener">
              <span class="res-name">YouTube</span>
              <span class="res-desc">GenTalks, demos, and deep dives on the protocol.</span>
            </a>
          </div>
        </div>
      </section>

      <footer class="footer-card reveal">
        <p class="foot-line">&ldquo;Two answers can be different and <em>still be the same</em>.&rdquo;</p>
        <div class="footer-actions">
          <a class="btn-hero" href="#/foundations/manifesto">The Manifesto &mdash; For the Right to Decide
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
          </a>
          <a class="btn-ghost" href="https://genlayer.com" target="_blank" rel="noopener">genlayer.com</a>
        </div>
        <div class="foot-meta">
          GenLayer Labs &middot; GenLayer Foundation<br />
          <a href="https://genlayer.com" target="_blank" rel="noopener">genlayer.com</a>
        </div>
      </footer>
    </div>
  </div>
</FoundationsShell>

<style>
  .fd-page {
    --border: #e5e7eb;
    --border-strong: #d1d5db;
    --ink: #1f2937;
    --ink-strong: #111827;
    --muted: #6b7280;
    --faint: #9ca3af;
    --violet: #7c5cff;
    --violet-deep: #6d4aff;
    --violet-text: #5b3df5;
    --lavender: #eeedfb;
    --lavender-border: #ddd9f6;
    --dark: #131214;
    --darker: #101010;
    --radius: 18px;
    --radius-sm: 12px;
    --shadow-card: 0 1px 2px rgba(16, 16, 16, 0.04), 0 1px 3px rgba(16, 16, 16, 0.03);
    --shadow-hover: 0 4px 10px rgba(16, 16, 16, 0.06), 0 2px 4px rgba(16, 16, 16, 0.04);
    --ed-aside: 248px;
    --ed-gap: 56px;
    --ed-measure: 660px;
    --ed-sticky: 24px;

    padding: 24px;
    font-family: 'Switzer', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    font-size: 18px;
    line-height: 1.72;
    color: var(--ink);
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }
  .fd-page h1,
  .fd-page h2,
  .fd-page h3,
  .fd-page h4,
  .fd-page h5 {
    font-family: 'Geist', 'Switzer', system-ui, sans-serif;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--ink-strong);
    line-height: 1.25;
  }
  .fd-page a {
    color: var(--violet-text);
    text-decoration: none;
  }
  .fd-page a:hover {
    text-decoration: underline;
  }

  .shell {
    max-width: 1060px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  /* ============ HERO ============ */
  .hero {
    position: relative;
    background: var(--dark);
    border-radius: 24px;
    padding: 60px 56px 52px;
    overflow: hidden;
    color: #fff;
    isolation: isolate;
    margin-bottom: 22px;
  }
  .hero::before {
    content: '';
    position: absolute;
    z-index: -1;
    width: 560px;
    height: 560px;
    border-radius: 50%;
    right: -180px;
    top: -260px;
    background: radial-gradient(circle, rgba(124, 92, 255, 0.5), rgba(124, 92, 255, 0.14) 45%, transparent 70%);
    filter: blur(8px);
  }
  .hero::after {
    content: '';
    position: absolute;
    z-index: -1;
    width: 420px;
    height: 420px;
    border-radius: 50%;
    left: -160px;
    bottom: -260px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.32), transparent 68%);
  }
  .hero-grid {
    position: absolute;
    inset: 0;
    z-index: -1;
    opacity: 0.5;
    background-image: linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse 90% 80% at 70% 20%, black, transparent 75%);
    -webkit-mask-image: radial-gradient(ellipse 90% 80% at 70% 20%, black, transparent 75%);
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: #fff;
    color: var(--ink-strong);
    font-size: 13px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 9999px;
    margin-bottom: 28px;
  }
  .chip .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--violet);
    box-shadow: 0 0 8px rgba(124, 92, 255, 0.8);
  }
  .hero h1 {
    color: #fff;
    font-size: clamp(34px, 4.6vw, 54px);
    font-weight: 600;
    letter-spacing: -0.03em;
    line-height: 1.12;
    max-width: 18ch;
    margin-bottom: 20px;
  }
  .hero h1 em {
    font-style: normal;
    color: #a78bfa;
  }
  .hero-lede {
    font-size: 19px;
    color: rgba(255, 255, 255, 0.84);
    max-width: 58ch;
    margin-bottom: 36px;
    line-height: 1.65;
  }
  .hero-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .btn-hero {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #fff;
    color: #101010 !important;
    font-size: 14.5px;
    font-weight: 600;
    padding: 11px 24px;
    border-radius: 9999px;
    text-decoration: none !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .btn-hero:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px -8px rgba(124, 92, 255, 0.65);
  }
  .btn-ghost {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: transparent;
    color: rgba(255, 255, 255, 0.85) !important;
    font-size: 14.5px;
    font-weight: 500;
    padding: 11px 22px;
    border-radius: 9999px;
    border: 1px solid rgba(255, 255, 255, 0.22);
    text-decoration: none !important;
    transition: border-color 0.15s ease, color 0.15s ease;
  }
  .btn-ghost:hover {
    border-color: rgba(255, 255, 255, 0.45);
    color: #fff !important;
  }

  /* ============ BENTO STAT TILES ============ */
  .bento {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin-bottom: 22px;
    width: 100%;
  }
  .bento-history {
    margin-bottom: 1.7em;
  }
  .stat {
    position: relative;
    background: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-card);
    padding: 24px 24px 22px;
    display: flex;
    flex-direction: column;
    min-height: 148px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
    overflow: hidden;
    isolation: isolate;
  }
  .stat:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-hover);
    transform: translateY(-2px);
  }
  .stat-eyebrow {
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: 0.03em;
    color: var(--violet-text);
    text-transform: uppercase;
    margin-bottom: auto;
  }
  .stat-num {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: clamp(30px, 3.2vw, 40px);
    font-weight: 600;
    letter-spacing: -0.03em;
    color: var(--ink-strong);
    line-height: 1.05;
    margin-top: 14px;
    font-variant-numeric: tabular-nums;
  }
  .stat-label {
    font-size: 14.5px;
    color: #525c68;
    line-height: 1.5;
    margin-top: 8px;
  }
  .stat-wide {
    grid-column: span 2;
  }
  .stat-dark {
    background: var(--darker);
    border-color: var(--darker);
    color: #fff;
  }
  .stat-dark::before {
    content: '';
    position: absolute;
    z-index: -1;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    right: -90px;
    top: -150px;
    background: radial-gradient(circle, rgba(124, 92, 255, 0.42), transparent 68%);
  }
  .stat-dark .stat-eyebrow {
    color: #c4b5fd;
  }
  .stat-dark .stat-num {
    color: #fff;
  }
  .stat-dark .stat-label {
    color: rgba(255, 255, 255, 0.78);
  }
  .stat-lav {
    background: linear-gradient(180deg, #fbfaff, var(--lavender) 180%);
    border-color: var(--lavender-border);
  }
  .stat-lav .stat-num {
    color: var(--violet-deep);
  }

  /* ============ EDITORIAL SIDENOTE SECTION ============ */
  .ed-section {
    display: grid;
    grid-template-columns: var(--ed-aside) minmax(0, 1fr);
    column-gap: var(--ed-gap);
    align-items: start;
    background: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-card);
    padding: 48px 56px 52px;
    margin-bottom: 22px;
    transition: border-color 0.2s ease;
    scroll-margin-top: 24px;
  }
  .ed-section:hover {
    border-color: var(--border-strong);
  }
  .ed-aside {
    position: sticky;
    top: var(--ed-sticky);
    align-self: start;
  }
  .ed-aside .sec-badge {
    margin-bottom: 18px;
  }
  .ed-aside h2 {
    font-size: clamp(23px, 2.5vw, 29px);
    line-height: 1.18;
    margin-bottom: 14px;
  }
  .ed-aside .sec-lede {
    font-size: 15.5px;
    color: #525c68;
    line-height: 1.6;
    margin: 0;
  }
  .ed-aside .ed-rule {
    height: 2px;
    width: 40px;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--violet), rgba(124, 92, 255, 0.25));
    margin-top: 20px;
  }
  .sec-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: var(--lavender);
    color: var(--violet-text);
    border: 1px solid var(--lavender-border);
    font-size: 12.5px;
    font-weight: 600;
    padding: 4px 13px;
    border-radius: 9999px;
  }
  .ed-body {
    max-width: var(--ed-measure);
    min-width: 0;
  }

  /* prose */
  .prose {
    max-width: var(--ed-measure);
  }
  .prose p {
    font-size: 19px;
    line-height: 1.72;
    margin-bottom: 1.25em;
  }
  .prose p:first-child {
    margin-top: 0;
  }
  .prose p:last-child {
    margin-bottom: 0;
  }
  .prose h3 {
    font-size: 22px;
    margin: 1.9em 0 0.7em;
    letter-spacing: -0.02em;
  }
  .ed-body .prose > h3:first-child {
    margin-top: 0;
  }
  .prose h4 {
    font-size: 18px;
    margin: 1.9em 0 0.8em;
  }
  .prose strong {
    font-weight: 600;
    color: var(--ink-strong);
  }
  .prose em {
    font-style: italic;
  }

  /* dark pull quote */
  .pull {
    position: relative;
    background: #0c0b11;
    color: #fff;
    border-radius: 16px;
    padding: 48px 52px 44px;
    margin: 1.9em 0;
    overflow: hidden;
    isolation: isolate;
    font-family: 'Geist', system-ui, sans-serif;
    font-size: clamp(23px, 2.7vw, 31px);
    font-weight: 500;
    letter-spacing: -0.028em;
    line-height: 1.28;
    box-shadow: 0 22px 50px -34px rgba(0, 0, 0, 0.6);
  }
  .pull::before {
    content: '\201C';
    position: absolute;
    z-index: -1;
    top: -0.26em;
    left: 0.02em;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 200px;
    line-height: 1;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.05);
    pointer-events: none;
  }
  .pull strong {
    font-weight: 600;
    color: #a78bfa;
  }
  .pull .attr {
    display: block;
    margin-top: 18px;
    font-family: 'Switzer', system-ui, sans-serif;
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0;
    color: rgba(255, 255, 255, 0.7);
  }
  .pull em {
    font-style: italic;
    color: #c4b5fd;
  }

  /* ============ TRUST LAYERS — feature grid ============ */
  .layers-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
    width: 100%;
  }
  .layer {
    background: #fcfcfd;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 24px 26px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  }
  .layer:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }
  .layer-head {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 4px;
  }
  .layer-no {
    display: inline-grid;
    place-items: center;
    min-width: 34px;
    height: 24px;
    padding: 0 8px;
    background: #f3f4f6;
    border: 1px solid var(--border);
    border-radius: 9999px;
    font-size: 11.5px;
    font-weight: 600;
    color: var(--muted);
    font-variant-numeric: tabular-nums;
  }
  .layer h5 {
    font-size: 17.5px;
  }
  .layer-tag {
    display: block;
    font-size: 13.5px;
    color: var(--muted);
    margin-bottom: 10px;
  }
  .layer p {
    font-size: 16px;
    color: #3d4654;
    margin-bottom: 0.9em;
    line-height: 1.66;
  }
  .layer p:last-child {
    margin-bottom: 0;
  }
  .layer-seven {
    grid-column: 1 / -1;
    border: 1px solid var(--lavender-border);
    background: linear-gradient(180deg, #fbfaff, var(--lavender) 220%);
    box-shadow: 0 0 0 3px rgba(124, 92, 255, 0.06), var(--shadow-card);
  }
  .layer-seven:hover {
    border-color: #c9c2f2;
  }
  .layer-seven .layer-no {
    background: var(--violet);
    border-color: var(--violet);
    color: #fff;
  }
  .layer-seven h5 {
    color: var(--violet-deep);
  }
  .layer-seven p {
    font-size: 16.5px;
    max-width: none;
  }

  /* ============ DEFINITION CARDS ============ */
  .defs {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    width: 100%;
  }
  .def {
    background: #fcfcfd;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 24px 26px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  }
  .def:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }
  .def dt {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 16.5px;
    font-weight: 600;
    letter-spacing: -0.015em;
    color: var(--violet-text);
    margin-bottom: 8px;
  }
  .def dd {
    margin: 0;
  }
  .def dd p {
    font-size: 16px;
    color: #3d4654;
    line-height: 1.66;
    margin: 0;
  }
  .def-wide {
    grid-column: 1 / -1;
  }

  /* ============ VOICE CARD GRID ============ */
  .voices {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    width: 100%;
  }
  .voice {
    background: #fcfcfd;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 24px 24px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  }
  .voice:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }
  .voice-for {
    display: inline-flex;
    align-items: center;
    background: var(--lavender);
    color: var(--violet-text);
    border: 1px solid var(--lavender-border);
    font-size: 11.5px;
    font-weight: 600;
    padding: 3px 11px;
    border-radius: 9999px;
    margin-bottom: 12px;
  }
  .voice p {
    font-size: 16px;
    color: #3d4654;
    line-height: 1.65;
    margin: 0;
  }
  .voice-wide {
    grid-column: span 2;
  }
  .voice-dark {
    position: relative;
    overflow: hidden;
    isolation: isolate;
    background: var(--darker);
    border-color: var(--darker);
  }
  .voice-dark::before {
    content: '';
    position: absolute;
    z-index: -1;
    width: 300px;
    height: 300px;
    border-radius: 50%;
    right: -80px;
    top: -150px;
    background: radial-gradient(circle, rgba(124, 92, 255, 0.4), transparent 68%);
  }
  .voice-dark .voice-for {
    background: rgba(238, 237, 251, 0.12);
    color: #c4b5fd;
    border-color: rgba(196, 181, 253, 0.25);
  }
  .voice-dark p {
    color: rgba(255, 255, 255, 0.92);
    font-family: 'Geist', system-ui, sans-serif;
    font-weight: 500;
    font-size: 17px;
    letter-spacing: -0.01em;
  }

  /* ============ ONE-LINERS ============ */
  .lines {
    list-style: none;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    width: 100%;
    margin: 0;
    padding: 0;
  }
  .lines li {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    background: #fcfcfd;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 16px 18px;
    font-size: 16px;
    color: #323a46;
    line-height: 1.6;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .lines li:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-hover);
  }
  .line-tag {
    flex-shrink: 0;
    display: inline-flex;
    background: #fff;
    color: var(--muted);
    border: 1px solid var(--border);
    font-size: 11.5px;
    font-weight: 600;
    white-space: nowrap;
    padding: 3px 11px;
    border-radius: 9999px;
  }

  /* ============ PILLAR CARDS ============ */
  .pillars {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
    width: 100%;
  }
  .pillar {
    background: #fcfcfd;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  }
  .pillar:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }
  .pillar-body {
    padding: 26px 30px 24px;
    flex: 1;
  }
  .pillar-no {
    display: inline-flex;
    align-items: center;
    background: #f3f4f6;
    color: var(--muted);
    border: 1px solid var(--border);
    font-size: 11.5px;
    font-weight: 600;
    padding: 3px 12px;
    border-radius: 9999px;
    margin-bottom: 14px;
  }
  .pillar h3 {
    font-size: 21px;
    margin-bottom: 10px;
  }
  .pillar-thesis {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 16.5px;
    font-weight: 500;
    letter-spacing: -0.01em;
    color: var(--violet-deep);
    margin-bottom: 14px;
    line-height: 1.5;
  }
  .pillar-body p {
    font-size: 16px;
    color: #3d4654;
    line-height: 1.66;
    margin-bottom: 0.95em;
  }
  .pillar-body p:last-child {
    margin-bottom: 0;
  }
  .pillar-value {
    background: linear-gradient(180deg, #f6f4ff, var(--lavender));
    border-top: 1px solid var(--lavender-border);
    padding: 18px 30px;
    font-size: 14.5px;
    color: #4c3db0;
    line-height: 1.6;
  }
  .pillar-value strong {
    display: block;
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: -0.005em;
    color: var(--violet-text);
    margin-bottom: 4px;
  }

  /* ============ BIBLIOGRAPHY ============ */
  .bib-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin-bottom: 1.8em;
    width: 100%;
  }
  .bib-group {
    background: #fcfcfd;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 22px 24px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
  }
  .bib-group:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }
  .bib-group h4 {
    font-size: 15px;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .bib-group h4 .bib-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--violet);
    flex-shrink: 0;
  }
  .bib-group ul {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 11px;
    margin: 0;
    padding: 0;
  }
  .bib-group li {
    font-size: 15px;
    color: #3d4654;
    line-height: 1.62;
    padding-left: 14px;
    position: relative;
  }
  .bib-group li::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.62em;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--border-strong);
  }
  .bib-group cite {
    font-style: italic;
    color: var(--ink-strong);
  }
  .bib-group a {
    color: var(--violet-text);
    text-decoration: none;
    border-bottom: 1px solid var(--lavender-border);
  }
  .bib-group a:hover {
    border-bottom-color: var(--violet);
    text-decoration: none;
  }
  .bib-group a cite {
    font-style: italic;
  }
  .bib-note {
    color: #6b7280;
  }
  .bib-foot {
    font-size: 15px;
    color: var(--muted);
    max-width: 60ch;
  }

  /* ============ RESOURCES ============ */
  .resources {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .res {
    display: flex;
    flex-direction: column;
    gap: 3px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: #fcfcfd;
    padding: 16px 18px;
    text-decoration: none !important;
    transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
  }
  .res:hover {
    border-color: var(--lavender-border);
    background: #fbfaff;
    transform: translateY(-1px);
    box-shadow: var(--shadow-hover);
  }
  .res-name {
    font-family: 'Geist', system-ui, sans-serif;
    font-weight: 600;
    font-size: 15px;
    color: var(--ink-strong);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .res-name::after {
    content: '\2197';
    font-size: 12px;
    color: var(--faint);
    transition: color 0.15s ease, transform 0.15s ease;
  }
  .res:hover .res-name {
    color: var(--violet-text);
  }
  .res:hover .res-name::after {
    color: var(--violet);
    transform: translate(1px, -1px);
  }
  .res-desc {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.45;
  }
  @media (max-width: 560px) {
    .resources {
      grid-template-columns: 1fr;
    }
  }

  /* ============ FOOTER ============ */
  .footer-card {
    position: relative;
    background: var(--dark);
    border-radius: 24px;
    padding: 56px;
    overflow: hidden;
    isolation: isolate;
    color: #fff;
    text-align: center;
    margin-bottom: 22px;
  }
  .footer-card::before {
    content: '';
    position: absolute;
    z-index: -1;
    width: 520px;
    height: 520px;
    border-radius: 50%;
    left: 50%;
    top: -300px;
    transform: translateX(-50%);
    background: radial-gradient(circle, rgba(124, 92, 255, 0.42), transparent 68%);
  }
  .foot-line {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: clamp(22px, 2.6vw, 28px);
    font-weight: 500;
    letter-spacing: -0.02em;
    line-height: 1.35;
    max-width: 24ch;
    margin: 0 auto 28px;
  }
  .foot-line em {
    font-style: normal;
    color: #a78bfa;
  }
  .footer-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 36px;
  }
  .foot-meta {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.45);
    line-height: 1.7;
  }
  .foot-meta a {
    color: rgba(255, 255, 255, 0.75);
  }
  .foot-meta a:hover {
    color: #fff;
  }

  /* ============ MOTION ============ */
  .reveal {
    opacity: 0;
    transform: translateY(18px);
    transition: opacity 0.65s cubic-bezier(0.2, 0.7, 0.2, 1), transform 0.65s cubic-bezier(0.2, 0.7, 0.2, 1);
  }
  .reveal:global(.in) {
    opacity: 1;
    transform: none;
  }
  .reveal-stagger > :global(*) {
    opacity: 0;
    transform: translateY(16px) scale(0.985);
    transition: opacity 0.6s cubic-bezier(0.2, 0.7, 0.2, 1), transform 0.6s cubic-bezier(0.2, 0.7, 0.2, 1);
  }
  .reveal-stagger:global(.in) > :global(*) {
    opacity: 1;
    transform: none;
  }
  .reveal-stagger:global(.in) > :global(*:nth-child(2)) {
    transition-delay: 0.07s;
  }
  .reveal-stagger:global(.in) > :global(*:nth-child(3)) {
    transition-delay: 0.14s;
  }
  .reveal-stagger:global(.in) > :global(*:nth-child(4)) {
    transition-delay: 0.21s;
  }
  .reveal-stagger:global(.in) > :global(*:nth-child(5)) {
    transition-delay: 0.28s;
  }
  .reveal-stagger:global(.in) > :global(*:nth-child(6)) {
    transition-delay: 0.35s;
  }
  .reveal-stagger:global(.in) > :global(*:nth-child(7)) {
    transition-delay: 0.42s;
  }
  .reveal-stagger:global(.in) > :global(*:nth-child(n + 8)) {
    transition-delay: 0.49s;
  }
  .reveal-stagger:global(.settled) > :global(*) {
    transition-delay: 0s !important;
  }

  @keyframes riseIn {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }
  .hero .chip {
    animation: riseIn 0.6s 0.05s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  }
  .hero h1 {
    animation: riseIn 0.7s 0.16s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  }
  .hero .hero-lede {
    animation: riseIn 0.7s 0.28s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  }
  .hero .hero-actions {
    animation: riseIn 0.7s 0.4s cubic-bezier(0.2, 0.7, 0.2, 1) both;
  }

  @keyframes glowDrift {
    0%,
    100% {
      transform: translate(0, 0);
    }
    50% {
      transform: translate(-36px, 22px);
    }
  }
  .hero::before,
  .pull::before,
  .stat-dark::before {
    animation: glowDrift 10s ease-in-out infinite;
  }
  @media (prefers-reduced-motion: reduce) {
    .reveal,
    .reveal-stagger > :global(*) {
      opacity: 1;
      transform: none;
      transition: none;
    }
    .hero .chip,
    .hero h1,
    .hero .hero-lede,
    .hero .hero-actions {
      animation: none;
    }
    .hero::before,
    .pull::before,
    .stat-dark::before {
      animation: none;
    }
  }

  /* ============ DIAGRAMS ============ */
  .diagram {
    background: #fcfcfd;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 26px 28px 22px;
    margin: 1.7em 0;
  }
  .diagram-title {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 12.5px;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: var(--violet-text);
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .diagram-title::before {
    content: '';
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--violet);
    box-shadow: 0 0 8px rgba(124, 92, 255, 0.6);
  }
  .diagram-cap {
    font-size: 13.5px;
    color: var(--muted);
    margin-top: 16px;
  }

  /* trust layers timeline */
  .timeline {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 14px;
    margin: 1.7em 0 0.4em;
    position: relative;
  }
  .timeline::before {
    content: '';
    position: absolute;
    left: 8px;
    right: 8px;
    top: 7px;
    height: 2px;
    background: var(--border);
    border-radius: 2px;
  }
  .tl-item {
    position: relative;
    padding-top: 26px;
  }
  .tl-item::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #fff;
    border: 2.5px solid var(--border-strong);
  }
  .tl-item.tl-now::before {
    border-color: var(--violet);
    background: var(--violet);
    box-shadow: 0 0 10px rgba(124, 92, 255, 0.65);
  }
  .tl-no {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--faint);
    display: block;
    letter-spacing: 0.04em;
  }
  .tl-name {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 13.5px;
    font-weight: 600;
    color: var(--ink-strong);
    display: block;
    margin: 2px 0 3px;
    line-height: 1.25;
  }
  .tl-era {
    font-size: 12px;
    color: var(--muted);
    line-height: 1.4;
    display: block;
  }
  .tl-now .tl-name {
    color: var(--violet-text);
  }
  .tl-now .tl-no {
    color: var(--violet);
  }
  @media (max-width: 1100px) {
    .timeline {
      grid-template-columns: repeat(4, 1fr);
      row-gap: 24px;
    }
    .timeline::before {
      display: none;
    }
  }
  @media (max-width: 640px) {
    .timeline {
      grid-template-columns: 1fr 1fr;
    }
  }

  /* internet court stack diagram */
  .ic-diagram {
    display: flex;
    gap: 14px;
    align-items: stretch;
  }
  .ic-bracket {
    flex-shrink: 0;
    width: 56px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    border: 1.5px solid var(--border-strong);
    border-radius: 10px;
    background: #fcfcfd;
    padding: 14px 0;
  }
  .ic-bracket-label {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    font-family: 'Geist', system-ui, sans-serif;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--ink-strong);
    white-space: nowrap;
  }
  .ic-bracket-sub {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    font-size: 10.5px;
    letter-spacing: 0.03em;
    color: var(--muted);
    white-space: nowrap;
  }
  .ic-stack {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .ic-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .ic-no {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 11.5px;
    font-weight: 700;
    color: var(--faint);
    width: 22px;
    flex-shrink: 0;
    text-align: right;
  }
  .ic-block {
    flex: 1;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    background: #fff;
    padding: 12px 16px;
  }
  .ic-name {
    font-family: 'Geist', system-ui, sans-serif;
    font-weight: 600;
    font-size: 14.5px;
    color: var(--ink-strong);
  }
  .ic-std {
    font-size: 12.5px;
    color: var(--muted);
  }
  .ic-row-genlayer .ic-block {
    border: 1.5px solid var(--violet);
    background: linear-gradient(180deg, #fbfaff, var(--lavender));
  }
  .ic-row-genlayer .ic-name {
    color: var(--violet-text);
  }
  .ic-row-genlayer .ic-std {
    color: var(--violet-text);
  }
  .ic-row-genlayer .ic-std strong {
    color: var(--violet-text);
    font-weight: 700;
  }
  .ic-tag {
    flex-shrink: 0;
    width: 118px;
    font-size: 11.5px;
    font-weight: 600;
    color: var(--violet-text);
    line-height: 1.35;
  }
  @media (max-width: 760px) {
    .ic-tag {
      display: none;
    }
    .ic-bracket {
      width: 46px;
    }
    .ic-bracket-sub {
      display: none;
    }
  }

  /* ============ LARGE SCREENS ============ */
  @media (min-width: 1500px) {
    .fd-page {
      font-size: 19px;
      padding: 32px;
      --ed-measure: 700px;
      --ed-gap: 60px;
      --ed-aside: 264px;
    }
    .shell {
      max-width: 1140px;
    }
  }
  @media (min-width: 1800px) {
    .fd-page {
      font-size: 20px;
      --ed-measure: 740px;
      --ed-gap: 64px;
      --ed-aside: 280px;
    }
    .shell {
      max-width: 1240px;
    }
  }

  /* ============ RESPONSIVE ============ */
  @media (max-width: 1120px) {
    .ed-section {
      display: block;
      padding: 40px 44px 44px;
    }
    .ed-aside {
      position: static;
      top: auto;
      margin-bottom: 28px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--border);
      max-width: none;
    }
    .ed-aside .ed-rule {
      display: none;
    }
    .ed-aside h2 {
      font-size: clamp(24px, 3vw, 30px);
    }
    .ed-aside .sec-lede {
      font-size: 1.02em;
      max-width: 62ch;
    }
    .ed-body,
    .prose {
      max-width: none;
    }
  }
  @media (max-width: 1180px) {
    .bento {
      grid-template-columns: repeat(2, 1fr);
    }
    .voices {
      grid-template-columns: 1fr 1fr;
    }
    .bib-grid {
      grid-template-columns: 1fr 1fr;
    }
  }
  @media (max-width: 899.98px) {
    .fd-page {
      padding: 16px;
    }
    .hero {
      padding: 44px 26px;
    }
    .ed-section {
      padding: 30px 24px 34px;
    }
    .ed-aside {
      margin-bottom: 24px;
      padding-bottom: 20px;
    }
    .bento {
      grid-template-columns: 1fr;
    }
    .stat-wide {
      grid-column: auto;
    }
    .layers-grid {
      grid-template-columns: 1fr;
    }
    .defs {
      grid-template-columns: 1fr;
    }
    .voices {
      grid-template-columns: 1fr;
    }
    .voice-wide {
      grid-column: auto;
    }
    .lines {
      grid-template-columns: 1fr;
    }
    .pillars {
      grid-template-columns: 1fr;
    }
    .bib-grid {
      grid-template-columns: 1fr;
    }
    .footer-card {
      padding: 44px 24px;
    }
    .pull {
      padding: 34px 26px 30px;
      font-size: 21px;
    }
    .pull::before {
      font-size: 140px;
      top: -0.28em;
    }
    .pillar-body {
      padding: 22px 22px 20px;
    }
    .pillar-value {
      padding: 16px 22px;
    }
    .prose p {
      font-size: 17px;
    }
  }
</style>
