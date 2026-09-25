export type Artifact = {
  id: number;
  key: string;
  title: string;
  kind: string;
  status: string;
  project_id: number | null;
  revision: number;
  [key: string]: any;
};
export type Session = {
  actor: string;
  role: string;
  csrf_token: string;
  demo_mode: boolean;
};
export type FieldSchema = {
  type?: string;
  title?: string;
  default?: any;
  enum?: any[];
  anyOf?: FieldSchema[];
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  format?: string;
};
export type ModelSchema = {
  properties: Record<string, FieldSchema>;
  required?: string[];
};
export type Metadata = {
  schemas: Record<string, ModelSchema>;
  transitions: Record<string, Record<string, string[]>>;
  default_transitions: Record<string, string[]>;
};
export type Execution = {
  id: number;
  test_case_id: number;
  status: string;
  actual_result: string;
  evidence: string;
  executed_by: string;
  executed_at: string;
  request_body: string;
  response_body: string;
  response_status: number;
  duration_ms: number;
  defect_id: number | null;
  current_contract?: boolean;
};
export type Gate = {
  name: string;
  status: string;
  mandatory: boolean;
  detail: string;
};
export type Readiness = { status: string; gates: Gate[]; scope: Artifact[] };

let csrfToken = "";
export function setCsrf(token: string) {
  csrfToken = token;
}
export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: "The server could not complete this request." }));
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (e: any) => `${e.loc?.slice(1).join(".") || "Input"}: ${e.msg}`,
              )
              .join("; ")
          : detail?.message ||
            "The request failed. Review the record and try again.";
    throw new Error(message);
  }
  return response.json();
}
export function post<T = any>(path: string, data: unknown = {}) {
  return api<T>(path, { method: "POST", body: JSON.stringify(data) });
}
export function label(value: string) {
  return value
    .toLowerCase()
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\b(rest|soap|json|xml|uat|api|http|oauth2|oidc)\b/gi, (c) =>
      c.toUpperCase(),
    );
}
export function date(value?: string) {
  return value
    ? new Date(value).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC",
      })
    : "Not scheduled";
}
export const titles: Record<string, string> = {
  dashboard: "Overview",
  projects: "Projects",
  requirements: "Requirements",
  traceability: "Traceability matrix",
  systems: "Systems",
  integrations: "Integration catalog",
  "test-plans": "Test plans",
  "test-cases": "Test management",
  uat: "User acceptance testing",
  "uat-scenarios": "UAT scenarios",
  incidents: "Incidents & defects",
  changes: "Change requests",
  risks: "Risk register",
  dependencies: "Dependencies",
  releases: "Releases",
  reports: "Reports & documents",
  training: "Training library",
  administration: "Administration",
  processes: "Process design",
  stakeholders: "Stakeholders",
  documents: "Controlled documents",
};
