// Recap iOS — design references for the native SwiftUI app.
// Frame: iPhone 17 Pro, 402 × 874 pt. Native iOS chrome (SF font, large titles,
// tab bar) with Recap brand tokens (blue-500 accent, black brand mark, amber digest eyebrow).

const IOS = {
  font: '-apple-system, "SF Pro Text", system-ui, sans-serif',
  serif: 'Georgia, "Times New Roman", serif',
  bg: '#f2f2f7',          // systemGroupedBackground
  card: '#ffffff',
  label: '#111827',
  secondary: '#6b7280',
  tertiary: '#9ca3af',
  separator: '#e5e7eb',
  blue: '#3b82f6',        // Recap blue-500 (tint)
  blueDark: '#1d4ed8',
  amber: '#d97706',
  amberSoft: '#fffbeb',
  amberBorder: '#fcd34d',
};

const ARTICLES = [
  { id: 1, title: 'How Agents Can Improve LLM Performance', source: 'deeplearning.ai', author: 'Andrew Ng', date: 'Nov 24', category: 'Artificial Intelligence', unread: true,
    summary: 'Agentic workflows — reflection, tool use, planning and multi-agent collaboration — can lift a model’s results more than moving to the next model generation.',
    topics: ['AI agent workflows', 'Iterative process in AI', 'Design patterns for AI agents'] },
  { id: 2, title: 'From the Battlefield to the Boardroom', source: 'ivp.com', author: 'Gen. Richard D. Clarke (Ret.)', date: 'Nov 23', category: 'Leadership', unread: true,
    summary: 'Lessons from a 4-star general on over-communicating, setting clear standards, and adapting leadership style to a new team.' },
  { id: 3, title: 'Visual Guide to Vision Transformer', source: 'blog.mdturp.ch', author: 'Unknown', date: 'Nov 22', category: 'Artificial Intelligence', unread: false,
    summary: 'A step-by-step visual walkthrough of how ViTs split images into patches, embed them, and classify with self-attention.' },
  { id: 4, title: 'Optimizing RAG: Choosing the Right Vector Database', source: 'medium.com', author: 'mutahar789', date: 'Nov 21', category: 'Software Architecture', unread: false,
    summary: 'Architectural trade-offs between Pinecone, Weaviate and Chroma for production retrieval pipelines.' },
  { id: 5, title: 'Taking Risk', source: 'tomblomfield.com', author: 'Tom Blomfield', date: 'Nov 20', category: 'Leadership', unread: false,
    summary: 'Why UK and US cultures differ on entrepreneurial risk, and what that means for startups and venture capital.' },
  { id: 6, title: 'The Best Way to Have Complex Discussions', source: 'cq2.co', author: 'Unknown', date: 'Nov 19', category: 'Communication', unread: true, urlOnly: true,
    summary: 'Likely covers methods for structuring complex, multi-threaded discussions.' },
];

const CATEGORIES = ['All', 'Artificial Intelligence', 'Leadership', 'Software Architecture', 'Cooking'];

// ── Icons (SF Symbols approximations) ───────────────────────────────────────
const Icon = {
  search: (c = IOS.tertiary, s = 16) => (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.4" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>),
  list: (c) => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round"><path d="M8 6h13M8 12h13M8 18h13" /><circle cx="3.5" cy="6" r="1" fill={c} /><circle cx="3.5" cy="12" r="1" fill={c} /><circle cx="3.5" cy="18" r="1" fill={c} /></svg>),
  news: (c) => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinejoin="round"><path d="M4 5h13v14H6a2 2 0 0 1-2-2V5z" /><path d="M17 9h3v8a2 2 0 0 1-2 2" /><path d="M7 9h7M7 13h7M7 16h4" strokeLinecap="round" /></svg>),
  gear: (c) => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" strokeLinecap="round" /></svg>),
  chevronLeft: (c = IOS.blue) => (
    <svg width="12" height="20" viewBox="0 0 12 20" fill="none" stroke={c} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M10 2L2 10l8 8" /></svg>),
  share: (c = IOS.blue) => (
    <svg width="20" height="22" viewBox="0 0 20 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 15V2M5 6l5-5 5 5" /><path d="M6 10H3v12h14V10h-3" /></svg>),
  safari: (c = '#fff') => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M15.5 8.5l-2 5-5 2 2-5z" fill={c} /></svg>),
  warn: (c = IOS.amber) => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round"><path d="M12 3l10 18H2z" strokeLinejoin="round" /><path d="M12 10v5M12 18h.01" /></svg>),
  refresh: (c = '#fff') => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2.4" strokeLinecap="round"><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 4v7h-7" /></svg>),
  sparkle: (c = IOS.amber) => (
    <svg width="34" height="34" viewBox="0 0 24 24" fill={c}><path d="M12 2l2.2 6.3L20 10l-5.8 1.7L12 18l-2.2-6.3L4 10l5.8-1.7z" /><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z" /></svg>),
  check: (c = '#16a34a') => (
    <svg width="18" height="18" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill={c} /><path d="M7 12.5l3.2 3L17 9" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>),
  readDot: (c = IOS.blue) => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4" fill={c} /></svg>),
};

// ── Device chrome ────────────────────────────────────────────────────────────
const StatusBar = () => (
  <div style={{ height: 54, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 34px 0 44px', fontFamily: IOS.font, fontWeight: 600, fontSize: 17, position: 'relative' }}>
    <span>9:41</span>
    <div style={{ position: 'absolute', left: '50%', top: 11, transform: 'translateX(-50%)', width: 124, height: 36, borderRadius: 20, background: '#000' }} />
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <svg width="18" height="12" viewBox="0 0 18 12" fill="#000"><rect x="0" y="8" width="3" height="4" rx="1" /><rect x="5" y="5" width="3" height="7" rx="1" /><rect x="10" y="2.5" width="3" height="9.5" rx="1" /><rect x="15" y="0" width="3" height="12" rx="1" /></svg>
      <div style={{ width: 26, height: 13, border: '1.5px solid #000', borderRadius: 4, padding: 1.5 }}><div style={{ width: '80%', height: '100%', background: '#000', borderRadius: 1.5 }} /></div>
    </div>
  </div>
);

const HomeIndicator = () => (
  <div style={{ position: 'absolute', bottom: 8, left: '50%', transform: 'translateX(-50%)', width: 140, height: 5, borderRadius: 3, background: '#000' }} />
);

const TabBar = ({ active, digestDot = false }) => {
  const tabs = [
    { id: 'articles', label: 'Articles', icon: Icon.list },
    { id: 'digest', label: 'Digest', icon: Icon.news, dot: digestDot },
    { id: 'settings', label: 'Settings', icon: Icon.gear },
  ];
  return (
    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 92, background: 'rgba(249,249,249,0.96)', borderTop: `0.5px solid ${IOS.separator}`, display: 'flex', justifyContent: 'space-around', paddingTop: 8 }}>
      {tabs.map(t => {
        const c = t.id === active ? IOS.blue : '#8e8e93';
        return (
          <div key={t.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, width: 90, position: 'relative', fontFamily: IOS.font }}>
            {t.icon(c)}
            {t.dot && <div style={{ position: 'absolute', top: -2, left: 54, width: 9, height: 9, borderRadius: 5, background: IOS.amber, border: '2px solid #f9f9f9' }} />}
            <span style={{ fontSize: 10, fontWeight: 500, color: c }}>{t.label}</span>
          </div>
        );
      })}
      <HomeIndicator />
    </div>
  );
};

const Phone = ({ children, bg = IOS.bg }) => (
  <div style={{ width: 402, height: 874, background: bg, position: 'relative', overflow: 'hidden', fontFamily: IOS.font, color: IOS.label }}>
    <StatusBar />
    {children}
  </div>
);

const LargeTitle = ({ children, trailing }) => (
  <div style={{ padding: '4px 20px 8px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
    <h1 style={{ fontSize: 34, fontWeight: 700, letterSpacing: 0.3, margin: 0 }}>{children}</h1>
    {trailing}
  </div>
);

const SearchField = ({ value, focused }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 16px 10px' }}>
    <div style={{ flex: 1, height: 38, borderRadius: 12, background: 'rgba(118,118,128,0.12)', display: 'flex', alignItems: 'center', gap: 7, padding: '0 10px' }}>
      {Icon.search('#8e8e93')}
      <span style={{ fontSize: 17, color: value ? IOS.label : '#8e8e93' }}>{value || 'Search your articles'}</span>
      {focused && <span style={{ width: 2, height: 20, background: IOS.blue, marginLeft: -5 }} />}
    </div>
    {focused && <span style={{ color: IOS.blue, fontSize: 17 }}>Cancel</span>}
  </div>
);

const CategoryPill = ({ label, active, count }) => (
  <div style={{ flexShrink: 0, padding: '7px 14px', borderRadius: 99, fontSize: 14, fontWeight: 600, background: active ? IOS.blue : '#fff', color: active ? '#fff' : '#374151', boxShadow: active ? 'none' : '0 0 0 0.5px #d1d5db', whiteSpace: 'nowrap' }}>
    {label}{count != null && <span style={{ opacity: 0.6, marginLeft: 5, fontWeight: 500 }}>{count}</span>}
  </div>
);

const CategoryBadge = ({ label }) => (
  <span style={{ display: 'inline-block', background: '#f3f4f6', borderRadius: 99, padding: '3px 10px', fontSize: 12, fontWeight: 600, color: '#374151' }}>{label}</span>
);

const highlight = (text, q) => {
  if (!q) return text;
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  if (i < 0) return text;
  return <>{text.slice(0, i)}<mark style={{ background: '#fef08a', color: 'inherit', borderRadius: 3, padding: '0 1px' }}>{text.slice(i, i + q.length)}</mark>{text.slice(i + q.length)}</>;
};

const ArticleCard = ({ a, q }) => (
  <div style={{ background: IOS.card, borderRadius: 14, padding: '14px 16px', marginBottom: 10, position: 'relative' }}>
    {a.unread && <div style={{ position: 'absolute', left: 6, top: 20, width: 7, height: 7, borderRadius: 4, background: IOS.blue }} />}
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 4 }}>
      <div style={{ fontSize: 16, fontWeight: 600, lineHeight: 1.3, color: a.unread ? IOS.label : '#374151' }}>{highlight(a.title, q)}</div>
      <div style={{ fontSize: 13, color: IOS.tertiary, flexShrink: 0 }}>{a.date}</div>
    </div>
    {a.urlOnly ? (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#92400e', margin: '6px 0 10px' }}>{Icon.warn()} Summary not available — tap to read</div>
    ) : (
      <div style={{ fontSize: 14, color: '#4b5563', lineHeight: 1.45, margin: '2px 0 10px', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{highlight(a.summary, q)}</div>
    )}
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <CategoryBadge label={a.category} />
      <span style={{ fontSize: 12, color: IOS.tertiary }}>{a.source}</span>
    </div>
  </div>
);

const SectionLabel = ({ children }) => (
  <div style={{ fontSize: 13, color: IOS.secondary, textTransform: 'uppercase', letterSpacing: 0.4, margin: '4px 4px 8px' }}>{children}</div>
);

// ── 1. Articles (home) ───────────────────────────────────────────────────────
const Keyboard = () => {
  const rows = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm'];
  return (
    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 300, background: '#d1d3d9', padding: '10px 4px 0' }}>
      {rows.map((r, i) => (
        <div key={r} style={{ display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 12 }}>
          {i === 2 && <div style={{ width: 44, height: 44, borderRadius: 6, background: '#abb0ba' }} />}
          {r.split('').map(k => <div key={k} style={{ width: 33, height: 44, borderRadius: 6, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, boxShadow: '0 1px 0 #898a8d' }}>{k}</div>)}
          {i === 2 && <div style={{ width: 44, height: 44, borderRadius: 6, background: '#abb0ba' }} />}
        </div>
      ))}
      <div style={{ display: 'flex', gap: 6, padding: '0 4px' }}>
        <div style={{ width: 88, height: 44, borderRadius: 6, background: '#abb0ba' }} />
        <div style={{ flex: 1, height: 44, borderRadius: 6, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>space</div>
        <div style={{ width: 88, height: 44, borderRadius: 6, background: IOS.blue, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>search</div>
      </div>
    </div>
  );
};

const ArticlesScreen = ({ state = 'list' }) => {
  const searching = state === 'search';
  const q = searching ? 'agent' : '';
  const list = searching
    ? [ARTICLES[0], { ...ARTICLES[2], title: 'Train Your Own LLM with Metaflow', summary: 'Using agent-style orchestration in Metaflow to fine-tune and deploy Databricks’ Dolly.' }]
    : ARTICLES;
  const counts = { 'All': 53, 'Artificial Intelligence': 27, 'Leadership': 10, 'Software Architecture': 6, 'Cooking': 3 };
  return (
    <Phone>
      {searching ? <div style={{ height: 8 }} /> : (
        <LargeTitle trailing={<div style={{ width: 34, height: 34, borderRadius: 9, background: '#000', color: '#fff', fontWeight: 800, fontSize: 18, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 6 }}>R</div>}>Articles</LargeTitle>
      )}
      <SearchField value={q} focused={searching} />
      {!searching && (
        <div style={{ display: 'flex', gap: 8, overflow: 'hidden', padding: '2px 16px 12px' }}>
          {CATEGORIES.map((c, i) => <CategoryPill key={c} label={c} active={i === 0} count={counts[c]} />)}
        </div>
      )}
      <div style={{ padding: '0 16px' }}>
        <SectionLabel>{searching ? `${list.length} results for “${q}”` : 'Recently saved'}</SectionLabel>
        {list.map(a => <ArticleCard key={a.id + a.title} a={a} q={q} />)}
      </div>
      {searching ? <Keyboard /> : <TabBar active="articles" digestDot />}
    </Phone>
  );
};

// ── 2. Article detail ────────────────────────────────────────────────────────
const NavBar = ({ back, trailing }) => (
  <div style={{ height: 44, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px 0 10px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: IOS.blue, fontSize: 17 }}>{Icon.chevronLeft()}<span>{back}</span></div>
    <div style={{ display: 'flex', gap: 22, alignItems: 'center' }}>{trailing}</div>
  </div>
);

const ArticleDetailScreen = ({ variant = 'summary' }) => {
  const blocked = variant === 'blocked';
  const a = blocked ? ARTICLES[5] : ARTICLES[0];
  return (
    <Phone bg="#fff">
      <NavBar back="Articles" trailing={<>{Icon.readDot()}{Icon.share()}</>} />
      <div style={{ padding: '10px 22px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <CategoryBadge label={a.category} />
          <span style={{ fontSize: 13, color: IOS.tertiary }}>Saved {a.date}</span>
        </div>
        <h1 style={{ fontSize: 28, fontWeight: 700, lineHeight: 1.18, letterSpacing: -0.2, margin: '0 0 10px' }}>{a.title}</h1>
        <div style={{ fontSize: 15, color: IOS.secondary, marginBottom: 20 }}>{a.author !== 'Unknown' ? `${a.author} · ` : ''}{a.source}</div>

        {blocked ? (
          <div style={{ background: IOS.amberSoft, border: `1px solid ${IOS.amberBorder}`, borderRadius: 14, padding: '14px 16px', marginBottom: 22 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 600, fontSize: 15, color: '#92400e', marginBottom: 6 }}>{Icon.warn('#b45309')} Summary not available</div>
            <div style={{ fontSize: 14, color: '#78350f', lineHeight: 1.45 }}>This site blocked Recap from reading it, so the category is a guess from the link. Open it in Safari and tap <b>Share → Recap</b> to send the full text.</div>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 13, fontWeight: 600, color: IOS.secondary, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 }}>Summary</div>
            <p style={{ fontSize: 17, lineHeight: 1.55, color: '#1f2937', margin: '0 0 22px' }}>
              Andrew Ng argues that agentic workflows — letting a model reflect on and revise its output, call tools, plan multi-step work and collaborate with other agents — can improve results more than upgrading to the next model generation. He walks through each design pattern with examples from coding benchmarks.
            </p>
            <div style={{ fontSize: 13, fontWeight: 600, color: IOS.secondary, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>Key topics</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
              {a.topics.map(t => (
                <div key={t} style={{ display: 'flex', gap: 10, alignItems: 'center', fontSize: 16, color: '#374151' }}>
                  <span style={{ width: 6, height: 6, borderRadius: 3, background: IOS.blue, flexShrink: 0 }} />{t}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, padding: '14px 20px 42px', background: 'linear-gradient(rgba(255,255,255,0), #fff 30%)' }}>
        <div style={{ height: 52, borderRadius: 14, background: IOS.blue, color: '#fff', fontSize: 17, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          {Icon.safari()} Read article
        </div>
        <div style={{ textAlign: 'center', fontSize: 12, color: IOS.tertiary, marginTop: 8 }}>Opens in Safari view · marks as read</div>
        <HomeIndicator />
      </div>
    </Phone>
  );
};

// ── 3. Digest ────────────────────────────────────────────────────────────────
const CLUSTERS = [
  { label: 'Agents are eating the model roadmap', narrative: 'Three of your saves this week argue the same thing from different angles: better scaffolding — reflection, tools, planning — now beats waiting for a bigger model.',
    articles: ['How Agents Can Improve LLM Performance', 'Consistency Large Language Models (CLLMs)', 'Train Your Own LLM with Metaflow'] },
  { label: 'Leading through clarity', narrative: 'A general and a founder agree: say the expectation out loud, then say it again. Risk-taking follows from teams that know where the line is.',
    articles: ['From the Battlefield to the Boardroom', 'Taking Risk'] },
];

const DigestScreen = () => (
  <Phone bg="#fafaf9">
    <LargeTitle>Digest</LargeTitle>
    <div style={{ margin: '4px 16px 12px', background: IOS.amberSoft, border: `1px solid ${IOS.amberBorder}`, borderRadius: 12, padding: '10px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
      <div style={{ fontSize: 14, color: '#78350f', lineHeight: 1.35 }}><b>4 new bookmarks</b> since this digest.</div>
      <div style={{ background: '#0f172a', color: '#fff', borderRadius: 8, padding: '7px 11px', fontSize: 13, fontWeight: 700, display: 'flex', gap: 6, alignItems: 'center', whiteSpace: 'nowrap' }}>{Icon.refresh()} Regenerate</div>
    </div>
    <div style={{ margin: '0 16px', background: '#fff', borderRadius: 16, boxShadow: '0 1px 3px rgba(0,0,0,0.06)', overflow: 'hidden' }}>
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid #f1f5f9' }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase', color: IOS.amber, marginBottom: 6 }}>Recap · Week of November 17</div>
        <div style={{ fontFamily: IOS.serif, fontSize: 26, fontWeight: 700, color: '#0f172a', lineHeight: 1.1, marginBottom: 6 }}>Your Weekly Recap</div>
        <div style={{ fontSize: 14, color: '#64748b' }}>12 articles · 4 topics</div>
      </div>
      <div style={{ padding: '6px 20px 14px' }}>
        {CLUSTERS.map((c, i) => (
          <div key={c.label} style={{ padding: '14px 0', borderBottom: i < CLUSTERS.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
            <div style={{ fontFamily: IOS.serif, fontSize: 19, fontWeight: 700, color: '#0f172a', lineHeight: 1.25, marginBottom: 6 }}>{c.label}</div>
            <div style={{ fontSize: 15, lineHeight: 1.5, color: '#334155', marginBottom: 10 }}>{c.narrative}</div>
            {c.articles.map(t => <div key={t} style={{ fontSize: 14, color: IOS.blueDark, padding: '3px 0', display: 'flex', gap: 6 }}><span style={{ color: IOS.tertiary }}>→</span>{t}</div>)}
          </div>
        ))}
      </div>
    </div>
    <TabBar active="digest" />
  </Phone>
);

const DigestEmptyScreen = () => (
  <Phone bg="#fafaf9">
    <LargeTitle>Digest</LargeTitle>
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '130px 40px 0' }}>
      <div style={{ width: 72, height: 72, borderRadius: 20, background: IOS.amberSoft, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>{Icon.sparkle()}</div>
      <div style={{ fontFamily: IOS.serif, fontSize: 24, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>No digest yet this week</div>
      <div style={{ fontSize: 16, color: IOS.secondary, lineHeight: 1.45, marginBottom: 26 }}>You’ve saved <b style={{ color: IOS.label }}>9 articles</b> since your last recap. Recap can group them into themes and pull out what matters.</div>
      <div style={{ height: 50, width: 240, borderRadius: 14, background: '#0f172a', color: '#fff', fontSize: 17, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 14 }}>Generate digest</div>
      <div style={{ fontSize: 13, color: IOS.tertiary }}>Takes about a minute · it will appear here</div>
    </div>
    <TabBar active="digest" />
  </Phone>
);

// ── 4. Settings + share confirmation (continuity with what's built) ─────────
const SettingsScreen = () => {
  const Row = ({ children, last }) => <div style={{ padding: '12px 16px', borderBottom: last ? 'none' : `0.5px solid ${IOS.separator}`, fontSize: 17 }}>{children}</div>;
  const Group = ({ header, footer, children }) => (
    <div style={{ margin: '0 16px 22px' }}>
      {header && <div style={{ fontSize: 13, color: IOS.secondary, textTransform: 'uppercase', margin: '0 16px 6px' }}>{header}</div>}
      <div style={{ background: '#fff', borderRadius: 12, overflow: 'hidden' }}>{children}</div>
      {footer && <div style={{ fontSize: 13, color: IOS.secondary, margin: '6px 16px 0', lineHeight: 1.35 }}>{footer}</div>}
    </div>
  );
  return (
    <Phone>
      <LargeTitle>Settings</LargeTitle>
      <div style={{ height: 8 }} />
      <Group header="Account" footer="Find your token in Recap under Settings → API Token.">
        <Row><span style={{ color: IOS.secondary, fontSize: 13, display: 'block' }}>Server</span>https://dev.recaprai.com</Row>
        <Row last><span style={{ color: IOS.secondary, fontSize: 13, display: 'block' }}>API token</span>•••••••••••••••••••••• <span style={{ color: IOS.blue, float: 'right' }}>Show</span></Row>
      </Group>
      <Group header="Share extension">
        <Row><span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>{Icon.check()} Connected — last save 2 min ago</span></Row>
        <Row last><span style={{ color: IOS.blue }}>How to add Recap to the share sheet</span></Row>
      </Group>
      <Group header="More">
        <Row last><span style={{ display: 'flex', justifyContent: 'space-between' }}>Open Recap on the web <span style={{ color: IOS.tertiary }}>↗</span></span></Row>
      </Group>
      <TabBar active="settings" />
    </Phone>
  );
};

const ShareSheetScreen = () => (
  <Phone bg="#9ca3af">
    <div style={{ position: 'absolute', left: 16, right: 16, top: 330, background: '#fff', borderRadius: 22, padding: 20, boxShadow: '0 10px 40px rgba(0,0,0,0.2)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}><b style={{ fontSize: 17 }}>Recap</b><span style={{ color: IOS.blue, fontSize: 17 }}>Done</span></div>
      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 2 }}>How Agents Can Improve LLM Performance</div>
      <div style={{ fontSize: 12, color: IOS.secondary, marginBottom: 14, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>https://www.deeplearning.ai/the-batch/how-agents-can-improve…</div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: '#16a34a', fontSize: 15 }}>{Icon.check()} Saved! Recap is summarizing it.</div>
    </div>
    <HomeIndicator />
  </Phone>
);

Object.assign(window, { ArticlesScreen, ArticleDetailScreen, DigestScreen, DigestEmptyScreen, SettingsScreen, ShareSheetScreen });
