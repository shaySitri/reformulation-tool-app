/**
 * StatsPage.jsx
 * -------------
 * Tab-based developer / operator analytics dashboard at /stats.
 * Not linked from the main UI — accessible by URL only.
 *
 * Tabs:
 *   1. סקירה כללית   — KPI cards + bar chart + problematic intent callout
 *   2. ניתוח כוונות  — Per-intent bar chart + sortable table
 *   3. יומן פעילות   — Full paginated logs with search / filter / export
 *   4. הערות          — User notes list
 */

import { useEffect, useState, useMemo } from 'react'
import styles from './StatsPage.module.css'

const PAGE_SIZE = 15

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTimestamp(ts) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString('he-IL', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return ts
  }
}

function understoodLabel(value) {
  if (value === true)  return 'כן'
  if (value === false) return 'לא'
  return '—'
}

function understoodCls(value) {
  if (value === true)  return 'yes'
  if (value === false) return 'no'
  return 'unanswered'
}

function successRate(yes, no) {
  const answered = yes + no
  if (answered === 0) return null
  return Math.round((yes / answered) * 100)
}

function exportCSV(records) {
  const header = ['timestamp', 'original_input', 'intent_label', 'reformulated_command', 'backend_status', 'siri_understood', 'notes']
  const rows = records.map(r => header.map(k => {
    let v = r[k]
    if (v === null || v === undefined) v = ''
    v = String(v).replace(/"/g, '""')
    if (v.includes(',') || v.includes('"') || v.includes('\n')) v = `"${v}"`
    return v
  }).join(','))
  const csv = [header.join(','), ...rows].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'feedback_log.csv'; a.click()
  URL.revokeObjectURL(url)
}

function exportJSON(records) {
  const blob = new Blob([JSON.stringify(records, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'feedback_log.json'; a.click()
  URL.revokeObjectURL(url)
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview',  label: 'סקירה כללית' },
  { id: 'intents',   label: 'ניתוח כוונות' },
  { id: 'log',       label: 'יומן פעילות' },
  { id: 'notes',     label: 'הערות' },
]

function TabBar({ active, onChange }) {
  return (
    <nav className={styles.tabBar}>
      {TABS.map(t => (
        <button
          key={t.id}
          className={`${styles.tabBtn} ${active === t.id ? styles.tabBtnActive : ''}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </nav>
  )
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, accent, onClick }) {
  return (
    <div
      className={`${styles.kpiCard} ${styles[accent]} ${onClick ? styles.kpiClickable : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <p className={styles.kpiValue}>{value}</p>
      <p className={styles.kpiLabel}>{label}</p>
      {sub != null && <p className={styles.kpiSub}>{sub}</p>}
    </div>
  )
}

// ── Horizontal bar ────────────────────────────────────────────────────────────

function HBar({ pct, colorClass, label, count, percentText }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div className={styles.barRow}>
      <span className={styles.barLabel}>{label}</span>
      <div className={styles.barTrack}>
        <div
          className={`${styles.barFill} ${styles[colorClass]}`}
          style={{ width: `${pct}%` }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          {hovered && (
            <span className={styles.barTooltip}>{count} ({percentText}%)</span>
          )}
        </div>
      </div>
      <span className={styles.barStat}>{count} ({percentText}%)</span>
    </div>
  )
}

// ── Sort helper ───────────────────────────────────────────────────────────────

function useSortedData(data, defaultKey, defaultDir = 'desc') {
  const [sortKey, setSortKey] = useState(defaultKey)
  const [sortDir, setSortDir] = useState(defaultDir)

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    if (!data) return []
    return [...data].sort((a, b) => {
      let av = a[sortKey], bv = b[sortKey]
      if (av == null) av = ''
      if (bv == null) bv = ''
      if (typeof av === 'string') av = av.toLowerCase()
      if (typeof bv === 'string') bv = bv.toLowerCase()
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [data, sortKey, sortDir])

  return { sorted, sortKey, sortDir, toggleSort }
}

function SortTh({ label, sortKey, currentKey, dir, onSort }) {
  const active = currentKey === sortKey
  return (
    <th className={styles.sortTh} onClick={() => onSort(sortKey)}>
      {label}
      <span className={`${styles.sortArrow} ${active ? styles.sortArrowActive : ''}`}>
        {active ? (dir === 'asc' ? ' ▲' : ' ▼') : ' ⇅'}
      </span>
    </th>
  )
}

// ── Pagination ────────────────────────────────────────────────────────────────

function Pagination({ currentPage, totalPages, onChange }) {
  if (totalPages <= 1) return null

  function pageNumbers() {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1)
    const pages = [1]
    if (currentPage > 3) pages.push('…')
    for (let p = Math.max(2, currentPage - 1); p <= Math.min(totalPages - 1, currentPage + 1); p++) {
      pages.push(p)
    }
    if (currentPage < totalPages - 2) pages.push('…')
    pages.push(totalPages)
    return pages
  }

  return (
    <div className={styles.pagination}>
      <button className={styles.pageBtn} onClick={() => onChange(currentPage - 1)} disabled={currentPage === 1}>
        ▶ הקודם
      </button>
      <div className={styles.pageNumbers}>
        {pageNumbers().map((p, i) =>
          p === '…'
            ? <span key={`e${i}`} className={styles.pageEllipsis}>…</span>
            : <button
                key={p}
                className={`${styles.pageBtn} ${p === currentPage ? styles.pageBtnActive : ''}`}
                onClick={() => onChange(p)}
              >
                {p}
              </button>
        )}
      </div>
      <button className={styles.pageBtn} onClick={() => onChange(currentPage + 1)} disabled={currentPage === totalPages}>
        הבא ◀
      </button>
    </div>
  )
}

// ── Intent badge ──────────────────────────────────────────────────────────────

function IntentTag({ label }) {
  return <span className={styles.intentTag}>{label}</span>
}

function SrBadge({ rate }) {
  if (rate === null) return <span className={styles.cellMuted}>—</span>
  const cls = rate >= 70 ? styles.srGood : rate >= 40 ? styles.srMid : styles.srBad
  return <span className={`${styles.srBadge} ${cls}`}>{rate}%</span>
}

// ── Tab 1: Overview ───────────────────────────────────────────────────────────

function OverviewTab({ stats, onNavigateToLog }) {
  const su = stats.siri_understood
  const responseRate = stats.total > 0
    ? Math.round(((su.yes + su.no) / stats.total) * 100)
    : 0

  let problematicIntent = null
  let minRate = Infinity
  for (const [label, counts] of Object.entries(stats.by_intent)) {
    const answered = counts.yes + counts.no
    if (answered >= 3) {
      const rate = successRate(counts.yes, counts.no)
      if (rate !== null && rate < minRate) {
        minRate = rate
        problematicIntent = { label, rate }
      }
    }
  }

  const maxBar = Math.max(su.yes, su.no, su.unanswered, 1)

  return (
    <div className={styles.tabContent}>
      {/* KPI cards */}
      <div className={styles.kpiGrid}>
        <KpiCard label="סה״כ אינטראקציות" value={stats.total} accent="accentTotal" />
        <KpiCard
          label="סירי הבינה"
          value={su.yes}
          sub={`${su.yes_pct}%`}
          accent="accentYes"
          onClick={() => onNavigateToLog('yes')}
        />
        <KpiCard
          label="סירי לא הבינה"
          value={su.no}
          sub={`${su.no_pct}%`}
          accent="accentNo"
          onClick={() => onNavigateToLog('no')}
        />
        <KpiCard label="ללא תשובה" value={su.unanswered} sub={`${su.unanswered_pct}%`} accent="accentUnanswered" />
        <KpiCard label="שיעור תגובה" value={`${responseRate}%`} sub={`${su.yes + su.no} ענו`} accent="accentResponse" />
      </div>

      {/* Problematic intent */}
      {problematicIntent && (
        <div className={styles.callout}>
          <span className={styles.calloutIcon}>⚠</span>
          <span>
            הכוונה הבעייתית ביותר:&nbsp;
            <strong><IntentTag label={problematicIntent.label} /></strong>
            &nbsp;— שיעור הצלחה: <strong>{problematicIntent.rate}%</strong>
          </span>
        </div>
      )}

      {/* Distribution bar chart */}
      <div className={styles.sectionCard}>
        <h2 className={styles.sectionTitle}>התפלגות תשובות</h2>
        <div className={styles.barChart}>
          <HBar
            label="הבינה (כן)"
            count={su.yes}
            percentText={su.yes_pct}
            pct={(su.yes / maxBar) * 100}
            colorClass="barYes"
          />
          <HBar
            label="לא הבינה (לא)"
            count={su.no}
            percentText={su.no_pct}
            pct={(su.no / maxBar) * 100}
            colorClass="barNo"
          />
          <HBar
            label="ללא תשובה"
            count={su.unanswered}
            percentText={su.unanswered_pct}
            pct={(su.unanswered / maxBar) * 100}
            colorClass="barUnanswered"
          />
        </div>
      </div>
    </div>
  )
}

// ── Tab 2: Intent Analysis ────────────────────────────────────────────────────

function IntentsTab({ stats }) {
  const intentEntries = Object.entries(stats.by_intent)
  const maxTotal = Math.max(...intentEntries.map(([, c]) => c.total), 1)

  const tableData = intentEntries.map(([label, counts]) => ({
    label,
    total: counts.total,
    yes: counts.yes,
    no: counts.no,
    unanswered: counts.unanswered,
    rate: successRate(counts.yes, counts.no),
  }))

  const { sorted, sortKey, sortDir, toggleSort } = useSortedData(tableData, 'total', 'desc')

  return (
    <div className={styles.tabContent}>
      {/* Per-intent bar chart */}
      <div className={styles.sectionCard}>
        <h2 className={styles.sectionTitle}>שיעור הצלחה לפי כוונה</h2>
        <div className={styles.barChart}>
          {intentEntries.map(([label, counts]) => {
            const rate = successRate(counts.yes, counts.no)
            const colorClass = rate === null ? 'barUnanswered' : rate >= 70 ? 'barGood' : rate >= 40 ? 'barMid' : 'barBad'
            return (
              <HBar
                key={label}
                label={label}
                count={counts.total}
                percentText={rate !== null ? rate : '—'}
                pct={(counts.total / maxTotal) * 100}
                colorClass={colorClass}
              />
            )
          })}
        </div>
      </div>

      {/* Sortable intent table */}
      <div className={styles.sectionCard}>
        <h2 className={styles.sectionTitle}>פירוט לפי כוונה</h2>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortTh label="כוונה"      sortKey="label"     currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <SortTh label="סה״כ"       sortKey="total"     currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <SortTh label="הבינה"      sortKey="yes"       currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <SortTh label="לא הבינה"   sortKey="no"        currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <SortTh label="ללא תשובה"  sortKey="unanswered" currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <SortTh label="% הצלחה"    sortKey="rate"      currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
              </tr>
            </thead>
            <tbody>
              {sorted.map(row => (
                <tr key={row.label}>
                  <td><IntentTag label={row.label} /></td>
                  <td>{row.total}</td>
                  <td className={styles.cellYes}>{row.yes}</td>
                  <td className={styles.cellNo}>{row.no}</td>
                  <td className={styles.cellMuted}>{row.unanswered}</td>
                  <td><SrBadge rate={row.rate} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Tab 3: Activity Log ───────────────────────────────────────────────────────

const UNDERSTOOD_FILTERS = [
  { id: 'all',       label: 'הכל' },
  { id: 'yes',       label: 'כן' },
  { id: 'no',        label: 'לא' },
  { id: 'unanswered', label: 'ללא תשובה' },
]

function LogTab({ records, initialUnderstoodFilter }) {
  const [search, setSearch]         = useState('')
  const [intentFilter, setIntent]   = useState('all')
  const [understoodFilter, setUnd]  = useState(initialUnderstoodFilter || 'all')
  const [currentPage, setPage]      = useState(1)

  const { sorted, sortKey, sortDir, toggleSort } = useSortedData(records, 'timestamp', 'desc')

  const allIntents = useMemo(() => {
    const s = new Set(records.map(r => r.intent_label).filter(Boolean))
    return ['all', ...Array.from(s).sort()]
  }, [records])

  const filtered = useMemo(() => {
    return sorted.filter(r => {
      if (search && !((r.original_input || '').includes(search))) return false
      if (intentFilter !== 'all' && r.intent_label !== intentFilter) return false
      if (understoodFilter === 'yes' && r.siri_understood !== true) return false
      if (understoodFilter === 'no' && r.siri_understood !== false) return false
      if (understoodFilter === 'unanswered' && r.siri_understood !== null && r.siri_understood !== undefined) return false
      return true
    })
  }, [sorted, search, intentFilter, understoodFilter])

  // Reset to page 1 when filters change
  useEffect(() => { setPage(1) }, [search, intentFilter, understoodFilter])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageRecords = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  return (
    <div className={styles.tabContent}>
      {/* Filter bar */}
      <div className={styles.filterBar}>
        <input
          className={styles.searchInput}
          type="text"
          placeholder="חיפוש בקלט מקורי..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          dir="rtl"
        />

        <select
          className={styles.filterSelect}
          value={intentFilter}
          onChange={e => setIntent(e.target.value)}
        >
          {allIntents.map(i => (
            <option key={i} value={i}>{i === 'all' ? 'כל הכוונות' : i}</option>
          ))}
        </select>

        <div className={styles.filterBtnGroup}>
          {UNDERSTOOD_FILTERS.map(f => (
            <button
              key={f.id}
              className={`${styles.filterBtn} ${understoodFilter === f.id ? styles.filterBtnActive : ''}`}
              onClick={() => setUnd(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className={styles.exportBtns}>
          <button className={styles.exportBtn} onClick={() => exportCSV(filtered)}>
            ↓ CSV
          </button>
          <button className={styles.exportBtn} onClick={() => exportJSON(filtered)}>
            ↓ JSON
          </button>
        </div>
      </div>

      {/* Logs table */}
      <div className={styles.sectionCard}>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <SortTh label="זמן"          sortKey="timestamp"         currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <th>קלט מקורי</th>
                <SortTh label="כוונה"        sortKey="intent_label"      currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <th>פקודה מתוקנת</th>
                <th>סטטוס</th>
                <SortTh label="הבינה?"       sortKey="siri_understood"   currentKey={sortKey} dir={sortDir} onSort={toggleSort} />
                <th>הערות</th>
              </tr>
            </thead>
            <tbody>
              {pageRecords.length === 0 && (
                <tr><td colSpan={7} className={styles.emptyRow}>אין רשומות תואמות</td></tr>
              )}
              {pageRecords.map((r, i) => {
                const isSuccess = r.backend_status === 'success'
                const uCls = understoodCls(r.siri_understood)
                return (
                  <tr key={i}>
                    <td className={styles.cellMono}>{formatTimestamp(r.timestamp)}</td>
                    <td dir="rtl">{r.original_input}</td>
                    <td><IntentTag label={r.intent_label} /></td>
                    <td dir="rtl">{r.reformulated_command}</td>
                    <td>
                      <span className={`${styles.badge} ${isSuccess ? styles.statusSuccess : styles.statusFailed}`}>
                        {isSuccess ? 'success' : 'failed'}
                      </span>
                    </td>
                    <td>
                      <span className={`${styles.badge} ${styles[uCls]}`}>
                        {understoodLabel(r.siri_understood)}
                      </span>
                    </td>
                    <td dir="rtl" className={styles.cellNotes}>{r.notes || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className={styles.paginationRow}>
          <span className={styles.pageInfo}>
            {filtered.length} רשומות · עמוד {currentPage} מתוך {totalPages || 1}
          </span>
          <Pagination currentPage={currentPage} totalPages={totalPages} onChange={setPage} />
        </div>
      </div>
    </div>
  )
}

// ── Tab 4: Notes ──────────────────────────────────────────────────────────────

function NotesTab({ records }) {
  const notes = records.filter(r => r.notes).map(r => ({
    note: r.notes,
    ts: r.timestamp,
    intent: r.intent_label,
  }))

  if (notes.length === 0) {
    return (
      <div className={styles.tabContent}>
        <p className={styles.emptyState}>אין הערות משתמשים עדיין.</p>
      </div>
    )
  }

  return (
    <div className={styles.tabContent}>
      <div className={styles.sectionCard}>
        <h2 className={styles.sectionTitle}>הערות משתמשים ({notes.length})</h2>
        <ul className={styles.notesList}>
          {notes.map((n, i) => (
            <li key={i} className={styles.noteItem}>
              <span className={styles.noteMeta}>
                {formatTimestamp(n.ts)} · <IntentTag label={n.intent} />
              </span>
              <span className={styles.noteText} dir="rtl">{n.note}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StatsPage() {
  const [stats, setStats]   = useState(null)
  const [error, setError]   = useState(false)
  const [activeTab, setTab] = useState('overview')
  const [logFilter, setLogFilter] = useState('all')

  useEffect(() => {
    fetch('/api/stats')
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setStats)
      .catch(() => setError(true))
  }, [])

  function navigateToLog(filter) {
    setLogFilter(filter)
    setTab('log')
  }

  if (error) {
    return (
      <div className={styles.page}>
        <p className={styles.errorMsg}>שגיאה בטעינת הנתונים. ודא שהשרת פעיל.</p>
      </div>
    )
  }
  if (!stats) {
    return (
      <div className={styles.page}>
        <p className={styles.loading}>טוען נתונים...</p>
      </div>
    )
  }

  const allRecords = stats.records || []

  return (
    <div className={styles.page}>
      {/* ── Header ── */}
      <header className={styles.header}>
        <h1 className={styles.title}>לוח בקרה</h1>
        <p className={styles.subtitle}>סטטיסטיקות מערכת · feedback.jsonl · {allRecords.length} רשומות</p>
      </header>

      {/* ── Tab bar ── */}
      <TabBar active={activeTab} onChange={setTab} />

      {/* ── Tab content ── */}
      <div className={styles.contentArea}>
        {stats.total === 0 ? (
          <p className={styles.emptyState}>אין נתונים עדיין. שלחו פקודה וענו על שאלת המשוב.</p>
        ) : (
          <>
            {activeTab === 'overview' && (
              <OverviewTab stats={stats} onNavigateToLog={navigateToLog} />
            )}
            {activeTab === 'intents' && (
              <IntentsTab stats={stats} />
            )}
            {activeTab === 'log' && (
              <LogTab records={allRecords} initialUnderstoodFilter={logFilter} />
            )}
            {activeTab === 'notes' && (
              <NotesTab records={allRecords} />
            )}
          </>
        )}
      </div>
    </div>
  )
}
