import { useCallback, useEffect, useRef, useState } from "react";
import api from "./api";
import { createPlaybackController } from "./ttsPlayback";

let serverTtsAvailable = null;

/** Object-URL cache (legacy / HTMLAudio src). */
const audioUrlCache = new Map();
/** Raw blob cache — preferred; lets iOS play inside the tap gesture. */
const audioBlobCache = new Map();
const AUDIO_CACHE_MAX = 300;

/** Shared AudioContext — resume() must run inside a user gesture on iOS. */
let sharedAudioCtx = null;

/** One shared element — iOS is picky about many Audio() instances. */
let sharedHtmlAudio = null;

const IS_IOS =
  typeof navigator !== "undefined" &&
  (/iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1));

const playback = createPlaybackController();

function getAudioContext() {
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  if (!sharedAudioCtx || sharedAudioCtx.state === "closed") {
    sharedAudioCtx = new AC();
  }
  return sharedAudioCtx;
}

function getHtmlAudio() {
  if (!sharedHtmlAudio) {
    sharedHtmlAudio = new Audio();
    sharedHtmlAudio.preload = "auto";
    sharedHtmlAudio.playsInline = true;
    sharedHtmlAudio.setAttribute("playsinline", "true");
    sharedHtmlAudio.setAttribute("webkit-playsinline", "true");
  }
  return sharedHtmlAudio;
}

/**
 * Call synchronously at the start of a click/tap handler (before any await).
 * Unlocks both Web Audio and HTMLAudio for iPhone / PWA.
 */
export function unlockAudio() {
  const ctx = getAudioContext();
  if (ctx && ctx.state === "suspended") {
    ctx.resume().catch(() => {});
  }
  try {
    playback.unlockHtmlAudio(getHtmlAudio());
  } catch {
    /* ignore */
  }
}

export function stopPlayback() {
  try {
    playback.stop(getHtmlAudio());
  } catch {
    /* ignore */
  }
}

function cacheKey(text, profile, lemma = "") {
  const inf = String(lemma || "").trim().toLowerCase();
  return `${profile}:${inf}:${text.replace(/\s+/g, " ").trim()}`;
}

function cacheGetUrl(text, profile, lemma = "") {
  const key = cacheKey(text, profile, lemma);
  const url = audioUrlCache.get(key);
  if (url) {
    audioUrlCache.delete(key);
    audioUrlCache.set(key, url);
  }
  return url;
}

function cacheGetBlob(text, profile, lemma = "") {
  const key = cacheKey(text, profile, lemma);
  const blob = audioBlobCache.get(key);
  if (blob) {
    audioBlobCache.delete(key);
    audioBlobCache.set(key, blob);
  }
  return blob;
}

function cachePut(text, profile, blob, url, lemma = "") {
  const key = cacheKey(text, profile, lemma);
  audioBlobCache.set(key, blob);
  audioUrlCache.set(key, url);
  while (audioBlobCache.size > AUDIO_CACHE_MAX) {
    const oldestKey = audioBlobCache.keys().next().value;
    audioBlobCache.delete(oldestKey);
    const oldestUrl = audioUrlCache.get(oldestKey);
    audioUrlCache.delete(oldestKey);
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
  if (!window.speechSynthesis) return false;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const voice = pickMexicanVoice();
  if (voice) u.voice = voice;
  u.lang = voice?.lang || "es-MX";
  u.rate = childLike ? 0.96 : 0.92;
  u.pitch = childLike ? 1.0 : 1;
  window.speechSynthesis.speak(u);
  return true;
}

function assertAudioBlob(data) {
  if (!data || !(data instanceof Blob)) throw new Error("TTS: empty response");
  if (data.size < 800) throw new Error("TTS: response too small");
  const type = (data.type || "").toLowerCase();
  if (type.includes("json") || type.includes("text/html") || type.includes("text/plain")) {
    throw new Error("TTS: non-audio response");
  }
}

async function blobLooksLikeMp3(blob) {
  const head = new Uint8Array(await blob.slice(0, 3).arrayBuffer());
  if (head.length < 2) return false;
  if (head[0] === 0x49 && head[1] === 0x44 && head[2] === 0x33) return true; // ID3
  return head[0] === 0xff && (head[1] & 0xe0) === 0xe0;
}

export function isSpeakableSpanish(text) {
  const s = String(text || "").trim();
  if (!s) return false;
  const low = s.toLowerCase();
  if (s.includes("+") || s.includes("...") || low.includes("infinitive")) return false;
  if (/^-[a-záéíóúüñ]{1,4}$/i.test(s)) return false;
  return true;
}

function playUrlHtmlAudio(url) {
  return playback.playUrl(getHtmlAudio(), url);
}

async function playBlobViaWebAudio(blob) {
  const ctx = getAudioContext();
  if (!ctx) throw new Error("no AudioContext");
  if (ctx.state === "suspended") {
    await ctx.resume();
  }
  if (ctx.state !== "running") {
    throw new Error("AudioContext not running");
  }
  const ab = await blob.arrayBuffer();
  const copy = ab.slice(0);
  const audioBuf = await ctx.decodeAudioData(copy);
  const source = ctx.createBufferSource();
  source.buffer = audioBuf;
  source.connect(ctx.destination);
  await new Promise((resolve, reject) => {
    source.onended = () => resolve();
    try {
      source.start(0);
    } catch (err) {
      reject(err);
    }
  });
}

async function playBlob(blob, url) {
  // iPhone: HTMLAudio + playsInline is more reliable than Web Audio (silent switch /
  // PWA). Other platforms: try Web Audio first (lower latency), then HTMLAudio.
  if (IS_IOS) {
    await playUrlHtmlAudio(url);
    return;
  }
  try {
    await playBlobViaWebAudio(blob);
  } catch {
    await playUrlHtmlAudio(url);
  }
}

let probePromise = null;

async function probeServerTts() {
  if (serverTtsAvailable !== null) return serverTtsAvailable;
  if (probePromise) return probePromise;
  probePromise = (async () => {
    try {
      const { data } = await api.get("/tts/config", { timeout: 4000 });
      serverTtsAvailable = !!data.server_tts;
    } catch {
      serverTtsAvailable = false;
    } finally {
      probePromise = null;
    }
    return serverTtsAvailable;
  })();
  return probePromise;
}

async function fetchTtsBlob(endpoint, text, lemma = "") {
  const body = { text };
  if (lemma) body.infinitive = lemma;
  const { data } = await api.post(endpoint, body, { responseType: "blob", timeout: 12000 });
  assertAudioBlob(data);
  let blob = data;
  // iOS sometimes gives an empty MIME — force audio/mpeg so <audio> accepts it.
  if (!data.type || data.type === "application/octet-stream") {
    blob = new Blob([data], { type: "audio/mpeg" });
  }
  if (!(await blobLooksLikeMp3(blob))) throw new Error("TTS: not mp3");
  return blob;
}

export function useSpeak(profile = "default") {
  const isAngelica = profile === "angelica";
  const endpoint = isAngelica ? "/tts/speak/angelica" : "/tts/speak";
  const cacheProfile = isAngelica ? "angelica-v16" : "default-v17";

  const [speaking, setSpeaking] = useState(false);
  const genRef = useRef(0);
  const prefetchingRef = useRef(new Set());

  useEffect(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
    probeServerTts();

    const warm = () => unlockAudio();
    window.addEventListener("pointerdown", warm, { once: true, passive: true });
    window.addEventListener("touchstart", warm, { once: true, passive: true });
    window.addEventListener("keydown", warm, { once: true });
    return () => {
      window.removeEventListener("pointerdown", warm);
      window.removeEventListener("touchstart", warm);
      window.removeEventListener("keydown", warm);
    };
  }, []);

  const prefetch = useCallback(
    async (text, lemma = "") => {
      if (!text || !isSpeakableSpanish(text)) return;
      if (cacheGetBlob(text, cacheProfile, lemma)) return;
      const waitKey = cacheKey(text, cacheProfile, lemma);
      if (prefetchingRef.current.has(waitKey)) return;
      prefetchingRef.current.add(waitKey);
      try {
        if (serverTtsAvailable !== true) await probeServerTts();
        if (!serverTtsAvailable) return;
        const blob = await fetchTtsBlob(endpoint, text, lemma);
        const url = URL.createObjectURL(blob);
        cachePut(text, cacheProfile, blob, url, lemma);
      } catch {
        /* ignore — speak() will retry */
      } finally {
        prefetchingRef.current.delete(waitKey);
      }
    },
    [cacheProfile, endpoint]
  );

  const speak = useCallback(
    async (text, lemma = "") => {
      if (!text || !isSpeakableSpanish(text)) return;

      // CRITICAL: must run before any await — keeps iOS audio unlocked.
      unlockAudio();

      const myGen = ++genRef.current;
      setSpeaking(true);
      const stillMine = () => myGen === genRef.current;

      try {
        if (serverTtsAvailable !== true) {
          await probeServerTts();
        }
        if (!stillMine()) return;

        if (serverTtsAvailable) {
          let blob = cacheGetBlob(text, cacheProfile, lemma);
          let url = cacheGetUrl(text, cacheProfile, lemma);

          if (!blob) {
            blob = await fetchTtsBlob(endpoint, text, lemma);
            if (!stillMine()) return;
            url = URL.createObjectURL(blob);
            cachePut(text, cacheProfile, blob, url, lemma);
          }

          if (!stillMine()) return;
          await playBlob(blob, url);
          if (stillMine()) setSpeaking(false);
          return;
        }
      } catch {
        // Fall through to browser voice.
      }

      if (!stillMine()) return;
      speakBrowser(text, isAngelica);
      setTimeout(() => {
        if (stillMine()) setSpeaking(false);
      }, Math.min(4000, 600 + text.length * 90));
    },
    [cacheProfile, endpoint, isAngelica]
  );

  return { speak, speaking, prefetch };
}
