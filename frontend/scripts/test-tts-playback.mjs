import { strict as assert } from "node:assert";
import { test } from "node:test";
import { cacheKey, createPlaybackController, SILENT_WAV } from "../src/ttsPlayback.js";

class FakeAudio {
  constructor() {
    this.src = "";
    this.paused = true;
    this.volume = 1;
    this.playsInline = false;
    this.currentTime = 0;
    this.playCalls = [];
    this._attrs = {};
    this._listeners = { ended: [], error: [] };
  }
  setAttribute(k, v) {
    this._attrs[k] = v;
  }
  removeAttribute(k) {
    if (k === "src") this.src = "";
    delete this._attrs[k];
  }
  addEventListener(type, fn) {
    (this._listeners[type] ||= []).push(fn);
  }
  removeEventListener(type, fn) {
    this._listeners[type] = (this._listeners[type] || []).filter((f) => f !== fn);
  }
  load() {}
  pause() {
    this.paused = true;
  }
  play() {
    this.paused = false;
    this.playCalls.push(this.src);
    return Promise.resolve();
  }
}

test("cache keys differ for consecutive lesson words", () => {
  const a = cacheKey("hola", "default-v14");
  const b = cacheKey("adiós", "default-v14");
  assert.notEqual(a, b);
  assert.equal(cacheKey("  hola  ", "default-v14"), cacheKey("hola", "default-v14"));
});

test("unlock primes silent wav once and never replays previous lesson src", () => {
  const ctl = createPlaybackController();
  const audio = new FakeAudio();

  const first = ctl.unlockHtmlAudio(audio);
  assert.equal(first.action, "prime-silent");
  assert.equal(audio.src, SILENT_WAV);
  assert.equal(audio.playCalls.length, 1);
  assert.equal(audio.playCalls[0], SILENT_WAV);

  // Simulate finished first word sitting in the element (the old bug).
  audio.src = "blob:hola-from-lesson-1";
  audio.paused = true;
  audio.playCalls = [];

  const second = ctl.unlockHtmlAudio(audio);
  assert.equal(second.action, "noop");
  assert.equal(audio.playCalls.length, 0, "must not replay previous lesson audio");
  assert.equal(audio.src, "blob:hola-from-lesson-1");
});

test("playUrl replaces previous src instead of mixing clips", async () => {
  const ctl = createPlaybackController();
  const audio = new FakeAudio();
  audio.src = "blob:old-word";

  const p = ctl.playUrl(audio, "blob:new-word");
  assert.equal(audio.src, "blob:new-word");
  assert.deepEqual(audio.playCalls, ["blob:new-word"]);
  audio._listeners.ended.forEach((fn) => fn());
  await p;
});

test("stop after word A leaves a clean element for word B", () => {
  const ctl = createPlaybackController();
  const audio = new FakeAudio();
  audio.src = "blob:word-a";
  audio.paused = false;
  ctl.stop(audio);
  assert.equal(audio.src, "");
  assert.equal(audio.paused, true);
});
