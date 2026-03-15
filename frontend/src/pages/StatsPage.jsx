/**
 * StatsPage.jsx
 * -------------
 * Developer / operator analytics page at /stats.
 * Not linked from the main UI — accessible by URL only.
 *
 * Layout:
 *   1. Header + summary cards (always visible)
 *   2. Most-problematic-intent callout (if data available)
 *   3. [Collapsible] Response distribution bar chart
 *   4. [Collapsible] Intent breakdown table (with success rate)
 *   5. [Collapsible] Full logs table with 15-row pagination
 *   6. [Collapsible] User notes list
 */

import { useEffect, useState } from 'react'
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

function understoodInfo(value) {
  if (value === true)  return { label: 'כן', cls: 'yes' }
  if (value === false) return { label: 'לא', cls: 'no' }
  return { label: '—', cls: 'unanswered' }
}

function successRate(yes, no) {
  const answered = yes + no
  if (answered === 0) return null
  return Math.round((yes / answered) * 100)
}

// ── CollapsibleSection ────────────────────────────────────────────────────────

function CollapsibleSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section className={styles.collapsibleSection}>
      <button
        className={styles.collapsibleHeader}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <span className={`${styles.arrow} ${open ? styles.arrowOpen : ''}`}>▶</span>
        <span className={styles.collapsibleTitle}>{title}</span>
      </button>
      {open && <div className={styles.collapsibleBody}>{children}</div>}
    </section>
  )
}

// ── SummaryCard ───────────────────────────────────────────────────────────────

function SummaryCard({ label, value, sub, accent }) {
  return (
    <div className={`${styles.card} ${styles[accent]}`}>
      <p className={styles.cardValue}>{value}</p>
      <p className={styles.cardLabel}>{label}</p>
      {sub != null && <p className={styles.cardSub}>{sub}</p>}
    </div>
  )
}

// ── BarChart ──────────────────────────────────────────────────────────────────

function BarChart({ data }) {
  const max = Math.max(data.yes, data.no, data.unanswered, 1)
  const bars = [
    { key: 'yes',        label: 'הבינה (כן)',     pct: data.yes_pct,        count: data.yes,        cls: styles.barYes },
    { key: 'no',         label: 'לא הבינה (לא)',  pct: data.no_pct,         count: data.no,         cls: styles.barNo },
    { key: 'unanswered', label: 'ללא תשובה',       pct: data.unanswered_pct, count: data.unanswered, cls: styles.barUnanswered },
  ]
  return (
    <div className={styles.barChart}>
      {bars.map(b => (
        <div key={b.key} className={styles.barRow}>
          <span className={styles.barLabel}>{b.label}</span>
          <div className={styles.barTrack}>
            <div
              className={`${styles.barFill} ${b.cls}`}
              style={{ width: `${(b.count / max) * 100}%` }}
            />
          </div>
          <span className={styles.barStat}>{b.count} ({b.pct}%)</span>
        </div>
      ))}
    </div>
  )
}

// ── Pagination ────────────────────────────────────────────────────────────────

function Pagination({ currentPage, totalPages, onChange }) {
  if (totalPages <= 1) return null

  // Build page number list with ellipsis
  function pageNumbers() {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1)
    const pages = []
    pages.push(1)
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
      <button
        className={styles.pageBtn}
        onClick={() => onChange(currentPage - 1)}
        disabled={currentPage === 1}
      >
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

      <button
        className={styles.pageBtn}
        onClick={() => onChange(currentPage + 1)}
        disabled={currentPage === totalPages}
      >
        הבא ◀
      </button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StatsPage() {
  const [stats, setStats]       = useState(null)
  const [error, setError]       = useState(false)
  const [currentPage, setPage]  = useState(1)

  useEffect(() => {
    fetch('/api/stats')
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(setStats)
      .catch(() => setError(true))
  }, [])

  if (error) {
    return <div className={styles.page}><p className={styles.errorMsg}>שגיאה בטעינת הנתונים. ודא שהשרת פעיל.</p></div>
  }
  if (!stats) {
    return <div className={styles.page}><p className={styles.loading}>טוען נתונים...</p></div>
  }

  const noData = stats.total === 0
  const su = stats.siri_understood
  const responseRate = stats.total > 0
    ? Math.round(((su.yes + su.no) / stats.total) * 100)
    : 0

  // Most problematic intent (min success rate, ≥3 samples with answered feedback)
  let problematicIntent = null
  if (!noData) {
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
  }

  // Pagination
  const allRecords = stats.records || []
  const totalPages = Math.ceil(allRecords.length / PAGE_SIZE)
  const pageRecords = allRecords.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  // Non-empty notes
  const notes = allRecords.filter(r => r.notes).map(r => ({ note: r.notes, ts: r.timestamp, intent: r.intent_label }))

  return (
    <div className={styles.page}>

      {/* ── Header ── */}
      <header className={styles.header}>
        <h1 className={styles.title}>לוח בקרה</h1>
        <p className={styles.subtitle}>סטטיסטיקות מערכת · feedback.jsonl</p>
      </header>

      {noData ? (
        <p className={styles.noData}>אין נתונים עדיין. שלחו פקודה וענו על שאלת המשוב.</p>
      ) : (
        <>
          {/* ── Summary cards (always visible) ── */}
          <div className={styles.cards}>
            <SummaryCard label="סה״כ אינטראקציות" value={stats.total}  accent="accentTotal" />
            <SummaryCard label="סירי הבינה"        value={su.yes}       sub={`${su.yes_pct}%`}        accent="accentYes" />
            <SummaryCard label="סירי לא הבינה"     value={su.no}        sub={`${su.no_pct}%`}         accent="accentNo" />
            <SummaryCard label="ללא תשובה"          value={su.unanswered} sub={`${su.unanswered_pct}%`} accent="accentUnanswered" />
            <SummaryCard label="שיעור תגובה"        value={`${responseRate}%`} sub={`${su.yes + su.no} ענו`} accent="accentResponse" />
          </div>

          {/* ── Problematic intent callout ── */}
          {problematicIntent && (
            <div className={styles.callout}>
              <span className={styles.calloutIcon}>⚠</span>
              <span>
                הכוונה הבעייתית ביותר:&nbsp;
                <strong><span className={styles.intentTag}>{problematicIntent.label}</span></strong>
                &nbsp;— שיעור הצלחה: <strong>{problematicIntent.rate}%</strong>
              </span>
            </div>
          )}

          {/* ── Collapsible: bar chart ── */}
          <CollapsibleSection title="התפלגות תשובות">
            <BarChart data={su} />
          </CollapsibleSection>

          {/* ── Collapsible: intent table ── */}
          {Object.keys(stats.by_intent).length > 0 && (
            <CollapsibleSection title="פירוט לפי כוונה">
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>כוונה</th>
                      <th>סה״כ</th>
                      <th>הבינה</th>
                      <th>לא הבינה</th>
                      <th>ללא תשובה</th>
                      <th>% הצלחה</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(stats.by_intent).map(([intent, counts]) => {
                      const sr = successRate(counts.yes, counts.no)
                      return (
                        <tr key={intent}>
                          <td><span className={styles.intentTag}>{intent}</span></td>
                          <td>{counts.total}</td>
                          <td className={styles.cellYes}>{counts.yes}</td>
                          <td className={styles.cellNo}>{counts.no}</td>
                          <td className={styles.cellUnanswered}>{counts.unanswered}</td>
                          <td>
                            {sr !== null
                              ? <span className={`${styles.srBadge} ${sr >= 70 ? styles.srGood : sr >= 40 ? styles.srMid : styles.srBad}`}>{sr}%</span>
                              : <span className={styles.cellUnanswered}>—</span>
                            }
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </CollapsibleSection>
          )}

          {/* ── Collapsible: full logs with pagination ── */}
          <CollapsibleSection title={`כל הרשומות (${allRecords.length})`}>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>זמן</th>
                    <th>קלט מקורי</th>
                    <th>כוונה</th>
                    <th>פקודה מתוקנת</th>
                    <th>סטטוס</th>
                    <th>הבינה?</th>
                    <th>הערות</th>
                  </tr>
                </thead>
                <tbody>
                  {pageRecords.map((r, i) => {
                    const u = understoodInfo(r.siri_understood)
                    const isSuccess = r.backend_status === 'success'
                    return (
                      <tr key={i}>
                        <td className={styles.cellMono}>{formatTimestamp(r.timestamp)}</td>
                        <td dir="rtl">{r.original_input}</td>
                        <td><span className={styles.intentTag}>{r.intent_label}</span></td>
                        <td dir="rtl">{r.reformulated_command}</td>
                        <td>
                          <span className={`${styles.badge} ${isSuccess ? styles.statusSuccess : styles.statusFailed}`}>
                            {isSuccess ? 'success' : 'failed'}
                          </span>
                        </td>
                        <td><span className={`${styles.badge} ${styles[u.cls]}`}>{u.label}</span></td>
                        <td dir="rtl" className={styles.cellNotes}>{r.notes || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className={styles.paginationRow}>
              <span className={styles.pageInfo}>
                עמוד {currentPage} מתוך {totalPages} · {allRecords.length} רשומות
              </span>
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onChange={p => setPage(p)}
              />
            </div>
          </CollapsibleSection>

          {/* ── Collapsible: user notes ── */}
          {notes.length > 0 && (
            <CollapsibleSection title={`הערות משתמשים (${notes.length})`} defaultOpen={false}>
              <ul className={styles.notesList}>
                {notes.map((n, i) => (
                  <li key={i} className={styles.noteItem}>
                    <span className={styles.noteMeta}>
                      {formatTimestamp(n.ts)} · <span className={styles.intentTag}>{n.intent}</span>
                    </span>
                    <span className={styles.noteText} dir="rtl">{n.note}</span>
                  </li>
                ))}
              </ul>
            </CollapsibleSection>
          )}
        </>
      )}
    </div>
  )
}
