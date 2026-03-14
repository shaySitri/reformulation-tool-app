/**
 * CommandInput.jsx
 * ----------------
 * A controlled Hebrew text input with a submit button.
 *
 * Props:
 *   utterance  {string}   - The current input value (controlled).
 *   onChange   {function} - Called with the new string when the user types.
 *   onSubmit   {function} - Called when the form is submitted.
 *   loading    {boolean}  - When true, the button is disabled and shows a
 *                           loading indicator.
 *
 * Design notes:
 *   - Full-width layout so the touch targets are easy to hit on a phone.
 *   - Large text and padding for comfortable use by older adults.
 *   - The input's inputMode="text" and lang="he" hint to mobile browsers to
 *     open a Hebrew keyboard.
 *   - The submit button is disabled while a request is in flight to prevent
 *     double-submission.
 */

import styles from './CommandInput.module.css'

/**
 * CommandInput — renders the Hebrew text field and submit button.
 *
 * @param {Object} props
 * @param {string}   props.utterance - Controlled input value.
 * @param {Function} props.onChange  - Handler called on every keystroke.
 * @param {Function} props.onSubmit  - Handler called when the form is submitted.
 * @param {boolean}  props.loading   - Whether a backend request is in flight.
 */
function CommandInput({ utterance, onChange, onSubmit, loading }) {
  /**
   * Handle form submission.
   * Prevent the default browser form POST, then delegate to the parent handler.
   *
   * @param {React.FormEvent} e
   */
  function handleSubmit(e) {
    e.preventDefault()
    onSubmit()
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      {/* Descriptive label — visually prominent, associated with the input */}
      <label htmlFor="utterance-input" className={styles.label}>
        הקלד פקודה קולית בעברית
      </label>

      {/* Hebrew text input */}
      <input
        id="utterance-input"
        type="text"
        className={styles.input}
        value={utterance}
        onChange={(e) => onChange(e.target.value)}
        placeholder="לדוגמה: תשלחי הודעה לישראל שאני מאחרת"
        lang="he"
        inputMode="text"
        autoComplete="off"
        spellCheck={false}
        disabled={loading}
        aria-label="הקלד פקודה קולית בעברית"
      />

      {/* Submit button — full width, large touch target */}
      <button
        type="submit"
        className={styles.button}
        disabled={loading || utterance.trim() === ''}
        aria-busy={loading}
      >
        {loading ? 'שולח...' : 'שלח פקודה'}
      </button>
    </form>
  )
}

export default CommandInput
