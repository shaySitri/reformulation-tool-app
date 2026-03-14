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
 *   Step 2 — cleanInput(text)
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
// Step 2 — character cleaning
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
 *   2. cleanInput       — strip any remaining disallowed characters
 *
 * @param {string} utterance - The raw text typed by the user.
 * @returns {string} The cleaned, normalised string ready for the backend.
 *
 * @example
 * preprocessInput("שעה 7")              // → "שעה שבע"
 * preprocessInput("514")                // → "חמש מאות וארבע עשרה"
 * preprocessInput("שלום hello")         // → "שלום "
 * preprocessInput("תשלחי, הודעה!")      // → "תשלחי הודעה"
 * preprocessInput("שעה 7 call mom!")    // → "שעה שבע "
 * preprocessInput("תתקשרי לאמא")       // → "תתקשרי לאמא"
 */
export function preprocessInput(utterance) {
  const afterNumbers = normalizeNumbers(utterance)
  const afterClean   = cleanInput(afterNumbers)
  return afterClean
}
