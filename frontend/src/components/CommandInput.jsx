/**
 * CommandInput.jsx
 * ----------------
 * A controlled Hebrew text input with a submit button and an optional
 * microphone button for voice recording.
 *
 * Props:
 *   utterance        {string}   - The current input value (controlled).
 *   onChange         {function} - Called with the new string when the user types.
 *   onSubmit         {function} - Called when the form is submitted.
 *   loading          {boolean}  - When true, submit is disabled and shows a
 *                                 loading indicator.
 *   recording        {boolean}  - When true, the mic is active; input and submit
 *                                 are disabled, mic button shows stop state.
 *   onStartRecording {function} - Called when the user presses the mic button
 *                                 while not recording.
 *   onStopRecording  {function} - Called when the user presses the mic button
 *                                 while recording.
 *   speechSupported  {boolean}  - When false, the mic button is not rendered.
 *                                 Older browsers that lack SpeechRecognition
 *                                 simply see the text-input-only interface.
 *
 * Design notes:
 *   - Full-width layout for easy touch targets on a phone.
 *   - Input and submit are disabled during recording — the user cannot submit
 *     while the mic is still open.
 *   - The mic button changes label and colour to give clear recording feedback.
 *   - The text field is always visible and editable when not recording, so the
 *     user can correct the transcription before submitting.
 */

import styles from './CommandInput.module.css'

/**
 * CommandInput — Hebrew text field, submit button, and optional mic button.
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

      {/* Hebrew text input */}
      <input
        id="utterance-input"
        type="text"
        className={`${styles.input} ${recording ? styles.inputRecording : ''}`}
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

      {/* Submit button */}
      <button
        type="submit"
        className={styles.button}
        disabled={submitDisabled}
        aria-busy={loading}
      >
        {loading ? 'שולח...' : 'שלח פקודה'}
      </button>

      {/*
        Microphone button — rendered only when SpeechRecognition is available.
        Changes appearance while recording to give clear visual feedback.
      */}
      {speechSupported && (
        <button
          type="button"
          className={`${styles.micButton} ${recording ? styles.micButtonRecording : ''}`}
          onClick={handleMicClick}
          disabled={loading}
          aria-label={recording ? 'עצור הקלטה' : 'התחל הקלטה קולית'}
          aria-pressed={recording}
        >
          {recording ? '⏹ עצור הקלטה' : '🎙 הקלטה קולית'}
        </button>
      )}

      {/* Recording status line — visible only while mic is active */}
      {recording && (
        <p className={styles.recordingHint} role="status" aria-live="polite">
          ההקלטה פעילה. לחצו על "עצור הקלטה" לסיום (עד 30 שניות).
        </p>
      )}
    </form>
  )
}

export default CommandInput
