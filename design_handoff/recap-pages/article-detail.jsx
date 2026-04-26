
// Article Detail Page
const ArticleDetail = ({ width = 390 }) => {
  const mobile = width < 768;

  const article = {
    title: 'The Attention Economy and Deep Work',
    author: 'Cal Newport',
    date: 'Apr 24, 2025',
    category: 'Productivity',
    source: 'nytimes.com',
    url: 'https://nytimes.com/example',
    summary: [
      'Newport argues that the ability to focus without distraction on cognitively demanding tasks — what he calls "deep work" — is becoming both increasingly rare and increasingly valuable in our economy.',
      'The attention economy, driven by social media platforms and notification-heavy software, systematically trains our brains to crave stimulation and resist sustained concentration. This has profound implications for knowledge workers.',
      'The author proposes a set of practices: scheduling deep work blocks, embracing boredom, quitting social media, and draining the shallows of low-value tasks. These habits, practiced consistently, can dramatically improve output quality and career capital.',
    ],
    subCategories: ['Focus & Flow', 'Career Development', 'Digital Minimalism'],
    keyTopics: ['Deep Work', 'Attention Economy', 'Knowledge Work', 'Cal Newport', 'Digital Distraction', 'Productivity Systems'],
    prev: { title: 'Mediterranean Diet: 10-Year Study Results', id: 3 },
    next: { title: 'Understanding Transformer Architecture', id: 2 },
  };

  const s = {
    page: { fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', background: '#f9fafb', minHeight: 600 },
    main: { padding: mobile ? '12px 12px' : '20px 32px' },
    layout: { display: mobile ? 'block' : 'flex', gap: 24, alignItems: 'flex-start' },
    content: { flex: 1, minWidth: 0 },
    backLink: { display: 'inline-flex', alignItems: 'center', gap: 6, color: '#6b7280', fontSize: 13, textDecoration: 'none', marginBottom: 16 },
    h1: { fontSize: mobile ? 22 : 26, fontWeight: 800, color: '#111827', lineHeight: 1.2, margin: '0 0 8px' },
    meta: { fontSize: 13, color: '#6b7280', marginBottom: 12 },
    badge: {
      display: 'inline-block', background: '#f3f4f6', borderRadius: 99,
      padding: '4px 12px', fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 20
    },
    para: { fontSize: 15, color: '#1f2937', lineHeight: 1.75, marginBottom: 16 },
    actions: { display: 'flex', gap: 10, flexWrap: 'wrap', margin: '24px 0' },
    readBtn: {
      display: 'inline-flex', alignItems: 'center', gap: 6,
      background: '#3b82f6', color: '#fff', borderRadius: 8,
      padding: '10px 20px', fontWeight: 700, fontSize: 14, textDecoration: 'none', border: 'none', cursor: 'pointer'
    },
    backBtn: {
      display: 'inline-flex', alignItems: 'center', gap: 6,
      background: '#fff', color: '#374151', borderRadius: 8,
      padding: '10px 20px', fontWeight: 600, fontSize: 14, textDecoration: 'none',
      border: '1px solid #d1d5db', cursor: 'pointer'
    },
    nav: {
      borderTop: '1px solid #e5e7eb', paddingTop: 16, marginTop: 8,
      display: 'flex', justifyContent: 'space-between', gap: 12
    },
    navBtn: (align) => ({
      flex: 1, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8,
      padding: '10px 14px', cursor: 'pointer', textAlign: align,
      textDecoration: 'none', display: 'block'
    }),
    navLabel: { fontSize: 11, color: '#9ca3af', display: 'block', marginBottom: 2 },
    navTitle: { fontSize: 13, fontWeight: 600, color: '#111827', lineHeight: 1.3 },
    sidebar: {
      width: mobile ? '100%' : 200, flexShrink: 0,
      marginTop: mobile ? 24 : 0
    },
    sidePanel: { background: '#e5e7eb', borderRadius: 10, padding: '16px', marginBottom: mobile ? 0 : 16 },
    sidePanelTitle: { fontWeight: 700, fontSize: 13, color: '#111827', marginBottom: 10 },
    sideItem: {
      display: 'block', padding: '6px 8px', borderRadius: 6, fontSize: 12,
      marginBottom: 4, wordBreak: 'break-word'
    },
  };

  return (
    <div style={s.page}>
      <RecapNav authenticated={true} />
      <div style={s.main}>
        <a href="#" style={s.backLink}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
          Back to articles
        </a>

        <div style={s.layout}>
          <div style={s.content}>
            <h1 style={s.h1}>{article.title}</h1>
            <div style={s.meta}>by {article.author} · {article.date} · <span style={{ color: '#9ca3af' }}>{article.source}</span></div>
            <span style={s.badge}>{article.category}</span>

            {article.summary.map((p, i) => <p key={i} style={s.para}>{p}</p>)}

            <div style={s.actions}>
              <a href={article.url} target="_blank" style={s.readBtn}>
                Read full article
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/>
                </svg>
              </a>
              <a href="#" style={s.backBtn}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 12H5M12 5l-7 7 7 7"/>
                </svg>
                Back to articles
              </a>
            </div>

            {/* Prev / Next navigation */}
            <div style={s.nav}>
              <a href="#" style={s.navBtn('left')}>
                <span style={s.navLabel}>← Previous</span>
                <span style={s.navTitle}>{article.prev.title}</span>
              </a>
              <a href="#" style={s.navBtn('right')}>
                <span style={s.navLabel}>Next →</span>
                <span style={s.navTitle}>{article.next.title}</span>
              </a>
            </div>
          </div>

          {/* Sidebar */}
          <div style={s.sidebar}>
            <div style={s.sidePanel}>
              <div style={s.sidePanelTitle}>Sub-Categories</div>
              {article.subCategories.map((c, i) => (
                <div key={i} style={{ ...s.sideItem, background: i % 2 === 0 ? '#fff' : '#f3f4f6' }}>{c}</div>
              ))}
            </div>
            <div style={{ ...s.sidePanel, marginTop: mobile ? 12 : 0 }}>
              <div style={s.sidePanelTitle}>Key Topics</div>
              {article.keyTopics.map((t, i) => (
                <div key={i} style={{ ...s.sideItem, background: i % 2 === 0 ? '#fff' : '#f3f4f6' }}>{t}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { ArticleDetail });
