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
 *   - result !== null     → show the reformulated command string only.
 *
 * Design notes:
 *   - The result card uses a large, prominent font (1.6rem) to make the output
 *     easy to read at a glance for older adults.
 *   - Success and error states use distinct background colours with sufficient
 *     contrast (WCAG AA) so the user can tell at a glance which occurred.
 *   - No technical fields (status, intent, HTTP code) are ever rendered.
 */

import styles from './ResultDisplay.module.css'

/**
 * ResultDisplay — shows the pipeline result or a generic error card.
 *
 * @param {Object}        props
 * @param {string|null}   props.result - Reformulated Hebrew command, or null.
 * @param {boolean}       props.error  - Whether to show the error message.
 */
function ResultDisplay({ result, error }) {
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
        <p className={styles.errorText}>אירעה שגיאה. אנא נסה שוב.</p>
      </div>
    )
  }

  return (
    <div
      className={`${styles.card} ${styles.successCard}`}
      role="status"
      aria-live="polite"
    >
      {/* Instruction line above the reformulated command */}
      <p className={styles.resultLabel}>הפעילו את סירי ואמרו לה את הפקודה הבאה:</p>
      {/* The reformulated command — large, prominent text */}
      <p className={styles.resultText}>{result}</p>
    </div>
  )
}

export default ResultDisplay
