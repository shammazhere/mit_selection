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
};

export type TimelineEvent = {
  timestamp: string;
  event: string;
};

export type CaseDetail = QueueItem & {
  self_score: number;
  peer_score: number;
  drift_score: number;
  cohort_used: "role" | "department" | string;
  fallback_applied: boolean;
  explanation_text: string;
  cusum_path: number[];
  event_timeline: TimelineEvent[];
  is_false_positive?: boolean;
  feedback_reason?: string;
};

const base = (import.meta.env.VITE_API_BASE ?? "/api").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
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
