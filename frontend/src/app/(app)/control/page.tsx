"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RunForm } from "@/components/scraper/run-form";
import { StatsRow } from "@/components/panel/stats-row";
import { CronCard } from "@/components/panel/cron-card";
import { LogsPanel } from "@/components/panel/logs-panel";
import { useScraperStatus } from "@/hooks/use-scraper-status";

export default function ControlPage() {
  const { isRunning, hasCaptcha } = useScraperStatus();

  const isActive = isRunning || hasCaptcha;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Panel de Control</h1>

      {/* Metric cards */}
      <StatsRow />

      {/* Scraper + Cron */}
      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <CardHeader className="border-b pb-3">
            <CardTitle>Iniciar scraper</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <RunForm />
          </CardContent>
        </Card>
        <CronCard />
      </div>

      {/* Logs — full width, fixed height with scroll */}
      <LogsPanel isActive={isActive} />
    </div>
  );
}
