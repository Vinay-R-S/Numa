"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  clearIntegrationBootstrapPending,
  hasIntegrationBootstrapPending,
  runIntegrationBootstrap,
} from "@/lib/bootstrapIntegrations";

/**
 * OAuth Callback Page
 *
 * After the user authenticates with Google / GitHub, Supabase redirects here.
 * The Supabase JS client automatically picks up the session from the URL hash/code.
 * We then exchange the Supabase access_token for our own 7-day backend JWT.
 */
export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const handleCallback = async () => {
      let accessToken: string | null = null;

      try {
        const query = new URLSearchParams(window.location.search);
        const code = query.get("code");

        if (code) {
          const { data, error } = await supabase.auth.exchangeCodeForSession(code);
          if (error || !data.session?.access_token) {
            router.replace("/auth?error=oauth_failed");
            return;
          }

          accessToken = data.session.access_token;
        } else {
          const hash = window.location.hash.startsWith("#")
            ? window.location.hash.slice(1)
            : window.location.hash;
          const hashParams = new URLSearchParams(hash);
          const hashToken = hashParams.get("access_token");

          if (hashToken) {
            accessToken = hashToken;
          } else {
            const { data, error } = await supabase.auth.getSession();
            if (error || !data.session?.access_token) {
              router.replace("/auth?error=oauth_failed");
              return;
            }

            accessToken = data.session.access_token;
          }
        }
      } catch {
        router.replace("/auth?error=oauth_failed");
        return;
      }

      try {
        // Use relative URL to go through Next.js API proxy - works on mobile/any network device
        const res = await fetch("/api/auth/exchange", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ supabase_token: accessToken }),
        });

        const json = await res.json();

        if (!res.ok) {
          router.replace(`/auth?error=${encodeURIComponent(json.detail ?? "exchange_failed")}`);
          return;
        }

        localStorage.setItem("numa_token", json.access_token);

        if (hasIntegrationBootstrapPending()) {
          const result = await runIntegrationBootstrap(json.access_token);
          if (result === "redirected") return;
        }

        clearIntegrationBootstrapPending();
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
