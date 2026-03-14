/**
 * preprocessInput.js
 * ------------------
 * Chains the two frontend input preprocessing steps that run before every
 * API call. The original text typed by the user is never modified in the UI —
 * preprocessing applies only to the string sent in the request body.
 *
 * Pipeline (applied in order):
 *
 *   Step 1 — normalizeNumbers(text)
 *     Converts digit sequences to Hebrew word form (0–999).
 *     Must run first so that converted words are not accidentally stripped
 *     in the cleaning step.
 *     e.g. "שעה 7" → "שעה שבע"
 *
 *   Step 2 — removeSiri(text)
 *     Removes the word "סירי" (and surrounding whitespace) from the text.
 *     Users commonly address Siri by name at the start of a command; the
 *     backend pipeline does not expect it and may misclassify the intent.
 *     The word is removed silently — the visible input field is never changed.
 *     e.g. "סירי תשלחי הודעה לאמא" → "תשלחי הודעה לאמא"
 *
 *   Step 3 — cleanInput(text)
 *     Removes any character that the backend rejects.
 *     The backend accepts only Hebrew letters (U+05D0–U+05EA) and ASCII space.
 *     Everything else — English letters, punctuation, symbols — is silently
 *     removed. No error is shown to the user; invalid characters simply
 *     disappear before the request is sent.
 *     e.g. "שלום hello!" → "שלום "
 *
 * Usage:
 *   import { preprocessInput } from './utils/preprocessInput'
 *   const cleaned = preprocessInput(utterance)
 *   // send `cleaned` to the backend instead of `utterance`
 */

import { normalizeNumbers } from './normalizeNumbers.js'

// ---------------------------------------------------------------------------
// Step 2 — remove "סירי"
// ---------------------------------------------------------------------------

/**
 * Remove the word "סירי" wherever it appears in the text.
 *
 * Users commonly say "סירי" at the start (or anywhere) of a command because
 * they are used to addressing Siri by name. The backend pipeline does not
 * expect the wake word and may misclassify the intent if it is present.
 *
 * The regex matches "סירי" surrounded by optional whitespace and collapses
 * any extra spaces that result from the removal so the backend receives
 * clean, single-spaced Hebrew text.
 *
 * @param {string} text - Text after number normalization.
 * @returns {string} Text with "סירי" removed and whitespace normalized.
 *
 * @example
 * removeSiri("סירי תשלחי הודעה לאמא")   // → "תשלחי הודעה לאמא"
 * removeSiri("תשלחי סירי הודעה")         // → "תשלחי הודעה"
 * removeSiri("תתקשרי לאמא")             // → "תתקשרי לאמא"  (unchanged)
 */
function removeSiri(text) {
  return text.replace(/\s*סירי\s*/g, ' ').trim()
}

// ---------------------------------------------------------------------------
// Step 3 — character cleaning
// ---------------------------------------------------------------------------

/**
 * Remove all characters that the backend does not accept.
 *
 * Allowed characters (mirrors backend validators.py):
 *   - Hebrew letters: Unicode block U+05D0–U+05EA (א–ת)
 *   - ASCII space (U+0020)
 *
 * Everything else is removed silently. After normalizeNumbers has run, there
 * should be no digits left; this step catches any remaining Latin letters,
 * punctuation, and other symbols.
 *
 * @param {string} text - Text after number normalization.
 * @returns {string} Text containing only Hebrew letters and spaces.
 *
 * @example
 * cleanInput("שלום hello")          // → "שלום "
 * cleanInput("תשלחי, הודעה!")       // → "תשלחי הודעה"
 * cleanInput("תתקשרי לאמא")        // → "תתקשרי לאמא"  (unchanged)
 */
function cleanInput(text) {
  return text.replace(/[^\u05D0-\u05EA ]/g, '')
}

// ---------------------------------------------------------------------------
// Public API — combined pipeline
// ---------------------------------------------------------------------------

/**
 * Apply all preprocessing steps to a raw user utterance before sending it
 * to the backend.
 *
 * Steps applied (in order):
 *   1. normalizeNumbers — digits → Hebrew words
 *   2. removeSiri       — strip the wake word "סירי" if present
 *   3. cleanInput       — strip any remaining disallowed characters
 *
 * @param {string} utterance - The raw text typed by the user.
 * @returns {string} The cleaned, normalised string ready for the backend.
 *
 * @example
 * preprocessInput("שעה 7")                      // → "שעה שבע"
 * preprocessInput("514")                        // → "חמש מאות וארבע עשרה"
 * preprocessInput("סירי תשלחי הודעה לאמא")     // → "תשלחי הודעה לאמא"
 * preprocessInput("שלום hello")                 // → "שלום "
 * preprocessInput("תשלחי, הודעה!")              // → "תשלחי הודעה"
 * preprocessInput("תתקשרי לאמא")               // → "תתקשרי לאמא"
 */
export function preprocessInput(utterance) {
  const afterNumbers = normalizeNumbers(utterance)
  const afterSiri    = removeSiri(afterNumbers)
  const afterClean   = cleanInput(afterSiri)
  return afterClean
}
