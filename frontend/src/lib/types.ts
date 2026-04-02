export interface ScraperStatus {
  state: "idle" | "running" | "error" | "stopped";
  pid: number | null;
  started_at: string | null;
  finished_at: string | null;
  last_error: string | null;
  current_page: number;
  total_new: number;
  total_skipped: number;
  needs_session_renewal: boolean;
  challenge_waiting: boolean;
}

export interface SessionStatus {
  state: "idle" | "running" | "error";
  pid: number | null;
  started_at: string | null;
  finished_at: string | null;
  last_error: string | null;
  waiting_for_login: boolean;
  login_detected?: boolean;
  navigating?: boolean;
}

export interface WebflowStatus {
  total: number;
  synced: number;
  pending: number;
  last_sync_at: string | null;
}

export interface CronConfig {
  cron_expr: string;
  max_pages: number;
  next_run: string | null;
}

export interface ScrapeRunRequest {
  max_pages: number;
  dry_run: boolean;
  reset: boolean;
}

export interface CronConfigRequest {
  cron_expr: string;
  max_pages: number;
}

export interface Listing {
  listing_id: string;
  url: string | null;
  title: string | null;
  price: string | null;
  price_numeric: number | null;
  price_per_m2: number | null;
  surface_m2: number | null;
  province: string | null;
  location: string | null;
  ad_type: string | null;
  property_type: string | null;
  seller_name: string | null;
  published_at: string | null;
  scraped_at: string | null;
  webflow_item_id: string | null;
}

export interface ListingsResponse {
  items: Listing[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SyncResult {
  status: string;
  synced?: number;
  errors?: number;
}
