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
 *   - The mic icon sits inside the input field on the leading (right) edge,
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
      {/* Descriptive label */}
      <label htmlFor="utterance-input" className={styles.label}>
        הקלד פקודה קולית בעברית
      </label>

      {/*
        Input wrapper — position:relative so the mic icon can be placed
        absolutely inside the field on the leading (right) edge.
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
              : 'לדוגמה: תשלחי הודעה לישראל שאני מאחרת'
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
            {recording ? '⏹' : '🎙'}
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
