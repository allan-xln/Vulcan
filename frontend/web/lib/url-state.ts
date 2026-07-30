"use client";

import { useCallback, useEffect, useState } from "react";

type RouteMap<T extends string> = Readonly<Record<T, string>>;

function normalizePathname(pathname: string) {
  if (!pathname || pathname === "/") return "/";
  return `/${pathname.split("/").filter(Boolean).join("/")}`;
}

export function readPathState<T extends string>(
  pathname: string,
  routes: RouteMap<T>,
  fallback: T
): T {
  const normalizedPathname = normalizePathname(pathname);
  const match = (Object.entries(routes) as [T, string][])
    .sort((left, right) => right[1].length - left[1].length)
    .find(([, path]) => {
      const normalizedRoute = normalizePathname(path);
      return (
        normalizedPathname === normalizedRoute ||
        (normalizedRoute !== "/" && normalizedPathname.startsWith(`${normalizedRoute}/`))
      );
    });
  return match?.[0] ?? fallback;
}

export function urlWithPath(
  href: string,
  pathname: string,
  parametersToDelete: readonly string[] = []
): string {
  const url = new URL(href);
  url.pathname = normalizePathname(pathname);
  parametersToDelete.forEach((parameter) => url.searchParams.delete(parameter));
  return `${url.pathname}${url.search}${url.hash}`;
}

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

export function usePathState<T extends string>(
  routes: RouteMap<T>,
  fallback: T,
  legacyParameter?: string,
  legacyAllowedValues?: readonly T[]
): [T, (value: T) => void] {
  const readCurrentValue = useCallback(() => {
    const pathValue = readPathState(window.location.pathname, routes, fallback);
    if (
      legacyParameter &&
      legacyAllowedValues &&
      window.location.pathname === "/" &&
      new URLSearchParams(window.location.search).has(legacyParameter)
    ) {
      return readUrlState(
        window.location.search,
        legacyParameter,
        legacyAllowedValues,
        pathValue
      );
    }
    return pathValue;
  }, [fallback, legacyAllowedValues, legacyParameter, routes]);

  const [value, setValue] = useState<T>(() =>
    typeof window === "undefined" ? fallback : readCurrentValue()
  );

  useEffect(() => {
    const synchronize = () => setValue(readCurrentValue());
    synchronize();
    window.addEventListener("popstate", synchronize);
    return () => window.removeEventListener("popstate", synchronize);
  }, [readCurrentValue]);

  const navigate = useCallback(
    (nextValue: T) => {
      setValue(nextValue);
      const nextUrl = urlWithPath(
        window.location.href,
        routes[nextValue],
        legacyParameter ? [legacyParameter] : []
      );
      const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (nextUrl !== currentUrl) {
        window.history.pushState({ route: nextValue }, "", nextUrl);
      }
    },
    [legacyParameter, routes]
  );

  return [value, navigate];
}
