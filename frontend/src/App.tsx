import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { FormEvent, ReactNode } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  BookOpen,
  Box,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDot,
  ClipboardCheck,
  Code2,
  Download,
  ExternalLink,
  FileText,
  FlaskConical,
  GitBranch,
  Layers3,
  LayoutDashboard,
  Link2,
  Loader2,
  LogOut,
  Menu,
  Moon,
  MoreHorizontal,
  Network,
  Play,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sun,
  Target,
  Trash2,
  TriangleAlert,
  Users,
  Workflow,
  X,
} from "lucide-react";
import { api, date, label, post, setCsrf, titles } from "./api";
import type {
  Artifact,
  Execution,
  FieldSchema,
  Metadata,
  ModelSchema,
  Readiness,
  Session,
} from "./api";

type Dialog = {
  title: string;
  description?: string;
  schema: ModelSchema;
  values?: Record<string, any>;
  submit: (data: any) => Promise<any>;
  submitLabel?: string;
};
type Workspace = { items: Artifact[]; executions: Execution[] };
type Context = Workspace & {
  session: Session;
  project: Artifact | undefined;
  meta: Metadata;
  refresh: () => Promise<void>;
  open: (d: Dialog) => void;
  notify: (message: string) => void;
  action: (fn: () => Promise<any>, message?: string) => Promise<void>;
  busy: boolean;
};
const WorkspaceContext = createContext<Context>(null!);
const useWorkspace = () => useContext(WorkspaceContext);
const s = (type: string, extra: Partial<FieldSchema> = {}): FieldSchema => ({
  type,
  ...extra,
});
const schema = (
  properties: Record<string, FieldSchema>,
  required = Object.keys(properties),
): ModelSchema => ({ properties, required });
const icons: Record<string, typeof Activity> = {
  projects: Layers3,
  requirements: FileText,
  systems: Box,
  integrations: Network,
  "test-cases": FlaskConical,
  "test-plans": ClipboardCheck,
  incidents: TriangleAlert,
  changes: GitBranch,
  uat: Users,
  risks: ShieldCheck,
  releases: Box,
  training: BookOpen,
  processes: Workflow,
  dependencies: Link2,
};
const referenceKinds: Record<string, string> = {
  source_system_id: "systems",
  target_system_id: "systems",
  requirement_id: "requirements",
  integration_id: "integrations",
  test_plan_id: "test-plans",
  session_id: "uat",
  stakeholder_id: "stakeholders",
  project_id: "projects",
};

function Badge({ status }: { status: string }) {
  const positive = [
    "PASS",
    "COMPLETE",
    "COMPLETED",
    "APPROVED",
    "READY",
    "ACTIVE",
    "SATISFIED",
    "CLOSED",
    "RESOLVED",
    "MITIGATED",
    "DEPLOYED",
  ].includes(status);
  const negative = [
    "FAIL",
    "FAILED",
    "CRITICAL",
    "REJECTED",
    "NOT READY",
    "DEGRADED",
  ].includes(status);
  const warning = [
    "BLOCKED",
    "HIGH",
    "PENDING_APPROVAL",
    "IN_PROGRESS",
    "IMPLEMENTING",
    "OPEN",
    "NEW",
    "WARNING",
    "NOT_READY",
  ].includes(status);
  return (
    <span
      className={`badge ${positive ? "positive" : negative ? "negative" : warning ? "warning" : "neutral"}`}
    >
      <span className="status-dot" />
      {label(status)}
    </span>
  );
}
function Empty({
  title = "No records to show",
  description = "Create a record or adjust your filters to get started.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="empty">
      <Layers3 size={30} />
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}
function Loading() {
  return (
    <div className="loading" role="status">
      <Loader2 className="spin" />
      Loading workspace…
    </div>
  );
}
function Section({
  title,
  subtitle,
  children,
  aside,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  );
}
function ArtifactLink({ item }: { item: Artifact }) {
  const Icon = icons[item.kind] || FileText;
  return (
    <Link className="artifact-link" to={`/${item.kind}/${item.id}`}>
      <span className="mini-icon">
        <Icon size={16} />
      </span>
      <span>
        <span className="record-key">{item.key}</span>
        <strong>{item.title}</strong>
      </span>
      <ChevronRight size={15} />
    </Link>
  );
}
function useResource<T = any>(url: string) {
  const { items } = useWorkspace();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError("");
    api<T>(url)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [url, items]);
  return { data, error };
}
function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error-box" role="alert">
      <TriangleAlert size={18} />
      {message}
    </div>
  );
}

function Login({ onLogin }: { onLogin: (session: Session) => void }) {
  const [role, setRole] = useState("analyst");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<boolean | null>(null);
  useEffect(() => {
    api("/api/health")
      .then((d) => setDemo(d.demo_mode))
      .catch((e) => setError(e.message));
  }, []);
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      onLogin(
        await post("/api/auth/login", {
          email: form.get("email"),
          password: form.get("password"),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login-screen">
      <div className="login-art">
        <div className="brand large">
          <span className="brand-mark">
            <Network />
          </span>
          EICC<span className="brand-label">CONTROL CENTER</span>
        </div>
        <div>
          <span className="eyebrow">ENTERPRISE INTEGRATION WORKSPACE</span>
          <h1>
            Trace requirements
            <br />
            through testing
            <br />
            <em>and release.</em>
          </h1>
          <p>
            Track requirements through integration tests and stakeholder
            approval before making a release decision.
          </p>
          <div className="login-flow">
            <span>Define</span>
            <ArrowRight />
            <span>Integrate</span>
            <ArrowRight />
            <span>Validate</span>
            <ArrowRight />
            <span>Deliver</span>
          </div>
        </div>
        <p className="fiction-note">
          A software project built around the fictional Northstar Enterprise
          Services scenario.
        </p>
      </div>
      <div className="login-form">
        <span className="eyebrow">YOUR ANALYST WORKSPACE</span>
        <h2>Welcome to EICC</h2>
        <p>Your projects, integrations, and delivery decisions in one place.</p>
        {error && <ErrorBox message={error} />}
        {demo && (
          <div className="demo-entry">
            <div className="demo-label">
              <span className="status-dot" />
              LIVE LOCAL DEMO
            </div>
            <h3>Explore Northstar</h3>
            <p>
              Run the local integration tests, inspect failures, and check what
              blocks the pilot release.
            </p>
            <label htmlFor="demo-role">Explore as</label>
            <select
              id="demo-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              {[
                "analyst",
                "tester",
                "stakeholder",
                "manager",
                "viewer",
                "admin",
              ].map((r) => (
                <option key={r} value={r}>
                  {label(r)}
                </option>
              ))}
            </select>
            <button
              className="button primary full"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  onLogin(await post("/api/auth/demo", { role }));
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Enter demo workspace <ArrowRight size={17} />
            </button>
            <small>
              Demo roles are available only in the isolated demo environment.
            </small>
          </div>
        )}
        <form onSubmit={login}>
          <h3>{demo ? "Or use your account" : "Sign in to your workspace"}</h3>
          <label>
            Email
            <input
              name="email"
              type="email"
              autoComplete="username"
              required
              placeholder="you@organization.com"
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          <button className="button secondary full" disabled={busy}>
            Sign in <ArrowRight size={16} />
          </button>
        </form>
        <p className="login-disclaimer">
          Fictional portfolio project. No affiliation with or endorsement by the
          Maryland Judiciary or any government organization.
        </p>
      </div>
    </div>
  );
}

function FormDialog({ dialog, close }: { dialog: Dialog; close: () => void }) {
  const { items, project, refresh, notify } = useWorkspace();
  const [values, setValues] = useState<Record<string, any>>(() => {
    const initial: Record<string, any> = {};
    for (const [key, field] of Object.entries(dialog.schema.properties)) {
      const value =
        dialog.values?.[key] ??
        field.default ??
        (field.type === "boolean" ? false : "");
      initial[key] =
        typeof value === "object" && value !== null
          ? JSON.stringify(value, null, 2)
          : value;
    }
    return initial;
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const node = ref.current!;
    node.showModal();
    return () => node.close();
  }, []);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload: Record<string, any> = {};
      for (const [key, raw] of Object.entries(dialog.schema.properties)) {
        const field = raw.anyOf?.find((f) => f.type !== "null") || raw;
        let value = values[key];
        if (value === "" || value === undefined) {
          if (raw.anyOf?.some((f) => f.type === "null")) {
            payload[key] = null;
            continue;
          }
          if (!dialog.schema.required?.includes(key)) continue;
        }
        if (field.type === "integer" || field.type === "number")
          value = Number(value);
        if (
          (field.type === "object" || field.type === "array") &&
          typeof value === "string"
        )
          value = JSON.parse(value || (field.type === "array" ? "[]" : "{}"));
        payload[key] = value;
      }
      await dialog.submit(payload);
      await refresh();
      close();
      notify("Changes saved");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={ref}
      className="dialog"
      onCancel={close}
      aria-labelledby="dialog-title"
    >
      <form onSubmit={submit}>
        <div className="dialog-heading">
          <div>
            <span className="eyebrow">NORTHSTAR WORKSPACE</span>
            <h2 id="dialog-title">{dialog.title}</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={close}
            aria-label="Close dialog"
          >
            <X />
          </button>
        </div>
        {dialog.description && (
          <p className="dialog-description">{dialog.description}</p>
        )}
        <div className="dialog-fields">
          {error && <ErrorBox message={error} />}
          {Object.entries(dialog.schema.properties).map(([key, raw]) => {
            const field = raw.anyOf?.find((f) => f.type !== "null") || raw;
            const required = dialog.schema.required?.includes(key);
            if (key === "project_id" || key === "organization_id") return null;
            const referenceKind = referenceKinds[key];
            const references = ["source_id", "target_id"].includes(key)
              ? items.filter((a) => a.project_id === project?.id)
              : referenceKind
                ? items.filter(
                    (a) =>
                      a.kind === referenceKind &&
                      (a.project_id === project?.id ||
                        referenceKind === "projects"),
                  )
                : null;
            const choices = field.enum || raw.enum;
            const long =
              [
                "description",
                "acceptance_criteria",
                "steps",
                "expected_result",
                "preconditions",
                "content",
                "scope",
                "objectives",
                "entry_criteria",
                "exit_criteria",
                "root_cause",
                "resolution",
                "workaround",
                "impact",
                "reason",
                "risk",
                "mitigation",
                "evidence",
                "comments",
                "override_reason",
                "actual_result",
                "current_state",
                "future_state",
                "deployment_notes",
                "rollback_plan",
                "request_format",
                "response_format",
                "business_impact",
                "technical_impact",
              ].includes(key) || ["object", "array"].includes(field.type || "");
            const value = values[key] ?? "";
            return (
              <label key={key} className={long ? "span-two" : ""}>
                {raw.title || label(key.replace(/_id$/, ""))}
                {required && <span className="required"> *</span>}
                {field.type === "boolean" ? (
                  <span className="check-input">
                    <input
                      type="checkbox"
                      checked={!!value}
                      onChange={(e) =>
                        setValues({ ...values, [key]: e.target.checked })
                      }
                    />
                    Enabled
                  </span>
                ) : choices || references ? (
                  <select
                    required={required}
                    value={value}
                    onChange={(e) =>
                      setValues({ ...values, [key]: e.target.value })
                    }
                  >
                    <option value="">
                      Select {label(key.replace(/_id$/, "")).toLowerCase()}
                    </option>
                    {references
                      ? references.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.key} · {a.title}
                          </option>
                        ))
                      : choices!.map((choice) => (
                          <option key={choice} value={choice}>
                            {label(String(choice))}
                          </option>
                        ))}
                  </select>
                ) : long ? (
                  <textarea
                    required={required}
                    minLength={field.minLength}
                    maxLength={field.maxLength}
                    rows={key === "content" ? 10 : 3}
                    className={
                      ["payload", "request_format", "response_format"].includes(
                        key,
                      )
                        ? "code-input"
                        : ""
                    }
                    value={value}
                    onChange={(e) =>
                      setValues({ ...values, [key]: e.target.value })
                    }
                  />
                ) : (
                  <input
                    required={required}
                    type={
                      field.type === "integer" || field.type === "number"
                        ? "number"
                        : field.format === "date"
                          ? "date"
                          : "text"
                    }
                    min={field.minimum}
                    max={field.maximum}
                    minLength={field.minLength}
                    maxLength={field.maxLength}
                    value={value}
                    onChange={(e) =>
                      setValues({ ...values, [key]: e.target.value })
                    }
                  />
                )}
              </label>
            );
          })}
        </div>
        <div className="dialog-footer">
          <button type="button" className="button secondary" onClick={close}>
            Cancel
          </button>
          <button className="button primary" disabled={busy}>
            {busy && <Loader2 className="spin" size={16} />}
            {dialog.submitLabel || "Save changes"}
            <Check size={16} />
          </button>
        </div>
      </form>
    </dialog>
  );
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [items, setItems] = useState<Artifact[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [projectId, setProjectId] = useState<number>(() =>
    Number(localStorage.getItem("eicc-project") || 0),
  );
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [dark, setDark] = useState(
    localStorage.getItem("eicc-theme") === "dark",
  );
  const [mobile, setMobile] = useState(false);
  const [compact, setCompact] = useState(
    () => window.matchMedia("(max-width: 1100px)").matches,
  );
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<Artifact[]>([]);
  const searchRef = useRef<HTMLInputElement>(null);
  const navigationButtonRef = useRef<HTMLButtonElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    const media = window.matchMedia("(max-width: 1100px)");
    const resize = () => {
      setCompact(media.matches);
      setMobile(false);
    };
    media.addEventListener("change", resize);
    return () => media.removeEventListener("change", resize);
  }, []);
  const login = (value: Session) => {
    setCsrf(value.csrf_token);
    setSession(value);
  };
  useEffect(() => {
    api<Session>("/api/auth/me")
      .then(login)
      .catch(() => {})
      .finally(() => setInitializing(false));
  }, []);
  const refresh = useCallback(async () => {
    const [workspace, metadata] = await Promise.all([
      api<Workspace>("/api/workspace"),
      api<Metadata>("/api/meta"),
    ]);
    setItems(workspace.items);
    setExecutions(workspace.executions);
    setMeta(metadata);
  }, []);
  useEffect(() => {
    if (session) refresh().catch((e) => setError(e.message));
  }, [session, refresh]);
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("eicc-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    setMobile(false);
    setSearch("");
    window.scrollTo(0, 0);
  }, [location.pathname]);
  useEffect(() => {
    if (notice) {
      const timeout = setTimeout(() => setNotice(""), 5000);
      return () => clearTimeout(timeout);
    }
  }, [notice]);
  const project =
    items.find((a) => a.id === projectId && a.kind === "projects") ||
    items.find((a) => a.kind === "projects" && a.key === "NS-CASE") ||
    items.find((a) => a.kind === "projects");
  useEffect(() => {
    if (!search.trim()) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(
      () =>
        api<Artifact[]>(
          `/api/search?q=${encodeURIComponent(search)}${project ? `&project_id=${project.id}` : ""}`,
        )
          .then((v) => {
            if (!cancelled) setResults(v);
          })
          .catch((e) => {
            if (!cancelled) setError(e.message);
          }),
      200,
    );
    return () => {
      clearTimeout(timer);
      cancelled = true;
    };
  }, [search, project?.id]);
  useEffect(() => {
    const keyboard = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (e.key === "Escape") {
        setSearch("");
        if (
          navigationButtonRef.current?.getAttribute("aria-expanded") === "true"
        )
          navigationButtonRef.current.focus();
        setMobile(false);
      }
    };
    window.addEventListener("keydown", keyboard);
    return () => window.removeEventListener("keydown", keyboard);
  }, []);
  async function action(fn: () => Promise<any>, message = "Changes saved") {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (initializing) return <Loading />;
  if (!session) return <Login onLogin={login} />;
  if (!meta) return error ? <ErrorBox message={error} /> : <Loading />;
  const nav = [
    [
      "WORKSPACE",
      [
        ["dashboard", LayoutDashboard],
        ["projects", Layers3],
        ["requirements", FileText],
        ["traceability", Network],
        ["processes", Workflow],
      ],
    ],
    [
      "INTEGRATION & QUALITY",
      [
        ["systems", Box],
        ["integrations", GitBranch],
        ["test-cases", FlaskConical],
        ["uat", ClipboardCheck],
        ["incidents", TriangleAlert],
      ],
    ],
    [
      "DELIVERY GOVERNANCE",
      [
        ["changes", GitBranch],
        ["risks", ShieldCheck],
        ["dependencies", Link2],
        ["releases", Box],
        ["reports", FileText],
        ["training", BookOpen],
      ],
    ],
  ] as const;
  const section = location.pathname.split("/")[1] || "dashboard";
  return (
    <WorkspaceContext.Provider
      value={{
        items,
        executions,
        session,
        project,
        meta,
        refresh,
        open: setDialog,
        notify: setNotice,
        action,
        busy,
      }}
    >
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <div className="app-shell">
        {mobile && (
          <button
            className="mobile-scrim"
            aria-label="Close navigation"
            onClick={() => setMobile(false)}
          />
        )}
        <aside
          id="workspace-navigation"
          className={`sidebar ${mobile ? "is-open" : ""}`}
          inert={compact && !mobile}
        >
          <Link to="/" className="brand">
            <span className="brand-mark">
              <Network size={21} />
            </span>
            <span>
              EICC<small>Integration workspace</small>
            </span>
          </Link>
          <div className="organization">
            <span className="org-mark">N</span>
            <div>
              <strong>Northstar</strong>
              <small>Enterprise Services</small>
            </div>
            <Chevrons />
          </div>
          <div className="sidebar-nav">
            {nav.map(([heading, entries]) => (
              <div className="nav-group" key={heading}>
                <span className="nav-label">{heading}</span>
                {entries.map(([key, Icon]) => (
                  <NavLink
                    key={key}
                    to={key === "dashboard" ? "/" : `/${key}`}
                    end={key === "dashboard"}
                    className={({ isActive }) =>
                      isActive ? "nav-item selected" : "nav-item"
                    }
                  >
                    <Icon size={17} />
                    <span>
                      {key === "test-cases"
                        ? "Testing"
                        : key === "traceability"
                          ? "Traceability"
                          : key === "incidents"
                            ? "Incidents"
                            : key === "integrations"
                              ? "Integrations"
                              : key === "uat"
                                ? "UAT"
                                : key === "risks"
                                  ? "Risks"
                                  : key === "changes"
                                    ? "Changes"
                                    : key === "reports"
                                      ? "Reports"
                                      : titles[key]}
                    </span>
                    {key === "incidents" && (
                      <span className="nav-count">
                        {
                          items.filter(
                            (a) =>
                              a.kind === "incidents" &&
                              a.project_id === project?.id &&
                              !["CLOSED", "RESOLVED"].includes(a.status),
                          ).length
                        }
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            ))}
          </div>
          <div className="sidebar-bottom">
            <Link className="nav-item" to="/administration">
              <Settings2 size={17} />
              Administration
            </Link>
            <div className="demo-card">
              <span className="demo-pulse" />
              <div>
                <strong>Portfolio environment</strong>
                <small>Fictional data · local simulation</small>
              </div>
              <ShieldCheck size={17} />
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <button
              className="icon-button mobile-menu"
              ref={navigationButtonRef}
              onClick={() => setMobile(true)}
              aria-label="Open navigation"
              aria-expanded={mobile}
              aria-controls="workspace-navigation"
            >
              <Menu />
            </button>
            <div className="breadcrumbs">
              <span>Workspace</span>
              <ChevronRight size={14} />
              <strong>{titles[section] || "Overview"}</strong>
            </div>
            <div className="topbar-tools">
              <div className="global-search">
                <Search size={16} />
                <input
                  ref={searchRef}
                  aria-label="Search workspace"
                  placeholder="Search workspace…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <kbd>Ctrl K</kbd>
                {search && (
                  <div
                    className="search-results"
                    role="region"
                    aria-label="Search results"
                  >
                    {results.length ? (
                      results.map((a) => <ArtifactLink key={a.id} item={a} />)
                    ) : (
                      <p>No matching records.</p>
                    )}
                  </div>
                )}
              </div>
              <button
                className="icon-button theme-toggle"
                aria-label={
                  dark ? "Switch to light mode" : "Switch to dark mode"
                }
                onClick={() => setDark(!dark)}
              >
                {dark ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <div className="top-divider" />
              <button
                className="profile"
                onClick={() => navigate("/administration")}
                aria-label="Open account and administration"
              >
                <span className="avatar">
                  {session.actor
                    .split(" ")
                    .map((n) => n[0])
                    .slice(0, 2)
                    .join("")}
                </span>
                <span>
                  <strong>{session.actor}</strong>
                  <small>{label(session.role)}</small>
                </span>
                <ChevronDown size={14} />
              </button>
            </div>
          </header>
          <div className="project-strip">
            <span className="project-indicator" />
            <label className="sr-only" htmlFor="project-select">
              Active project
            </label>
            <select
              id="project-select"
              value={project?.id || ""}
              onChange={(e) => {
                setProjectId(Number(e.target.value));
                localStorage.setItem("eicc-project", e.target.value);
                navigate("/");
              }}
            >
              {items
                .filter((a) => a.kind === "projects")
                .map((p) => (
                  <option value={p.id} key={p.id}>
                    {p.title}
                  </option>
                ))}
            </select>
            <span className="project-key">
              {project?.key || "No project selected"}
            </span>
            <span className="environment-tag">
              {session.demo_mode ? "DEMO ENVIRONMENT" : "WORKSPACE"}
            </span>
          </div>
          <main id="main-content" tabIndex={-1}>
            {error && (
              <div className="dismiss-error">
                <ErrorBox message={error} />
                <button
                  className="icon-button"
                  onClick={() => setError("")}
                  aria-label="Dismiss error"
                >
                  <X size={16} />
                </button>
              </div>
            )}
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/traceability" element={<Traceability />} />
              <Route path="/reports" element={<Reports />} />
              <Route
                path="/administration"
                element={
                  <Administration
                    logout={() => {
                      post("/api/auth/logout")
                        .then(() => {
                          setSession(null);
                          setMeta(null);
                          setCsrf("");
                        })
                        .catch((e) => setError(e.message));
                    }}
                  />
                }
              />
              <Route path="/:kind/:id" element={<Detail />} />
              <Route path="/:kind" element={<Catalog />} />
              <Route path="*" element={<Empty title="Page not found" />} />
            </Routes>
          </main>
          <footer className="workspace-footer">
            <span>
              <span className="status-dot" />
              EICC · Connected lifecycle workspace
            </span>
            <span>
              Fictional portfolio · No government affiliation{" "}
              <span className="footer-version">v1.0.0</span>
            </span>
          </footer>
        </div>
      </div>
      {notice && (
        <div className="toast" role="status">
          <CheckCircle2 size={18} />
          {notice}
          <button
            className="icon-button"
            onClick={() => setNotice("")}
            aria-label="Dismiss notification"
          >
            <X size={14} />
          </button>
        </div>
      )}
      {dialog && (
        <FormDialog
          key={dialog.title + JSON.stringify(dialog.values?.id || "")}
          dialog={dialog}
          close={() => setDialog(null)}
        />
      )}
    </WorkspaceContext.Provider>
  );
}
function Chevrons() {
  return <ChevronDown size={15} />;
}

function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  );
}
function NewButton({ kind }: { kind: string }) {
  const { meta, open, project } = useWorkspace();
  const navigate = useNavigate();
  return (
    <button
      className="button primary"
      onClick={() =>
        open({
          title: `Create ${titles[kind]?.toLowerCase() || label(kind)}`,
          schema: meta.schemas[kind],
          values: {
            project_id: kind === "projects" ? null : project?.id,
            organization_id: 1,
          },
          submit: async (data) => {
            const item = await post<Artifact>(`/api/${kind}`, data);
            navigate(`/${kind}/${item.id}`);
          },
          submitLabel: "Create record",
        })
      }
    >
      <Plus size={16} />
      New{" "}
      {kind === "test-cases"
        ? "test case"
        : kind === "uat"
          ? "UAT session"
          : kind === "processes"
            ? "process"
            : kind === "training"
              ? "material"
              : kind.replace(/s$/, "").replaceAll("-", " ")}
    </button>
  );
}

function Dashboard() {
  const { project, items, executions, action, busy } = useWorkspace();
  const [view, setView] = useState("Executive");
  const { data, error } = useResource(
    `/api/analytics?project_id=${project?.id || 0}`,
  );
  if (!project)
    return (
      <>
        <PageHeading
          title="Your workspace starts here"
          description="Create a project to connect its requirements, integrations, and delivery evidence."
        >
          <NewButton kind="projects" />
        </PageHeading>
      </>
    );
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading />;
  const currentRelease = data.releases.find(
    (r: Artifact) => r.status !== "COMPLETED",
  );
  const projectItems = items.filter((a) => a.project_id === project.id);
  const integrations = projectItems.filter((a) => a.kind === "integrations");
  const sourceCounts = integrations.reduce<Record<number, number>>(
    (counts, i) => ({
      ...counts,
      [i.source_system_id]: (counts[i.source_system_id] || 0) + 1,
    }),
    {},
  );
  const sourceId = Number(
    Object.entries(sourceCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 0,
  );
  const sourceSystem = items.find((a) => a.id === sourceId);
  const graphIntegrations = integrations
    .filter((i) => i.source_system_id === sourceId)
    .sort(
      (a, b) =>
        Number(b.status === "DEGRADED") - Number(a.status === "DEGRADED"),
    )
    .slice(0, 3);
  const recent = [...executions]
    .filter((e) => projectItems.some((a) => a.id === e.test_case_id))
    .sort((a, b) => b.id - a.id)
    .slice(0, 4);
  const blockers = [
    ...data.critical_defects,
    ...data.blocked_dependencies,
    ...data.high_risks,
  ].slice(0, 4);
  const totalTests = data.counts["test-cases"];
  const completion = Math.round(
    (100 * data.completed_requirements) / Math.max(data.counts.requirements, 1),
  );
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE / OVERVIEW"
        title="Project overview"
        description="Review test results and the issues blocking your next release."
      >
        <button
          className="button secondary"
          disabled={busy}
          onClick={() =>
            action(async () => {
              const doc = await post("/api/reports", {
                project_id: project.id,
                document_type: "Project Status Report",
              });
              window.location.assign(`/api/documents/${doc.id}/export`);
            }, "Project status report generated")
          }
        >
          <Download size={16} />
          Export report
        </button>
        <Link className="button primary" to="/traceability">
          Open traceability <ArrowUpRight size={16} />
        </Link>
      </PageHeading>
      <section className="project-spotlight" aria-label="Project summary">
        <div className="spotlight-main">
          <div className="spotlight-kicker">
            <span className="spotlight-dot" /> {label(project.status)} project{" "}
            <span>·</span> {project.key}
          </div>
          <h2>{project.title}</h2>
          <p>
            {data.counts.requirements} requirements <span>/</span>{" "}
            {integrations.length} integrations <span>/</span> {totalTests} test
            cases
          </p>
          <Link to={`/projects/${project.id}`}>
            View project details <ArrowUpRight size={15} />
          </Link>
        </div>
        <div className="spotlight-progress">
          <span>Requirements completed</span>
          <div>
            <strong>
              {completion}
              <small>%</small>
            </strong>
            <span>
              {data.completed_requirements} of {data.counts.requirements}
            </span>
          </div>
          <div className="spotlight-track">
            <span style={{ width: `${completion}%` }} />
          </div>
          <p>
            Target delivery <strong>{date(project.target_date)}</strong>
          </p>
        </div>
      </section>
      <div className="overview-toolbar">
        <div className="segmented" aria-label="Dashboard view">
          {["Executive", "Analyst"].map((v) => (
            <button
              key={v}
              className={view === v ? "active" : ""}
              onClick={() => setView(v)}
            >
              {v === "Executive" ? (
                <LayoutDashboard size={14} />
              ) : (
                <Activity size={14} />
              )}
              {v} view
            </button>
          ))}
        </div>
        <span className="live-note">
          <span className="status-dot" />
          Calculated from project evidence
        </span>
      </div>
      <div className="stats-grid">
        <Stat
          title="Requirements coverage"
          value={`${data.coverage.coverage}%`}
          detail={`${data.coverage.with_tests} of ${data.coverage.total} linked to tests`}
          icon={Target}
          color="blue"
        >
          <div className="mini-progress">
            <span style={{ width: `${data.coverage.coverage}%` }} />
          </div>
        </Stat>
        <Stat
          title="Connected integrations"
          value={String(integrations.length).padStart(2, "0")}
          detail={`${data.protocols.REST || 0} REST · ${data.protocols.SOAP || 0} SOAP`}
          icon={Network}
          color="blue"
        >
          <span className="stat-chip">
            {data.failing_integrations} with failing tests
          </span>
        </Stat>
        <Stat
          title="Test pass rate"
          value={`${data.pass_rate}%`}
          detail={`${data.test_results.PASS} passed / ${totalTests - data.test_results.NOT_RUN} executed`}
          icon={FlaskConical}
          color="blue"
        >
          <div className="tiny-bars">
            {["PASS", "FAIL", "BLOCKED", "NOT_RUN"].map((k) => (
              <span
                key={k}
                className={k.toLowerCase()}
                style={{ flex: data.test_results[k] || 0.1 }}
              />
            ))}
          </div>
        </Stat>
        <Stat
          title="Open critical defects"
          value={String(data.critical_defects.length).padStart(2, "0")}
          detail="Require resolution before release"
          icon={TriangleAlert}
          color="orange"
        >
          <Link className="text-link" to="/incidents">
            Review blockers <ArrowRight size={13} />
          </Link>
        </Stat>
      </div>
      <div className="operations-grid">
        <Section
          className="release-panel"
          title="Release readiness"
          subtitle={
            currentRelease
              ? `${currentRelease.key} · v${currentRelease.version}`
              : "Current delivery readiness"
          }
          aside={<Box size={18} />}
        >
          {currentRelease ? (
            <>
              <div className="release-summary">
                <h3>{currentRelease.title}</h3>
                <Badge status={currentRelease.readiness.status} />
              </div>
              <p className="release-explanation">
                {currentRelease.readiness.status === "READY"
                  ? "Every mandatory gate is satisfied."
                  : "Open criteria need attention before this release can proceed."}
              </p>
              <div className="compact-gates">
                {currentRelease.readiness.gates.slice(0, 5).map((g: any) => (
                  <div key={g.name}>
                    <span>{g.name}</span>
                    {g.status === "PASS" ? (
                      <CheckCircle2 size={16} className="green-text" />
                    ) : (
                      <span className="gate-missing">
                        {g.status === "WARNING" ? "Review" : "Pending"}
                        <CircleDot size={14} />
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <Link
                className="release-link"
                to={`/releases/${currentRelease.id}`}
              >
                Review release readiness <ArrowRight size={16} />
              </Link>
            </>
          ) : (
            <Empty
              title="No upcoming release"
              description="Create a release and define its scope to evaluate readiness."
            />
          )}
        </Section>
        <Section
          className="quality-panel"
          title="Quality snapshot"
          subtitle="Latest result for each test case"
          aside={
            <Link
              className="icon-button"
              to="/test-cases"
              aria-label="Open test management"
            >
              <ArrowUpRight size={17} />
            </Link>
          }
        >
          <div className="quality-content">
            <div
              className="donut"
              style={{
                background: `conic-gradient(var(--accent) 0 ${(data.test_results.PASS / Math.max(totalTests, 1)) * 100}%, var(--orange) ${(data.test_results.PASS / Math.max(totalTests, 1)) * 100}% ${((data.test_results.PASS + data.test_results.FAIL) / Math.max(totalTests, 1)) * 100}%, var(--amber) ${((data.test_results.PASS + data.test_results.FAIL) / Math.max(totalTests, 1)) * 100}% ${((data.test_results.PASS + data.test_results.FAIL + data.test_results.BLOCKED) / Math.max(totalTests, 1)) * 100}%, var(--line) 0)`,
              }}
              role="img"
              aria-label={`${data.test_results.PASS} passing, ${data.test_results.FAIL} failing, ${data.test_results.BLOCKED} blocked, ${data.test_results.NOT_RUN} not run`}
            >
              <div>
                <strong>{totalTests}</strong>
                <small>Total tests</small>
              </div>
            </div>
            <div className="quality-legend">
              {["PASS", "FAIL", "BLOCKED", "NOT_RUN"].map((k) => (
                <div key={k}>
                  <span>
                    <i className={`legend-dot ${k.toLowerCase()}`} />
                    {label(k)}
                  </span>
                  <strong>{data.test_results[k]}</strong>
                </div>
              ))}
            </div>
          </div>
          <div className="quality-footer">
            <span>Test completion</span>
            <strong>{data.test_completion}%</strong>
            <div className="mini-progress">
              <span style={{ width: `${data.test_completion}%` }} />
            </div>
          </div>
        </Section>
        <Section
          className="attention-panel"
          title="Needs your attention"
          subtitle={`${blockers.length} priority items surfaced`}
          aside={<span className="count-pill">{blockers.length}</span>}
        >
          <div className="attention-list">
            {blockers.length ? (
              blockers.map((a: Artifact) => (
                <Link key={a.id} to={`/${a.kind}/${a.id}`}>
                  <span
                    className={`attention-icon ${a.kind === "incidents" ? "orange" : "amber"}`}
                  >
                    <TriangleAlert size={16} />
                  </span>
                  <div>
                    <span className="record-key">
                      {a.key} <span>· {label(a.kind)}</span>
                    </span>
                    <strong>{a.title}</strong>
                  </div>
                  <ChevronRight size={15} />
                </Link>
              ))
            ) : (
              <Empty
                title="No priority blockers"
                description="Keep validating the remaining release criteria."
              />
            )}
          </div>
          <Link className="panel-bottom-link" to="/risks">
            Open risk & dependency review <ArrowRight size={14} />
          </Link>
        </Section>
        <Section
          className="progress-panel"
          title="Delivery progress"
          subtitle="Requirement status and acceptance"
          aside={<Activity size={17} />}
        >
          <div className="delivery-progress">
            {[
              [
                "Requirements complete",
                completion,
                `${data.completed_requirements}/${data.counts.requirements}`,
              ],
              [
                "Tests executed",
                data.test_completion,
                `${totalTests - data.test_results.NOT_RUN}/${totalTests}`,
              ],
              [
                "UAT sessions approved",
                data.uat_approval_rate,
                `${data.uat_approval_rate}%`,
              ],
            ].map(([name, value, detail]) => (
              <div key={name}>
                <div>
                  <span>{name}</span>
                  <strong>{detail}</strong>
                </div>
                <div className="mini-progress">
                  <span style={{ width: `${value}%` }} />
                </div>
              </div>
            ))}
          </div>
          <div className="milestone">
            <span className="milestone-icon">
              <Box size={18} />
            </span>
            <div>
              <small>PROJECT TARGET</small>
              <strong>{date(project.target_date)}</strong>
            </div>
            <Badge status={project.status} />
          </div>
        </Section>
        <Section
          className="landscape-panel"
          title="Integration landscape"
          subtitle="Systems in the case-intake workflow"
          aside={
            <Link className="subtle-link" to="/integrations">
              View catalog <ArrowUpRight size={15} />
            </Link>
          }
        >
          <div className="landscape-legend">
            <span>
              <i className="legend-dot green" />
              REST / JSON
            </span>
            <span>
              <i className="legend-dot amber" />
              SOAP / XML
            </span>
            <span className="landscape-mode">LOCAL SIMULATION</span>
          </div>
          <div className="landscape">
            <div className="landscape-source">
              <div className="system-node intake">
                <span className="node-icon">
                  <Layers3 size={24} />
                </span>
                <strong>{sourceSystem?.title || "No source system"}</strong>
                <small>{sourceSystem?.key || "Connect an integration"}</small>
                <span className="node-tag">
                  <span className="status-dot" />
                  Connected
                </span>
              </div>
            </div>
            <svg
              className="landscape-wires"
              viewBox="0 0 230 270"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path d="M0 135 H75 Q95 135 95 115 V45 Q95 25 115 25 H230" />
              <path d="M0 135 H230" />
              <path d="M0 135 H75 Q95 135 95 155 V225 Q95 245 115 245 H230" />
              <circle cx="95" cy="135" r="5" />
            </svg>
            <div className="landscape-targets">
              {graphIntegrations.map((i) => (
                <Link
                  key={i.id}
                  className={`system-node target ${i.protocol === "SOAP" ? "soap" : ""}`}
                  to={`/integrations/${i.id}`}
                >
                  <span className="node-icon">
                    {i.protocol === "SOAP" ? (
                      <Box size={18} />
                    ) : i.endpoint.includes("notification") ? (
                      <Bell size={18} />
                    ) : (
                      <FileText size={18} />
                    )}
                  </span>
                  <span>
                    <strong>
                      {items.find((a) => a.id === i.target_system_id)?.title}
                    </strong>
                    <small>
                      {i.protocol} / {i.data_format}
                    </small>
                  </span>
                  <span
                    className={`node-health ${i.status === "DEGRADED" ? "amber" : "green"}`}
                  />
                </Link>
              ))}
            </div>
          </div>
          <div className="landscape-caption">
            <Link2 size={14} />
            <span>
              Every connection links to requirements, mappings, and test
              evidence.
            </span>
          </div>
        </Section>
      </div>
      {view === "Analyst" && (
        <div className="analyst-grid">
          <Section
            title="Latest execution evidence"
            subtitle="Open a test to inspect its request, response, and history"
          >
            {recent.map((e) => {
              const test = items.find((a) => a.id === e.test_case_id);
              return (
                test && (
                  <div className="execution-row" key={e.id}>
                    <ArtifactLink item={test} />
                    <Badge status={e.status} />
                  </div>
                )
              );
            })}
          </Section>
          <Section title="Analyst quality metrics">
            <dl className="metric-list">
              <div>
                <dt>Failure rate</dt>
                <dd>{data.failure_rate}%</dd>
              </div>
              <div>
                <dt>Blocked rate</dt>
                <dd>{data.blocked_rate}%</dd>
              </div>
              <div>
                <dt>Open defects per requirement</dt>
                <dd>{data.defect_density}</dd>
              </div>
              <div>
                <dt>Requirements without tests</dt>
                <dd>{data.coverage.without_tests}</dd>
              </div>
              <div>
                <dt>Requirements without UAT approval</dt>
                <dd>{data.coverage.without_uat}</dd>
              </div>
            </dl>
          </Section>
        </div>
      )}
      <div className="insight-strip">
        <span className="insight-icon">
          <GitBranch size={18} />
        </span>
        <p>
          <strong>Follow the evidence.</strong> Open a requirement to see how
          business intent connects to systems, tests, UAT, and release
          decisions.
        </p>
        <Link to="/requirements">
          Explore requirements <ArrowRight size={15} />
        </Link>
      </div>
    </>
  );
}
function Stat({
  title,
  value,
  detail,
  icon: Icon,
  color,
  children,
}: {
  title: string;
  value: string;
  detail: string;
  icon: typeof Activity;
  color: string;
  children: ReactNode;
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{title}</span>
        <span className={`stat-icon ${color}`}>
          <Icon size={17} />
        </span>
      </div>
      <strong className="stat-value">{value}</strong>
      <p>{detail}</p>
      <div className="stat-bottom">{children}</div>
    </div>
  );
}

function Catalog() {
  const { kind = "" } = useParams();
  const { items, project, executions, meta } = useWorkspace();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  useEffect(() => {
    setQuery("");
    setStatus("");
    setType("");
  }, [kind]);
  if (!meta.schemas[kind])
    return (
      <Empty
        title="Page not found"
        description="Choose a workspace page from the navigation."
      />
    );
  const all = items.filter(
    (a) =>
      a.kind === kind && (kind === "projects" || a.project_id === project?.id),
  );
  const rows = all.filter(
    (a) =>
      (!query ||
        `${a.key} ${a.title} ${a.owner}`
          .toLowerCase()
          .includes(query.toLowerCase())) &&
      (!status || a.status === status) &&
      (!type || a.type === type || a.protocol === type),
  );
  const descriptions: Record<string, string> = {
    requirements:
      "Capture the business need. Define acceptance. Connect every decision.",
    integrations:
      "Service contracts, field mappings, and the evidence behind every connection.",
    "test-cases":
      "Design, execute, investigate, and retest with a complete evidence trail.",
    incidents:
      "Investigate business impact, document root cause, and verify the resolution.",
    changes: "Understand the impact before authorizing a change.",
    releases:
      "Explicit scope. Current evidence. Explainable release decisions.",
    risks: "Make uncertainty visible and track the work that reduces it.",
    dependencies:
      "Understand what delivery depends on and where progress is blocked.",
    uat: "Turn acceptance criteria into stakeholder evidence and recorded decisions.",
    processes: "Describe today’s workflow and make the future state clear.",
  };
  return (
    <>
      <PageHeading
        eyebrow="CONNECTED PROJECT RECORDS"
        title={titles[kind] || label(kind)}
        description={
          descriptions[kind] ||
          "Create and maintain the records that support your project lifecycle."
        }
      >
        <NewButton kind={kind} />
      </PageHeading>
      {["test-cases", "test-plans"].includes(kind) && (
        <div className="page-tabs">
          <NavLink to="/test-cases">Test cases</NavLink>
          <NavLink to="/test-plans">Test plans</NavLink>
        </div>
      )}
      {["uat", "uat-scenarios", "stakeholders"].includes(kind) && (
        <div className="page-tabs">
          <NavLink to="/uat">Acceptance sessions</NavLink>
          <NavLink to="/uat-scenarios">UAT scenarios</NavLink>
          <NavLink to="/stakeholders">Stakeholders</NavLink>
        </div>
      )}
      <div className="catalog-summary">
        <span>
          <strong>{all.length}</strong> {titles[kind]?.toLowerCase()}
        </span>
        <span>
          <span className="status-dot" />
          {
            all.filter((a) =>
              [
                "COMPLETE",
                "COMPLETED",
                "APPROVED",
                "ACTIVE",
                "SATISFIED",
              ].includes(a.status),
            ).length
          }{" "}
          active or approved
        </span>
        <span>
          <span className="status-dot amber" />
          {
            all.filter((a) =>
              ["BLOCKED", "NEW", "OPEN", "DEGRADED"].includes(a.status),
            ).length
          }{" "}
          need attention
        </span>
      </div>
      <section className="panel">
        <div className="table-toolbar">
          <div className="filter-search">
            <Search size={16} />
            <input
              aria-label="Filter records"
              placeholder="Search by key, title, or owner…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            {[...new Set(all.map((a) => a.status))].sort().map((s) => (
              <option value={s} key={s}>
                {label(s)}
              </option>
            ))}
          </select>
          {all.some((a) => a.type || a.protocol) && (
            <select
              aria-label="Filter by type"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="">All types</option>
              {[
                ...new Set(
                  all.map((a) => a.type || a.protocol).filter(Boolean),
                ),
              ].map((s) => (
                <option value={s} key={s}>
                  {label(s)}
                </option>
              ))}
            </select>
          )}
          <span className="row-count">{rows.length} records</span>
        </div>
        {kind === "integrations" ? (
          <div className="integration-grid">
            {rows.map((i) => (
              <Link
                to={`/integrations/${i.id}`}
                key={i.id}
                className="integration-card"
              >
                <div>
                  <span
                    className={`protocol-tag ${i.protocol === "SOAP" ? "soap" : ""}`}
                  >
                    {i.protocol} <span>/ {i.data_format}</span>
                  </span>
                  <Badge status={i.status} />
                </div>
                <span className="record-key">{i.key}</span>
                <h3>{i.title}</h3>
                <div className="connection-pair">
                  <span>
                    {items.find((a) => a.id === i.source_system_id)?.title}
                  </span>
                  <ArrowRight size={15} />
                  <span>
                    {items.find((a) => a.id === i.target_system_id)?.title}
                  </span>
                </div>
                <div className="integration-card-footer">
                  <span>{label(i.mode)}</span>
                  <span>
                    View contract <ArrowUpRight size={14} />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : kind === "processes" ? (
          <div className="process-list">
            {rows.map((p) => (
              <div key={p.id}>
                <ArtifactLink item={p} />
                <ProcessFlow steps={p.steps || []} />
                <div className="process-states">
                  <p>
                    <strong>Current state</strong>
                    {p.current_state}
                  </p>
                  <p>
                    <strong>Future state</strong>
                    {p.future_state}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Record / business context</th>
                  <th>
                    {kind === "requirements"
                      ? "Type"
                      : kind === "releases"
                        ? "Version"
                        : "Owner"}
                  </th>
                  <th>Status</th>
                  <th>
                    {kind === "test-cases"
                      ? "Latest result"
                      : kind === "risks"
                        ? "Risk score"
                        : "Priority / updated"}
                  </th>
                  <th>
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <Link className="table-record" to={`/${kind}/${a.id}`}>
                        <span className="record-key">{a.key}</span>
                        <strong>{a.title}</strong>
                      </Link>
                    </td>
                    <td>
                      {kind === "requirements" ? (
                        <span className="type-label">{label(a.type)}</span>
                      ) : kind === "releases" ? (
                        `v${a.version}`
                      ) : (
                        <span className="owner-cell">
                          <span className="tiny-avatar">
                            {a.owner
                              ?.split(" ")
                              .map((n: string) => n[0])
                              .slice(0, 2)
                              .join("")}
                          </span>
                          {a.owner}
                        </span>
                      )}
                    </td>
                    <td>
                      <Badge
                        status={
                          kind === "releases" && a.status === "READY"
                            ? a.readiness_status
                            : a.status
                        }
                      />
                    </td>
                    <td>
                      {kind === "test-cases" ? (
                        <Badge
                          status={
                            a.effective_test_status ||
                            executions.find((e) => e.test_case_id === a.id)
                              ?.status ||
                            "NOT_RUN"
                          }
                        />
                      ) : kind === "risks" ? (
                        <span
                          className={`risk-score ${a.probability * a.impact >= 15 ? "high" : ""}`}
                        >
                          {a.probability * a.impact}
                          <small> / 25</small>
                        </span>
                      ) : a.priority ? (
                        <span
                          className={`priority ${a.priority.toLowerCase()}`}
                        >
                          <i />
                          {label(a.priority)}
                        </span>
                      ) : (
                        <span className="muted">{date(a.updated_at)}</span>
                      )}
                    </td>
                    <td>
                      <Link
                        className="icon-button"
                        to={`/${kind}/${a.id}`}
                        aria-label={`Open ${a.key}`}
                      >
                        <ArrowUpRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!rows.length && <Empty />}
        <div className="table-footer">
          Showing {rows.length} of {all.length} records
          <span>All relationships are persisted in the project database.</span>
        </div>
      </section>
    </>
  );
}

function Traceability() {
  const { project, items } = useWorkspace();
  const [filters, setFilters] = useState<Record<string, string>>({});
  const params = new URLSearchParams({
    project_id: String(project?.id || 0),
    ...filters,
  });
  const { data, error } = useResource(`/api/traceability?${params}`);
  const set = (key: string, value: string) =>
    setFilters({ ...filters, [key]: value });
  return (
    <>
      <PageHeading
        eyebrow="BUSINESS INTENT → DELIVERY EVIDENCE"
        title="Traceability matrix"
        description="Trace each requirement through implementation, test results, acceptance, and release scope."
      >
        <Link className="button secondary" to="/requirements">
          <FileText size={16} />
          Manage requirements
        </Link>
      </PageHeading>
      {error && <ErrorBox message={error} />}
      {data && (
        <>
          <div className="trace-metrics">
            {[
              ["With tests", data.metrics.with_tests, "green"],
              ["Without tests", data.metrics.without_tests, "neutral"],
              ["Passing", data.metrics.passing, "green"],
              ["Failing", data.metrics.failing, "orange"],
              ["Blocked", data.metrics.blocked, "amber"],
              ["Awaiting UAT", data.metrics.without_uat, "blue"],
            ].map(([name, value, color]) => (
              <div key={name}>
                <span className={`legend-dot ${color}`} />
                <strong>{value}</strong>
                <span>{name}</span>
              </div>
            ))}
          </div>
          <section className="panel">
            <div className="trace-filters">
              <div className="filter-search">
                <Search size={15} />
                <input
                  aria-label="Filter requirement"
                  placeholder="Find a requirement…"
                  value={filters.requirement || ""}
                  onChange={(e) => set("requirement", e.target.value)}
                />
              </div>
              {[
                ["system_id", "systems", "All systems"],
                ["integration_id", "integrations", "All integrations"],
                ["release_id", "releases", "All releases"],
              ].map(([field, kind, name]) => (
                <select
                  key={field}
                  aria-label={name}
                  value={filters[field] || ""}
                  onChange={(e) => set(field, e.target.value)}
                >
                  <option value="">{name}</option>
                  {items
                    .filter(
                      (a) => a.kind === kind && a.project_id === project?.id,
                    )
                    .map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.key} · {a.title}
                      </option>
                    ))}
                </select>
              ))}
              <select
                aria-label="Test status"
                value={filters.test_status || ""}
                onChange={(e) => set("test_status", e.target.value)}
              >
                <option value="">All test results</option>
                {["PASS", "FAIL", "BLOCKED", "NOT_RUN"].map((s) => (
                  <option value={s} key={s}>
                    {label(s)}
                  </option>
                ))}
              </select>
              <select
                aria-label="UAT status"
                value={filters.uat_status || ""}
                onChange={(e) => set("uat_status", e.target.value)}
              >
                <option value="">All UAT states</option>
                <option>APPROVED</option>
                <option>PENDING</option>
              </select>
            </div>
            <div className="table-scroll">
              <table className="trace-table">
                <thead>
                  <tr>
                    <th>Requirement</th>
                    <th>Type</th>
                    <th>Systems / integrations</th>
                    <th>Test coverage</th>
                    <th>Latest result</th>
                    <th>UAT</th>
                    <th>Release</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((r: any) => (
                    <tr key={r.id}>
                      <td>
                        <Link
                          className="table-record"
                          to={`/requirements/${r.id}`}
                        >
                          <span className="record-key">{r.key}</span>
                          <strong>{r.title}</strong>
                        </Link>
                      </td>
                      <td>
                        <span className="type-label">{label(r.type)}</span>
                      </td>
                      <td>
                        <div className="trace-tags">
                          {r.related
                            .filter((a: Artifact) =>
                              ["systems", "integrations"].includes(a.kind),
                            )
                            .slice(0, 4)
                            .map((a: Artifact) => (
                              <Link to={`/${a.kind}/${a.id}`} key={a.id}>
                                {a.key}
                              </Link>
                            ))}
                        </div>
                      </td>
                      <td>
                        <span
                          className={`coverage-count ${r.test_count ? "" : "uncovered"}`}
                        >
                          <FlaskConical size={14} />
                          {r.test_count} tests
                        </span>
                      </td>
                      <td>
                        <Badge status={r.test_status} />
                      </td>
                      <td>
                        <Badge status={r.uat_status} />
                      </td>
                      <td>
                        <div className="trace-tags">
                          {r.related
                            .filter((a: Artifact) => a.kind === "releases")
                            .map((a: Artifact) => (
                              <Link to={`/releases/${a.id}`} key={a.id}>
                                {a.key}
                              </Link>
                            ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!data.rows.length && (
              <Empty description="No requirements match these filters." />
            )}
            <div className="table-footer">
              {data.filtered_count} matching requirements
              <span>
                Coverage includes tests on decomposed child requirements.
              </span>
            </div>
          </section>
        </>
      )}
      {!data && !error && <Loading />}
    </>
  );
}
function ProcessFlow({ steps }: { steps: string[] }) {
  return (
    <div className="process-flow">
      {steps.map((step, i) => (
        <div key={i}>
          <span
            className={`process-step ${i === 0 || i === steps.length - 1 ? "boundary" : ""}`}
          >
            <span>{String(i + 1).padStart(2, "0")}</span>
            {step}
            {step.toLowerCase().includes("validat") && (
              <small>Invalid → Return error</small>
            )}
          </span>
          {i < steps.length - 1 && <ArrowRight size={18} />}
        </div>
      ))}
    </div>
  );
}

function Detail() {
  const { kind = "", id = "" } = useParams();
  const { items, meta, open, action, busy } = useWorkspace();
  const { data: record, error } = useResource<Artifact>(`/api/${kind}/${id}`);
  const [tab, setTab] = useState("Overview");
  const navigate = useNavigate();
  useEffect(() => setTab("Overview"), [id, kind]);
  if (error) return <ErrorBox message={error} />;
  if (!record) return <Loading />;
  const related: Artifact[] = record.impact_analysis?.items || [];
  const directTrace: Artifact[] = record.traceability?.related || related;
  const detailFields = [
    "description",
    "acceptance_criteria",
    "source",
    "preconditions",
    "steps",
    "expected_result",
    "scope",
    "objectives",
    "entry_criteria",
    "exit_criteria",
    "reason",
    "impact",
    "risk",
    "mitigation",
    "business_impact",
    "technical_impact",
    "root_cause",
    "workaround",
    "resolution",
    "deployment_notes",
    "rollback_plan",
    "current_state",
    "future_state",
    "content",
  ];
  const transition = () =>
    open({
      title: `Update ${record.key} status`,
      description:
        "The server checks transition permissions and mandatory workflow criteria before saving.",
      schema: schema(
        {
          status: s("string", { enum: record.allowed_transitions }),
          comment: s("string", { title: "Decision / transition comment" }),
        },
        ["status"],
      ),
      submit: (data) => post(`/api/${kind}/${id}/transition`, data),
      submitLabel: "Apply transition",
    });
  const addLink = () =>
    open({
      title: `Link ${record.key}`,
      description:
        "Connect a project artifact. Release scope uses Contains; parent requirements use Decomposes.",
      schema: schema({
        target_id: s("integer", { title: "Related artifact" }),
        relation: s("string", {
          enum: [
            "AFFECTS",
            "DECOMPOSES",
            "CONTAINS",
            "DOCUMENTS",
            "MITIGATES",
            "RELATES",
          ],
          default:
            kind === "releases"
              ? "CONTAINS"
              : kind === "requirements"
                ? "DECOMPOSES"
                : "AFFECTS",
        }),
      }),
      submit: (data) => post("/api/links", { source_id: record.id, ...data }),
      submitLabel: "Create relationship",
    });
  const edit = () =>
    open({
      title: `Edit ${record.key}`,
      schema: meta.schemas[kind],
      values: record,
      submit: (data) =>
        api(`/api/${kind}/${id}`, {
          method: "PATCH",
          body: JSON.stringify(data),
          headers: { "If-Match": String(record.revision) },
        }),
    });
  const tabs = [
    "Overview",
    ...(kind === "integrations" ? ["Field mappings", "Contract"] : []),
    ...(kind === "test-cases" ? ["Execution evidence"] : []),
    ...(kind === "uat" ? ["Acceptance"] : []),
    ...(kind === "incidents" ? ["Timeline"] : []),
    ...(kind === "releases" ? ["Readiness"] : []),
    "Traceability",
    "Impact analysis",
  ];
  return (
    <>
      <Link className="back-link" to={`/${kind}`}>
        <ArrowLeft size={15} />
        {titles[kind]}
      </Link>
      <PageHeading
        eyebrow={`${record.key} · ${label(kind)}`}
        title={record.title}
        description={
          kind === "requirements"
            ? "Business context, acceptance criteria, and a connected delivery record."
            : `Owned by ${record.owner} · Updated ${date(record.updated_at)} · Revision ${record.revision}`
        }
      >
        <Badge
          status={
            kind === "releases" && record.status === "READY"
              ? record.readiness.status
              : record.status
          }
        />
        {kind !== "documents" && (
          <button className="button secondary" onClick={edit}>
            Edit record
          </button>
        )}
        {record.allowed_transitions?.length > 0 && (
          <button className="button primary" onClick={transition}>
            Update status <ChevronDown size={15} />
          </button>
        )}
      </PageHeading>
      <div className="record-facts">
        {[
          "type",
          "priority",
          "environment",
          "protocol",
          "data_format",
          "mode",
          "technology",
          "version",
          "coordinator",
          "audience",
          "target_date",
        ]
          .filter((k) => record[k])
          .map((k) => (
            <span key={k}>
              <small>{label(k)}</small>
              <strong>
                {k === "target_date"
                  ? date(record[k])
                  : label(String(record[k]))}
              </strong>
            </span>
          ))}
        {kind === "risks" && (
          <span>
            <small>Severity score</small>
            <strong>
              {record.probability * record.impact} / 25 ·{" "}
              {record.probability * record.impact >= 15 ? "High" : "Moderate"}
            </strong>
          </span>
        )}
        {kind === "integrations" && (
          <>
            <span>
              <small>Source system</small>
              <Link to={`/systems/${record.source_system_id}`}>
                {items.find((a) => a.id === record.source_system_id)?.title}
              </Link>
            </span>
            <ArrowRight size={18} />
            <span>
              <small>Target system</small>
              <Link to={`/systems/${record.target_system_id}`}>
                {items.find((a) => a.id === record.target_system_id)?.title}
              </Link>
            </span>
          </>
        )}
      </div>
      <div className="detail-tabs" role="tablist" aria-label="Record details">
        {tabs.map((t) => (
          <button
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? "active" : ""}
            key={t}
            onClick={() => setTab(t)}
          >
            {t}
            {t === "Traceability" && <span>{directTrace.length}</span>}
          </button>
        ))}
      </div>
      <div role="tabpanel" aria-label={tab}>
        {tab === "Overview" && (
          <div className="detail-grid">
            <div className="detail-main">
              {kind === "test-cases" && (
                <ExecutionPanel record={record} compact />
              )}
              {kind === "uat" && <AcceptancePanel record={record} />}
              {kind === "releases" && (
                <ReadinessPanel readiness={record.readiness} />
              )}
              {kind === "changes" && (
                <Section
                  title="Impact assessment"
                  subtitle="Record the current impact before requesting approval"
                >
                  <div className="padded">
                    <Badge
                      status={
                        record.analysis_current ? "COMPLETE" : "NOT_READY"
                      }
                    />
                    <p>
                      {record.analysis_current
                        ? "The recorded analysis matches the current affected artifacts."
                        : "A current assessment is required before this change can be approved."}
                    </p>
                    <button
                      className="button primary"
                      disabled={busy}
                      onClick={() =>
                        action(
                          () => post(`/api/changes/${id}/analyze`),
                          "Current impact analysis recorded",
                        )
                      }
                    >
                      <Network size={16} />
                      Record impact analysis
                    </button>
                  </div>
                </Section>
              )}
              {kind === "processes" && (
                <Section title="Future-state workflow">
                  <ProcessFlow steps={record.steps || []} />
                </Section>
              )}
              <Section
                title={
                  kind === "requirements"
                    ? "Requirement definition"
                    : "Record details"
                }
              >
                <div className="definition">
                  {detailFields
                    .filter(
                      (field) =>
                        record[field] && typeof record[field] !== "object",
                    )
                    .map((field) => (
                      <div key={field}>
                        <h3>{label(field)}</h3>
                        <p
                          className={
                            field === "content" ? "document-content" : ""
                          }
                        >
                          {record[field]}
                        </p>
                      </div>
                    ))}
                  {detailFields.every((field) => !record[field]) && (
                    <p className="muted">
                      Add context and specifications using Edit record.
                    </p>
                  )}
                </div>
              </Section>
              {kind === "documents" && (
                <a
                  className="button primary"
                  href={`/api/documents/${id}/export`}
                >
                  <Download size={16} />
                  Download Markdown
                </a>
              )}
            </div>
            <div className="detail-side">
              <Section
                title="Connected evidence"
                aside={
                  <button
                    className="icon-button"
                    onClick={addLink}
                    aria-label="Add relationship"
                  >
                    <Plus size={17} />
                  </button>
                }
              >
                <div className="related-summary">
                  {[
                    "requirements",
                    "systems",
                    "integrations",
                    "test-cases",
                    "uat",
                    "incidents",
                    "changes",
                    "releases",
                  ].map((k) => (
                    <button key={k} onClick={() => setTab("Traceability")}>
                      <span>{titles[k]}</span>
                      <strong>
                        {directTrace.filter((a) => a.kind === k).length}
                      </strong>
                      <ChevronRight size={13} />
                    </button>
                  ))}
                </div>
              </Section>
              {kind === "requirements" && (
                <Section title="Validation status">
                  <div className="padded">
                    <div className="validation-row">
                      <span>Latest test result</span>
                      <Badge
                        status={record.traceability?.test_status || "NOT_RUN"}
                      />
                    </div>
                    <div className="validation-row">
                      <span>Stakeholder acceptance</span>
                      <Badge
                        status={record.traceability?.uat_status || "PENDING"}
                      />
                    </div>
                    {record.traceability?.parents.map((a: Artifact) => (
                      <div key={a.id}>
                        <small className="eyebrow">PARENT REQUIREMENT</small>
                        <ArtifactLink item={a} />
                      </div>
                    ))}
                  </div>
                </Section>
              )}
              <Section title="Record controls">
                <div className="padded control-stack">
                  <button className="button secondary" onClick={addLink}>
                    <Link2 size={15} />
                    Add relationship
                  </button>
                  {record.status === "DRAFT" && (
                    <button
                      className="button danger-quiet"
                      onClick={() =>
                        open({
                          title: `Delete ${record.key}`,
                          description:
                            "Only unlinked draft records can be deleted. Governed history is retained.",
                          schema: schema({
                            confirmation: s("string", {
                              title: `Type ${record.key} to confirm`,
                            }),
                          }),
                          submit: async (data) => {
                            if (data.confirmation !== record.key)
                              throw new Error("The record key does not match");
                            await api(`/api/${kind}/${id}`, {
                              method: "DELETE",
                            });
                            navigate(`/${kind}`);
                          },
                          submitLabel: "Delete draft",
                        })
                      }
                    >
                      <Trash2 size={15} />
                      Delete draft
                    </button>
                  )}
                  <small>
                    Changes and decisions are recorded in the audit trail.
                  </small>
                </div>
              </Section>
            </div>
          </div>
        )}
        {tab === "Field mappings" && <Mappings record={record} />}
        {tab === "Contract" && (
          <Section
            title="Integration contract"
            subtitle={`${record.method} ${record.endpoint}`}
          >
            <div className="contract-details">
              <p>
                <strong>Authentication design</strong>{" "}
                {record.authentication_type}
              </p>
              <p className="info-note">
                <ShieldCheck size={17} />
                Execution uses the authenticated local simulator. Authentication
                types above document the fictional integration design.
              </p>
              <div className="evidence-grid">
                <div>
                  <h3>Request format</h3>
                  <pre>
                    {record.request_format || "No request format documented."}
                  </pre>
                </div>
                <div>
                  <h3>Response format</h3>
                  <pre>
                    {record.response_format || "No response format documented."}
                  </pre>
                </div>
              </div>
            </div>
          </Section>
        )}
        {tab === "Execution evidence" && <ExecutionPanel record={record} />}
        {tab === "Acceptance" && <AcceptancePanel record={record} />}
        {tab === "Readiness" && <ReadinessPanel readiness={record.readiness} />}
        {tab === "Timeline" && (
          <Section
            title="Incident timeline"
            subtitle="Persisted changes and investigation events"
          >
            <div className="timeline">
              {record.timeline.map((event: any) => (
                <div key={event.id}>
                  <span className="timeline-dot" />
                  <div>
                    <h3>{label(event.action)}</h3>
                    <p>
                      {event.actor} ·{" "}
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                    {event.new_value?.status && (
                      <Badge status={event.new_value.status} />
                    )}
                    {event.new_value?.comment && (
                      <p>{event.new_value.comment}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}
        {tab === "Traceability" && (
          <Section
            title="Connected lifecycle"
            subtitle="Stored relationships and linked implementation evidence"
            aside={
              <button className="button secondary" onClick={addLink}>
                <Plus size={15} />
                Add relationship
              </button>
            }
          >
            <div className="trace-detail-grid">
              {Object.keys(titles)
                .filter((k) => directTrace.some((a) => a.kind === k))
                .map((k) => (
                  <div key={k}>
                    <h3>
                      {titles[k]}{" "}
                      <span>
                        {directTrace.filter((a) => a.kind === k).length}
                      </span>
                    </h3>
                    {directTrace
                      .filter((a) => a.kind === k)
                      .map((a) => (
                        <ArtifactLink key={a.id} item={a} />
                      ))}
                  </div>
                ))}
            </div>
            {!directTrace.length && (
              <Empty
                title="No connected records yet"
                description="Add a relationship to begin this record’s traceability chain."
              />
            )}
            <div className="stored-links">
              {record.links?.map((link: any) => {
                const other = items.find(
                  (a) =>
                    a.id ===
                    (link.source_id === record.id
                      ? link.target_id
                      : link.source_id),
                );
                return (
                  <div key={link.id}>
                    <span>
                      {link.source_id === record.id ? "Outgoing" : "Incoming"} ·{" "}
                      {label(link.relation)} · {other?.key}
                    </span>
                    <button
                      className="icon-button"
                      aria-label={`Remove relationship ${link.id}`}
                      onClick={() =>
                        open({
                          title: "Remove relationship",
                          description:
                            "This may invalidate an impact assessment or change release scope.",
                          schema: schema({
                            confirmation: s("string", {
                              title: "Type REMOVE to confirm",
                            }),
                          }),
                          submit: async (data) => {
                            if (data.confirmation !== "REMOVE")
                              throw new Error("Type REMOVE to confirm");
                            await api(`/api/links/${link.id}`, {
                              method: "DELETE",
                            });
                          },
                          submitLabel: "Remove relationship",
                        })
                      }
                    >
                      <X size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          </Section>
        )}
        {tab === "Impact analysis" && (
          <Section
            title="Change impact map"
            subtitle="Calculated from stored links and domain references"
          >
            <div className="impact-counts">
              {Object.entries(record.impact_analysis?.counts || {}).map(
                ([k, count]) => (
                  <div key={k}>
                    <strong>{String(count)}</strong>
                    <span>{titles[k] || label(k)}</span>
                  </div>
                ),
              )}
            </div>
            <div className="impact-explanation">
              <Network size={18} />
              The analysis follows requirements, integration consumers, tests,
              and delivery artifacts. Shared systems and containers terminate
              further expansion.
            </div>
            <div className="trace-detail-grid">
              {related.map((a) => (
                <ArtifactLink item={a} key={a.id} />
              ))}
            </div>
          </Section>
        )}
      </div>
    </>
  );
}

function Mappings({ record }: { record: Artifact }) {
  const { open } = useWorkspace();
  const mappingSchema = schema({
    source_field: s("string"),
    target_field: s("string"),
    datatype: s("string", {
      enum: ["string", "integer", "boolean"],
      default: "string",
    }),
    transformation: s("string", {
      enum: ["identity", "to_string", "to_integer", "uppercase", "lowercase"],
      default: "identity",
    }),
    required: s("boolean", { default: true }),
    validation_rule: s("string", {
      enum: ["none", "non_empty", "positive", "email"],
      default: "non_empty",
    }),
  });
  const edit = (mapping?: any) =>
    open({
      title: mapping ? "Edit field mapping" : "Add field mapping",
      description:
        "Use mappings to transform the payload sent to the local simulator.",
      schema: mappingSchema,
      values: mapping,
      submit: (data) =>
        mapping
          ? api(`/api/mappings/${mapping.id}`, {
              method: "PATCH",
              body: JSON.stringify(data),
            })
          : post(`/api/integrations/${record.id}/mappings`, data),
    });
  return (
    <Section
      title="Source-to-target field mappings"
      subtitle="Define how source fields map to the integration payload."
      aside={
        <button className="button primary" onClick={() => edit()}>
          <Plus size={16} />
          Add mapping
        </button>
      }
    >
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Source field</th>
              <th>Target field</th>
              <th>Data type</th>
              <th>Transformation</th>
              <th>Validation</th>
              <th>Required</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {record.mappings.map((mapping: any) => (
              <tr key={mapping.id}>
                <td>
                  <code>{mapping.source_field}</code>
                </td>
                <td>
                  <code>{mapping.target_field}</code>
                </td>
                <td>{mapping.datatype}</td>
                <td>
                  <code>{mapping.transformation}</code>
                </td>
                <td>{mapping.validation_rule}</td>
                <td>{mapping.required ? "Yes" : "No"}</td>
                <td>
                  <button
                    className="button small secondary"
                    onClick={() => edit(mapping)}
                  >
                    Edit mapping
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!record.mappings.length && (
        <Empty
          title="No mappings defined"
          description="Without mappings, the local runner sends the test payload unchanged."
        />
      )}
    </Section>
  );
}

function ExecutionPanel({
  record,
  compact = false,
}: {
  record: Artifact;
  compact?: boolean;
}) {
  const { action, open, busy } = useWorkspace();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<number | null>(null);
  const executions: Execution[] = record.executions || [];
  const execution = executions.find((e) => e.id === selected) || executions[0];
  return (
    <Section
      title="Test execution"
      subtitle="Run the stored payload against the local simulator or record manual evidence"
      aside={
        <button
          className="button primary"
          disabled={busy}
          onClick={() =>
            action(
              () => post(`/api/test-cases/${record.id}/execute`),
              "Test executed. Request and response evidence saved.",
            )
          }
        >
          <Play size={15} />
          Run test
        </button>
      }
    >
      <div className="padded">
        <div className="execution-controls">
          <span>
            <code>{record.key}</code> · Expected HTTP {record.expected_status} ·{" "}
            {label(record.scenario || "success")}
          </span>
          <button
            className="text-link"
            onClick={() =>
              open({
                title: "Record manual execution",
                schema: schema({
                  status: s("string", {
                    enum: ["PASS", "FAIL", "BLOCKED", "NOT_RUN"],
                  }),
                  actual_result: s("string", { minLength: 5 }),
                  evidence: s("string", { minLength: 10 }),
                }),
                submit: (data) =>
                  post(`/api/test-cases/${record.id}/execute`, {
                    mode: "MANUAL",
                    ...data,
                  }),
              })
            }
          >
            Record manual evidence
          </button>
        </div>
        {execution ? (
          <>
            <div className="execution-result">
              <Badge status={execution.status} />
              <strong>{execution.actual_result}</strong>
            </div>
            {execution.current_contract === false && (
              <p className="info-note">
                <RefreshCw size={15} />
                This execution predates the current contract. Run a fresh test
                before using it for release readiness.
              </p>
            )}
            <div className="execution-meta">
              <span>Execution #{execution.id}</span>
              <span>{execution.executed_by}</span>
              <span>{new Date(execution.executed_at).toLocaleString()}</span>
              <span>{execution.duration_ms} ms</span>
            </div>
            {execution.status === "FAIL" && (
              <div className="failure-action">
                <TriangleAlert size={18} />
                <span>
                  Investigate the captured response and link a defect to this
                  failure.
                </span>
                {execution.defect_id ? (
                  <Link
                    className="button small secondary"
                    to={`/incidents/${execution.defect_id}`}
                  >
                    Open defect <ArrowUpRight size={14} />
                  </Link>
                ) : (
                  <button
                    className="button small primary"
                    disabled={busy}
                    onClick={() =>
                      action(async () => {
                        const defect = await post(
                          `/api/test-executions/${execution.id}/defect`,
                        );
                        navigate(`/incidents/${defect.id}`);
                      }, "Defect created and linked to the failed execution")
                    }
                  >
                    Create defect
                  </button>
                )}
              </div>
            )}
            {!compact && (
              <>
                <div className="evidence-grid">
                  <div>
                    <h3>Captured request</h3>
                    <pre>
                      {execution.request_body ||
                        "Manual execution: no HTTP request"}
                    </pre>
                  </div>
                  <div>
                    <h3>
                      Captured response{" "}
                      <span>
                        {execution.response_status
                          ? `HTTP ${execution.response_status}`
                          : ""}
                      </span>
                    </h3>
                    <pre>
                      {execution.response_body ||
                        "Manual execution: see recorded evidence below"}
                    </pre>
                  </div>
                </div>
                <div className="evidence-note">
                  <h3>Execution evidence</h3>
                  <p>{execution.evidence}</p>
                </div>
                <Attachments executionId={execution.id} />
                <h3>Execution history</h3>
                <div className="execution-history">
                  {executions.map((e) => (
                    <button
                      key={e.id}
                      className={e.id === execution.id ? "selected" : ""}
                      onClick={() => setSelected(e.id)}
                    >
                      <span>#{e.id}</span>
                      <Badge status={e.status} />
                      <span>{date(e.executed_at)}</span>
                      <span>{e.executed_by}</span>
                      <ChevronRight size={14} />
                    </button>
                  ))}
                </div>
              </>
            )}
          </>
        ) : (
          <Empty
            title="Ready for its first run"
            description="Run the integration test to save its request and response, or record evidence from a manual test."
          />
        )}
      </div>
    </Section>
  );
}

function AcceptancePanel({ record }: { record: Artifact }) {
  const { open, items } = useWorkspace();
  const state = record.acceptance;
  if (!state) return null;
  const approve = () =>
    open({
      title: "Record stakeholder decision",
      description:
        "Approval requires passing mandatory scenarios with evidence. An explicit override is recorded when criteria are incomplete. Your account must be a stakeholder or manager.",
      schema: schema(
        {
          stakeholder_id: s("integer", { title: "Represented stakeholder" }),
          decision: s("string", {
            enum: ["APPROVED", "REJECTED"],
            default: "APPROVED",
          }),
          comments: s("string", { minLength: 5 }),
          override_reason: s("string", {
            title: "Override reason (only for incomplete criteria)",
          }),
        },
        ["stakeholder_id", "decision", "comments"],
      ),
      submit: (data) => post(`/api/uat/${record.id}/approve`, data),
      submitLabel: "Record decision",
    });
  return (
    <Section
      title="Acceptance evidence"
      subtitle="Mandatory criteria must be satisfied or explicitly overridden"
      aside={
        <button className="button primary" onClick={approve}>
          <ClipboardCheck size={15} />
          Record decision
        </button>
      }
    >
      <div className="padded">
        <div className="acceptance-summary">
          <Badge
            status={
              state.approved ? "APPROVED" : state.ready ? "READY" : "NOT_READY"
            }
          />
          <span>{state.incomplete.length} mandatory scenarios incomplete</span>
          {state.stale_approval && (
            <strong className="orange-text">
              Previous approval is stale. Review changed acceptance criteria.
            </strong>
          )}
        </div>
        {state.scenarios.map((scenario: any) => (
          <div className="uat-scenario" key={scenario.id}>
            <div>
              <span className="record-key">
                {scenario.key} · {scenario.mandatory ? "MANDATORY" : "OPTIONAL"}
              </span>
              <h3>{scenario.title}</h3>
              <p>{scenario.steps}</p>
              <p>
                <strong>Expected:</strong> {scenario.expected_result}
              </p>
              <Link
                className="text-link"
                to={`/requirements/${scenario.requirement_id}`}
              >
                {items.find((a) => a.id === scenario.requirement_id)?.key} ·
                Review acceptance criteria <ArrowUpRight size={13} />
              </Link>
              {scenario.result && (
                <div className="recorded-evidence">
                  <strong>Recorded evidence</strong>
                  <p>{scenario.result.evidence}</p>
                  <small>
                    {scenario.result.actor} · {date(scenario.result.timestamp)}
                  </small>
                  <Attachments uatResultId={scenario.result.id} />
                </div>
              )}
            </div>
            <div className="uat-actions">
              <Badge status={scenario.result?.status || "NOT_RUN"} />
              <button
                className="button secondary small"
                onClick={() =>
                  open({
                    title: `Record result · ${scenario.key}`,
                    schema: schema(
                      {
                        status: s("string", {
                          enum: ["PASS", "FAIL", "BLOCKED"],
                        }),
                        evidence: s("string", { minLength: 10 }),
                        comments: s("string"),
                      },
                      ["status", "evidence"],
                    ),
                    submit: (data) =>
                      post(`/api/uat-scenarios/${scenario.id}/results`, data),
                    submitLabel: "Save evidence",
                  })
                }
              >
                Record result
              </button>
            </div>
          </div>
        ))}
        {!state.scenarios.length && (
          <Empty
            title="Define UAT scenarios"
            description="Create scenarios linked to this session and the requirements being accepted."
          />
        )}
        {state.approval && (
          <div className="approval-record">
            <ShieldCheck size={21} />
            <div>
              <strong>
                {label(state.approval.decision)} · {state.approval.actor}
              </strong>
              <p>{state.approval.comments}</p>
              {state.approval.override_reason && (
                <p>
                  <strong>Explicit override:</strong>{" "}
                  {state.approval.override_reason}
                </p>
              )}
              <small>
                {date(state.approval.timestamp)} · Stakeholder record #
                {state.approval.stakeholder_id}
              </small>
            </div>
          </div>
        )}
      </div>
    </Section>
  );
}

function ReadinessPanel({ readiness }: { readiness: Readiness }) {
  return (
    <Section
      title="Release readiness gate"
      subtitle="Recalculated from the current release scope and its latest evidence"
      aside={<Badge status={readiness.status} />}
    >
      <div className="readiness-banner">
        <ShieldCheck size={24} />
        <p>
          {readiness.status === "READY"
            ? "All mandatory criteria pass. The release is eligible for an authorized transition."
            : "This release cannot proceed until every mandatory criterion passes."}
          <small>
            Warnings remain visible for review. Mandatory failures always block
            readiness.
          </small>
        </p>
      </div>
      <div className="readiness-gates">
        {readiness.gates.map((g) => (
          <div key={g.name}>
            <span
              className={`gate-icon ${g.status === "PASS" ? "green" : g.status === "WARNING" ? "amber" : "orange"}`}
            >
              {g.status === "PASS" ? (
                <Check size={18} />
              ) : (
                <TriangleAlert size={18} />
              )}
            </span>
            <div>
              <h3>
                {g.name} <small>{g.mandatory ? "MANDATORY" : "ADVISORY"}</small>
              </h3>
              <p>{g.detail}</p>
            </div>
            <Badge status={g.status} />
          </div>
        ))}
      </div>
    </Section>
  );
}

function Reports() {
  const { items, project, action, busy } = useWorkspace();
  const navigate = useNavigate();
  const types = [
    "Business Requirements Document",
    "Functional Requirements Document",
    "Integration Specification",
    "Test Plan",
    "UAT Plan",
    "Release Notes",
    "Training Guide",
    "Project Status Report",
  ];
  const documents = items.filter(
    (a) => a.kind === "documents" && a.project_id === project?.id,
  );
  return (
    <>
      <PageHeading
        eyebrow="CONTROLLED PROJECT DOCUMENTATION"
        title="Project reports"
        description="Generate versioned Markdown reports from your stored project records."
      />
      <div className="report-grid">
        {types.map((type, i) => {
          const Icon = [
            FileText,
            Layers3,
            Code2,
            FlaskConical,
            ClipboardCheck,
            Box,
            BookOpen,
            Activity,
          ][i];
          return (
            <div className="report-card" key={type}>
              <span className="report-icon">
                <Icon size={22} />
              </span>
              <h3>{type}</h3>
              <p>
                {
                  [
                    "Business needs, stakeholders, and the current-to-future process.",
                    "Functional, technical, and non-functional acceptance requirements.",
                    "System boundaries, protocol contracts, and source-to-target mappings.",
                    "Test scope, entry and exit criteria, and executable case definitions.",
                    "Stakeholder sessions, acceptance scenarios, and expected results.",
                    "Release scope, deployment, rollback, and live readiness criteria.",
                    "Audience-specific guidance and business process instructions.",
                    "Current coverage, delivery state, risks, and dependencies.",
                  ][i]
                }
              </p>
              <button
                className="text-link"
                disabled={busy || !project}
                onClick={() =>
                  action(async () => {
                    const doc = await post("/api/reports", {
                      project_id: project?.id,
                      document_type: type,
                    });
                    navigate(`/documents/${doc.id}`);
                  }, "Versioned document generated from project data")
                }
              >
                Generate document <ArrowUpRight size={15} />
              </button>
            </div>
          );
        })}
      </div>
      <Section
        title="Document register"
        subtitle="Immutable generated snapshots with controlled review status"
      >
        {documents.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Export</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <Link
                        className="table-record"
                        to={`/documents/${doc.id}`}
                      >
                        <span className="record-key">{doc.key}</span>
                        <strong>{doc.title}</strong>
                      </Link>
                    </td>
                    <td>v{doc.version}</td>
                    <td>
                      <Badge status={doc.status} />
                    </td>
                    <td>{date(doc.created_at)}</td>
                    <td>
                      <a
                        className="button small secondary"
                        href={`/api/documents/${doc.id}/export`}
                      >
                        <Download size={14} />
                        Markdown
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty title="Generate your first document" />
        )}
      </Section>
    </>
  );
}

function Administration({ logout }: { logout: () => void }) {
  const { session, open, action, busy } = useWorkspace();
  const { data: audit, error } = useResource<any[]>("/api/audit?limit=100");
  const [expanded, setExpanded] = useState<number | null>(null);
  return (
    <>
      <PageHeading
        eyebrow="WORKSPACE CONTROLS"
        title="Administration"
        description="Understand who changed what, inspect recorded decisions, and manage the fictional demo."
      >
        <button className="button secondary" onClick={logout}>
          <LogOut size={16} />
          Sign out
        </button>
      </PageHeading>
      <div className="admin-grid">
        <Section
          title="Your session"
          subtitle="Revocable, authenticated workspace access"
        >
          <div className="padded">
            <div className="session-identity">
              <span className="avatar large-avatar">{session.actor[0]}</span>
              <div>
                <h3>{session.actor}</h3>
                <p>
                  {label(session.role)} ·{" "}
                  {session.demo_mode
                    ? "Demo environment"
                    : "Authenticated environment"}
                </p>
              </div>
            </div>
            {session.demo_mode && (
              <>
                <label className="switch-role">
                  Explore another demo role
                  <select
                    value={session.role}
                    disabled={busy}
                    onChange={(e) =>
                      action(async () => {
                        await post("/api/auth/demo", { role: e.target.value });
                        window.location.reload();
                      }, "Role changed")
                    }
                  >
                    {[
                      "analyst",
                      "tester",
                      "stakeholder",
                      "manager",
                      "viewer",
                      "admin",
                    ].map((r) => (
                      <option key={r} value={r}>
                        {label(r)}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="muted">
                  Analysts manage records and tests. Stakeholders record
                  acceptance. Managers authorize changes and releases.
                  Administrators can reset the demo.
                </p>
              </>
            )}
          </div>
        </Section>
        <Section
          title="Northstar demo data"
          subtitle="Reset the fictional demonstration project"
        >
          <div className="padded">
            <p>
              Reset replaces the Northstar project and its linked evidence with
              the seeded scenario. Other projects and the audit history are
              retained.
            </p>
            <button
              className="button danger-quiet"
              disabled={!session.demo_mode || session.role !== "admin"}
              onClick={() =>
                open({
                  title: "Reset Northstar demo",
                  description:
                    "This removes edits, test executions, and decisions within the Northstar demo project. Type RESET NORTHSTAR DEMO to confirm.",
                  schema: schema({
                    confirmation: s("string", { title: "Confirmation phrase" }),
                  }),
                  submit: (data) => post("/api/admin/reset-demo", data),
                  submitLabel: "Reset demo data",
                })
              }
            >
              <RefreshCw size={16} />
              Reset Demo Data
            </button>
            <p className="muted">
              Available only to an administrator in demo mode.
            </p>
          </div>
        </Section>
      </div>
      <Section
        title="Audit trail"
        subtitle="Actor, action, entity, and preserved values"
        aside={
          <a
            className="subtle-link"
            href="/docs"
            target="_blank"
            rel="noreferrer"
          >
            OpenAPI reference <ExternalLink size={14} />
          </a>
        }
      >
        {error && <ErrorBox message={error} />}
        {audit ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {audit.flatMap((event) => [
                  <tr key={event.id}>
                    <td>{new Date(event.timestamp).toLocaleString()}</td>
                    <td>{event.actor}</td>
                    <td>{label(event.action)}</td>
                    <td>
                      {label(event.entity)} · {event.entity_id || "Workspace"}
                    </td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Inspect audit event ${event.id}`}
                        onClick={() =>
                          setExpanded(expanded === event.id ? null : event.id)
                        }
                      >
                        <MoreHorizontal size={18} />
                      </button>
                    </td>
                  </tr>,
                  expanded === event.id ? (
                    <tr key={`detail-${event.id}`}>
                      <td colSpan={5}>
                        <div className="evidence-grid">
                          <div>
                            <h3>Previous value</h3>
                            <pre>
                              {JSON.stringify(event.previous_value, null, 2)}
                            </pre>
                          </div>
                          <div>
                            <h3>New value</h3>
                            <pre>
                              {JSON.stringify(event.new_value, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : null,
                ])}
              </tbody>
            </table>
          </div>
        ) : (
          <Loading />
        )}
      </Section>
    </>
  );
}

function Attachments({
  executionId,
  uatResultId,
}: {
  executionId?: number;
  uatResultId?: number;
}) {
  const { action, busy } = useWorkspace();
  const { data, error } = useResource<any[]>(
    `/api/attachments?${executionId ? `execution_id=${executionId}` : `uat_result_id=${uatResultId}`}`,
  );
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className="attachments">
      <div>
        <h3>Attached evidence</h3>
        <button
          className="button secondary small"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          <Plus size={14} />
          Attach file
        </button>
      </div>
      <input
        ref={input}
        type="file"
        className="sr-only"
        aria-label="Attach evidence file"
        accept=".txt,.png,.jpg,.jpeg,.pdf"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          action(async () => {
            if (file.size > 2 * 1024 * 1024)
              throw new Error("Evidence files must be 2 MiB or smaller");
            const encoded = await new Promise<string>((resolve, reject) => {
              const reader = new FileReader();
              reader.onload = () =>
                resolve(String(reader.result).split(",")[1]);
              reader.onerror = () =>
                reject(new Error("Unable to read the evidence file"));
              reader.readAsDataURL(file);
            });
            await post(
              `/api/${executionId ? `test-executions/${executionId}` : `uat-results/${uatResultId}`}/attachments`,
              {
                filename: file.name,
                media_type: file.type || "text/plain",
                content_base64: encoded,
              },
            );
          }, "Evidence file attached with a SHA-256 integrity digest");
          e.target.value = "";
        }}
      />
      {error && <ErrorBox message={error} />}
      {data?.length ? (
        data.map((file) => (
          <a
            key={file.id}
            href={`/api/attachments/${file.id}/download`}
            className="attachment-link"
          >
            <FileText size={15} />
            <span>
              {file.filename}
              <small>
                {Math.ceil(file.size / 1024)} KiB · {file.actor} · SHA-256{" "}
                {file.sha256.slice(0, 12)}…
              </small>
            </span>
            <Download size={15} />
          </a>
        ))
      ) : (
        <p>PNG, JPEG, PDF, or UTF-8 text · up to 2 MiB per file.</p>
      )}
    </div>
  );
}

export default App;
