"use client";

import { useEffect, useRef } from "react";

export function useScrollToBottom<T extends HTMLElement>(
  dependencies: ReadonlyArray<unknown>,
  options: { behavior?: ScrollBehavior } = {},
) {
  const ref = useRef<T | null>(null);
  const { behavior = "smooth" } = options;

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return ref;
}
