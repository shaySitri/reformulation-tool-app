/**
 * StatsPage.jsx
 * -------------
 * Developer / operator analytics page at /stats.
 * Not linked from the main UI — accessible by URL only.
 *
 * Fetches GET /api/stats on mount and displays:
 *   1. Summary cards  — total / understood / not understood / no answer
 *   2. Bar chart      — CSS-only horizontal bars for yes / no / unanswered
 *   3. Intent table   — per-intent breakdown
 *   4. Recent entries — last 20 records, newest first
 */

import { useEffect, useState } from 'react'
import styles from './StatsPage.module.css'

// ── Helpers ──────────────────────────────────────────────────────────────────

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

function understood(value) {
  if (value === true) return { label: 'כן', cls: 'yes' }
  if (value === false) return { label: 'לא', cls: 'no' }
  return { label: '—', cls: 'unanswered' }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SummaryCard({ label, value, sub, accent }) {
  return (
    <div className={`${styles.card} ${styles[accent]}`}>
      <p className={styles.cardValue}>{value}</p>
      <p className={styles.cardLabel}>{label}</p>
      {sub && <p className={styles.cardSub}>{sub}</p>}
    </div>
  )
}

function BarChart({ data }) {
  const max = Math.max(data.yes, data.no, data.unanswered, 1)
  const bars = [
    { key: 'yes',        label: 'הבינה (כן)',    pct: data.yes_pct,        count: data.yes,        cls: styles.barYes },
    { key: 'no',         label: 'לא הבינה (לא)', pct: data.no_pct,         count: data.no,         cls: styles.barNo },
    { key: 'unanswered', label: 'ללא תשובה',      pct: data.unanswered_pct, count: data.unanswered, cls: styles.barUnanswered },
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

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StatsPage() {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch('/api/stats')
      .then(r => {
        if (!r.ok) throw new Error('fetch failed')
        return r.json()
      })
      .then(setStats)
      .catch(() => setError(true))
  }, [])

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

  const noData = stats.total === 0

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
          {/* ── Summary cards ── */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>סיכום</h2>
            <div className={styles.cards}>
              <SummaryCard label="סה״כ אינטראקציות" value={stats.total} accent="accentTotal" />
              <SummaryCard
                label="סירי הבינה"
                value={stats.siri_understood.yes}
                sub={`${stats.siri_understood.yes_pct}%`}
                accent="accentYes"
              />
              <SummaryCard
                label="סירי לא הבינה"
                value={stats.siri_understood.no}
                sub={`${stats.siri_understood.no_pct}%`}
                accent="accentNo"
              />
              <SummaryCard
                label="ללא תשובה"
                value={stats.siri_understood.unanswered}
                sub={`${stats.siri_understood.unanswered_pct}%`}
                accent="accentUnanswered"
              />
            </div>
          </section>

          {/* ── Bar chart ── */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>התפלגות תשובות</h2>
            <BarChart data={stats.siri_understood} />
          </section>

          {/* ── Intent breakdown ── */}
          {Object.keys(stats.by_intent).length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>פירוט לפי כוונה</h2>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>כוונה</th>
                      <th>סה״כ</th>
                      <th>הבינה</th>
                      <th>לא הבינה</th>
                      <th>ללא תשובה</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(stats.by_intent).map(([intent, counts]) => (
                      <tr key={intent}>
                        <td><span className={styles.intentTag}>{intent}</span></td>
                        <td>{counts.total}</td>
                        <td className={styles.cellYes}>{counts.yes}</td>
                        <td className={styles.cellNo}>{counts.no}</td>
                        <td className={styles.cellUnanswered}>{counts.unanswered}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── Recent entries ── */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>20 רשומות אחרונות</h2>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>זמן</th>
                    <th>קלט מקורי</th>
                    <th>כוונה</th>
                    <th>פקודה מתוקנת</th>
                    <th>הבינה?</th>
                    <th>הערות</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent.map((r, i) => {
                    const u = understood(r.siri_understood)
                    return (
                      <tr key={i}>
                        <td className={styles.cellMono}>{formatTimestamp(r.timestamp)}</td>
                        <td dir="rtl">{r.original_input}</td>
                        <td><span className={styles.intentTag}>{r.intent_label}</span></td>
                        <td dir="rtl">{r.reformulated_command}</td>
                        <td><span className={`${styles.badge} ${styles[u.cls]}`}>{u.label}</span></td>
                        <td dir="rtl" className={styles.cellNotes}>{r.notes || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
