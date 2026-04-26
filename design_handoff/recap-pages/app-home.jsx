
// App Home — Authenticated (article list)
const AppHome = ({ width = 390 }) => {
  const mobile = width < 768;

  const articles = [
    { id: 1, title: 'The Attention Economy and Deep Work', author: 'Cal Newport', date: 'Apr 24, 2025', category: 'Productivity', summary: 'Newport argues that the ability to focus without distraction is increasingly rare and increasingly valuable. Companies that exploit attention are at odds with individual flourishing.', source: 'nytimes.com' },
    { id: 2, title: 'Understanding Transformer Architecture', author: 'Andrej Karpathy', date: 'Apr 22, 2025', category: 'Technology', summary: 'A deep dive into how self-attention mechanisms work, why they scale so well, and the architectural decisions that made GPT models possible.', source: 'karpathy.ai' },
    { id: 3, title: 'Mediterranean Diet: 10-Year Study Results', author: 'Dr. Sarah Chen', date: 'Apr 20, 2025', category: 'Health', summary: 'Participants following a traditional Mediterranean diet showed 28% lower rates of cardiovascular events compared to low-fat diet controls across a decade of follow-up.', source: 'nejm.org' },
    { id: 4, title: 'The Case for Four-Day Work Weeks', author: 'Andrew Barnes', date: 'Apr 18, 2025', category: 'Business', summary: 'Pilot programs across Iceland and New Zealand show productivity maintained or improved while employee wellbeing scores jumped significantly.', source: 'ft.com' },
  ];

  const categories = ['All', 'Productivity', 'Technology', 'Health', 'Business'];

  const s = {
    page: { fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', background: '#f9fafb', minHeight: 600 },
    main: { padding: mobile ? '12px 12px' : '16px 24px' },
    urlBox: {
      background: '#fff', borderRadius: 8, padding: '12px 14px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.08)', marginBottom: 16
    },
    urlLabel: { fontWeight: 700, fontSize: 15, color: '#111827', marginBottom: 8 },
    urlRow: { display: 'flex', gap: 8 },
    urlInput: {
      flex: 1, minWidth: 0, border: '1px solid #d1d5db', borderRadius: 6,
      padding: '8px 10px', fontSize: 14, fontFamily: 'inherit', outline: 'none'
    },
    urlBtn: {
      background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6,
      padding: '8px 16px', fontWeight: 700, fontSize: 14, cursor: 'pointer', flexShrink: 0
    },
    layout: { display: mobile ? 'block' : 'flex', gap: 20, alignItems: 'flex-start' },
    articleCol: { flex: 1, minWidth: 0, maxWidth: mobile ? '100%' : 620 },
    sidebar: {
      width: 220, flexShrink: 0, position: 'sticky', top: 8,
      display: mobile ? 'none' : 'block'
    },
    mobileFilter: {
      display: mobile ? 'flex' : 'none',
      gap: 6, overflowX: 'auto', marginBottom: 12, paddingBottom: 4
    },
    filterPill: (active) => ({
      background: active ? '#3b82f6' : '#e5e7eb', color: active ? '#fff' : '#374151',
      borderRadius: 99, padding: '6px 14px', fontSize: 12, fontWeight: 600,
      flexShrink: 0, cursor: 'pointer', border: 'none', whiteSpace: 'nowrap'
    }),
    sidebarTitle: { fontSize: 13, fontWeight: 700, color: '#374151', marginBottom: 8 },
    sidebarItem: (active) => ({
      display: 'block', padding: '8px 10px', borderRadius: 6, fontSize: 13,
      background: active ? '#dbeafe' : '#e5e7eb', color: active ? '#1d4ed8' : '#374151',
      fontWeight: active ? 600 : 400, marginBottom: 4, cursor: 'pointer', textDecoration: 'none'
    }),
    card: {
      background: '#fff', borderRadius: 8, padding: '12px 14px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.08)', marginBottom: 10
    },
    cardTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 4 },
    cardTitle: { fontWeight: 700, fontSize: 14, color: '#111827', lineHeight: 1.3, margin: 0 },
    cardDate: { fontSize: 11, color: '#9ca3af', flexShrink: 0, whiteSpace: 'nowrap' },
    cardAuthor: { fontSize: 12, color: '#6b7280', marginBottom: 6 },
    cardSummary: {
      fontSize: 13, color: '#374151', lineHeight: 1.55,
      display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
      overflow: 'hidden', marginBottom: 8
    },
    cardBottom: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
    badge: {
      display: 'inline-block', background: '#f3f4f6', borderRadius: 99,
      padding: '2px 10px', fontSize: 11, fontWeight: 600, color: '#374151'
    },
    cardRight: { display: 'flex', alignItems: 'center', gap: 10 },
    cardSource: { fontSize: 11, color: '#9ca3af', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
    cardLink: { fontSize: 13, fontWeight: 600, color: '#3b82f6', textDecoration: 'none' },
    sectionHead: { fontWeight: 700, fontSize: 15, color: '#111827', marginBottom: 10 },
  };

  return (
    <div style={s.page}>
      <RecapNav authenticated={true} />
      <div style={s.main}>
        {/* URL paste box */}
        <div style={s.urlBox}>
          <div style={s.urlLabel}>Save a new article</div>
          <div style={s.urlRow}>
            <input style={s.urlInput} placeholder="Paste a URL to bookmark and summarize…" readOnly />
            <button style={s.urlBtn}>Save</button>
          </div>
        </div>

        {/* Mobile filter pills */}
        <div style={s.mobileFilter}>
          {categories.map((c, i) => (
            <button key={i} style={s.filterPill(i === 0)}>{c}</button>
          ))}
        </div>

        <div style={s.layout}>
          {/* Article list */}
          <div style={s.articleCol}>
            <div style={s.sectionHead}>Your bookmarks</div>
            {articles.map(a => (
              <div key={a.id} style={s.card}>
                <div style={s.cardTop}>
                  <b style={s.cardTitle}>{a.title}</b>
                  <span style={s.cardDate}>{a.date}</span>
                </div>
                <div style={s.cardAuthor}>{a.author}</div>
                <p style={s.cardSummary}>{a.summary}</p>
                <div style={s.cardBottom}>
                  <span style={s.badge}>{a.category}</span>
                  <div style={s.cardRight}>
                    <span style={s.cardSource}>{a.source}</span>
                    <a href="#" style={s.cardLink}>View →</a>
                  </div>
                </div>
              </div>
            ))}
            {/* Pagination */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8, gap: 8 }}>
              <a href="#" style={{
                background: '#3b82f6', color: '#fff', borderRadius: 6,
                padding: '6px 14px', fontSize: 13, fontWeight: 600, textDecoration: 'none'
              }}>Older articles →</a>
            </div>
          </div>

          {/* Desktop sidebar */}
          <aside style={s.sidebar}>
            <div style={s.sidebarTitle}>Filter by category</div>
            {categories.map((c, i) => (
              <a key={i} href="#" style={s.sidebarItem(i === 0)}>
                {c} {i > 0 && <span style={{ float: 'right', opacity: 0.6 }}>{[12, 8, 5, 3][i - 1]}</span>}
              </a>
            ))}
          </aside>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { AppHome });
