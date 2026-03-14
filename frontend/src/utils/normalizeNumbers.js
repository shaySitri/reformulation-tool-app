/**
 * normalizeNumbers.js
 * -------------------
 * Preprocessing utility: converts digit sequences in Hebrew text to their
 * Hebrew word equivalents before the text is sent to the backend.
 *
 * Why this is needed:
 *   The backend validates that all characters in the utterance are Hebrew
 *   letters or spaces. Digits are rejected (HTTP 400). Users of voice-command
 *   apps often type numbers naturally (e.g. "שעה 7"), so we silently convert
 *   them to Hebrew words ("שעה שבע") before the API call.
 *
 * Supported range: 0–999.
 *   Numbers outside this range are left unchanged as digit strings.
 *
 * Number forms:
 *   Teens (11–19) use feminine forms (e.g. "שתים עשרה", "ארבע עשרה") which
 *   are the most natural and commonly understood standalone forms in
 *   colloquial Israeli Hebrew.
 *
 * Usage:
 *   import { normalizeNumbers } from './utils/normalizeNumbers'
 *   const normalized = normalizeNumbers("שלח הודעה ב 10 דקות")
 *   // → "שלח הודעה ב עשר דקות"
 */

// ---------------------------------------------------------------------------
// Word tables
// ---------------------------------------------------------------------------

/** Hebrew words for 1–9. Index 0 is unused (zero is a special case). */
const ONES = [
  '',        // 0 — handled separately
  'אחד',     // 1
  'שניים',   // 2
  'שלוש',    // 3
  'ארבע',    // 4
  'חמש',     // 5
  'שש',      // 6
  'שבע',     // 7
  'שמונה',   // 8
  'תשע',     // 9
]

/**
 * Hebrew words for 10–19 in feminine form.
 * Feminine forms (עשרה suffix) are the standard standalone form in modern
 * colloquial Hebrew and produce correct structure in compound numbers such as
 * "חמש מאות וארבע עשרה" (514).
 * Index 0 = ten (10), index 9 = nineteen (19).
 */
const TEENS = [
  'עשר',           // 10
  'אחת עשרה',      // 11
  'שתים עשרה',     // 12
  'שלוש עשרה',     // 13
  'ארבע עשרה',     // 14
  'חמש עשרה',      // 15
  'שש עשרה',       // 16
  'שבע עשרה',      // 17
  'שמונה עשרה',    // 18
  'תשע עשרה',      // 19
]

/** Hebrew words for multiples of ten: 20, 30, …, 90. */
const TENS = [
  '',            // 0 — unused
  '',            // 10 — handled by TEENS
  'עשרים',      // 20
  'שלושים',     // 30
  'ארבעים',     // 40
  'חמישים',     // 50
  'שישים',      // 60
  'שבעים',      // 70
  'שמונים',     // 80
  'תשעים',      // 90
]

// ---------------------------------------------------------------------------
// Core conversion function
// ---------------------------------------------------------------------------

/**
 * Convert a non-negative integer (0–999) to its Hebrew word representation.
 * Integers outside this range are returned as their original digit string.
 *
 * Structure rules:
 *   0         → אפס
 *   1–9       → ONES table
 *   10–19     → TEENS table (feminine forms)
 *   20–99     → TENS + " ו" + ONES (e.g. "עשרים ושלוש")
 *   100–999   → hundreds word + " ו" + recursive remainder
 *               מאה (100), מאתיים (200), X מאות (300–900)
 *
 * @param {number} n - A non-negative integer.
 * @returns {string} Hebrew word(s) for the number, or the original numeral
 *                   string if n > 999.
 */
function intToHebrew(n) {
  if (n === 0) return 'אפס'

  // 1–9
  if (n >= 1 && n <= 9) return ONES[n]

  // 10–19: use feminine TEENS table
  if (n >= 10 && n <= 19) return TEENS[n - 10]

  // 20–99: tens word + optional " ו" + ones word
  if (n >= 20 && n <= 99) {
    const tensWord = TENS[Math.floor(n / 10)]
    const remainder = n % 10
    return remainder === 0 ? tensWord : `${tensWord} ו${ONES[remainder]}`
  }

  // 100–999: hundreds word + optional " ו" + recursive remainder
  if (n >= 100 && n <= 999) {
    const hundredsDigit = Math.floor(n / 100)
    const remainder = n % 100

    // Special forms for 100 and 200; general form for 300–900
    let hundredsWord
    if (hundredsDigit === 1) {
      hundredsWord = 'מאה'
    } else if (hundredsDigit === 2) {
      hundredsWord = 'מאתיים'
    } else {
      hundredsWord = `${ONES[hundredsDigit]} מאות`
    }

    if (remainder === 0) return hundredsWord
    return `${hundredsWord} ו${intToHebrew(remainder)}`
  }

  // > 999: return the original numeral string unchanged
  return String(n)
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Replace all digit sequences in a Hebrew text string with their Hebrew word
 * equivalents.
 *
 * The replacement is performed left-to-right on each contiguous run of digits.
 * Non-digit characters (Hebrew letters, spaces, punctuation) are preserved
 * exactly as-is — the cleanInput step that follows handles those.
 *
 * @param {string} text - The raw utterance entered by the user.
 * @returns {string} The utterance with all digit sequences converted to
 *                   Hebrew words.
 *
 * @example
 * normalizeNumbers("שעה 7")                // → "שעה שבע"
 * normalizeNumbers("שלח הודעה ב 10 דקות") // → "שלח הודעה ב עשר דקות"
 * normalizeNumbers("514")                  // → "חמש מאות וארבע עשרה"
 * normalizeNumbers("שעה 7 ו30 דקות")      // → "שעה שבע ושלושים דקות"
 */
export function normalizeNumbers(text) {
  // Match one or more consecutive digits anywhere in the string.
  return text.replace(/\d+/g, (match) => {
    const n = parseInt(match, 10)
    return intToHebrew(n)
  })
}
