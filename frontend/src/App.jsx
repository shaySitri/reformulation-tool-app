/**
 * App.jsx
 * -------
 * Root component for the Hebrew Voice Command Reformulation UI.
 *
 * This component owns all application state and contains the only network
 * call in the frontend. Child components receive only what they need to
 * render; none of them know about the backend response structure.
 *
 * State:
 *   utterance {string}      - The user's current Hebrew input (controlled).
 *   result    {string|null} - The reformulated command from the backend.
 *                             null until a successful response is received.
 *   error     {boolean}     - true when any failure occurred (network error,
 *                             HTTP 4xx/5xx, or backend status === "failed").
 *   loading   {boolean}     - true while a fetch request is in flight.
 *
 * API contract:
 *   POST /api/reformulate
 *   Body:     { utterance: string }
 *   Success:  HTTP 200, { status: "success", reformulated: string, ... }
 *   Failure:  HTTP 200 with status "failed", OR HTTP 4xx/5xx
 *
 *   The frontend treats all non-success outcomes identically — it shows a
 *   generic error message without exposing any technical details.
 *
 * Vite proxy:
 *   /api/* is forwarded to http://127.0.0.1:8000/* by vite.config.js, so no
 *   CORS issues occur during development.
 */

import { useState } from 'react'
import CommandInput from './components/CommandInput.jsx'
import ResultDisplay from './components/ResultDisplay.jsx'
import { normalizeNumbers } from './utils/normalizeNumbers.js'
import styles from './App.module.css'

/**
 * App — top-level component; owns state and the backend fetch call.
 */
function App() {
  const [utterance, setUtterance] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(false)

  /**
   * sendUtterance — POST the current utterance to the reformulation API.
   *
   * Success path: HTTP 200 with status "success" → store reformulated string.
   * Failure path: any other outcome → set error flag.
   *
   * All error detail is deliberately discarded; the user only sees the
   * generic error message rendered by ResultDisplay.
   */
  async function sendUtterance() {
    // Guard: ignore empty input (the button is disabled, but be defensive)
    if (!utterance.trim()) return

    // Reset previous result/error before the new request
    setResult(null)
    setError(false)
    setLoading(true)

    // Preprocessing: convert any digit sequences to Hebrew words before
    // sending to the backend. The input field is not mutated — the user
    // always sees their original text. Example: "שעה 7" → "שעה שבע".
    const processedUtterance = normalizeNumbers(utterance)

    try {
      const response = await fetch('/api/reformulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ utterance: processedUtterance }),
      })

      if (!response.ok) {
        // HTTP 4xx or 5xx — show error, no detail exposed
        setError(true)
        return
      }

      const data = await response.json()

      if (data.status === 'success' && data.reformulated) {
        // Pipeline succeeded and output passed validation
        setResult(data.reformulated)
      } else {
        // HTTP 200 but pipeline status is "failed" or reformulated is null
        setError(true)
      }
    } catch {
      // Network failure (fetch threw) — show generic error
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  /**
   * resetAll — restore the interface to its initial empty state.
   * Clears the text input, the result, and any error message.
   */
  function resetAll() {
    setUtterance('')
    setResult(null)
    setError(false)
  }

  // The reset button is visible whenever there is any content to clear.
  const showReset = utterance !== '' || result !== null || error

  return (
    <div className={styles.page}>
      {/* App header */}
      <header className={styles.header}>
        <h1 className={styles.title}>עוזר הפקודות הקולי</h1>
        <p className={styles.subtitle}>
          הפכו כל בקשה בשפה טבעית לפקודה מובנית לסירי
        </p>
      </header>

      {/* Main card — instructions, input, result */}
      <main className={styles.card}>
        {/* Usage instructions for older adults */}
        <section className={styles.instructions} aria-label="הוראות שימוש">
          <p className={styles.instructionsTitle}>איך משתמשים?</p>
          <ol className={styles.instructionsList}>
            <li>הקלידו את הבקשה שלכם בתיבה.</li>
            <li>לחצו על כפתור השליחה.</li>
            <li>הפעילו את סירי ואמרו לה את הפקודה המתוקנת, או לחצו על כפתור ההקראה כדי להשמיע אותה.</li>
          </ol>
        </section>

        {/* Hebrew text input + submit button */}
        <CommandInput
          utterance={utterance}
          onChange={setUtterance}
          onSubmit={sendUtterance}
          loading={loading}
        />

        {/* Result / error area — only rendered after a response */}
        <div className={styles.resultArea}>
          <ResultDisplay result={result} error={error} />
        </div>

        {/* Reset button — visible once the user has typed or received a response */}
        {showReset && (
          <button
            type="button"
            className={styles.resetButton}
            onClick={resetAll}
            disabled={loading}
          >
            התחל מחדש
          </button>
        )}
      </main>
    </div>
  )
}

export default App
