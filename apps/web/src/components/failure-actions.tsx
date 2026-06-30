"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type Props = {
  articleUrl: string;
  fingerprint: string;
};

export function FailureActions({ articleUrl, fingerprint }: Props) {
  const router = useRouter();
  const [pending, setPending] = useState<"add" | "ignore" | "dismiss" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function post(path: string, body: object) {
    setError(null);
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const data = (await response.json().catch(() => ({}))) as { error?: string };
      throw new Error(data.error ?? "Request failed");
    }
    router.refresh();
  }

  return (
    <div className="failure-actions">
      <button
        type="button"
        className="failure-action-btn failure-action-btn--add"
        disabled={pending !== null}
        onClick={async () => {
          setPending("add");
          try {
            await post("/api/whitelist-validation", { articleUrl });
          } catch (err) {
            setError(err instanceof Error ? err.message : "Add failed");
          } finally {
            setPending(null);
          }
        }}
      >
        {pending === "add" ? "Adding…" : "Add"}
      </button>
      <button
        type="button"
        className="failure-action-btn failure-action-btn--ignore"
        disabled={pending !== null}
        onClick={async () => {
          setPending("ignore");
          try {
            await post("/api/ignore", { articleUrl });
          } catch (err) {
            setError(err instanceof Error ? err.message : "Ignore failed");
          } finally {
            setPending(null);
          }
        }}
      >
        {pending === "ignore" ? "Ignoring…" : "Ignore"}
      </button>
      <button
        type="button"
        className="failure-action-btn failure-action-btn--dismiss"
        disabled={pending !== null}
        onClick={async () => {
          setPending("dismiss");
          try {
            await post("/api/dismiss-failure", { fingerprint });
          } catch (err) {
            setError(err instanceof Error ? err.message : "Dismiss failed");
          } finally {
            setPending(null);
          }
        }}
      >
        {pending === "dismiss" ? "Dismissing…" : "Dismiss"}
      </button>
      {error && <span className="form-error">{error}</span>}
    </div>
  );
}
