import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ??
  "";

let client: SupabaseClient | null = null;

export function isSupabaseAuthAvailable() {
  return Boolean(
    supabaseUrl &&
      supabaseAnonKey &&
      !supabaseUrl.includes("your-project") &&
      !supabaseAnonKey.includes("replace-me")
  );
}

export function isMockAuthEnabled() {
  return process.env.NEXT_PUBLIC_MOCK_AUTH === "true";
}

export function getSupabaseClient() {
  if (!isSupabaseAuthAvailable()) {
    return null;
  }

  client ??= createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true
    }
  });

  return client;
}
