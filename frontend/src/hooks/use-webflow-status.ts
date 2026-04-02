import useSWR from "swr";
import { fetcher } from "@/lib/api";
import type { WebflowStatus } from "@/lib/types";

export function useWebflowStatus() {
  const { data, error, mutate } = useSWR<WebflowStatus>(
    "/api/webflow/status",
    fetcher,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    webflow: data,
    isLoading: !error && !data,
    isError: !!error,
    mutate,
  };
}
