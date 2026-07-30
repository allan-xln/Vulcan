"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { EChartsOption } from "echarts";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="command-chart-skeleton" aria-hidden="true" />
});

const VULCAN_THEME = {
  color: ["#ff7a1a", "#ffb347", "#39d98a", "#44b7ff", "#ff4d5f", "#8d929c"],
  backgroundColor: "transparent",
  textStyle: {
    color: "#d9dde5",
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
  },
  title: { textStyle: { color: "#f7f8fa" } },
  legend: { textStyle: { color: "#8d929c" } },
  categoryAxis: {
    axisLine: { lineStyle: { color: "rgba(156,163,175,.22)" } },
    axisTick: { show: false },
    axisLabel: { color: "#737985" },
    splitLine: { show: false }
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: "#737985" },
    splitLine: { lineStyle: { color: "rgba(156,163,175,.10)" } }
  },
  tooltip: {
    backgroundColor: "rgba(8,10,13,.96)",
    borderColor: "rgba(255,122,26,.45)",
    textStyle: { color: "#f7f8fa" }
  }
};

export function VulcanChart({
  option,
  height = "100%",
  ariaLabel
}: {
  option: EChartsOption;
  height?: string | number;
  ariaLabel: string;
}) {
  const [ready, setReady] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    let active = true;
    void import("echarts").then((echarts) => {
      echarts.registerTheme("vulcan-command", VULCAN_THEME);
      if (active) setReady(true);
    });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(preference.matches);
    update();
    preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);

  if (!ready) return <div className="command-chart-skeleton" style={{ height }} aria-hidden="true" />;

  return (
    <div role="img" aria-label={ariaLabel} className="h-full min-h-0 w-full">
      <ReactECharts
        option={{
          animationDuration: 650,
          animationDurationUpdate: 420,
          ...option,
          animation: reducedMotion ? false : option.animation
        }}
        theme="vulcan-command"
        notMerge
        lazyUpdate
        style={{ height, width: "100%" }}
        opts={{ renderer: "canvas", devicePixelRatio: Math.min(window.devicePixelRatio, 2) }}
      />
    </div>
  );
}
