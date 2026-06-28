"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { patchItem } from "@/lib/items";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import type { CurationV1 } from "@/lib/curation";

async function requireUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    throw new Error("Unauthorized");
  }
  return user;
}

export async function setRating(
  itemId: number,
  rating: "like" | "dislike" | null,
) {
  await requireUser();
  const admin = createAdminClient();
  await patchItem(admin, itemId, { rating });
  revalidatePath("/");
}

export async function setRead(itemId: number, read: boolean) {
  await requireUser();
  const admin = createAdminClient();
  await patchItem(admin, itemId, {
    read_at: read ? new Date().toISOString() : null,
  });
  revalidatePath("/");
}

export async function setCategory(itemId: number, category: string | null) {
  await requireUser();
  const admin = createAdminClient();
  await patchItem(admin, itemId, { category });
  revalidatePath("/");
}

export async function setCuration(itemId: number, curation: CurationV1) {
  await requireUser();
  const admin = createAdminClient();
  await patchItem(admin, itemId, { curation });
  revalidatePath("/");
}

export async function signOut() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
