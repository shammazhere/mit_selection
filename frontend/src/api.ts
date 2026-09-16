export type Severity = "low" | "medium" | "high" | "critical";

export type QueueItem = {
  user_id: string;
  name: string;
  role: string;
  team?: string;
  risk_score: number;
  severity: Severity;
  last_updated: string;
  fallback_applied?: boolean;
  is_false_positive?: boolean;
  feedback_reason?: string;
};

export type TimelineEvent = {
  timestamp: string;
  event: string;
};

export type CusumPoint = {
  time?: string;
  timestamp?: string;
  value: number;
  label?: string;
  event?: string;
};

export type AccessAuditEntry = {
  id: number;
  timestamp: string;
  investigator_id: string;
  target_user_id: string;
  action: string;
  details?: string;
};

export type CaseDetail = QueueItem & {
  self_score: number;
  peer_score: number;
  drift_score: number;
  cohort_used: "role" | "department" | string;
  fallback_applied: boolean;
  explanation_text: string;
  cusum_path: (number | CusumPoint)[];
  event_timeline: TimelineEvent[];
  is_false_positive?: boolean;
  feedback_reason?: string;
  access_audit_log?: AccessAuditEntry[];
};

const base = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const urlsToTry = [
    `${base}${cleanPath}`,
    cleanPath,
    cleanPath.startsWith("/api") ? cleanPath.replace(/^\/api/, "") : `/api${cleanPath}`
  ];
  
  // Deduplicate URLs
  const uniqueUrls = Array.from(new Set(urlsToTry));
  
  let lastError: Error | null = null;
  for (const url of uniqueUrls) {
    try {
      const res = await fetch(url, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          ...(init?.headers ?? {}),
        },
      });
      
      const cType = res.headers.get("content-type") || "";
      // If server returned HTML (SPA fallback), skip and try next URL
      if (cType.includes("text/html")) {
        continue;
      }
      
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status} ${url}: ${text}`);
      }
      
      const text = await res.text();
      // Verify response is actually JSON and not an HTML error document
      if (text.trim().startsWith("<")) {
        continue;
      }
      
      return JSON.parse(text) as T;
    } catch (e: any) {
      lastError = e instanceof Error ? e : new Error(String(e));
    }
  }
  
  throw lastError || new Error(`Failed to load ${path}`);
}

export function fetchQueue() {
  return request<QueueItem[]>("/queue");
}

export function fetchCase(userId: string) {
  return request<CaseDetail>(`/case/${encodeURIComponent(userId)}`);
}

export function postFeedback(userId: string, reason: string) {
  return request<{ ok: boolean }>("/feedback", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      is_false_positive: true,
      reason,
    }),
  });
}

export function simulateThreat(params: {
  name: string;
  role: string;
  site: string;
  file: string;
  email: string;
  after_hours: boolean;
  usb: boolean;
  cloud_upload: boolean;
}) {
  return request<{
    ok: boolean;
    user_id: string;
    name: string;
    role: string;
    risk_score: number;
    severity: string;
    explanation_text: string;
  }>("/simulate_threat", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function postTelemetry(payload: Record<string, unknown>) {
  return request<{ ok: boolean; status: string; user_id: string }>("/telemetry", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}


