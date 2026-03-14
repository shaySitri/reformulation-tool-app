/**
 * CommandInput.jsx
 * ----------------
 * A controlled Hebrew text input with a submit button and an optional
 * microphone icon embedded inside the input field for voice recording.
 *
 * Props:
 *   utterance        {string}   - The current input value (controlled).
 *   onChange         {function} - Called with the new string when the user types.
 *   onSubmit         {function} - Called when the form is submitted.
 *   loading          {boolean}  - When true, submit is disabled and shows a
 *                                 loading indicator.
 *   recording        {boolean}  - When true, the mic is active; input and submit
 *                                 are disabled, mic icon shows active/stop state.
 *   onStartRecording {function} - Called when the user presses the mic icon
 *                                 while not recording.
 *   onStopRecording  {function} - Called when the user presses the mic icon
 *                                 while recording.
 *   speechSupported  {boolean}  - When false, the mic icon is not rendered.
 *                                 Older browsers that lack SpeechRecognition
 *                                 simply see the text-input-only interface.
 *
 * Design notes:
 *   - The mic icon sits inside the input field on the physical left edge,
 *     using a position:relative wrapper + position:absolute icon button.
 *     The input gains extra inline-start padding so text never overlaps the icon.
 *   - During recording the icon turns red and pulses; the input border also
 *     pulses red to reinforce that the mic is open.
 *   - Input and submit are disabled during recording — the user cannot submit
 *     while the mic is still open.
 *   - A status hint below the input field tells the user recording is active.
 */

import styles from './CommandInput.module.css'

/**
 * CommandInput — Hebrew text field with an embedded mic icon, and a submit button.
 *
 * @param {Object}   props
 * @param {string}   props.utterance        - Controlled input value.
 * @param {Function} props.onChange          - Handler called on every keystroke.
 * @param {Function} props.onSubmit          - Handler called on form submission.
 * @param {boolean}  props.loading           - Whether a backend request is in flight.
 * @param {boolean}  props.recording         - Whether mic recording is active.
 * @param {Function} props.onStartRecording  - Start recording handler.
 * @param {Function} props.onStopRecording   - Stop recording handler.
 * @param {boolean}  props.speechSupported   - Whether SpeechRecognition is available.
 */
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
  /**
   * Handle form submission.
   * Prevent the default browser form POST, then delegate to the parent handler.
   */
  function handleSubmit(e) {
    e.preventDefault()
    onSubmit()
  }

  /**
   * Toggle the microphone: start if idle, stop if currently recording.
   */
  function handleMicClick() {
    if (recording) {
      onStopRecording()
    } else {
      onStartRecording()
    }
  }

  // Disable input and submit while either loading or recording is active.
  const inputDisabled  = loading || recording
  const submitDisabled = loading || recording || utterance.trim() === ''

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      {/*
        Input wrapper — position:relative so the mic icon can be placed
        absolutely inside the field on the physical left edge.
      */}
      <div className={styles.inputWrapper}>
        <input
          id="utterance-input"
          type="text"
          className={`${styles.input} ${recording ? styles.inputRecording : ''} ${speechSupported ? styles.inputWithMic : ''}`}
          value={utterance}
          onChange={(e) => onChange(e.target.value)}
          placeholder={
            recording
              ? 'מאזין... דברו בבקשה'
              : 'הקלד או הקלט פקודה בעברית'
          }
          lang="he"
          inputMode="text"
          autoComplete="off"
          spellCheck={false}
          disabled={inputDisabled}
          aria-label="הקלד פקודה קולית בעברית"
          aria-live={recording ? 'polite' : undefined}
        />

        {/*
          Mic icon button — absolutely positioned inside the input on the
          right (RTL leading) edge. Visible only when SpeechRecognition
          is available. Turns red and pulses while recording is active.
        */}
        {speechSupported && (
          <button
            type="button"
            className={`${styles.micIcon} ${recording ? styles.micIconRecording : ''}`}
            onClick={handleMicClick}
            disabled={loading}
            aria-label={recording ? 'עצור הקלטה' : 'התחל הקלטה קולית'}
            aria-pressed={recording}
          >
            {recording ? (
              /* Stop icon — shown while mic is active */
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="26" height="26" aria-hidden="true">
                <rect x="5" y="5" width="14" height="14" rx="2"/>
              </svg>
            ) : (
              /* Microphone icon — shown in idle state */
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="26" height="26" aria-hidden="true">
                <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"/>
                <path d="M19 11a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 0 0-2 0 7 7 0 0 0 6 6.92V20h-2a1 1 0 0 0 0 2h6a1 1 0 0 0 0-2h-2v-2.08A7 7 0 0 0 19 11z"/>
              </svg>
            )}
          </button>
        )}
      </div>

      {/* Recording status line — visible only while mic is active */}
      {recording && (
        <p className={styles.recordingHint} role="status" aria-live="polite">
          ההקלטה פעילה. לחצו על הסמל לעצירה (עד 30 שניות).
        </p>
      )}

      {/* Submit button */}
      <button
        type="submit"
        className={styles.button}
        disabled={submitDisabled}
        aria-busy={loading}
      >
        {loading ? 'שולח...' : 'שלח פקודה'}
      </button>
    </form>
  )
}

export default CommandInput
