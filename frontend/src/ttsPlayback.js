/** Tiny silent WAV — unlocks HTMLAudio inside a user gesture on iOS. */
export const SILENT_WAV =
  "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";

/**
 * Shared-element playback for iOS.
 *
 * iPhone reuses one <audio>. If pointerdown calls play() on whatever is
 * already in src, the NEXT word/lesson replays the PREVIOUS clip.
 */
export function createPlaybackController() {
  let primed = false;
  let playGen = 0;

  return {
    isPrimed() {
      return primed;
    },

    /**
     * Unlock only. Never replay the last lesson's file.
     * First call: play a silent WAV once. Later calls: no-op on HTMLAudio.
     */
    unlockHtmlAudio(audio) {
      if (!audio) return { action: "skip" };
      if (primed) return { action: "noop" };
      primed = true;
      audio.src = SILENT_WAV;
      try {
        audio.load();
      } catch {
        /* ignore */
      }
      const p = audio.play();
      if (p && typeof p.then === "function") {
        p.then(() => {
          try {
            audio.pause();
            audio.currentTime = 0;
          } catch {
            /* ignore */
          }
        }).catch(() => {});
      }
      return { action: "prime-silent" };
    },

    /** Tear down current src so iOS cannot keep playing the previous blob. */
    hardReset(audio) {
      if (!audio) return;
      try {
        audio.pause();
      } catch {
        /* ignore */
      }
      try {
        audio.removeAttribute("src");
        audio.src = "";
        audio.load();
      } catch {
        /* ignore */
      }
    },

    playUrl(audio, url) {
      const myGen = ++playGen;
      this.hardReset(audio);
      audio.playsInline = true;
      audio.setAttribute("playsinline", "true");
      audio.setAttribute("webkit-playsinline", "true");
      audio.volume = 1;
      audio.src = url;
      try {
        audio.load();
      } catch {
        /* ignore */
      }

      return new Promise((resolve, reject) => {
        const onEnded = () => {
          cleanup();
          if (myGen === playGen) resolve();
        };
        const onError = () => {
          cleanup();
          if (myGen === playGen) reject(new Error("HTMLAudio play failed"));
        };
        const cleanup = () => {
          audio.removeEventListener("ended", onEnded);
          audio.removeEventListener("error", onError);
        };
        audio.addEventListener("ended", onEnded);
        audio.addEventListener("error", onError);
        const p = audio.play();
        if (p && typeof p.then === "function") {
          p.catch(onError);
        }
      });
    },

    stop(audio) {
      playGen += 1;
      this.hardReset(audio);
    },
  };
}

export function cacheKey(text, profile) {
  return `${profile}:${String(text || "").replace(/\s+/g, " ").trim()}`;
}
