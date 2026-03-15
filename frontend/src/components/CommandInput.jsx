/**
 * CommandInput.jsx
 * ----------------
 * Hebrew text input with a large circular microphone button and submit button.
 *
 * Layout:
 *   [text input — full width]
 *   [large circular mic]  [── שלח ── wide send button]
 *
 * The mic button is a prominent 64px circle — not embedded inside the input.
 * It is the primary voice-input affordance, equal in weight to the send button.
 *
 * Props:
 *   utterance        {string}   - Controlled input value.
 *   onChange         {function} - Called on every keystroke.
 *   onSubmit         {function} - Called on form submission.
 *   loading          {boolean}  - When true, shows "מעבד..." and disables input.
 *   recording        {boolean}  - When true, mic is active (red pulsing circle).
 *   onStartRecording {function} - Start recording handler.
 *   onStopRecording  {function} - Stop recording handler.
 *   speechSupported  {boolean}  - When false, mic button is not rendered.
 */

import styles from './CommandInput.module.css'

function CommandInput({
  utterance,
  onChange,
  onSubmit,
  loading,
  recording,
  onStartRecording,
  onStopRecording,
  speechSupported,
}) {
  function handleSubmit(e) {
    e.preventDefault()
    onSubmit()
  }

  function handleMicClick() {
    if (recording) {
      onStopRecording()
    } else {
      onStartRecording()
    }
  }

  const inputDisabled  = loading || recording
  const submitDisabled = loading || recording || utterance.trim() === ''

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>

      {/* Text input */}
      <input
        id="utterance-input"
        type="text"
        className={`${styles.input} ${recording ? styles.inputRecording : ''}`}
        value={utterance}
        onChange={(e) => onChange(e.target.value)}
        placeholder={recording ? 'מאזין... דברו בבקשה' : 'הקלידו או הקליטו פקודה בעברית...'}
        lang="he"
        inputMode="text"
        autoComplete="off"
        spellCheck={false}
        disabled={inputDisabled}
        aria-label="הקלד פקודה קולית בעברית"
        aria-live={recording ? 'polite' : undefined}
      />

      {/* Recording status hint */}
      {recording && (
        <p className={styles.recordingHint} role="status" aria-live="polite">
          ההקלטה פעילה. לחצו על כפתור המיקרופון לעצירה.
        </p>
      )}

      {/* Action row: circular mic (right) + send button (flex-grow) */}
      <div className={styles.actionRow}>
        {speechSupported && (
          <button
            type="button"
            className={`${styles.micButton} ${recording ? styles.micButtonRecording : ''}`}
            onClick={handleMicClick}
            disabled={loading}
            aria-label={recording ? 'עצור הקלטה' : 'התחל הקלטה קולית'}
            aria-pressed={recording}
          >
            {recording ? (
              /* Stop icon */
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="28" height="28" aria-hidden="true">
                <rect x="5" y="5" width="14" height="14" rx="2"/>
              </svg>
            ) : (
              /* Microphone icon */
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="28" height="28" aria-hidden="true">
                <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"/>
                <path d="M19 11a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 0 0-2 0 7 7 0 0 0 6 6.92V20h-2a1 1 0 0 0 0 2h6a1 1 0 0 0 0-2h-2v-2.08A7 7 0 0 0 19 11z"/>
              </svg>
            )}
          </button>
        )}

        <button
          type="submit"
          className={`${styles.button} ${loading ? styles.buttonLoading : ''}`}
          disabled={submitDisabled}
          aria-busy={loading}
        >
          {loading ? 'מעבד...' : 'שלח'}
        </button>
      </div>
    </form>
  )
}

export default CommandInput
