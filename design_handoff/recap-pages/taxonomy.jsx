
// Taxonomy / Organize Page — redesigned
const TaxonomyPage = ({ width = 390 }) => {
  const mobile = width < 768;
  const [accepted, setAccepted] = React.useState({ merge1: true });
  const [applied, setApplied] = React.useState(false);

  const current = [
    { name: 'Software Architecture', count: 3, type: 'unchanged' },
    { name: 'Cooking and Recipes', count: 2, type: 'unchanged' },
    { name: 'Artificial Intelligence', count: 1, type: 'unchanged' },
    { name: 'Business Strategy', count: 1, type: 'merging', mergeId: 'merge1' },
    { name: 'Contract Management', count: 1, type: 'merging', mergeId: 'merge1', isNew: true },
  ];

  const suggestions = [
    {
      id: 'merge1',
      type: 'merge',
      from: ['Business Strategy', 'Contract Management'],
      to: 'Business Operations',
      toCount: 2,
      reason: 'These categories share strong thematic overlap around running and managing a business. Merging them reduces fragmentation.',
    },
  ];

  const proposed = [
    { name: 'Software Architecture', count: 3, type: 'unchanged' },
    { name: 'Cooking and Recipes', count: 2, type: 'unchanged' },
    { name: 'Artificial Intelligence', count: 1, type: 'unchanged' },
    { name: 'Business Operations', count: 2, type: 'merged', mergeId: 'merge1' },
  ];

  const colors = {
    unchanged: { bg: '#f9fafb', border: '#e5e7eb', text: '#374151', badge: '#e5e7eb', badgeText: '#6b7280' },
    merging:   { bg: '#fffbeb', border: '#fcd34d', text: '#92400e', badge: '#fef3c7', badgeText: '#92400e' },
    merged:    { bg: '#f0fdf4', border: '#86efac', text: '#166534', badge: '#dcfce7', badgeText: '#166534' },
    new:       { bg: '#eff6ff', border: '#93c5fd', text: '#1e40af', badge: '#dbeafe', badgeText: '#1e40af' },
  };

  const CategoryChip = ({ name, count, type, isNew, dim }) => {
    const c = colors[type] || colors.unchanged;
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 12px', borderRadius: 8,
        background: dim ? '#f9fafb' : c.bg,
        border: `1.5px solid ${dim ? '#e5e7eb' : c.border}`,
        opacity: dim ? 0.45 : 1,
        marginBottom: 6, gap: 8
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, minWidth: 0 }}>
          {isNew && (
            <span style={{ fontSize: 9, fontWeight: 700, background: '#dbeafe', color: '#1e40af', borderRadius: 4, padding: '1px 5px', flexShrink: 0 }}>NEW</span>
          )}
          <span style={{ fontSize: 13, fontWeight: 600, color: dim ? '#9ca3af' : c.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</span>
        </div>
        <span style={{
          fontSize: 11, fontWeight: 700, background: dim ? '#f3f4f6' : c.badge,
          color: dim ? '#9ca3af' : c.badgeText,
          borderRadius: 99, padding: '2px 8px', flexShrink: 0
        }}>{count}</span>
      </div>
    );
  };

  const s = {
    page: { fontFamily: 'ui-sans-serif, system-ui, -apple-system, sans-serif', background: '#f9fafb', minHeight: 600 },
    main: { padding: mobile ? '16px 12px' : '24px 32px', maxWidth: 900, margin: '0 auto' },
    heading: { fontSize: mobile ? 20 : 24, fontWeight: 800, color: '#111827', margin: '0 0 4px' },
    sub: { fontSize: 13, color: '#6b7280', margin: '0 0 24px' },
    diffGrid: {
      display: 'grid',
      gridTemplateColumns: mobile ? '1fr' : '1fr 40px 1fr',
      gap: mobile ? 16 : 0,
      alignItems: 'start',
      marginBottom: 24
    },
    colHead: { fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 },
    arrowCol: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingTop: mobile ? 0 : 64 },
    divider: { height: 1, background: '#e5e7eb', margin: '20px 0' },
    suggestionCard: (acc) => ({
      background: '#fff', borderRadius: 10,
      border: `1.5px solid ${acc ? '#86efac' : '#e5e7eb'}`,
      padding: '14px 16px', marginBottom: 12
    }),
    suggHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 8 },
    suggTitle: { fontSize: 13, fontWeight: 700, color: '#111827' },
    toggle: (on) => ({
      display: 'flex', gap: 0, borderRadius: 6, overflow: 'hidden',
      border: '1px solid #e5e7eb', flexShrink: 0
    }),
    toggleBtn: (active, variant) => ({
      padding: '5px 12px', fontSize: 12, fontWeight: 600, cursor: 'pointer', border: 'none',
      background: active ? (variant === 'accept' ? '#22c55e' : '#ef4444') : '#fff',
      color: active ? '#fff' : '#9ca3af',
    }),
    mergeRow: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 },
    tag: (type) => ({
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: type === 'from' ? '#fffbeb' : '#f0fdf4',
      border: `1px solid ${type === 'from' ? '#fcd34d' : '#86efac'}`,
      color: type === 'from' ? '#92400e' : '#166534',
      borderRadius: 99, padding: '3px 10px', fontSize: 12, fontWeight: 600
    }),
    arrow: { color: '#9ca3af', fontSize: 16 },
    reason: { fontSize: 12, color: '#6b7280', lineHeight: 1.5 },
    applyBtn: (enabled) => ({
      width: '100%', padding: '13px', borderRadius: 8, border: 'none',
      background: enabled ? '#3b82f6' : '#e5e7eb',
      color: enabled ? '#fff' : '#9ca3af',
      fontWeight: 700, fontSize: 15, cursor: enabled ? 'pointer' : 'default',
      transition: 'background 0.15s'
    }),
    statsRow: {
      display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap'
    },
    stat: (color) => ({
      display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#6b7280'
    }),
    dot: (color) => ({
      width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0
    }),
    successBanner: {
      background: '#f0fdf4', border: '1.5px solid #86efac', borderRadius: 10,
      padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20
    }
  };

  const acceptedCount = Object.values(accepted).filter(Boolean).length;

  return (
    <div style={s.page}>
      <RecapNav authenticated={true} />
      <div style={s.main}>
        <h1 style={s.heading}>Organise Your Taxonomy</h1>
        <p style={s.sub}>AI has reviewed your categories and suggested improvements. Review and apply the changes below.</p>

        {applied && (
          <div style={s.successBanner}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13, color: '#166534' }}>Changes applied successfully</div>
              <div style={{ fontSize: 12, color: '#4ade80' }}>Your articles have been reclassified under the new taxonomy.</div>
            </div>
          </div>
        )}

        {/* Legend */}
        <div style={s.statsRow}>
          {[['#9ca3af', '3 unchanged'], ['#fbbf24', '2 being merged'], ['#4ade80', '1 new category']].map(([color, label], i) => (
            <div key={i} style={s.stat(color)}>
              <div style={s.dot(color)}></div>
              {label}
            </div>
          ))}
        </div>

        {/* Diff grid */}
        <div style={s.diffGrid}>
          {/* Current column */}
          <div>
            <div style={s.colHead}>Current ({current.length} categories)</div>
            {current.map((cat, i) => (
              <CategoryChip
                key={i}
                name={cat.name}
                count={cat.count}
                type={cat.type === 'merging' && !accepted[cat.mergeId] ? 'unchanged' : cat.type}
                isNew={cat.isNew}
                dim={cat.type === 'merging' && accepted[cat.mergeId]}
              />
            ))}
          </div>

          {/* Arrow column — desktop only */}
          {!mobile && (
            <div style={s.arrowCol}>
              <svg width="20" height="40" viewBox="0 0 20 40" fill="none">
                <path d="M10 0 L10 30 M6 26 L10 34 L14 26" stroke="#d1d5db" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          )}

          {/* Proposed column */}
          <div>
            <div style={s.colHead}>Proposed ({accepted.merge1 ? proposed.length : proposed.length} categories)</div>
            {proposed.map((cat, i) => (
              <CategoryChip
                key={i}
                name={cat.name}
                count={cat.count}
                type={cat.type === 'merged' && !accepted[cat.mergeId] ? 'unchanged' : cat.type}
                dim={cat.type === 'merged' && !accepted[cat.mergeId]}
              />
            ))}
            {!accepted.merge1 && (
              <>
                <CategoryChip name="Business Strategy" count={1} type="unchanged" />
                <CategoryChip name="Contract Management" count={1} type="unchanged" isNew={true} />
              </>
            )}
          </div>
        </div>

        <div style={s.divider} />

        {/* Suggestions */}
        <div style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
          AI suggestions — {suggestions.length} change{suggestions.length !== 1 ? 's' : ''}
        </div>

        {suggestions.map(sg => (
          <div key={sg.id} style={s.suggestionCard(accepted[sg.id])}>
            <div style={s.suggHead}>
              <div style={s.suggTitle}>
                {sg.type === 'merge' ? 'Merge categories' : sg.type}
              </div>
              <div style={s.toggle(accepted[sg.id])}>
                <button
                  style={s.toggleBtn(accepted[sg.id] === true, 'accept')}
                  onClick={() => setAccepted(a => ({ ...a, [sg.id]: true }))}
                >✓ Accept</button>
                <button
                  style={s.toggleBtn(accepted[sg.id] === false, 'reject')}
                  onClick={() => setAccepted(a => ({ ...a, [sg.id]: false }))}
                >✕ Reject</button>
              </div>
            </div>
            <div style={s.mergeRow}>
              {sg.from.map((f, i) => (
                <React.Fragment key={i}>
                  <span style={s.tag('from')}>{f}</span>
                  {i < sg.from.length - 1 && <span style={s.arrow}>+</span>}
                </React.Fragment>
              ))}
              <span style={s.arrow}>→</span>
              <span style={s.tag('to')}>{sg.to}</span>
            </div>
            <div style={s.reason}>{sg.reason}</div>
          </div>
        ))}

        <div style={{ marginTop: 20 }}>
          <button
            style={s.applyBtn(acceptedCount > 0 && !applied)}
            onClick={() => acceptedCount > 0 && setApplied(true)}
          >
            {applied ? '✓ Changes Applied' : `Apply ${acceptedCount} change${acceptedCount !== 1 ? 's' : ''}`}
          </button>
          {acceptedCount === 0 && (
            <div style={{ fontSize: 12, color: '#9ca3af', textAlign: 'center', marginTop: 8 }}>
              Accept at least one suggestion to apply changes
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { TaxonomyPage });
