"use client";

import { useCallback, useEffect, useState } from "react";

export function readUrlState<T extends string>(
  search: string,
  parameter: string,
  allowedValues: readonly T[],
  fallback: T
): T {
  const value = new URLSearchParams(search).get(parameter);
  return value && allowedValues.includes(value as T) ? (value as T) : fallback;
}

export function urlWithState(
  href: string,
  parameter: string,
  value: string,
  fallback: string
): string {
  const url = new URL(href);
  if (value === fallback) {
    url.searchParams.delete(parameter);
  } else {
    url.searchParams.set(parameter, value);
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

export function useUrlState<T extends string>(
  parameter: string,
  allowedValues: readonly T[],
  fallback: T
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() =>
    typeof window === "undefined"
      ? fallback
      : readUrlState(window.location.search, parameter, allowedValues, fallback)
  );

  useEffect(() => {
    const synchronize = () => {
      setValue(readUrlState(window.location.search, parameter, allowedValues, fallback));
    };
    synchronize();
    window.addEventListener("popstate", synchronize);
    return () => window.removeEventListener("popstate", synchronize);
  }, [allowedValues, fallback, parameter]);

  const navigate = useCallback(
    (nextValue: T) => {
      setValue(nextValue);
      const nextUrl = urlWithState(
        window.location.href,
        parameter,
        nextValue,
        fallback
      );
      const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (nextUrl !== currentUrl) {
        window.history.pushState({ [parameter]: nextValue }, "", nextUrl);
      }
    },
    [fallback, parameter]
  );

  return [value, navigate];
}
