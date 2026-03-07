"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * OAuth Callback Page
 *
 * After the user authenticates with Google / GitHub, Supabase redirects here.
 * The Supabase JS client automatically picks up the session from the URL hash/code.
 * We then exchange the Supabase access_token for our own 2-day backend JWT.
 */
export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const handleCallback = async () => {
      // Give Supabase JS a moment to parse the URL and hydrate the session
      const { data, error } = await supabase.auth.getSession();

      if (error || !data.session?.access_token) {
        router.replace("/auth?error=oauth_failed");
        return;
      }

      try {
        const res = await fetch(`${API}/auth/exchange`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ supabase_token: data.session.access_token }),
        });

        const json = await res.json();

        if (!res.ok) {
          router.replace(`/auth?error=${encodeURIComponent(json.detail ?? "exchange_failed")}`);
          return;
        }

        localStorage.setItem("numa_token", json.access_token);
        router.replace("/home");
      } catch {
        router.replace("/auth?error=network_error");
      }
    };

    handleCallback();
  }, [router]);

  return (
    <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4 text-white">
        <div className="h-8 w-8 rounded-full border-2 border-white/20 border-t-white animate-spin" />
        <p className="text-sm text-gray-400">Finishing sign-in…</p>
      </div>
    </div>
  );
}
