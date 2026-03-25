import { useEffect, useState } from "react";

/**
 * GitHub OAuth callback page.
 *
 * Receives `code` and `state` from the GitHub redirect URL,
 * sends them to the opener window via postMessage, and closes itself.
 * If opened directly (no opener), shows a message.
 */
export function GitHubCallbackPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (!code || !state) {
      setError("Missing code or state parameter from GitHub.");
      return;
    }

    if (window.opener) {
      window.opener.postMessage(
        { type: "github-oauth-callback", code, state },
        window.location.origin
      );
      window.close();
    } else {
      setError(
        "This page should be opened as a popup. Please return to Stack Bench and try again."
      );
    }
  }, []);

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {error ? (
          <>
            <h1 style={styles.title}>GitHub Connection</h1>
            <p style={styles.message}>{error}</p>
          </>
        ) : (
          <>
            <h1 style={styles.title}>Connecting GitHub...</h1>
            <p style={styles.message}>This window should close automatically.</p>
          </>
        )}
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
    textAlign: "center" as const,
  },
  title: {
    color: "var(--fg-default)",
    fontSize: "1.25rem",
    fontWeight: 600,
    margin: 0,
  },
  message: {
    color: "var(--fg-muted)",
    fontSize: "0.875rem",
    marginTop: "0.75rem",
  },
};
