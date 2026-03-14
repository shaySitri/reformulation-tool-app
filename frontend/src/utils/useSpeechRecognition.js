/**
 * useSpeechRecognition.js
 * -----------------------
 * Custom React hook that wraps the browser Web Speech API (SpeechRecognition)
 * for recording and transcribing Hebrew voice input.
 *
 * Browser support:
 *   iOS Safari  — available as window.webkitSpeechRecognition (primary target ✓)
 *   Chrome      — available as window.SpeechRecognition or webkitSpeechRecognition
 *   Firefox     — not supported; `supported` will be false and the mic button
 *                 is hidden by the caller
 *
 * Recording settings:
 *   lang            = 'he-IL'  — Hebrew transcription
 *   continuous      = true     — keeps listening through natural pauses; without
 *                                this the browser stops after a short silence
 *   interimResults  = true     — fires onresult with live (unfinished) text so
 *                                the input field updates while the user speaks
 *
 * Transcript accumulation:
 *   The SpeechRecognition result list contains a mix of finalised and interim
 *   segments. The hook concatenates all final segments plus the current interim
 *   segment and passes the combined string to the onTranscript callback on
 *   every result event. This gives the user live visual feedback.
 *
 * 30-second auto-stop:
 *   A setTimeout is started when recording begins. If the user does not press
 *   Stop manually within 30 seconds, recognition.stop() is called automatically.
 *
 * Preprocessing note:
 *   The transcribed text is passed to the caller raw and unmodified.
 *   preprocessInput() is applied only at submit time in App.jsx, not here.
 *
 * Usage:
 *   const { startRecording, stopRecording, recording, supported } =
 *     useSpeechRecognition({ onTranscript: setUtterance })
 */

import { useState, useEffect, useRef, useCallback } from 'react'

/** Maximum recording duration in milliseconds before auto-stop. */
const MAX_DURATION_MS = 30_000

/**
 * useSpeechRecognition — provides start/stop controls for Hebrew STT.
 *
 * @param {Object}   options
 * @param {Function} options.onTranscript - Called with the latest transcript
 *                                          string on every result event.
 *                                          Receives raw text — no preprocessing.
 *
 * @returns {{
 *   startRecording: () => void,
 *   stopRecording:  () => void,
 *   recording:      boolean,
 *   supported:      boolean,
 * }}
 */
export function useSpeechRecognition({ onTranscript }) {
  /** True while the microphone is open and the browser is transcribing. */
  const [recording, setRecording] = useState(false)

  /**
   * Store the latest onTranscript callback in a ref so the SpeechRecognition
   * event handlers always call the current version without needing to
   * re-register listeners on every render.
   */
  const onTranscriptRef = useRef(onTranscript)
  useEffect(() => {
    onTranscriptRef.current = onTranscript
  }, [onTranscript])

  /** Handle to the SpeechRecognition instance, created once on mount. */
  const recognitionRef = useRef(null)

  /** Handle to the auto-stop timer so it can be cancelled on manual stop. */
  const timerRef = useRef(null)

  /** Whether the current browser supports SpeechRecognition at all. */
  const supported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  // ---------------------------------------------------------------------------
  // Create the SpeechRecognition instance once on mount.
  // All event handlers are registered here; they read from refs so they never
  // become stale even if the component re-renders.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!supported) return

    const SpeechRecognitionClass =
      window.SpeechRecognition || window.webkitSpeechRecognition

    const recognition = new SpeechRecognitionClass()
    recognition.lang = 'he-IL'
    recognition.continuous = true      // keep listening through pauses
    recognition.interimResults = true  // fire events with live partial text

    /**
     * onresult — fires whenever the browser produces a new transcript segment.
     *
     * Accumulates all finalised segments from the result list and appends the
     * current interim segment, then calls onTranscript with the full string.
     */
    recognition.onresult = (event) => {
      let finalText = ''
      let interimText = ''

      for (let i = 0; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          finalText += event.results[i][0].transcript
        } else {
          interimText += event.results[i][0].transcript
        }
      }

      // Call the latest callback via ref to avoid stale closure issues.
      onTranscriptRef.current(finalText + interimText)
    }

    /**
     * onend — fires whenever recording stops (manually, via timer, or error).
     * Always clears the recording flag and the auto-stop timer.
     */
    recognition.onend = () => {
      setRecording(false)
      clearTimeout(timerRef.current)
    }

    /**
     * onerror — fires on microphone permission denial or other errors.
     * Clears state the same way as onend.
     */
    recognition.onerror = () => {
      setRecording(false)
      clearTimeout(timerRef.current)
    }

    recognitionRef.current = recognition

    // Cleanup: detach handlers and abort any in-progress recording on unmount.
    return () => {
      recognition.onresult = null
      recognition.onend = null
      recognition.onerror = null
      try { recognition.abort() } catch { /* ignore if not started */ }
    }
  }, [supported]) // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Public controls
  // ---------------------------------------------------------------------------

  /**
   * startRecording — request microphone access and begin transcription.
   *
   * Starts the 30-second auto-stop timer. Safe to call only when not already
   * recording (the mic button is disabled while recording === true).
   */
  const startRecording = useCallback(() => {
    if (!recognitionRef.current || recording) return

    recognitionRef.current.start()
    setRecording(true)

    // Auto-stop after MAX_DURATION_MS if the user does not press Stop.
    timerRef.current = setTimeout(() => {
      recognitionRef.current?.stop()
    }, MAX_DURATION_MS)
  }, [recording])

  /**
   * stopRecording — manually end the recording before the timer fires.
   *
   * Cancels the auto-stop timer and asks the browser to finalise the
   * current transcript. onend will fire shortly after, clearing the flag.
   */
  const stopRecording = useCallback(() => {
    clearTimeout(timerRef.current)
    recognitionRef.current?.stop()
  }, [])

  return { startRecording, stopRecording, recording, supported }
}
