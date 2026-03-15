/**
 * ResultDisplay.jsx
 * -----------------
 * Displays either the reformulated Hebrew command (on success) or a generic
 * error message (on failure).
 *
 * Props:
 *   result {string | null} - The reformulated command string from the backend.
 *                            null when there is no result to show yet.
 *   error  {boolean}       - true when the last request ended in any failure
 *                            (network error, HTTP 4xx/5xx, or status="failed").
 *
 * Visibility rules:
 *   - Neither prop set    → component renders nothing (initial state).
 *   - error === true      → show the generic Hebrew error message only.
 *   - result !== null     → show the reformulated command string and TTS button.
 *
 * TTS (text-to-speech):
 *   When a result is shown, a "הקראת הפקודה" button appears below the command.
 *   Pressing it reads the result aloud using the browser Web Speech API via
 *   the useTTS hook. The button is disabled while speech is in progress.
 *   It is hidden entirely on the error card.
 *
 * Design notes:
 *   - The result card uses a large, prominent font (1.6rem) for the command.
 *   - Success and error states use distinct background colours (WCAG AA).
 *   - No technical fields (status, intent, HTTP code) are ever rendered.
 */

import { useTTS } from '../utils/useTTS.js'
import styles from './ResultDisplay.module.css'

/**
 * ResultDisplay — shows the pipeline result (with TTS button) or error card.
 *
 * @param {Object}        props
 * @param {string|null}   props.result - Reformulated Hebrew command, or null.
 * @param {boolean}       props.error  - Whether to show the error message.
 */
function ResultDisplay({ result, error }) {
  const { speak, speaking } = useTTS()

  // Nothing to show yet — hide the component entirely.
  if (!error && result === null) {
    return null
  }

  if (error) {
    return (
      <div
        className={`${styles.card} ${styles.errorCard}`}
        role="alert"
        aria-live="assertive"
      >
        <p className={styles.errorTitle}>✕ לא הצלחנו לנסח את הפקודה</p>
        <p className={styles.errorSub}>אנא נסו שוב בניסוח שונה</p>
      </div>
    )
  }

  return (
    <div
      className={`${styles.card} ${styles.successCard}`}
      role="status"
      aria-live="polite"
    >
      {/* Status label */}
      <p className={styles.resultLabel}>✓ הפקודה לסירי מוכנה</p>

      {/* The reformulated command — very large, prominent */}
      <p className={styles.resultText}>{result}</p>

      {/* TTS button — reads the command aloud */}
      <button
        type="button"
        className={styles.ttsButton}
        onClick={() => speak(result)}
        disabled={speaking}
        aria-label="הקראת הפקודה בקול"
      >
        {speaking ? '▐▐ מנגן...' : '🔊 הקראת הפקודה'}
      </button>
    </div>
  )
}

export default ResultDisplay
