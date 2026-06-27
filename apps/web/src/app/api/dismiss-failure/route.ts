import { NextResponse } from "next/server";

import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request.json()) as { fingerprint?: string };
  const fingerprint = body.fingerprint?.trim();
  if (!fingerprint) {
    return NextResponse.json({ error: "fingerprint required" }, { status: 400 });
  }

  const admin = createAdminClient();
  const { error } = await admin
    .from("ingestion_log")
    .delete()
    .eq("article_fingerprint", fingerprint);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
