
// Homepage — Unauthenticated
const HomePage = ({ width = 390 }) => {
  const mobile = width < 768;
  const s = {
    page: { fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', background: '#f9fafb', minHeight: 600 },
    hero: {
      background: '#000', color: '#fff',
      padding: mobile ? '40px 20px 48px' : '64px 60px 72px',
      display: 'flex', flexDirection: mobile ? 'column' : 'row',
      gap: mobile ? 32 : 48, alignItems: 'center'
    },
    heroLeft: { flex: 1, minWidth: 0 },
    headline: {
      fontSize: mobile ? 32 : 48, fontWeight: 800, lineHeight: 1.1,
      letterSpacing: '-0.02em', marginBottom: 16, margin: '0 0 16px'
    },
    sub: {
      fontSize: mobile ? 15 : 18, color: '#94a3b8', lineHeight: 1.6,
      marginBottom: 28, margin: '0 0 28px', maxWidth: 460
    },
    ctaRow: { display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' },
    ctaPrimary: {
      background: '#3b82f6', color: '#fff', padding: '12px 24px',
      borderRadius: 8, fontWeight: 700, fontSize: 15, textDecoration: 'none',
      display: 'inline-block', cursor: 'pointer', border: 'none'
    },
    ctaSecondary: {
      color: '#94a3b8', fontSize: 14, textDecoration: 'underline', cursor: 'pointer'
    },
    heroRight: {
      flexShrink: 0, width: mobile ? '100%' : 340,
      display: 'flex', flexDirection: 'column', gap: 8
    },
    mockCard: {
      background: '#111827', borderRadius: 10, padding: '12px 14px',
      border: '1px solid #1f2937'
    },
    mockTitle: { color: '#f9fafb', fontWeight: 600, fontSize: 13, marginBottom: 4 },
    mockMeta: { color: '#6b7280', fontSize: 11, marginBottom: 6 },
    mockSummary: { color: '#9ca3af', fontSize: 11, lineHeight: 1.5 },
    mockBadge: {
      display: 'inline-block', background: '#1f2937', color: '#60a5fa',
      borderRadius: 99, padding: '2px 8px', fontSize: 10, fontWeight: 600, marginTop: 6
    },
    section: { padding: mobile ? '36px 20px' : '56px 60px' },
    sectionTitle: { fontSize: mobile ? 22 : 28, fontWeight: 700, color: '#111827', marginBottom: 8, margin: '0 0 8px' },
    sectionSub: { color: '#6b7280', fontSize: 14, marginBottom: 32, margin: '0 0 32px' },
    pillars: { display: 'grid', gridTemplateColumns: mobile ? '1fr' : '1fr 1fr 1fr', gap: 20 },
    pillar: { background: '#fff', borderRadius: 12, padding: '20px 20px 22px', boxShadow: '0 1px 4px rgba(0,0,0,0.07)' },
    pillarIcon: {
      width: 40, height: 40, borderRadius: 10, background: '#eff6ff',
      display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12
    },
    pillarTitle: { fontWeight: 700, fontSize: 15, color: '#111827', marginBottom: 6, margin: '0 0 6px' },
    pillarText: { color: '#6b7280', fontSize: 13, lineHeight: 1.6, margin: 0 },
    howSection: { padding: mobile ? '36px 20px' : '56px 60px', background: '#fff' },
    steps: { display: 'flex', flexDirection: mobile ? 'column' : 'row', gap: 24 },
    step: { flex: 1, display: 'flex', gap: 14, alignItems: 'flex-start' },
    stepNum: {
      width: 32, height: 32, borderRadius: '50%', background: '#3b82f6', color: '#fff',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontWeight: 700, fontSize: 14, flexShrink: 0
    },
    signupSection: {
      padding: mobile ? '40px 20px' : '64px 60px',
      background: 'linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 100%)',
      textAlign: 'center'
    },
    signupTitle: { color: '#fff', fontSize: mobile ? 24 : 32, fontWeight: 800, marginBottom: 8, margin: '0 0 8px' },
    signupSub: { color: '#bfdbfe', fontSize: 14, marginBottom: 28, margin: '0 0 28px' },
    signupForm: {
      background: '#fff', borderRadius: 12, padding: 24, maxWidth: 400,
      margin: '0 auto', boxShadow: '0 8px 32px rgba(0,0,0,0.2)'
    },
    input: {
      width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db',
      borderRadius: 6, padding: '10px 12px', fontSize: 14, marginBottom: 10,
      outline: 'none', fontFamily: 'inherit'
    },
    label: { fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 },
    submitBtn: {
      width: '100%', background: '#3b82f6', color: '#fff', border: 'none',
      borderRadius: 6, padding: '12px', fontWeight: 700, fontSize: 15, cursor: 'pointer'
    },
    footer: { padding: '20px', textAlign: 'center', color: '#9ca3af', fontSize: 12 }
  };

  return (
    <div style={s.page}>
      <RecapNav authenticated={false} />

      {/* Hero */}
      <div style={s.hero}>
        <div style={s.heroLeft}>
          <div style={{ color: '#60a5fa', fontSize: 12, fontWeight: 600, letterSpacing: '0.1em', marginBottom: 12, textTransform: 'uppercase' }}>
            Your personal reading memory
          </div>
          <h1 style={s.headline}>
            Bookmark it.<br />Recap will<br />remember it.
          </h1>
          <p style={s.sub}>
            Save any article from the web. Recap summarizes it, organizes it, and delivers a weekend digest for your morning coffee — all automatically.
          </p>
          <div style={s.ctaRow}>
            <button style={s.ctaPrimary}>Create free account →</button>
            <span style={s.ctaSecondary}>Already have an account? Sign in</span>
          </div>
        </div>

        {/* Mock article cards */}
        <div style={s.heroRight}>
          {[
            { title: 'The Future of AI in Healthcare', cat: 'Technology', summary: 'Researchers are exploring how LLMs can assist in early diagnosis…' },
            { title: 'Why Deep Work Matters More Than Ever', cat: 'Productivity', summary: 'Cal Newport argues that focused work is the competitive advantage…' },
            { title: 'Mediterranean Diet: New Findings', cat: 'Health', summary: 'A 10-year study confirms significant reduction in cardiovascular…' },
          ].map((a, i) => (
            <div key={i} style={{ ...s.mockCard, opacity: i === 0 ? 1 : i === 1 ? 0.85 : 0.6 }}>
              <div style={s.mockTitle}>{a.title}</div>
              <div style={s.mockSummary}>{a.summary}</div>
              <div style={s.mockBadge}>{a.cat}</div>
            </div>
          ))}
          <div style={{ textAlign: 'center', color: '#374151', fontSize: 11, marginTop: 4 }}>Your personalized reading library</div>
        </div>
      </div>

      {/* Value Pillars */}
      <div style={s.section}>
        <h2 style={s.sectionTitle}>Everything you want to read. Actually remembered.</h2>
        <p style={s.sectionSub}>Stop losing links in browser tabs and bookmarks folders.</p>
        <div style={s.pillars}>
          {[
            {
              title: 'Save from anywhere',
              text: 'Paste a URL, use our Chrome extension, or share from your iPhone. Recap captures it instantly.',
              color: '#eff6ff', icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                </svg>
              )
            },
            {
              title: 'AI summaries in seconds',
              text: 'Every article is summarized and categorized automatically. Scan the key ideas without reading the full piece.',
              color: '#f0fdf4', icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
                </svg>
              )
            },
            {
              title: 'Find it when you need it',
              text: 'Filter by your personal knowledge taxonomy. Get a weekly digest every weekend morning.',
              color: '#fefce8', icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#eab308" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              )
            }
          ].map((p, i) => (
            <div key={i} style={s.pillar}>
              <div style={{ ...s.pillarIcon, background: p.color }}>{p.icon}</div>
              <h3 style={s.pillarTitle}>{p.title}</h3>
              <p style={s.pillarText}>{p.text}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div style={s.howSection}>
        <h2 style={{ ...s.sectionTitle, marginBottom: 6 }}>How it works</h2>
        <p style={{ ...s.sectionSub, marginBottom: 32 }}>Three steps. Zero effort after setup.</p>
        <div style={s.steps}>
          {[
            { title: 'Bookmark', text: 'Paste a URL or click "Save to Recap" in Chrome. Takes 2 seconds.' },
            { title: 'Recap reads it', text: 'Our AI reads the full article and writes a clear summary, adding it to your knowledge library.' },
            { title: 'Review & discover', text: 'Browse summaries, filter by category, and get your weekend reading digest automatically.' }
          ].map((step, i) => (
            <div key={i} style={s.step}>
              <div style={s.stepNum}>{i + 1}</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14, color: '#111827', marginBottom: 4 }}>{step.title}</div>
                <div style={{ color: '#6b7280', fontSize: 13, lineHeight: 1.6 }}>{step.text}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sign Up CTA */}
      <div style={s.signupSection}>
        <h2 style={s.signupTitle}>Start building your reading memory</h2>
        <p style={s.signupSub}>Free to use. Your data is private by default.</p>
        <div style={s.signupForm}>
          <div style={{ textAlign: 'left', marginBottom: 16 }}>
            <div style={{ fontWeight: 700, fontSize: 18, color: '#111827', marginBottom: 4 }}>Create your account</div>
            <div style={{ fontSize: 13, color: '#6b7280' }}>Already have one? <span style={{ color: '#3b82f6', cursor: 'pointer' }}>Sign in</span></div>
          </div>
          <label style={s.label}>Username</label>
          <input style={s.input} placeholder="yourname" readOnly />
          <label style={s.label}>Email</label>
          <input style={s.input} placeholder="you@example.com" readOnly />
          <label style={s.label}>Password</label>
          <input style={s.input} type="password" placeholder="••••••••" readOnly />
          <button style={s.submitBtn}>Create free account →</button>
          <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 12, textAlign: 'center' }}>
            Your reading history is private by default.
          </div>
        </div>
      </div>

      <div style={s.footer}>© 2025 Recap AI. All rights reserved.</div>
    </div>
  );
};

Object.assign(window, { HomePage });
