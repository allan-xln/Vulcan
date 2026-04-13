"use client";

import React from "react";
import useSWR from "swr";
import { BarChart3, DatabaseZap, ShieldCheck } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { architectureLayers } from "@repo/domain";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from "@/components/ui/card";

type HealthResponse = {
  status: string;
  phase: string;
};

const fetcher = async (url: string): Promise<HealthResponse> => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("health check failed");
  }

  return response.json() as Promise<HealthResponse>;
};

const telemetryReadiness = [
  { area: "Control plane", readiness: 40 },
  { area: "Analytics", readiness: 30 },
  { area: "AI explainability", readiness: 25 }
] as const;

const valueIcons = {
  "Tenant isolation": ShieldCheck,
  "Structured truth": DatabaseZap,
  "Explainable analytics": BarChart3
} as const;

export function PhaseOneOverview() {
  const { data } = useSWR("/api/health", fetcher, {
    revalidateOnFocus: false
  });

  return (
    <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <Card>
        <CardHeader>
          <Badge>Required stack baseline</Badge>
          <CardTitle>Phase 1 is a control-plane shell, not a fake product.</CardTitle>
          <CardDescription>
            The repository now carries a real monorepo foundation with documented trust
            boundaries, executable health checks and reserved seams for Supabase, ingestion
            and the Windows-first collector.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          {architectureLayers.map((layer) => {
            const Icon = valueIcons[layer.value];

            return (
              <div
                key={layer.name}
                className="rounded-3xl border border-ink/10 bg-canvas/70 p-4"
              >
                <Icon className="h-5 w-5 text-accent" />
                <h3 className="mt-3 text-base font-semibold">{layer.name}</h3>
                <p className="mt-2 text-sm leading-6 text-ink/75">{layer.summary}</p>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card className="bg-ink text-canvas">
        <CardHeader>
          <Badge className="bg-signal/20 text-signal">Repository health</Badge>
          <CardTitle>Current foundation status</CardTitle>
          <CardDescription className="text-canvas/75">
            {data ? `Health endpoint: ${data.status} (${data.phase})` : "Loading health status..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[...telemetryReadiness]}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(247,243,234,0.15)" />
                <XAxis dataKey="area" stroke="rgba(247,243,234,0.75)" />
                <YAxis stroke="rgba(247,243,234,0.75)" />
                <Tooltip />
                <Bar dataKey="readiness" fill="#fca311" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
