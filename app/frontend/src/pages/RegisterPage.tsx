import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({
        first_name: firstName,
        last_name: lastName,
        email,
        password,
      });
      navigate("/", { replace: true });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Registration failed";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Stack Bench</h1>
        <p style={styles.subtitle}>Create your account</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          {error && <div style={styles.error}>{error}</div>}

          <div style={styles.row}>
            <label style={styles.label}>
              First name
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
                autoComplete="given-name"
                style={styles.input}
              />
            </label>
            <label style={styles.label}>
              Last name
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
                autoComplete="family-name"
                style={styles.input}
              />
            </label>
          </div>

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
              minLength={8}
              autoComplete="new-password"
              style={styles.input}
            />
            <span style={styles.hint}>
              Min 8 chars, uppercase, lowercase, digit, and symbol
            </span>
          </label>

          <button type="submit" disabled={submitting} style={styles.button}>
            {submitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p style={styles.footer}>
          Already have an account?{" "}
          <Link to="/login" style={styles.link}>
            Sign in
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
  row: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.75rem",
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
  hint: {
    color: "var(--fg-subtle)",
    fontSize: "0.75rem",
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
