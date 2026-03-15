/**
 * FeedbackDialog.jsx
 * ------------------
 * Inline AI follow-up card — appears below the result card in the page flow.
 * No blocking overlay. Feels like the AI asking a natural follow-up question.
 *
 * UX flow:
 *   1. Card slides in after a successful reformulation.
 *   2. User selects כן (Yes) or לא (No) — toggle buttons.
 *   3. Notes textarea appears after a selection is made (optional).
 *   4. User clicks "שלח משוב" (Submit) → logs selection + notes.
 *      OR clicks "סגור" (Close) → logs siri_understood: null, notes: null.
 *
 * Props:
 *   onSubmit(understood: boolean|null, notes: string|null)
 *   onClose()
 */

import { useState } from 'react'
import styles from './FeedbackDialog.module.css'

function FeedbackDialog({ onSubmit, onClose }) {
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
    <div className={styles.card} role="region" aria-label="משוב על הפקודה">

      {/* AI follow-up question */}
      <p className={styles.question}>האם סירי הבינה את הפקודה?</p>

      {/* Toggle selection buttons */}
      <div className={styles.selectionRow}>
        <button
          type="button"
          className={`${styles.selectButton} ${styles.yes} ${selected === true ? styles.selectedYes : ''}`}
          onClick={() => toggle(true)}
          aria-pressed={selected === true}
        >
          ✓ כן
        </button>
        <button
          type="button"
          className={`${styles.selectButton} ${styles.no} ${selected === false ? styles.selectedNo : ''}`}
          onClick={() => toggle(false)}
          aria-pressed={selected === false}
        >
          ✕ לא
        </button>
      </div>

      {/* Notes textarea — visible only after a selection */}
      {selected !== null && (
        <textarea
          className={styles.notes}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="הערות נוספות — לא חובה"
          rows={2}
          aria-label="הערות"
          dir="rtl"
        />
      )}

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
  )
}

export default FeedbackDialog
