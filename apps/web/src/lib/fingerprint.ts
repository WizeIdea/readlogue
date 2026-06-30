import { createHash } from "crypto";

/** Match Python `item_fingerprint` (scheme + host + path, no query/fragment). */
export function itemFingerprint(url: string): string {
  try {
    const parsed = new URL(url.trim());
    const clean = `${parsed.protocol}//${parsed.host}${parsed.pathname}`;
    return createHash("sha256").update(clean).digest("hex");
  } catch {
    return createHash("sha256").update(url.trim()).digest("hex");
  }
}
