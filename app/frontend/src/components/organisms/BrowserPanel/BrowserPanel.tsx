import { useState, useEffect, useRef } from "react";
import { Icon } from "@/components/atoms";

interface BrowserPanelProps {
  url: string;
  onNavigate?: (url: string) => void;
  onLoad?: () => void;
  onError?: (error: string) => void;
}

function LoadingOverlay() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg-canvas)]/80 z-10 transition-opacity duration-200">
      <div className="flex flex-col items-center gap-3">
        <div className="w-6 h-6 border-2 border-[var(--border)] border-t-[var(--accent)] rounded-full animate-spin" />
        <span className="text-xs text-[var(--fg-muted)]">Loading page...</span>
      </div>
    </div>
  );
}

function BrowserErrorState({ url }: { url: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4 max-w-md text-center px-6">
        <div className="w-10 h-10 rounded-full bg-[var(--bg-surface-hover)] flex items-center justify-center">
          <Icon name="globe" size="lg" className="text-[var(--fg-subtle)]" />
        </div>
        <div>
          <p className="text-sm text-[var(--fg-default)] font-medium">
            Unable to display this page
          </p>
          <p className="mt-1 text-xs text-[var(--fg-muted)]">
            This site may not support embedding. Some sites block rendering inside iframes for security reasons.
          </p>
        </div>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[var(--accent)] border border-[var(--border)] rounded-md hover:bg-[var(--bg-surface-hover)] transition-colors"
        >
          Open in new tab
          <Icon name="upload" size="xs" />
        </a>
      </div>
    </div>
  );
}

function BrowserHintState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-3 max-w-md text-center px-6">
        <div className="w-10 h-10 rounded-full bg-[var(--bg-surface-hover)] flex items-center justify-center">
          <Icon name="globe" size="lg" className="text-[var(--fg-subtle)]" />
        </div>
        <p className="text-sm text-[var(--fg-muted)]">
          Enter a URL above to preview a page
        </p>
      </div>
    </div>
  );
}

function BrowserPanel({ url, onNavigate: _onNavigate, onLoad, onError }: BrowserPanelProps) {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Reset loading state when URL changes
  useEffect(() => {
    if (url) {
      setLoading(true);
      setLoadError(false);
    }
  }, [url]);

  if (!url) {
    return (
      <div className="relative w-full h-full bg-[var(--bg-canvas)]">
        <BrowserHintState />
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[var(--bg-canvas)]">
      {loading && <LoadingOverlay />}
      {loadError ? (
        <BrowserErrorState url={url} />
      ) : (
        <iframe
          ref={iframeRef}
          src={url}
          title="Embedded browser"
          className="w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          onLoad={() => {
            setLoading(false);
            onLoad?.();
          }}
          onError={() => {
            setLoading(false);
            setLoadError(true);
            onError?.("Failed to load");
          }}
        />
      )}
    </div>
  );
}

BrowserPanel.displayName = "BrowserPanel";

export { BrowserPanel };
export type { BrowserPanelProps };
