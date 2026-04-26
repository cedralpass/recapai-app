
// Profile Page + Auth Pages (Login, Register)
const ProfilePage = ({ width = 390 }) => {
  const s = {
    page: { fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', background: '#f9fafb', minHeight: 500 },
    main: { padding: '20px 16px', maxWidth: 480, margin: '0 auto' },
    avatar: {
      width: 56, height: 56, borderRadius: '50%', background: '#1d4ed8',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#fff', fontWeight: 800, fontSize: 22, marginBottom: 12
    },
    name: { fontSize: 20, fontWeight: 800, color: '#111827', margin: '0 0 2px' },
    email: { fontSize: 13, color: '#6b7280', margin: '0 0 24px' },
    sectionTitle: { fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 },
    actionCard: {
      background: '#fff', borderRadius: 10, padding: '14px 16px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.07)', marginBottom: 10,
      display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer',
      textDecoration: 'none', border: '1px solid transparent'
    },
    iconBox: (bg) => ({
      width: 40, height: 40, borderRadius: 10, background: bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
    }),
    actionTitle: { fontWeight: 600, fontSize: 14, color: '#111827', margin: '0 0 2px' },
    actionDesc: { fontSize: 12, color: '#6b7280', margin: 0 },
    chevron: { marginLeft: 'auto', color: '#d1d5db' },
    divider: { height: 1, background: '#e5e7eb', margin: '20px 0' },
    dangerLink: { fontSize: 13, color: '#ef4444', textDecoration: 'underline', cursor: 'pointer' }
  };

  const actions = [
    {
      title: 'Edit Profile', desc: 'Update your email and phone number',
      bg: '#eff6ff', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
    },
    {
      title: 'Reclassify Articles', desc: 'Reorganize your knowledge taxonomy',
      bg: '#f0fdf4', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 6h16M4 12h10M4 18h14"/></svg>
    },
    {
      title: 'API Token', desc: 'Generate a token for integrations',
      bg: '#fef3c7', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
    },
  ];

  return (
    <div style={s.page}>
      <RecapNav authenticated={true} />
      <div style={s.main}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 28 }}>
          <div style={s.avatar}>A</div>
          <div>
            <div style={s.name}>alex</div>
            <div style={s.email}>alex@example.com</div>
          </div>
        </div>

        <div style={s.sectionTitle}>Account settings</div>
        {actions.map((a, i) => (
          <a key={i} href="#" style={s.actionCard}>
            <div style={s.iconBox(a.bg)}>{a.icon}</div>
            <div>
              <div style={s.actionTitle}>{a.title}</div>
              <div style={s.actionDesc}>{a.desc}</div>
            </div>
            <svg style={s.chevron} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </a>
        ))}

        <div style={s.divider}/>
        <div style={s.sectionTitle}>Stats</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 24 }}>
          {[['28', 'Bookmarks'], ['6', 'Categories'], ['4', 'This week']].map(([n, l], i) => (
            <div key={i} style={{ background: '#fff', borderRadius: 10, padding: '14px 10px', textAlign: 'center', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
              <div style={{ fontSize: 24, fontWeight: 800, color: '#111827' }}>{n}</div>
              <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{l}</div>
            </div>
          ))}
        </div>
        <span style={s.dangerLink}>Sign out</span>
      </div>
    </div>
  );
};

// Login Page
const LoginPage = ({ width = 390 }) => {
  const s = {
    page: { fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', background: '#f9fafb', minHeight: 500 },
    wrap: { padding: '32px 16px', maxWidth: 380, margin: '0 auto' },
    card: { background: '#fff', borderRadius: 12, padding: '28px 24px', boxShadow: '0 2px 12px rgba(0,0,0,0.09)' },
    logo: { fontWeight: 900, fontSize: 20, color: '#111827', marginBottom: 4 },
    title: { fontSize: 22, fontWeight: 800, color: '#111827', margin: '0 0 4px' },
    sub: { fontSize: 13, color: '#6b7280', margin: '0 0 24px' },
    label: { fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 },
    input: {
      width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db',
      borderRadius: 6, padding: '10px 12px', fontSize: 14, marginBottom: 14,
      outline: 'none', fontFamily: 'inherit'
    },
    checkRow: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20, fontSize: 13, color: '#374151' },
    btn: {
      width: '100%', background: '#3b82f6', color: '#fff', border: 'none',
      borderRadius: 6, padding: '11px', fontWeight: 700, fontSize: 15, cursor: 'pointer'
    },
    links: { display: 'flex', justifyContent: 'space-between', marginTop: 16, fontSize: 13 },
    link: { color: '#3b82f6', textDecoration: 'underline', cursor: 'pointer' },
  };

  return (
    <div style={s.page}>
      <RecapNav authenticated={false} />
      <div style={s.wrap}>
        <div style={s.card}>
          <div style={s.logo}>Recap AI</div>
          <h1 style={s.title}>Welcome back</h1>
          <p style={s.sub}>Don't have an account? <span style={s.link}>Create one free →</span></p>
          <label style={s.label}>Username</label>
          <input style={s.input} placeholder="yourname" readOnly />
          <label style={s.label}>Password</label>
          <input style={s.input} type="password" placeholder="••••••••" readOnly />
          <div style={s.checkRow}>
            <input type="checkbox" id="rem" readOnly />
            <label htmlFor="rem">Remember me</label>
          </div>
          <button style={s.btn}>Sign in →</button>
          <div style={s.links}>
            <span style={s.link}>Forgot password?</span>
            <span style={s.link}>Create account</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// Register Page
const RegisterPage = ({ width = 390 }) => {
  const s = {
    page: { fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', background: '#f9fafb', minHeight: 500 },
    wrap: { padding: '32px 16px', maxWidth: 380, margin: '0 auto' },
    card: { background: '#fff', borderRadius: 12, padding: '28px 24px', boxShadow: '0 2px 12px rgba(0,0,0,0.09)' },
    logo: { fontWeight: 900, fontSize: 20, color: '#111827', marginBottom: 4 },
    title: { fontSize: 22, fontWeight: 800, color: '#111827', margin: '0 0 4px' },
    sub: { fontSize: 13, color: '#6b7280', margin: '0 0 24px' },
    label: { fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 4 },
    input: {
      width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db',
      borderRadius: 6, padding: '10px 12px', fontSize: 14, marginBottom: 14,
      outline: 'none', fontFamily: 'inherit'
    },
    btn: {
      width: '100%', background: '#3b82f6', color: '#fff', border: 'none',
      borderRadius: 6, padding: '11px', fontWeight: 700, fontSize: 15, cursor: 'pointer', marginTop: 4
    },
    privacy: { fontSize: 11, color: '#9ca3af', textAlign: 'center', marginTop: 14 },
    link: { color: '#3b82f6', textDecoration: 'underline', cursor: 'pointer' },
  };

  return (
    <div style={s.page}>
      <RecapNav authenticated={false} />
      <div style={s.wrap}>
        <div style={s.card}>
          <div style={s.logo}>Recap AI</div>
          <h1 style={s.title}>Create your account</h1>
          <p style={s.sub}>Already have one? <span style={s.link}>Sign in</span></p>
          <label style={s.label}>Username</label>
          <input style={s.input} placeholder="yourname" readOnly />
          <label style={s.label}>Email</label>
          <input style={s.input} placeholder="you@example.com" readOnly />
          <label style={s.label}>Password</label>
          <input style={s.input} type="password" placeholder="••••••••" readOnly />
          <button style={s.btn}>Create free account →</button>
          <div style={s.privacy}>🔒 Your reading history is private by default.</div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { ProfilePage, LoginPage, RegisterPage });
