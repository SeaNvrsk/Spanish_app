/** App base path when deployed under a secret URL prefix (e.g. /a1b2c3d4/). */
export const appBase = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");

export function appPath(path = "/") {
  const p = path.startsWith("/") ? path : `/${path}`;
  return appBase ? `${appBase}${p}` : p;
}
