import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/generated/api/client";
import { useGitHubConnection } from "@/hooks/useGitHubConnection";
import { useOnboarding } from "@/hooks/useOnboarding";

type Step = "connect" | "install";

export function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("connect");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const github = useGitHubConnection();
  const { status, orgs, complete, invalidateStatus } =
    useOnboarding(null);
  const installUrl = useQuery({
    queryKey: ["onboarding", "install-url"],
    queryFn: () =>
      apiClient.get<{ install_url: string }>("/api/v1/onboarding/github/install"),
    enabled: step === "install",
  });

  // Auto-advance from connect step when GitHub is connected
  if (step === "connect" && status.data?.has_github && !connecting) {
    setStep("install");
  }

  const handleConnect = async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      await github.connect();
      invalidateStatus();
    } catch (err) {
      setConnectError(
        err instanceof Error ? err.message : "Failed to connect GitHub"
      );
    } finally {
      setConnecting(false);
    }
  };

  const handleFinish = async () => {
    try {
      await complete.mutateAsync({});
      await queryClient.invalidateQueries({ queryKey: ["onboarding", "status"] });
      navigate("/", { replace: true });
    } catch {
      // Error is available via complete.error
    }
  };


  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.title}>Stack Bench</h1>
        <p style={styles.subtitle}>Set up your workspace</p>

        {/* Progress indicator */}
        <div style={styles.steps}>
          <StepDot active={step === "connect"} done={step !== "connect"} label="1" />
          <div style={styles.stepLine} />
          <StepDot active={step === "install"} done={false} label="2" />
        </div>

        {/* Step 1: Connect GitHub */}
        {step === "connect" && (
          <div style={styles.stepContent}>
            <h2 style={styles.stepTitle}>Connect your GitHub account</h2>
            <p style={styles.stepDesc}>
              Stack Bench needs access to your repositories to manage stacked
              PRs.
            </p>
            {connectError && <div style={styles.error}>{connectError}</div>}
            <button
              onClick={handleConnect}
              disabled={connecting}
              style={styles.button}
            >
              {connecting ? "Connecting..." : "Connect GitHub"}
            </button>
          </div>
        )}

        {/* Step 2: Install app on accounts */}
        {step === "install" && (
          <div style={styles.stepContent}>
            <h2 style={styles.stepTitle}>Install Stack Bench</h2>
            <p style={styles.stepDesc}>
              Grant Stack Bench access to your GitHub accounts. You'll choose
              which repos to grant on GitHub.
            </p>

            {orgs.isLoading && (
              <p style={styles.loading}>Loading accounts...</p>
            )}

            {/* Show installed accounts */}
            {orgs.data && orgs.data.length > 0 && (
              <div style={styles.list}>
                {orgs.data.map((org: any) => (
                  <div key={org.login} style={styles.listItem}>
                    <img
                      src={org.avatar_url}
                      alt={org.login}
                      style={styles.avatar}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={styles.itemName}>{org.login}</div>
                      <div style={styles.itemDesc}>
                        {org.account_type === "User" ? "Personal account" : "Organization"}
                      </div>
                    </div>
                    <span style={styles.installedBadge}>Connected</span>
                  </div>
                ))}
              </div>
            )}

            {/* Install on more accounts */}
            {installUrl.data && (
              <a
                href={installUrl.data.install_url}
                target="_blank"
                rel="noopener noreferrer"
                style={styles.installLink}
                onClick={() => {
                  const check = setInterval(() => {
                    if (!document.hidden) {
                      clearInterval(check);
                      orgs.refetch();
                    }
                  }, 1000);
                }}
              >
                {orgs.data && orgs.data.length > 0
                  ? "Connect another organization"
                  : "Install Stack Bench on GitHub"}
              </a>
            )}

            {orgs.data && orgs.data.length === 0 && (
              <p style={styles.stepDesc}>
                Install the GitHub App to grant access to your repositories.
              </p>
            )}

            {/* Finish button — enabled when at least one account is connected */}
            {orgs.data && orgs.data.length > 0 && (
              <button
                onClick={handleFinish}
                disabled={complete.isPending}
                style={styles.button}
              >
                {complete.isPending ? "Setting up..." : "Continue to Stack Bench"}
              </button>
            )}

            {complete.error && (
              <div style={styles.error}>
                {(complete.error as { detail?: string })?.detail ?? "Setup failed"}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

function StepDot({
  active,
  done,
  label,
}: {
  active: boolean;
  done: boolean;
  label: string;
}) {
  return (
    <div
      style={{
        ...styles.stepDot,
        background: active
          ? "var(--accent)"
          : done
            ? "var(--green)"
            : "var(--bg-inset)",
        color: active || done ? "#fff" : "var(--fg-muted)",
      }}
    >
      {done ? "\u2713" : label}
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
    maxWidth: 480,
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
  steps: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 0,
    marginBottom: "1.5rem",
  },
  stepDot: {
    width: 28,
    height: 28,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.75rem",
    fontWeight: 600,
    flexShrink: 0,
  },
  stepLine: {
    width: 40,
    height: 2,
    background: "var(--border)",
  },
  stepContent: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.75rem",
  },
  stepHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  },
  stepTitle: {
    color: "var(--fg-default)",
    fontSize: "1rem",
    fontWeight: 600,
    margin: 0,
  },
  stepDesc: {
    color: "var(--fg-muted)",
    fontSize: "0.8125rem",
    margin: 0,
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
  backButton: {
    background: "none",
    color: "var(--fg-muted)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    padding: "0.25rem 0.75rem",
    fontSize: "0.75rem",
    cursor: "pointer",
    fontFamily: "var(--font-sans)",
    flexShrink: 0,
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
  list: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.25rem",
    maxHeight: 320,
    overflowY: "auto" as const,
  },
  listItem: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    padding: "0.625rem 0.75rem",
    background: "var(--bg-inset)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    cursor: "pointer",
    textAlign: "left" as const,
    fontFamily: "var(--font-sans)",
    width: "100%",
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    flexShrink: 0,
  },
  repoIcon: {
    width: 32,
    height: 32,
    borderRadius: 6,
    background: "var(--bg-surface)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.75rem",
    fontWeight: 600,
    color: "var(--fg-muted)",
    flexShrink: 0,
  },
  itemName: {
    color: "var(--fg-default)",
    fontSize: "0.875rem",
    fontWeight: 500,
  },
  itemDesc: {
    color: "var(--fg-muted)",
    fontSize: "0.75rem",
    marginTop: "0.125rem",
  },
  loading: {
    color: "var(--fg-muted)",
    fontSize: "0.8125rem",
    textAlign: "center" as const,
  },
  empty: {
    color: "var(--fg-muted)",
    fontSize: "0.8125rem",
    textAlign: "center" as const,
    padding: "1rem 0",
  },
  installedBadge: {
    fontSize: "0.6875rem",
    color: "var(--green)",
    border: "1px solid var(--green)",
    borderRadius: 4,
    padding: "0.125rem 0.5rem",
    flexShrink: 0,
  },
  installBadge: {
    fontSize: "0.6875rem",
    color: "var(--accent)",
    border: "1px solid var(--accent)",
    borderRadius: 4,
    padding: "0.125rem 0.5rem",
    flexShrink: 0,
  },
  installLink: {
    color: "var(--accent)",
    fontSize: "0.8125rem",
    textAlign: "center" as const,
    textDecoration: "none",
    display: "block",
    padding: "0.5rem",
    marginTop: "0.25rem",
  },
  installHint: {
    color: "var(--fg-muted)",
    fontSize: "0.8125rem",
    textAlign: "center" as const,
    margin: "0.5rem 0 0",
  },
  link: {
    color: "var(--accent)",
    textDecoration: "none",
  },
  error: {
    background: "var(--red-bg)",
    color: "var(--red)",
    border: "1px solid var(--red)",
    borderRadius: 6,
    padding: "0.5rem 0.75rem",
    fontSize: "0.8125rem",
  },
};
