
// Shared Nav Component — exports to window
const RecapNav = ({ authenticated = false, username = "alex" }) => (
  <nav style={{
    display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px',
    background: '#000', color: '#e2e8f0', padding: '8px 12px',
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif',
    fontWeight: 500, fontSize: 16, width: '100%', boxSizing: 'border-box'
  }}>
    <div style={{ flex: 1, minWidth: 0, fontSize: 18, fontWeight: 700 }}>
      <span style={{ fontWeight: 900 }}>Recap</span>
      <span style={{ fontWeight: 300, opacity: 0.7 }}> AI</span>
    </div>
    <div style={{ display: 'flex', gap: 16, shrink: 0, alignItems: 'center' }}>
      {authenticated ? <>
        <a href="#" style={navLink}>Home</a>
        <a href="#" style={navLink}>Profile</a>
        <a href="#" style={{ ...navLink, background: '#3b82f6', padding: '4px 12px', borderRadius: 6, textDecoration: 'none' }}>Logout</a>
      </> : <>
        <a href="#" style={navLink}>Login</a>
        <a href="#" style={{
          background: '#3b82f6', color: '#fff', padding: '6px 14px',
          borderRadius: 6, textDecoration: 'none', fontWeight: 600, fontSize: 14
        }}>Create Account →</a>
      </>}
    </div>
  </nav>
);

const navLink = {
  color: '#e2e8f0', textDecoration: 'underline', fontSize: 14,
  cursor: 'pointer'
};

Object.assign(window, { RecapNav, navLink });
