import { useEffect, useState } from "react";

/** Tracks mobile virtual keyboard overlap via Visual Viewport API. */
export function useKeyboardInset(active = true) {
  const [inset, setInset] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(
    () => window.visualViewport?.height ?? window.innerHeight,
  );

  useEffect(() => {
    if (!active || !window.visualViewport) return undefined;

    const vv = window.visualViewport;
    const sync = () => {
      setViewportHeight(vv.height);
      setInset(Math.max(0, window.innerHeight - vv.height - vv.offsetTop));
    };

    sync();
    vv.addEventListener("resize", sync);
    vv.addEventListener("scroll", sync);
    return () => {
      vv.removeEventListener("resize", sync);
      vv.removeEventListener("scroll", sync);
    };
  }, [active]);

  return {
    keyboardInset: inset,
    keyboardOpen: inset > 0,
    viewportHeight,
  };
}
