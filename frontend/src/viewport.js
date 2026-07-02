/** Portrait-first mobile viewport — fixes Android "desktop width" shrinking the UI. */
export function ensureMobileViewport() {
  const ua = navigator.userAgent || "";
  const mobile = /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
  if (!mobile) return;

  const deviceCssWidth = () => {
    const short = Math.min(window.screen.width, window.screen.height);
    const dpr = window.devicePixelRatio || 1;
    // Android often reports device pixels in screen.width
    if (short > 600) return Math.round(short / dpr);
    return short;
  };

  const apply = () => {
    const root = document.documentElement;
    const portrait = window.matchMedia("(orientation: portrait)").matches;
    const targetW = deviceCssWidth();

    let vp = document.querySelector('meta[name="viewport"]');
    if (!vp) {
      vp = document.createElement("meta");
      vp.name = "viewport";
      document.head.prepend(vp);
    }

    root.classList.add("is-mobile");
    root.classList.toggle("is-portrait", portrait);
    root.classList.toggle("is-landscape", !portrait);

    // Force phone-width layout when browser reports desktop width (~980px)
    vp.setAttribute("content", `width=${targetW}, initial-scale=1, viewport-fit=cover`);

    requestAnimationFrame(() => {
      const layoutW = root.clientWidth || window.innerWidth;
      if (layoutW > targetW + 60) {
        const zoom = layoutW / targetW;
        root.style.zoom = String(Math.min(zoom, 3));
        root.dataset.viewportZoom = "1";
      } else {
        root.style.zoom = portrait ? "1" : "";
        delete root.dataset.viewportZoom;
      }
    });
  };

  apply();
  window.addEventListener("orientationchange", () => setTimeout(apply, 150));
  window.addEventListener("resize", apply);
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", apply);
  }
}
