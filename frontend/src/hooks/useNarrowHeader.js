import { useEffect, useState } from "react";

/** Sync with `theme.css` @media (max-width: 900px) for `.nb-header`. */
export const NARROW_HEADER_QUERY = "(max-width: 900px)";

function readNarrow() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  try {
    return window.matchMedia(NARROW_HEADER_QUERY).matches;
  } catch {
    return false;
  }
}

export function useNarrowHeader() {
  const [narrow, setNarrow] = useState(readNarrow);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    let mq;
    try {
      mq = window.matchMedia(NARROW_HEADER_QUERY);
    } catch {
      return;
    }
    const onChange = () => setNarrow(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return narrow;
}
