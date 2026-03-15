/**
 * FeedbackDialog.jsx
 * ------------------
 * True modal feedback popup — appears centered on screen with a darkened
 * overlay that blocks interaction with the rest of the page.
 *
 * UX flow:
 *   1. Modal opens automatically after a successful reformulation.
 *   2. User optionally selects כן (Yes) or לא (No) — toggle buttons.
 *   3. User optionally types notes.
 *   4. User clicks "שלח משוב" (Submit) → logs selection + notes.
 *      OR clicks "סגור" (Close) → logs siri_understood: null, notes: null.
 *
 * Props:
 *   onSubmit(understood: boolean|null, notes: string|null) — Submit button
 *   onClose()                                              — Close button
 */

import { useState } from 'react'
import styles from './FeedbackDialog.module.css'

function FeedbackDialog({ command, onSubmit, onClose }) {
  // null = neither selected, true = כן selected, false = לא selected
  const [selected, setSelected] = useState(null)
  const [notes, setNotes] = useState('')

  function toggle(value) {
    setSelected(prev => (prev === value ? null : value))
  }

  function handleSubmit() {
    onSubmit(selected, notes.trim() || null)
  }

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="משוב על הפקודה">
      <div className={styles.modal}>

        {/* Close (X) button — top-left corner in RTL */}
        <button
          type="button"
          className={styles.closeX}
          onClick={onClose}
          aria-label="סגור"
        >
          ✕
        </button>

        {/* Reformulated command display */}
        <p className={styles.commandLabel}>פקודה מתוקנת:</p>
        <p className={styles.commandText}>"{command}"</p>

        {/* Question */}
        <p className={styles.question}>האם סירי הבינה את הפקודה?</p>

        {/* Toggle selection buttons */}
        <div className={styles.selectionRow}>
          <button
            type="button"
            className={`${styles.selectButton} ${styles.yes} ${selected === true ? styles.selectedYes : ''}`}
            onClick={() => toggle(true)}
            aria-pressed={selected === true}
          >
            כן
          </button>
          <button
            type="button"
            className={`${styles.selectButton} ${styles.no} ${selected === false ? styles.selectedNo : ''}`}
            onClick={() => toggle(false)}
            aria-pressed={selected === false}
          >
            לא
          </button>
        </div>

        {/* Optional notes */}
        <textarea
          className={styles.notes}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="הערות — לא חובה"
          rows={2}
          aria-label="הערות"
          dir="rtl"
        />

        {/* Action row */}
        <div className={styles.actionRow}>
          <button
            type="button"
            className={styles.submitButton}
            onClick={handleSubmit}
          >
            שלח משוב
          </button>
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
          >
            סגור
          </button>
        </div>

      </div>
    </div>
  )
}

export default FeedbackDialog
