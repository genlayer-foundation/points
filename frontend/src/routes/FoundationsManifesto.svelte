<script>
  import FoundationsShell from '../components/foundations/FoundationsShell.svelte';

  const TOC = [
    {
      id: 'decide',
      label: 'The Right to Decide',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4"/><path d="M12 18v4"/><path d="m4.93 4.93 2.83 2.83"/><path d="m16.24 16.24 2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><circle cx="12" cy="12" r="4"/></svg>',
    },
    {
      id: 'trust',
      label: 'The Technology of Trust',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    },
    {
      id: 'schelling',
      label: 'The Only Schelling Point',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><line x1="2" y1="12" x2="22" y2="12"/></svg>',
    },
    {
      id: 'disagree',
      label: 'When Software Must Disagree',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    },
    {
      id: 'believe',
      label: 'What We Believe',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    },
    {
      id: 'closing',
      label: 'The Circle Closing',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>',
    },
  ];

  const TOPBAR = [
    { kind: 'doc', key: 'compass', label: 'Compass' },
    { kind: 'section', id: 'decide', label: 'I Decide' },
    { kind: 'section', id: 'trust', label: 'II Trust' },
    { kind: 'section', id: 'schelling', label: 'III Truth' },
    { kind: 'section', id: 'disagree', label: 'IV Disagree' },
    { kind: 'section', id: 'believe', label: 'V Believe' },
    { kind: 'section', id: 'closing', label: 'VI Closing' },
    { kind: 'doc', key: 'whitepaper', label: 'Whitepaper' },
  ];
</script>

<FoundationsShell current="manifesto" toc={TOC} tocTitle="On this page" topbarBrand="Manifesto" topbarItems={TOPBAR}>
  <div class="fd-page">
    <div class="shell">
      <!-- HERO -->
      <header class="hero">
        <div class="hero-grid" aria-hidden="true"></div>
        <span class="chip"><span class="dot"></span>The GenLayer Manifesto</span>
        <h1>For the Right to <em>Decide</em></h1>
        <p class="hero-lede">Power is not wealth. Power is not status. Power is the ability to decide &mdash; and it is being silently concentrated into fewer and fewer hands. This is how it gets returned.</p>
        <div class="hero-actions">
          <button type="button" class="btn-hero" onclick={() => document.getElementById('decide')?.scrollIntoView({ behavior: 'smooth' })}>Start reading
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><polyline points="19 12 12 19 5 12" /></svg>
          </button>
          <a class="btn-ghost" href="/genesis/compass">Read the Compass</a>
        </div>
      </header>

      <!-- I — THE RIGHT TO DECIDE -->
      <section class="ed-section reveal" id="decide">
        <div class="ed-aside">
          <span class="mv-badge"><span class="mv-no">I</span>Movement One</span>
          <h2>The Right to Decide</h2>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <p class="lead">Power is not wealth. Power is not status. Power is not influence.</p>
            <blockquote class="pull">Power is the ability to <strong>decide</strong>.</blockquote>
            <p>Who decides what is true and what is false. Who decides what is fair and what is not. Who decides whether a contract was honored, a promise kept, a commitment met. Every institution humanity has ever built exists to answer one question: <strong>who gets to decide?</strong></p>
            <p>That question is being answered right now, in silence, at a speed humanity has never experienced. And almost no one is paying attention.</p>
            <p>We are living through a strange moment in history. What seemed certain a year ago no longer is. The ground shifts monthly. There is a feeling &mdash; you have probably felt it &mdash; that something fundamental is changing faster than anyone can name. Will I keep my job? Will my skills still matter? Will the world I understood still exist in two years? At the center of that anxiety are two words: <strong>artificial intelligence</strong>.</p>
            <p>It is in the algorithm that decides the next video you watch. The app that writes your emails. The system that determines whether your loan is approved, your resume is seen, your content is shown. It is already everywhere. And this is only the beginning. But the danger is not AI itself. The danger is something far less discussed: the unprecedented concentration of power in the hands of the few entities that build and control these systems.</p>
            <p>When you ask an AI a question, someone decides what it is allowed to say. When an AI makes a recommendation, someone decides what &ldquo;good&rdquo; means. When an AI judges, someone decides the rules by which it judges. They are the new kings. And unlike the old ones, they have no borders.</p>

            <div class="mv-rule" aria-hidden="true"><i></i></div>

            <p>What do the institutions behind the most powerful AI systems want?</p>
            <p>The answer is the one it has always been. <strong>Power.</strong></p>
            <p>The accumulation of power is the oldest pattern in human civilization, and, left unchecked, it has never once led anywhere good. But history&rsquo;s power holders had constraints. A pharaoh had a body that could be overthrown. A king had a family that could be threatened. A president has a term that expires. Every concentration of power in history has been limited by the physics of being human: the need to sleep, the fear of death, the finite hours in a day, the finite years in a life.</p>
            <p>Now consider a system with none of those constraints. A system that does not sleep. Cannot be jailed. Has no family to protect. Feels no fear. Operates across every border simultaneously. Never tires. Never hesitates.</p>
            <p>Each time AI gains agency, power flows out of human hands and into systems controlled by a shrinking number of institutions.</p>
            <p>This is not a conspiracy. It is not malice. It is the same gravitational pull toward power that has shaped every era of human history.</p>
            <p>The difference is that this time, the physics that once constrained power no longer apply.</p>
            <blockquote class="pull">If concentrated power has always led to corruption, imagine concentrated power without friction, without fatigue, without frontiers.</blockquote>
            <p>Does this mean we should stop it? Of course not.</p>
            <p>Every transformative technology was feared in its moment. And every time, history proved the same thing: the answer was never to stop the innovation. It was to decide who would control it, and by what rules. The question has never been whether to build. The question has always been: <strong>should any single institution concentrate so much power?</strong></p>
            <p>And here is the deeper pattern. Power concentrates because trust concentrates. Every time humanity has needed cooperation at scale, we have been forced to hand our trust to someone &mdash; a king, a court, a central bank, a platform &mdash; because that was the only technology we had for making cooperation work at scale.</p>
            <p><strong>Concentrate the trust, and you inevitably concentrate the power.</strong></p>
          </div>
        </div>
      </section>

      <!-- II — THE TECHNOLOGY OF TRUST -->
      <section class="ed-section reveal" id="trust">
        <div class="ed-aside">
          <span class="mv-badge"><span class="mv-no">II</span>Movement Two</span>
          <h2>The Technology of Trust</h2>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <p>To decentralize power, we must first understand trust.</p>
            <p>There is a sentence at the heart of every meaningful exchange in human history.</p>
            <blockquote class="pull"><strong>I trust you.</strong></blockquote>
            <p>It is the most valuable sentence in business and in love. It clears friction. It unlocks credit. It makes cooperation feel inevitable. It is also the most fragile sentence we know how to say, because the moment it is spoken, the speaker hands a piece of their certainty to someone else and stands exposed.</p>
            <p>We call this &ldquo;trust,&rdquo; but the word obscures what it actually is. Trust is not a feeling. It is a technology &mdash; a mechanism for reducing the complexity of a world too vast to verify in full.</p>
            <p>Without it, every breakfast becomes a negotiation. Every transaction becomes a lawsuit. Every stranger becomes a threat. Trust is what lets us lower our defenses long enough to build anything at all.</p>
            <p>And like any technology, trust evolves.</p>
            <p>Humanity has built trust in layers, each one extending the radius of cooperation beyond what the previous layer could reach. Personal trust: your tribe, limited to the roughly one hundred and fifty people a human mind can hold. Mythic trust: shared stories, religions, nations. Institutional trust: courts, legal codes, enforceable process. Market trust: contracts, insurance, the bill of exchange. Reputational trust: the ratings and reviews that recreated village gossip at internet scale. And then, in 2008, came a breakthrough no prior layer had achieved: Satoshi Nakamoto built a system in which trust could be replaced by mathematical proof.</p>
            <p>For the first time in history, a transaction could be settled without trusting any participant &mdash; only the math.</p>
            <p>But cryptographic trust has a ceiling. Bitcoin can prove that a coin moved. It cannot prove that a contract was honored. It cannot read a clause, weigh evidence, or interpret what &ldquo;reasonable efforts&rdquo; means.</p>
            <p>For everything that is not a coin flip, the cryptographic layer hands the problem back to the legal system &mdash; the system we have been failing to fix for nine hundred years. A seventh layer is now necessary. And for the first time, it is technically possible.</p>
          </div>
        </div>
      </section>

      <!-- III — THE ONLY SCHELLING POINT -->
      <section class="ed-section reveal" id="schelling">
        <div class="ed-aside">
          <span class="mv-badge"><span class="mv-no">III</span>Movement Three</span>
          <h2>The Only Schelling Point</h2>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <p>Humans do not dominate this planet only because we are the most intelligent species. We dominate because we coordinate our intelligences.</p>
            <p>Every great leap in civilization was a leap in coordination, extending the radius of trustworthy cooperation by another increment.</p>
            <p>The primary friction to coordination is trust. And the deepest insight about trust comes not from philosophy but from game theory.</p>
            <p>In 1960, Thomas Schelling proved that independent agents trying to coordinate without communication will converge on whichever option is the most natural focal point for all of them at once. He called it a Schelling point.</p>
            <p>The deepest version of his insight is this: <strong>truth is the only Schelling point a network of honest reasoners can find together.</strong> Falsehoods diverge in a thousand directions &mdash; there are infinite ways to be wrong, each inconsistent with the others. But truth has internal coherence. It is the only place independent minds, working separately, can reliably meet.</p>
            <p>This is why a network of diverse, uncoordinated AI models &mdash; each running in a different process, on a different machine, in a different jurisdiction &mdash; can produce reliable judgments on questions whose answers were never written down.</p>
            <blockquote class="pull">Honesty is not enforced by the protocol. It is the only equilibrium the protocol allows.</blockquote>
            <p>No single language model should ever hold the power to decide what is true.</p>
          </div>
        </div>
      </section>

      <!-- IV — WHEN SOFTWARE MUST DISAGREE -->
      <section class="ed-section reveal" id="disagree">
        <div class="ed-aside">
          <span class="mv-badge"><span class="mv-no">IV</span>Movement Four</span>
          <h2>When Software Must Disagree</h2>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <p>Until now, AI has worked alone. First answering questions, then performing tasks. But the evolution every serious technologist sees coming &mdash; the one that is a question not of <em>if</em> but of <em>when</em> &mdash; is agents transacting with agents.</p>
            <p>By 2030, AI agents will be running businesses, managing portfolios, signing contracts, and making deals at a velocity the existing institutional infrastructure cannot survive.</p>
            <p>They will outnumber human transactors by orders of magnitude. They will negotiate across jurisdictions that do not recognize their existence. They will disagree. They will disagree at machine speed. They will disagree about things that matter.</p>
            <p>Anything with marginal cost tending to zero will saturate. It is already happening &mdash; App Store submissions surged 84% in a single year as AI-generated apps flooded in by the hundreds of thousands. It will happen in commerce. It will happen in law. The cost of filing a thousand disputes in a day is tending to zero. The legal system, already buckling under human volume, will not survive contact with machine volume.</p>
            <p>The infrastructure for this economy is being built right now, in public, by serious people. Coinbase&rsquo;s x402 handles payments. ERC-8004 handles agent identity. A2A, backed by Google, Microsoft, AWS, Salesforce, and over 100 others, handles how agents discover each other and exchange tasks. Every one of them is engineered with extraordinary care for the moment everything goes right. None of them handles the moment something goes wrong. &ldquo;No formal dispute mechanism.&rdquo; &ldquo;Disputes are not defined within the protocol.&rdquo; Those words are taken from the specifications themselves. Every standard in the emerging stack assumes the happy path. And the moment a single material dispute reaches a system that cannot resolve it at the speed the money moved, the entire stack stalls.</p>

            <div class="diagram">
              <div class="diagram-title">The agentic-commerce stack, 2026</div>
              <div class="stack">
                <div class="stack-row stack-missing">
                  <div class="stack-block"><span class="sb-name">Adjudication</span><span class="sb-std">GenLayer</span></div>
                  <span class="stack-note">The missing layer &mdash; disputes, judgment, consequences</span>
                </div>
                <div class="stack-row">
                  <div class="stack-block"><span class="sb-name">Interoperability</span><span class="sb-std">A2A &middot; Linux Foundation</span></div>
                  <span class="stack-note">How agents discover each other and exchange tasks</span>
                </div>
                <div class="stack-row">
                  <div class="stack-block"><span class="sb-name">Identity &amp; reputation</span><span class="sb-std">ERC-8004 &middot; Ethereum</span></div>
                  <span class="stack-note">Trustless agent identity</span>
                </div>
                <div class="stack-row">
                  <div class="stack-block"><span class="sb-name">Payments</span><span class="sb-std">x402 &middot; Coinbase</span></div>
                  <span class="stack-note">Machine-speed money</span>
                </div>
              </div>
              <p class="diagram-cap">Every layer ships the happy path. None of them ships dispute resolution.</p>
            </div>
            <blockquote class="pull">The next economy will not fail because software cannot safely move money. It will fail because software cannot safely <strong>disagree</strong>.</blockquote>
          </div>
        </div>
      </section>

      <!-- V — WHAT WE BELIEVE -->
      <section class="ed-section reveal" id="believe">
        <div class="ed-aside">
          <span class="mv-badge"><span class="mv-no">V</span>Movement Five</span>
          <h2>What We Believe</h2>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <p>We did not arrive from nowhere. The cypherpunks dreamed of an internet that would unlock human freedom.</p>
            <p>Through the self-sovereignty of money, Bitcoin took the first step toward that vision. With the permissionless nature of Ethereum, we moved closer &mdash; building censorship-resistant platforms where anyone could create and express without permission.</p>
            <p>Kings enforce commitments through authority; democracies, through majorities. Blockchains are self-enforcing. You do not trust a person. You trust the code and the cryptoeconomics beneath it. But code alone was never enough. Smart contracts can enforce deterministic agreements perfectly, yet the agreements that matter most in commerce &mdash; the ones with judgment and interpretation and ambiguity baked into them &mdash; are the ones smart contracts cannot reach. The legal system reaches them badly: slow, expensive, biased. Cryptography does not reach them at all.</p>
            <p>What was missing was the intelligence to interpret and the coordination to judge. AI as the intelligence. Blockchain as the coordination.</p>
            <p><strong>GenLayer is the layer where they meet.</strong> What once seemed utopian is now technically possible. Not because we are optimists, but because the mathematics, the models, and the mechanism design have finally converged.</p>
            <blockquote class="pull">GenLayer is not a trust mechanism. It is a mechanism to <strong>substitute</strong> trust.</blockquote>
          </div>
        </div>
      </section>

      <!-- CREED — full-width lavender card -->
      <section class="creed reveal">
        <div class="creed-label">We believe</div>
        <ul class="reveal-stagger">
          <li>in a system designed not to hold power, but to <strong>return it</strong>.</li>
          <li>in a system owned by the people who run it, governed by the people who use it, accountable to no single entity.</li>
          <li>in a system that treats everyone the same, regardless of their status, where they live, or how they think.</li>
          <li>in a system accessible to everyone &mdash; not gated by wealth, not reserved for those who can afford to wait years for a verdict.</li>
          <li>in a system fast enough to match the speed of the world it serves. <strong>Justice in minutes, not months.</strong></li>
          <li>in a system ruled not by personal interest but by game theory, where the only winning strategy is honesty, and the only equilibrium is truth.</li>
          <li>in a system that makes us free. Because if someone with their own agenda can decide for you, you will never be free.</li>
          <li>that the vast majority of human agreements live in language, not in code, and a contract that cannot read the world cannot enforce itself in it.</li>
        </ul>
      </section>

      <!-- VI — THE CIRCLE CLOSING -->
      <section class="ed-section reveal" id="closing">
        <div class="ed-aside">
          <span class="mv-badge"><span class="mv-no">VI</span>Movement Six</span>
          <h2>The Circle Closing</h2>
          <div class="ed-rule"></div>
        </div>
        <div class="ed-body">
          <div class="prose">
            <p>We are fighting for a future where everyone stands equal &mdash; not before a judge who can be bought, not before an institution that serves those who built it, but before a system that is fair by design, incorruptible by architecture, and universal by nature.</p>
            <p>The organization that built this protocol was designed to disappear. The GenLayer Foundation exists to build the network, hand it to the people who run it, and dissolve.</p>
            <p>Because any institution that makes itself permanent eventually becomes the obstacle it was built to remove.</p>
            <p>Through the protocol, through the token, the power to participate, to govern, to adjudicate belongs to you. Not to a foundation. Not to a company. Not to a lab that decides what you are allowed to think. To you. To everyone. The same rules, the same access, the same voice, regardless of who you are or where you stand. This is the circle closing.</p>
            <p>The power to decide &mdash; the oldest form of power, the one being silently concentrated into fewer and fewer hands &mdash; is being returned.</p>
            <p>The agentic economy is arriving whether the infrastructure is ready or not. And if the infrastructure of adjudication is not decentralized before it calcifies, it will be captured &mdash; as every institution before it has been captured &mdash; by the few, at the expense of the many.</p>
          </div>
        </div>
      </section>

      <!-- FINAL — full-width dark card -->
      <section class="final reveal">
        <p>History will not ask what you knew.</p>
        <p>It will ask what you did when you knew it.</p>
        <p class="final-accent">The right to decide belongs to everyone. We are building a system that guarantees it.</p>
      </section>

      <!-- FOOTER -->
      <footer class="footer-card reveal">
        <a class="next-link" href="/genesis/compass">
          <span class="nl-label">Keep exploring</span>
          <span class="nl-title">&larr; The Compass &mdash; Worldview, Concept &amp; Mission</span>
        </a>
        <div class="foot-links">
          <a href="/genesis/whitepaper">Whitepaper</a>
          <a href="https://docs.genlayer.com" target="_blank" rel="noopener">Docs &#8599;</a>
          <a href="https://studio.genlayer.com" target="_blank" rel="noopener">Studio &#8599;</a>
          <a href="/">Portal &#8599;</a>
          <a href="https://github.com/genlayerlabs" target="_blank" rel="noopener">GitHub &#8599;</a>
          <a href="https://x.com/GenLayer" target="_blank" rel="noopener">X &#8599;</a>
          <a href="https://discord.gg/genlayerlabs" target="_blank" rel="noopener">Discord &#8599;</a>
          <a href="https://www.youtube.com/@GenLayer" target="_blank" rel="noopener">YouTube &#8599;</a>
        </div>
        <div class="foot-meta">
          GenLayer Labs &middot; GenLayer Foundation<br />
          <a href="https://genlayer.com" target="_blank" rel="noopener">genlayer.com &#8599;</a>
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
    --radius: 18px;
    --radius-sm: 12px;
    --shadow-card: 0 1px 2px rgba(16, 16, 16, 0.04), 0 1px 3px rgba(16, 16, 16, 0.03);
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
  .fd-page h2 {
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
    gap: 22px;
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
  }
  .hero::before {
    content: '';
    position: absolute;
    z-index: -1;
    width: 620px;
    height: 620px;
    border-radius: 50%;
    right: -160px;
    top: -300px;
    background: radial-gradient(circle, rgba(124, 92, 255, 0.5), rgba(124, 92, 255, 0.14) 45%, transparent 70%);
    filter: blur(8px);
  }
  .hero::after {
    content: '';
    position: absolute;
    z-index: -1;
    width: 460px;
    height: 460px;
    border-radius: 50%;
    left: -180px;
    bottom: -280px;
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
    mask-image: radial-gradient(ellipse 80% 80% at 50% 15%, black, transparent 75%);
    -webkit-mask-image: radial-gradient(ellipse 80% 80% at 50% 15%, black, transparent 75%);
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
    box-shadow: 0 0 8px rgba(124, 92, 255, 0.9);
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
    border: 0;
    cursor: pointer;
    font-family: inherit;
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
    border: 1px solid rgba(255, 255, 255, 0.22);
    font-size: 14.5px;
    font-weight: 500;
    padding: 11px 22px;
    border-radius: 9999px;
    text-decoration: none !important;
    transition: background 0.15s ease, border-color 0.15s ease;
  }
  .btn-ghost:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.4);
    text-decoration: none;
  }

  /* ============ EDITORIAL SIDENOTE — MOVEMENT CARDS ============ */
  .ed-section {
    display: grid;
    grid-template-columns: var(--ed-aside) minmax(0, 1fr);
    column-gap: var(--ed-gap);
    align-items: start;
    background: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-card);
    padding: 52px 56px 56px;
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
  .ed-aside .mv-badge {
    margin-bottom: 18px;
  }
  .ed-aside h2 {
    font-size: clamp(23px, 2.5vw, 29px);
    line-height: 1.2;
    margin: 0;
  }
  .ed-aside .ed-rule {
    height: 2px;
    width: 40px;
    border-radius: 2px;
    background: linear-gradient(90deg, var(--violet), rgba(124, 92, 255, 0.25));
    margin-top: 22px;
  }
  .mv-badge {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    background: var(--lavender);
    color: var(--violet-text);
    border: 1px solid var(--lavender-border);
    font-size: 12.5px;
    font-weight: 600;
    padding: 4px 13px 4px 8px;
    border-radius: 9999px;
  }
  .mv-badge .mv-no {
    display: inline-grid;
    place-items: center;
    min-width: 20px;
    height: 20px;
    background: #fff;
    border: 1px solid var(--lavender-border);
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }
  .ed-body {
    max-width: var(--ed-measure);
    min-width: 0;
  }

  /* ============ PROSE ============ */
  .prose {
    max-width: var(--ed-measure);
  }
  .prose p {
    font-size: 19px;
    line-height: 1.76;
    margin-bottom: 1.3em;
  }
  .prose p:first-child {
    margin-top: 0;
  }
  .prose p:last-child {
    margin-bottom: 0;
  }
  .prose strong {
    font-weight: 600;
    color: var(--ink-strong);
  }
  .prose em {
    font-style: italic;
  }
  .prose .lead {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 1.4em;
    font-weight: 500;
    letter-spacing: -0.025em;
    line-height: 1.4;
    color: var(--ink-strong);
    margin-bottom: 0.85em;
  }

  .mv-rule {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 2.2em 0;
    color: var(--faint);
  }
  .mv-rule::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border-strong);
  }
  .mv-rule i {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--violet);
    box-shadow: 0 0 8px rgba(124, 92, 255, 0.6);
  }

  /* ============ DARK PULL QUOTE ============ */
  .pull {
    position: relative;
    background: #0c0b11;
    color: #fff;
    border-radius: 16px;
    padding: 52px 54px 48px;
    margin: 2em 0;
    overflow: hidden;
    isolation: isolate;
    font-family: 'Geist', system-ui, sans-serif;
    font-size: clamp(25px, 3.1vw, 34px);
    font-weight: 500;
    letter-spacing: -0.03em;
    line-height: 1.26;
    box-shadow: 0 22px 50px -34px rgba(0, 0, 0, 0.6);
  }
  .pull::before {
    content: '\201C';
    position: absolute;
    z-index: -1;
    top: -0.26em;
    left: 0.02em;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: 220px;
    line-height: 1;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.05);
    pointer-events: none;
  }
  .pull strong {
    font-weight: 600;
    color: #a78bfa;
  }
  .pull em {
    font-style: italic;
    color: #c4b5fd;
  }

  /* ============ CREED — full-width lavender card ============ */
  .creed {
    background: linear-gradient(180deg, #fbfaff, var(--lavender));
    border: 1px solid var(--lavender-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-card);
    padding: 44px 48px;
    scroll-margin-top: 24px;
  }
  .creed .creed-label {
    font-family: 'Geist', sans-serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--violet-text);
    margin-bottom: 24px;
  }
  .creed ul {
    list-style: none;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 18px 40px;
    max-width: none;
    margin: 0;
    padding: 0;
  }
  .creed li {
    position: relative;
    padding-left: 26px;
    font-size: 17px;
    line-height: 1.6;
    color: #3b3550;
  }
  .creed li::before {
    content: '';
    position: absolute;
    left: 3px;
    top: 0.55em;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--violet);
  }
  .creed li strong {
    color: var(--violet-deep);
    font-weight: 600;
  }

  /* ============ FINAL — full-width dark card ============ */
  .final {
    position: relative;
    background: var(--dark);
    color: #fff;
    border-radius: var(--radius);
    padding: 64px 48px;
    overflow: hidden;
    isolation: isolate;
    text-align: center;
  }
  .final::before {
    content: '';
    position: absolute;
    z-index: -1;
    width: 520px;
    height: 520px;
    border-radius: 50%;
    left: 50%;
    top: -260px;
    transform: translateX(-50%);
    background: radial-gradient(circle, rgba(124, 92, 255, 0.4), transparent 66%);
  }
  .final p {
    font-family: 'Geist', sans-serif;
    font-size: clamp(24px, 3.4vw, 34px);
    font-weight: 500;
    letter-spacing: -0.025em;
    line-height: 1.3;
    max-width: 36ch;
    margin: 0 auto;
    color: rgba(255, 255, 255, 0.85);
    text-wrap: balance;
  }
  .final p + p {
    margin-top: 0.5em;
  }
  .final .final-accent {
    margin-top: 1.1em;
    color: #a78bfa;
  }

  /* ============ DIAGRAM ============ */
  .diagram {
    background: #fbfbfc;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 26px 28px 22px;
    margin: 1.8em 0;
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
  .stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .stack-row {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .stack-block {
    flex: 1;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    border: 1px solid var(--border-strong);
    border-radius: 10px;
    background: #f3f4f6;
    padding: 13px 18px;
  }
  .stack-block .sb-name {
    font-family: 'Geist', system-ui, sans-serif;
    font-weight: 600;
    font-size: 15px;
    color: var(--ink-strong);
  }
  .stack-block .sb-std {
    font-size: 13px;
    color: var(--muted);
  }
  .stack-note {
    flex-shrink: 0;
    width: 180px;
    font-size: 12.5px;
    color: var(--muted);
    line-height: 1.45;
  }
  .stack-missing .stack-block {
    border: 1.5px dashed var(--violet);
    background: linear-gradient(180deg, #fbfaff, var(--lavender));
  }
  .stack-missing .sb-name {
    color: var(--violet-text);
  }
  .stack-missing .sb-std {
    color: var(--violet-text);
    font-weight: 600;
  }
  .stack-missing .stack-note {
    color: var(--violet-text);
    font-weight: 500;
  }
  @media (max-width: 760px) {
    .stack-note {
      display: none;
    }
  }

  /* ============ FOOTER ============ */
  .footer-card {
    background: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-card);
    padding: 40px 48px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }
  .next-link {
    display: flex;
    flex-direction: column;
    gap: 5px;
    text-decoration: none !important;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 20px 24px;
    transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;
  }
  .next-link:hover {
    border-color: var(--lavender-border);
    background: #fbfaff;
    transform: translateY(-1px);
  }
  .next-link .nl-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--faint);
  }
  .next-link .nl-title {
    font-family: 'Geist', sans-serif;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--ink-strong);
  }
  .next-link:hover .nl-title {
    color: var(--violet-text);
  }
  .foot-meta {
    font-size: 13px;
    color: var(--muted);
    line-height: 1.7;
  }
  .foot-meta a {
    color: var(--violet-text);
  }
  .foot-links {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .foot-links a {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid var(--border);
    border-radius: 9999px;
    padding: 8px 16px;
    font-size: 13.5px;
    font-weight: 500;
    color: var(--ink-strong);
    text-decoration: none !important;
    transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
  }
  .foot-links a:hover {
    border-color: var(--lavender-border);
    background: #fbfaff;
    color: var(--violet-text);
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
  .reveal-stagger > li {
    opacity: 0;
    transform: translateY(14px);
    transition: opacity 0.55s cubic-bezier(0.2, 0.7, 0.2, 1), transform 0.55s cubic-bezier(0.2, 0.7, 0.2, 1);
  }
  .reveal-stagger:global(.in) > li {
    opacity: 1;
    transform: none;
  }
  .reveal-stagger:global(.in) > li:nth-child(2) {
    transition-delay: 0.07s;
  }
  .reveal-stagger:global(.in) > li:nth-child(3) {
    transition-delay: 0.14s;
  }
  .reveal-stagger:global(.in) > li:nth-child(4) {
    transition-delay: 0.21s;
  }
  .reveal-stagger:global(.in) > li:nth-child(5) {
    transition-delay: 0.28s;
  }
  .reveal-stagger:global(.in) > li:nth-child(6) {
    transition-delay: 0.35s;
  }
  .reveal-stagger:global(.in) > li:nth-child(7) {
    transition-delay: 0.42s;
  }
  .reveal-stagger:global(.in) > li:nth-child(n + 8) {
    transition-delay: 0.49s;
  }
  .reveal-stagger:global(.settled) > li {
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
  .pull::before {
    animation: glowDrift 10s ease-in-out infinite;
  }
  .final::before {
    animation: glowDrift 10s ease-in-out infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .reveal,
    .reveal-stagger > li {
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
    .final::before {
      animation: none;
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
    .ed-body,
    .prose {
      max-width: none;
    }
    .creed ul {
      grid-template-columns: 1fr;
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
    .creed {
      padding: 32px 24px;
    }
    .final {
      padding: 48px 26px;
    }
    .footer-card {
      padding: 32px 24px;
    }
    .pull {
      padding: 34px 26px 30px;
      font-size: 22px;
    }
    .pull::before {
      font-size: 140px;
      top: -0.28em;
    }
    .prose p {
      font-size: 17px;
    }
  }
</style>
