import { appPath } from "../appBase";

/** Cached vocabulary illustration (public URL, long browser cache). */
export function WordImage({ url, alt, className = "" }) {
  if (!url) return null;
  const src = url.startsWith("http") ? url : appPath(url);
  return (
    <img
      src={src}
      alt={alt || ""}
      loading="lazy"
      className={`mx-auto max-h-44 w-auto max-w-full rounded-2xl object-contain shadow-md sm:max-h-52 ${className}`}
    />
  );
}
