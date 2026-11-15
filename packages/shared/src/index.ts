export const LIFECYCLE_STATUSES = [
  "operational", "still_travelling", "mission_completed_hardware_left",
  "decommissioned_dormant", "lost_contact_failed", "crashed_impacted", "unknown_unverified",
] as const;
export type LifecycleStatus = (typeof LIFECYCLE_STATUSES)[number];

export const LIFECYCLE_LABELS: Record<LifecycleStatus, string> = {
  operational: "Operational",
  still_travelling: "Still travelling",
  mission_completed_hardware_left: "Mission completed, hardware left behind",
  decommissioned_dormant: "Decommissioned / dormant",
  lost_contact_failed: "Lost contact / failed",
  crashed_impacted: "Crashed / impacted",
  unknown_unverified: "Unknown / unverified",
};

export type LearningLevel = "explorer" | "investigator" | "scientist";
export interface User { id: number; email: string; display_name: string; xp: number }
export interface TokenOut { access_token: string; token_type: "bearer" }

export class AsteraClient {
  constructor(private baseUrl: string, private getToken: () => string | null = () => null) {}
  private async req<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const res = await fetch(`${this.baseUrl}/api/v1${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init.headers },
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? `Request failed (${res.status})`);
    return res.json() as Promise<T>;
  }
  health() { return this.req<{ status: string; database: string }>("/health"); }
  register(email: string, display_name: string, password: string) {
    return this.req<TokenOut>("/auth/register", { method: "POST", body: JSON.stringify({ email, display_name, password }) });
  }
  login(email: string, password: string) {
    return this.req<TokenOut>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
  }
  me() { return this.req<User>("/auth/me"); }
}
