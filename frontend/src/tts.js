import { useCallback, useEffect, useRef, useState } from "react";
import api from "./api";

let serverTtsAvailable = null; // null = unknown, true/false = cached

const audioCache = new Map();
const AUDIO_CACHE_MAX = 300;

function cacheKey(text) {
  return text.replace(/\s+/g, " ").trim();
}

function cacheGet(text) {
  const key = cacheKey(text);
  const url = audioCache.get(key);
  if (url) {
    audioCache.delete(key);
    audioCache.set(key, url);
  }
  return url;
}

function cachePut(text, url) {
  const key = cacheKey(text);
  audioCache.set(key, url);
  while (audioCache.size > AUDIO_CACHE_MAX) {
    const oldestKey = audioCache.keys().next().value;
    const oldestUrl = audioCache.get(oldestKey);
    audioCache.delete(oldestKey);
    if (oldestUrl) URL.revokeObjectURL(oldestUrl);
  }
}

function pickMexicanVoice() {
  const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
  if (!voices.length) return null;
  return (
    voices.find((v) => v.lang === "es-MX") ||
    voices.find((v) => /es[-_]419|es[-_]US|es[-_]CO|es[-_]AR/i.test(v.lang)) ||
    voices.find((v) => v.lang && v.lang.toLowerCase().startsWith("es")) ||
    null
  );
}

function speakBrowser(text) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const voice = pickMexicanVoice();
  if (voice) u.voice = voice;
  u.lang = voice?.lang || "es-MX";
  u.rate = 0.92;
  window.speechSynthesis.speak(u);
}

async function probeServerTts() {
  try {
    const { data } = await api.get("/tts/config");
    serverTtsAvailable = !!data.server_tts;
  } catch {
    // Don't cache false on transient errors — leave unknown for retry.
    if (serverTtsAvailable === null) serverTtsAvailable = false;
  }
  return serverTtsAvailable;
}

export function useSpeak() {
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
    probeServerTts();
  }, []);

  const playUrl = useCallback((url, text) => {
    if (audioRef.current) audioRef.current.pause();
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.onended = () => setSpeaking(false);
    audio.onerror = () => {
      setSpeaking(false);
      speakBrowser(text);
    };
    return audio.play();
  }, []);

  const speak = useCallback(
    async (text) => {
      if (!text) return;
      setSpeaking(true);
      try {
        // Re-check if we haven't confirmed server TTS yet (or after a prior failure).
        if (serverTtsAvailable !== true) {
          await probeServerTts();
        }
        if (serverTtsAvailable) {
          const cached = cacheGet(text);
          if (cached) {
            await playUrl(cached, text);
            return;
          }
          const { data } = await api.post("/tts/speak", { text }, { responseType: "blob" });
          const url = URL.createObjectURL(data);
          cachePut(text, url);
          await playUrl(url, text);
          return;
        }
      } catch {
        serverTtsAvailable = false;
      }
      speakBrowser(text);
      setTimeout(() => setSpeaking(false), Math.min(3000, 600 + text.length * 90));
    },
    [playUrl]
  );

  return { speak, speaking };
}
