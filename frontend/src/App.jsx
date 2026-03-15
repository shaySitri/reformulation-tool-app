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
 *                             May be typed manually or set from a voice
 *                             transcription — always stored raw and unmodified.
 *   result    {string|null} - The reformulated command from the backend.
 *                             null until a successful response is received.
 *   error     {boolean}     - true when any failure occurred (network error,
 *                             HTTP 4xx/5xx, or backend status === "failed").
 *   loading   {boolean}     - true while a fetch request is in flight.
 *
 * Voice input:
 *   useSpeechRecognition is called with setUtterance as its onTranscript
 *   callback. Live transcription updates the input field in real time.
 *   The raw transcript is stored as-is — no preprocessing at this stage.
 *   Recording never auto-submits; the user must press the submit button.
 *
 * Preprocessing:
 *   preprocessInput() is applied only in sendUtterance(), right before the
 *   fetch call. This converts digits to Hebrew words and strips disallowed
 *   characters. The visible input field always shows the original raw text.
 *
 * API contract:
 *   POST /api/reformulate
 *   Body:     { utterance: string }  ← preprocessed, not raw
 *   Success:  HTTP 200, { status: "success", reformulated: string, ... }
 *   Failure:  HTTP 200 with status "failed", OR HTTP 4xx/5xx
 *
 * Vite proxy:
 *   /api/* is forwarded to http://127.0.0.1:8000/* by vite.config.js.
 */

import { useState } from 'react'
import CommandInput from './components/CommandInput.jsx'
import FeedbackDialog from './components/FeedbackDialog.jsx'
import ResultDisplay from './components/ResultDisplay.jsx'
import { preprocessInput } from './utils/preprocessInput.js'
import { useSpeechRecognition } from './utils/useSpeechRecognition.js'
import styles from './App.module.css'

/**
 * App — top-level component; owns state, voice hook, and backend fetch.
 */
function App() {
  const [utterance, setUtterance] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(false)
  // feedbackData is non-null while the feedback dialog is visible.
  // Holds the fields needed to build the feedback log record.
  const [feedbackData, setFeedbackData] = useState(null)

  // Voice recording hook. onTranscript writes the raw transcript directly into
  // the utterance state — no preprocessing, no modification of the visible text.
  const {
    startRecording,
    stopRecording,
    recording,
    supported: speechSupported,
  } = useSpeechRecognition({ onTranscript: setUtterance })

  /**
   * sendUtterance — POST the current utterance to the reformulation API.
   *
   * Applies preprocessInput() (number normalisation + character cleaning)
   * silently before the request. The visible input field is never changed.
   *
   * Success path: HTTP 200 with status "success" → store reformulated string.
   * Failure path: any other outcome → set error flag.
   */
  async function sendUtterance() {
    // Guard: ignore empty input (button is disabled, but be defensive)
    if (!utterance.trim()) return

    // Reset previous result/error before the new request
    setResult(null)
    setError(false)
    setLoading(true)

    // Preprocessing: (1) convert digits to Hebrew words, (2) strip any
    // remaining characters the backend does not accept. Applied only here,
    // only at submit time. The input field always shows the raw text.
    const processedUtterance = preprocessInput(utterance)

    try {
      const response = await fetch('/api/reformulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ utterance: processedUtterance }),
      })

      if (!response.ok) {
        setError(true)
        return
      }

      const data = await response.json()

      if (data.status === 'success' && data.reformulated) {
        setResult(data.reformulated)
        setFeedbackData({
          original_input: data.original,
          intent_id: data.intent_id,
          intent_label: data.intent_label,
          reformulated_command: data.reformulated,
          backend_status: data.status,
        })
      } else {
        setError(true)
      }
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  /**
   * postFeedback — fire-and-forget POST to /api/feedback.
   * Errors are silently ignored so the UI is never blocked by a logging failure.
   */
  async function postFeedback(siريUnderstand, notes) {
    if (!feedbackData) return
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...feedbackData,
          siri_understood: siريUnderstand,
          notes: notes ?? null,
        }),
      })
    } catch {
      // Feedback logging failure must never disrupt the user experience.
    }
  }

  /** Called when user answers כן or לא (with optional notes). */
  async function handleFeedbackSubmit(siريUnderstand, notes) {
    await postFeedback(siريUnderstand, notes)
    setFeedbackData(null)
  }

  /** Called when user closes the dialog without answering. */
  async function handleFeedbackClose() {
    await postFeedback(null, null)
    setFeedbackData(null)
  }

  /**
   * resetAll — restore the interface to its initial empty state.
   * Stops any active recording, clears the input, result, and error.
   */
  function resetAll() {
    if (recording) stopRecording()
    setUtterance('')
    setResult(null)
    setError(false)
    setFeedbackData(null)
  }

  // Show the reset button whenever there is anything to clear.
  const showReset = utterance !== '' || result !== null || error

  return (
    <div className={styles.page}>

      {/* ── Branded full-width header ── */}
      <header className={styles.appHeader}>
        <div className={styles.appHeaderContent}>
          <h1 className={styles.appTitle}>איך אפשר לעזור?</h1>
          <p className={styles.appSubtitle}>הקלידו או אמרו בקשה והמערכת תיצור פקודה שסירי תבין</p>
        </div>
      </header>

      {/* ── Centered workspace ── */}
      <div className={styles.workspace}>

        {/* Input card */}
        <main className={`${styles.card} ${loading ? styles.cardLoading : ''}`}>
          <CommandInput
            utterance={utterance}
            onChange={setUtterance}
            onSubmit={sendUtterance}
            loading={loading}
            recording={recording}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            speechSupported={speechSupported}
          />
        </main>

        {/* AI processing indicator */}
        {loading && (
          <div className={styles.processingCard} role="status" aria-live="polite">
            <span className={styles.processingIcon}>⚙</span>
            <span className={styles.processingText}>מעבד את הבקשה...</span>
            <span className={styles.processingDots} aria-hidden="true">
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.dot} />
            </span>
          </div>
        )}

        {/* Result / error card */}
        <ResultDisplay result={result} error={error} />

        {/* Inline feedback card — appears below result */}
        {feedbackData && (
          <FeedbackDialog
            onSubmit={handleFeedbackSubmit}
            onClose={handleFeedbackClose}
          />
        )}

        {/* Reset button */}
        {showReset && (
          <button
            type="button"
            className={styles.resetButton}
            onClick={resetAll}
            disabled={loading}
          >
            ↩ ניסיון חדש
          </button>
        )}
      </div>
    </div>
  )
}

export default App
