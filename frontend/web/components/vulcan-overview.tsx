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

import { architectureLayers } from "@vulcan/domain";

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
  product: string;
};

const fetcher = async (url: string): Promise<HealthResponse> => {
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("falha no health check");
  }

  return response.json() as Promise<HealthResponse>;
};

const operationalReadiness = [
  { area: "Dados do tenant", readiness: 55 },
  { area: "Fatos operacionais", readiness: 45 },
  { area: "Insights de IA", readiness: 35 }
] as const;

const valueIcons = {
  "Tenant isolation": ShieldCheck,
  "Structured truth": DatabaseZap,
  "Explainable analytics": BarChart3
} as const;

export function VulcanOverview() {
  const { data } = useSWR("/api/health", fetcher, {
    revalidateOnFocus: false
  });

  return (
    <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
      <Card>
        <CardHeader>
          <Badge>Base técnica essencial</Badge>
          <CardTitle>Vulcan transforma fatos operacionais em decisões explicáveis.</CardTitle>
          <CardDescription>
            A fundação da plataforma combina isolamento por tenant, evidências operacionais
            estruturadas, análise com IA e um agente com limites claros de privacidade.
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
          <Badge className="bg-signal/20 text-signal">Saúde do repositório</Badge>
          <CardTitle>Status atual da fundação</CardTitle>
          <CardDescription className="text-canvas/75">
            {data ? `Endpoint de saúde: ${data.status} (${data.product})` : "Carregando status de saúde..."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[...operationalReadiness]}>
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
