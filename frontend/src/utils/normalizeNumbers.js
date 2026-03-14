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

/** Hebrew words for 10–19. Index 0 = ten, index 9 = nineteen. */
const TEENS = [
  'עשר',          // 10
  'אחד עשר',      // 11
  'שניים עשר',    // 12
  'שלוש עשר',     // 13
  'ארבע עשר',     // 14
  'חמש עשר',      // 15
  'שש עשר',       // 16
  'שבע עשר',      // 17
  'שמונה עשר',    // 18
  'תשע עשר',      // 19
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
 * @param {number} n - A non-negative integer.
 * @returns {string} - Hebrew word(s) for the number, or the original numeral
 *                     string if n > 999.
 */
function intToHebrew(n) {
  if (n === 0) return 'אפס'

  // 1–9
  if (n >= 1 && n <= 9) return ONES[n]

  // 10–19
  if (n >= 10 && n <= 19) return TEENS[n - 10]

  // 20–99: tens + optional ones joined with ו
  if (n >= 20 && n <= 99) {
    const tensWord = TENS[Math.floor(n / 10)]
    const remainder = n % 10
    return remainder === 0 ? tensWord : `${tensWord} ו${ONES[remainder]}`
  }

  // 100–999: hundreds + optional tens/ones
  if (n >= 100 && n <= 999) {
    const hundredsDigit = Math.floor(n / 100)
    const remainder = n % 100

    // Hundred word: מאה (1), מאתיים (2), X מאות (3–9)
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
 * exactly as-is.
 *
 * @param {string} text - The raw utterance entered by the user.
 * @returns {string} - The utterance with all digit sequences converted to
 *                     Hebrew words.
 *
 * @example
 * normalizeNumbers("שעה 7")           // → "שעה שבע"
 * normalizeNumbers("שלח הודעה ב 10 דקות") // → "שלח הודעה ב עשר דקות"
 * normalizeNumbers("כנסו 3 אנשים")    // → "כנסו שלוש אנשים"
 * normalizeNumbers("שעה 7 ו30 דקות") // → "שעה שבע ושלושים דקות"
 */
export function normalizeNumbers(text) {
  // Match one or more consecutive digits anywhere in the string.
  return text.replace(/\d+/g, (match) => {
    const n = parseInt(match, 10)
    return intToHebrew(n)
  })
}
