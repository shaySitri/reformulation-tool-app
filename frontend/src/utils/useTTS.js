/**
 * useTTS.js
 * ---------
 * Custom React hook that wraps the browser Web Speech API (SpeechSynthesis)
 * for reading Hebrew text aloud.
 *
 * Behaviour:
 *   - On mount, loads the list of voices available on this device. The list
 *     is populated asynchronously (the 'voiceschanged' event fires once the
 *     browser has finished loading system voices), so the hook listens for
 *     that event and updates its internal voice list when it fires.
 *   - When speak() is called, any current speech is cancelled first, then the
 *     new utterance is started.
 *   - The 'speaking' flag is true from the moment speech starts until it ends
 *     or an error occurs.
 *
 * Hebrew voice selection:
 *   The hook always sets utterance.lang = 'he-IL'. It additionally tries to
 *   select a voice whose lang starts with 'he' from the available voice list.
 *
 *   Availability by platform:
 *     iOS Safari   — Hebrew voice built-in (primary target device ✓)
 *     Android Chrome — Hebrew usually available
 *     Windows Chrome — depends on installed Windows TTS voices
 *
 *   If no Hebrew voice is found, lang = 'he-IL' is still set and the browser
 *   uses its best fallback. The button remains functional regardless.
 *
 * Usage:
 *   const { speak, speaking } = useTTS()
 *   speak("תפתחי מצלמה")   // reads the text aloud
 *   speaking               // true while audio is playing
 */

import { useState, useEffect, useCallback } from 'react'

/**
 * useTTS — provides speak() and speaking state for Hebrew text-to-speech.
 *
 * @returns {{ speak: (text: string) => void, speaking: boolean }}
 */
export function useTTS() {
  /** List of SpeechSynthesisVoice objects available on this device. */
  const [voices, setVoices] = useState([])

  /** True while the browser is currently speaking. */
  const [speaking, setSpeaking] = useState(false)

  // Load the voice list on mount and whenever the browser signals a change.
  useEffect(() => {
    if (!window.speechSynthesis) return

    function loadVoices() {
      setVoices(window.speechSynthesis.getVoices())
    }

    // Voices may already be available synchronously (e.g. Chrome desktop).
    loadVoices()

    // On most browsers the list is populated asynchronously.
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices)
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices)
    }
  }, [])

  /**
   * speak — read the given Hebrew text aloud.
   *
   * Any speech currently in progress is cancelled before the new utterance
   * begins, preventing overlapping audio if the user presses the button again.
   *
   * @param {string} text - The Hebrew text to speak.
   */
  const speak = useCallback(
    (text) => {
      if (!window.speechSynthesis) return

      // Stop any speech already in progress.
      window.speechSynthesis.cancel()

      const utterance = new SpeechSynthesisUtterance(text)

      // Always set the language so the browser applies Hebrew phonology.
      utterance.lang = 'he-IL'

      // Prefer a Hebrew voice if one is available on this device.
      const hebrewVoice = voices.find((v) => v.lang.startsWith('he'))
      if (hebrewVoice) {
        utterance.voice = hebrewVoice
      }

      // Slightly slower rate for older adults — 0.9 instead of the default 1.0.
      utterance.rate = 0.9

      utterance.onstart = () => setSpeaking(true)
      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)

      window.speechSynthesis.speak(utterance)
    },
    [voices],
  )

  return { speak, speaking }
}
