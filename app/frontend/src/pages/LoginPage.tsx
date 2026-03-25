import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useGitHubConnection } from "@/hooks/useGitHubConnection";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const github = useGitHubConnection();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate("/", { replace: true });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Login failed";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGitHubLogin() {
    setError(null);
    setGithubLoading(true);
    try {
      await github.connect();
      navigate("/", { replace: true });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "GitHub login failed";
      setError(msg);
    } finally {
      setGithubLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Stack Bench</h1>
        <p style={styles.subtitle}>Sign in to your account</p>

        {error && <div style={styles.error}>{error}</div>}

        <button
          onClick={handleGitHubLogin}
          disabled={githubLoading}
          style={styles.githubButton}
        >
          {githubLoading ? "Connecting..." : "Sign in with GitHub"}
        </button>

        <div style={styles.divider}>
          <span style={styles.dividerText}>or</span>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              style={styles.input}
              placeholder="you@example.com"
            />
          </label>

          <label style={styles.label}>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              style={styles.input}
            />
          </label>

          <button type="submit" disabled={submitting} style={styles.button}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p style={styles.footer}>
          No account?{" "}
          <Link to="/register" style={styles.link}>
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "var(--bg-canvas)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "var(--font-sans)",
  },
  card: {
    background: "var(--bg-surface)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    padding: "2.5rem 2rem",
    width: "100%",
    maxWidth: 380,
  },
  title: {
    color: "var(--fg-default)",
    fontSize: "1.25rem",
    fontWeight: 600,
    margin: 0,
    textAlign: "center" as const,
  },
  subtitle: {
    color: "var(--fg-muted)",
    fontSize: "0.875rem",
    marginTop: "0.25rem",
    marginBottom: "1.5rem",
    textAlign: "center" as const,
  },
  form: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "1rem",
  },
  label: {
    color: "var(--fg-muted)",
    fontSize: "0.8125rem",
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.375rem",
  },
  input: {
    background: "var(--bg-inset)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    padding: "0.5rem 0.75rem",
    color: "var(--fg-default)",
    fontSize: "0.875rem",
    fontFamily: "var(--font-sans)",
    outline: "none",
  },
  button: {
    background: "var(--accent)",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "0.5rem 1rem",
    fontSize: "0.875rem",
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "var(--font-sans)",
    marginTop: "0.25rem",
  },
  githubButton: {
    background: "#24292e",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "0.5rem 1rem",
    fontSize: "0.875rem",
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "var(--font-sans)",
    width: "100%",
    marginBottom: "0.5rem",
  },
  divider: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    margin: "0.75rem 0",
  },
  dividerText: {
    color: "var(--fg-muted)",
    fontSize: "0.75rem",
    flexShrink: 0,
  },
  error: {
    background: "var(--red-bg)",
    color: "var(--red)",
    border: "1px solid var(--red)",
    borderRadius: 6,
    padding: "0.5rem 0.75rem",
    fontSize: "0.8125rem",
  },
  footer: {
    color: "var(--fg-muted)",
    fontSize: "0.8125rem",
    textAlign: "center" as const,
    marginTop: "1.25rem",
  },
  link: {
    color: "var(--accent)",
    textDecoration: "none",
  },
};
