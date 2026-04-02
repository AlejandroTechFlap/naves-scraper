import useSWR from "swr";
import { fetcher } from "@/lib/api";

interface VncStatus {
  available: boolean;
  ws_port: number | null;
}

export function useVncStatus() {
  const { data } = useSWR<VncStatus>("/api/vnc/status", fetcher, {
    refreshInterval: 30_000,
    revalidateOnFocus: false,
  });

  return {
    vncAvailable: data?.available ?? false,
    wsPort: data?.ws_port ?? null,
  };
}
