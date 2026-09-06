"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import {
  clearIntegrationBootstrapPending,
  hasIntegrationBootstrapPending,
  runIntegrationBootstrap,
} from "@/lib/bootstrapIntegrations";
import { storeToken } from "@/lib/session";

/**
 * OAuth Callback Page
 *
 * After the user authenticates with Google / GitHub, Supabase redirects here
 * with a PKCE `code`, which we exchange for a session; failing that, we read the
 * session the client already holds. We then trade that Supabase access token for
 * our own 7-day backend JWT.
 *
 * A token is only ever accepted from one of those two sources. Anything handed
 * to this page in the URL is ignored (NUMA-142 P6, PLAN 8).
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
          // The session Supabase established, never a token handed to us in the
          // URL. This used to read `access_token` out of the location hash and
          // exchange it for a 7-day NUMA JWT, with nothing tying that token to
          // a sign-in this browser started: opening
          // `/auth/callback#access_token=<someone else's>` silently signed the
          // visitor in as that someone, so everything they wrote afterwards
          // landed in the attacker's account (NUMA-142 P6, PLAN 8). The client
          // is configured `flowType: "pkce"` with `detectSessionInUrl: false`,
          // so Supabase never produces that hash form here and nothing
          // legitimate is lost by refusing it.
          const { data, error } = await supabase.auth.getSession();
          if (error || !data.session?.access_token) {
            router.replace("/auth?error=oauth_failed");
            return;
          }

          accessToken = data.session.access_token;
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

        if (!json.access_token) {
          router.replace("/auth?error=exchange_failed");
          return;
        }

        storeToken(json.access_token);

        if (hasIntegrationBootstrapPending()) {
          const result = await runIntegrationBootstrap(json.access_token);
          if (result === "redirected") return;
          // Only a finished run clears the flag. Clearing it unconditionally
          // here undid the retry the 5xx path exists to preserve, and the
          // protected layout's copy of this logic already disagreed
          // (NUMA-142 P6 review).
          if (result === "done") clearIntegrationBootstrapPending();
        } else {
          clearIntegrationBootstrapPending();
        }

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
