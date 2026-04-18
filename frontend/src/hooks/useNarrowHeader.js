import { useEffect, useState } from "react";

/** Sync with `theme.css` @media (max-width: 900px) for `.nb-header`. */
export const NARROW_HEADER_QUERY = "(max-width: 900px)";

export function useNarrowHeader() {
  const [narrow, setNarrow] = useState(() =>
    typeof window !== "undefined" && window.matchMedia(NARROW_HEADER_QUERY).matches,
  );

  useEffect(() => {
    const mq = window.matchMedia(NARROW_HEADER_QUERY);
    const onChange = () => setNarrow(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return narrow;
}
