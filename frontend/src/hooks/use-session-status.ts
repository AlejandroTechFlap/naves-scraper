import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { SessionStatus } from "@/lib/types";

export function useSessionStatus() {
  const { data, error, mutate } = useSWR<SessionStatus>(
    "/api/session/status",
    fetcher,
    {
      refreshInterval: (data) => {
        if (!data) return 0;
        if (data.state === "running") return 3000;
        return 0;
      },
      revalidateOnFocus: false,
    }
  );

  return {
    session: data,
    isLoading: !error && !data,
    isError: !!error,
    mutate,
    isRenewing: data?.state === "running",
  };
}
