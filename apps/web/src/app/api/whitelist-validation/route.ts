import { NextResponse } from "next/server";

import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import { itemFingerprint } from "@/lib/fingerprint";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request.json()) as { articleUrl?: string };
  const articleUrl = body.articleUrl?.trim();
  if (!articleUrl) {
    return NextResponse.json({ error: "articleUrl required" }, { status: 400 });
  }

  const fingerprint = itemFingerprint(articleUrl);
  const admin = createAdminClient();

  const { error: insertError } = await admin.from("validation_whitelist").upsert(
    {
      article_fingerprint: fingerprint,
      article_url: articleUrl,
      created_at: new Date().toISOString(),
    },
    { onConflict: "article_fingerprint" },
  );

  if (insertError) {
    return NextResponse.json({ error: insertError.message }, { status: 500 });
  }

  const { error: deleteError } = await admin
    .from("ingestion_log")
    .delete()
    .eq("article_fingerprint", fingerprint);

  if (deleteError) {
    return NextResponse.json({ error: deleteError.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
