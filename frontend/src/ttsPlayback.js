/** Tiny silent WAV — optional HTMLAudio unlock on the first page gesture. */
export const SILENT_WAV =
  "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";

/**
 * Playback that stays inside the tap gesture.
 *
 * Mobile browsers ignore HTMLAudio.play() after await. They DO allow
 * AudioContext.resume() in the tap, then BufferSource.start() later.
 * Never clear src + load() on the shared <audio> — that leaves it dead
 * for the next word.
 */
export function createPlaybackController() {
  let htmlPrimed = false;
  let playGen = 0;
  let currentSource = null;

  function stopCurrentSource() {
    if (!currentSource) return;
    try {
      currentSource.onended = null;
      currentSource.stop();
    } catch {
      /* already stopped */
    }
    try {
      currentSource.disconnect();
    } catch {
      /* ignore */
    }
    currentSource = null;
  }

  return {
    isPrimed() {
      return htmlPrimed;
    },

    /**
     * Unlock only. First call may play a silent WAV. Later calls never
     * replay whatever clip is sitting in <audio>.
     */
    unlockHtmlAudio(audio) {
      if (!audio) return { action: "skip" };
      if (htmlPrimed) return { action: "noop" };
      htmlPrimed = true;
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

    hardReset(audio) {
      stopCurrentSource();
      if (!audio) return;
      try {
        audio.pause();
        audio.currentTime = 0;
      } catch {
        /* ignore */
      }
    },

    async playDecoded(ctx, blob) {
      const myGen = ++playGen;
      stopCurrentSource();
      if (ctx.state === "suspended") {
        await ctx.resume();
      }
      if (ctx.state !== "running") {
        throw new Error("AudioContext not running");
      }
      const ab = await blob.arrayBuffer();
      if (myGen !== playGen) return;
      const buf = await ctx.decodeAudioData(ab.slice(0));
      if (myGen !== playGen) return;
      await new Promise((resolve, reject) => {
        const source = ctx.createBufferSource();
        source.buffer = buf;
        source.connect(ctx.destination);
        source.onended = () => {
          if (currentSource === source) currentSource = null;
          if (myGen === playGen) resolve();
        };
        try {
          currentSource = source;
          source.start(0);
        } catch (err) {
          currentSource = null;
          reject(err);
        }
      });
    },

    playUrl(audio, url) {
      const myGen = ++playGen;
      stopCurrentSource();
      if (!audio) return Promise.reject(new Error("no audio element"));
      try {
        audio.pause();
      } catch {
        /* ignore */
      }
      audio.playsInline = true;
      audio.setAttribute("playsinline", "true");
      audio.setAttribute("webkit-playsinline", "true");
      audio.volume = 1;
      if (audio.src !== url) {
        audio.src = url;
      } else {
        try {
          audio.currentTime = 0;
        } catch {
          /* ignore */
        }
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
