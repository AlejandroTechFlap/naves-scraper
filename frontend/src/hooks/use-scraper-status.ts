import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { ScraperStatus } from "@/lib/types";

export function useScraperStatus() {
  const { data, error, mutate } = useSWR<ScraperStatus>(
    "/api/scraper/status",
    fetcher,
    {
      refreshInterval: (data) => {
        if (!data) return 3000;
        if (data.state === "running" || data.challenge_waiting || data.needs_session_renewal) return 3000;
        return 0;
      },
      revalidateOnFocus: false,
    }
  );

  return {
    status: data,
    isLoading: !error && !data,
    isError: !!error,
    mutate,
    isRunning: data?.state === "running",
    hasCaptcha: data?.challenge_waiting ?? false,
    needsRenewal: data?.needs_session_renewal ?? false,
  };
}
