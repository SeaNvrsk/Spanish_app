import { useCallback, useEffect, useRef, useState } from "react";
import api from "./api";

let serverTtsAvailable = null;

const audioCache = new Map();
const AUDIO_CACHE_MAX = 300;

function cacheKey(text, profile) {
  return `${profile}:${text.replace(/\s+/g, " ").trim()}`;
}

function cacheGet(text, profile) {
  const key = cacheKey(text, profile);
  const url = audioCache.get(key);
  if (url) {
    audioCache.delete(key);
    audioCache.set(key, url);
  }
  return url;
}

function cachePut(text, profile, url) {
  const key = cacheKey(text, profile);
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

function speakBrowser(text, childLike = false) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const voice = pickMexicanVoice();
  if (voice) u.voice = voice;
  u.lang = voice?.lang || "es-MX";
  u.rate = childLike ? 0.96 : 0.92;
  u.pitch = childLike ? 1.0 : 1;
  window.speechSynthesis.speak(u);
}

async function probeServerTts() {
  try {
    const { data } = await api.get("/tts/config");
    serverTtsAvailable = !!data.server_tts;
  } catch {
    if (serverTtsAvailable === null) serverTtsAvailable = false;
  }
  return serverTtsAvailable;
}

export function useSpeak(profile = "default") {
  const isAngelica = profile === "angelica";
  const endpoint = isAngelica ? "/tts/speak/angelica" : "/tts/speak";
  const cacheProfile = isAngelica ? "angelica-v13" : "default";

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
      speakBrowser(text, isAngelica);
    };
    return audio.play();
  }, [isAngelica]);

  const speak = useCallback(
    async (text) => {
      if (!text) return;
      setSpeaking(true);
      try {
        if (serverTtsAvailable !== true) {
          await probeServerTts();
        }
        if (serverTtsAvailable) {
          const cached = cacheGet(text, cacheProfile);
          if (cached) {
            await playUrl(cached, text);
            return;
          }
          const { data } = await api.post(endpoint, { text }, { responseType: "blob" });
          const url = URL.createObjectURL(data);
          cachePut(text, cacheProfile, url);
          await playUrl(url, text);
          return;
        }
      } catch {
        serverTtsAvailable = false;
      }
      speakBrowser(text, isAngelica);
      setTimeout(() => setSpeaking(false), Math.min(4000, 600 + text.length * 90));
    },
    [cacheProfile, endpoint, isAngelica, playUrl]
  );

  return { speak, speaking };
}
