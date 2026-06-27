"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";

type Props = {
  articleUrl: string;
  fingerprint: string;
};

export function FailureActions({ articleUrl, fingerprint }: Props) {
  const router = useRouter();
  const [pending, setPending] = useState<"ignore" | "dismiss" | null>(null);
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
      <Button
        type="button"
        size="sm"
        variant="outline"
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
        {pending === "ignore" ? "Ignoring…" : "Ignore URL"}
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
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
      </Button>
      {error && <span className="form-error">{error}</span>}
    </div>
  );
}
