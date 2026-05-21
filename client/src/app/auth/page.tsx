"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Mail, Lock, User, Eye, EyeOff, Check, X } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

type Mode = "signin" | "signup";

const passwordChecks = [
  { label: "8+ characters", test: (p: string) => p.length >= 8 },
  { label: "Uppercase",     test: (p: string) => /[A-Z]/.test(p) },
  { label: "Lowercase",     test: (p: string) => /[a-z]/.test(p) },
  { label: "Number",        test: (p: string) => /[0-9]/.test(p) },
  { label: "Special char",  test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("signin");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const checks = useMemo(
    () => passwordChecks.map((c) => ({ ...c, passed: c.test(password) })),
    [password]
  );
  const allChecksPassed = checks.every((c) => c.passed);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setSuccess(null);
    setPassword("");
    setConfirmPassword("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (mode === "signup") {
      if (!allChecksPassed) { setError("Password does not meet all requirements."); return; }
      if (password !== confirmPassword) { setError("Passwords do not match."); return; }
    }

    setLoading(true);
    try {
      const endpoint = mode === "signin" ? "/auth/signin" : "/auth/signup";
      const body =
        mode === "signin"
          ? { email, password }
          : { email, password, full_name: name };

      const res = await fetch(`/api${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail ?? "Something went wrong.");
      }

      // Store JWT and redirect (works for both sign-in and sign-up)
      localStorage.setItem("numa_token", data.access_token);
      router.push("/home");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider: "google" | "github") => {
    setError(null);
    if (provider === "google") {
      localStorage.setItem("numa_connect_google_services_after_auth", "1");
    } else {
      localStorage.removeItem("numa_connect_google_services_after_auth");
    }
    // Supabase JS handles the OAuth dance; our /auth/callback page
    // will exchange the Supabase token for our backend JWT.
    const { error: err } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (err) {
      localStorage.removeItem("numa_connect_google_services_after_auth");
      setError(err.message);
    }
  };

  const inputCls =
    "w-full bg-white/4 border border-white/8 rounded-xl pl-10 pr-11 py-2.5 text-sm text-white placeholder:text-gray-600 focus:outline-none focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20 transition-all";

  return (
    <div className="h-screen overflow-hidden bg-[#0a0a0b] text-white relative">
      {/* Ambient glows */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-175 h-125 bg-indigo-500/6 rounded-full blur-[180px] pointer-events-none z-0" />
      <div className="fixed bottom-0 right-0 w-100 h-100 bg-purple-500/4 rounded-full blur-[150px] pointer-events-none z-0" />

      {/* Scrollable inner */}
      <div className="relative z-10 h-full overflow-y-auto" style={{ scrollbarWidth: "none" }}>

        {/* Top bar - NUMA left (mobile only) + Back to home right */}
        <div className="relative z-20 flex items-center justify-between px-6 pt-5">
          <a href="/" className="lg:hidden text-2xl font-extrabold tracking-tight">
            NUMA
          </a>
          <a
            href="/"
            className="ml-auto inline-flex items-center gap-2 text-sm text-gray-500 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </a>
        </div>

        {/* ── Mobile/tablet: single column ── */}
        <div className="lg:hidden flex flex-col items-center justify-start px-6 pt-6 pb-8 min-h-[calc(100vh-56px)]">
          <motion.div
            initial={{ opacity: 0, y: 20, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
            className="w-full max-w-sm"
          >
            <div className="text-left mb-5">
              <p className="text-gray-500 text-sm">
                {mode === "signin" ? "Welcome back. Sign in to continue." : "Create your account to get started."}
              </p>
            </div>
            <AuthCard
              mode={mode}
              switchMode={switchMode}
              error={error}
              success={success}
              email={email} setEmail={setEmail}
              password={password} setPassword={setPassword}
              confirmPassword={confirmPassword} setConfirmPassword={setConfirmPassword}
              name={name} setName={setName}
              showPassword={showPassword} setShowPassword={setShowPassword}
              showConfirm={showConfirm} setShowConfirm={setShowConfirm}
              checks={checks}
              loading={loading}
              handleSubmit={handleSubmit}
              handleOAuth={handleOAuth}
              inputCls={inputCls}
            />
            <p className="text-center text-[11px] text-gray-600 mt-4 leading-relaxed">
              By continuing, you agree to NUMA&apos;s{" "}
              <a href="/under-construction" className="text-gray-400 hover:text-white transition-colors underline underline-offset-2">Terms of Service</a>{" "}
              and{" "}
              <a href="/under-construction" className="text-gray-400 hover:text-white transition-colors underline underline-offset-2">Privacy Policy</a>.
            </p>
          </motion.div>
        </div>

        {/* ── Laptop+: split layout ── */}
        <div className="hidden lg:flex items-center justify-center min-h-screen px-12 gap-16 xl:gap-24">
          {/* Left - branding */}
          <motion.div
            initial={{ opacity: 0, x: -30, filter: "blur(6px)" }}
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
            className="flex-1 max-w-md"
          >
            <a href="/" className="block text-7xl xl:text-8xl font-extrabold tracking-tight leading-none mb-5">
              NUMA
            </a>
            <p className="text-gray-400 text-lg xl:text-xl leading-relaxed max-w-xs">
              {mode === "signin"
                ? "Welcome back. Sign in to continue."
                : "Create your account to get started."}
            </p>
          </motion.div>

          {/* Right - auth box */}
          <motion.div
            initial={{ opacity: 0, x: 30, filter: "blur(6px)" }}
            animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease: [0.23, 1, 0.32, 1] as [number, number, number, number] }}
            className="w-full max-w-md"
          >
            <AuthCard
              mode={mode}
              switchMode={switchMode}
              error={error}
              success={success}
              email={email} setEmail={setEmail}
              password={password} setPassword={setPassword}
              confirmPassword={confirmPassword} setConfirmPassword={setConfirmPassword}
              name={name} setName={setName}
              showPassword={showPassword} setShowPassword={setShowPassword}
              showConfirm={showConfirm} setShowConfirm={setShowConfirm}
              checks={checks}
              loading={loading}
              handleSubmit={handleSubmit}
              handleOAuth={handleOAuth}
              inputCls={inputCls}
            />
            <p className="text-center text-[11px] text-gray-600 mt-4 leading-relaxed">
              By continuing, you agree to NUMA&apos;s{" "}
              <a href="/under-construction" className="text-gray-400 hover:text-white transition-colors underline underline-offset-2">Terms of Service</a>{" "}
              and{" "}
              <a href="/under-construction" className="text-gray-400 hover:text-white transition-colors underline underline-offset-2">Privacy Policy</a>.
            </p>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Shared auth card extracted to avoid duplication
───────────────────────────────────────────── */
interface AuthCardProps {
  mode: Mode;
  switchMode: (m: Mode) => void;
  error: string | null;
  success: string | null;
  email: string; setEmail: (v: string) => void;
  password: string; setPassword: (v: string) => void;
  confirmPassword: string; setConfirmPassword: (v: string) => void;
  name: string; setName: (v: string) => void;
  showPassword: boolean; setShowPassword: (v: boolean) => void;
  showConfirm: boolean; setShowConfirm: (v: boolean) => void;
  checks: { label: string; passed: boolean }[];
  loading: boolean;
  handleSubmit: (e: React.FormEvent) => void;
  handleOAuth: (provider: "google" | "github") => void;
  inputCls: string;
}

function AuthCard({
  mode, switchMode, error, success,
  email, setEmail, password, setPassword,
  confirmPassword, setConfirmPassword,
  name, setName,
  showPassword, setShowPassword,
  showConfirm, setShowConfirm,
  checks, loading, handleSubmit, handleOAuth, inputCls,
}: AuthCardProps) {
  return (
    <div className="rounded-2xl border border-white/6 bg-white/2 p-6 backdrop-blur-sm">
      {/* Mode tabs */}
      <div className="flex rounded-xl bg-white/4 p-1 mb-5 border border-white/6">
        {(["signin", "signup"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => switchMode(m)}
            className={`flex-1 text-sm font-medium py-1.5 rounded-lg transition-all duration-300 ${
              mode === m ? "bg-white text-black shadow-sm" : "text-gray-400 hover:text-white"
            }`}
          >
            {m === "signin" ? "Sign In" : "Sign Up"}
          </button>
        ))}
      </div>

      {/* Banners */}
      <AnimatePresence>
        {error && (
          <motion.div
            key="error-banner"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden mb-3"
          >
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-2.5 text-xs text-red-400 flex items-start gap-2">
              <X className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          </motion.div>
        )}
        {success && (
          <motion.div
            key="success-banner"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden mb-3"
          >
            <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-4 py-2.5 text-xs text-emerald-400 flex items-start gap-2">
              <Check className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        <motion.form
          key={mode}
          initial={{ opacity: 0, x: mode === "signin" ? -10 : 10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: mode === "signin" ? 10 : -10 }}
          transition={{ duration: 0.2 }}
          onSubmit={handleSubmit}
          className="flex flex-col gap-3"
        >
          {mode === "signup" && (
            <div>
              <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-[0.15em] mb-1.5">Full Name</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-600" />
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="John Doe" required className={inputCls} />
              </div>
            </div>
          )}

          <div>
            <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-[0.15em] mb-1.5">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-600" />
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required className={inputCls} />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-[0.15em] mb-1.5">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-600" />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className={inputCls}
              />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400 transition-colors">
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {mode === "signup" && (
            <div>
              <label className="block text-[10px] font-medium text-gray-400 uppercase tracking-[0.15em] mb-1.5">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-600" />
                <input
                  type={showConfirm ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className={`${inputCls} ${
                    confirmPassword.length > 0
                      ? confirmPassword === password
                        ? "border-emerald-500/40 focus:border-emerald-500/40 focus:ring-emerald-500/20"
                        : "border-red-500/40 focus:border-red-500/40 focus:ring-red-500/20"
                      : ""
                  }`}
                />
                <button type="button" onClick={() => setShowConfirm(!showConfirm)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400 transition-colors">
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          )}

          {mode === "signup" && (
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 px-1 py-1">
              {checks.map(({ label, passed }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full transition-colors duration-200 ${passed ? "bg-emerald-500/20 text-emerald-400" : "bg-white/4 text-gray-600"}`}>
                    {passed ? <Check className="h-2.5 w-2.5" /> : <X className="h-2.5 w-2.5" />}
                  </span>
                  <span className={`text-[11px] transition-colors duration-200 ${passed ? "text-emerald-400" : "text-gray-600"}`}>{label}</span>
                </div>
              ))}
            </div>
          )}

          {mode === "signin" && (
            <div className="flex justify-end -mt-1">
              <a href="/under-construction" className="text-xs text-gray-500 hover:text-indigo-400 transition-colors">Forgot password?</a>
            </div>
          )}

          <Button
            type="submit"
            size="lg"
            disabled={loading}
            className="w-full bg-white text-black hover:bg-gray-100 font-semibold rounded-xl h-11 text-sm mt-1 shadow-[0_0_30px_rgba(255,255,255,0.06)] hover:shadow-[0_0_40px_rgba(255,255,255,0.12)] transition-all duration-500 disabled:opacity-60"
          >
            {loading ? "Please wait…" : mode === "signin" ? "Sign In" : "Create Account"}
          </Button>

          <div className="relative my-1">
            <div className="h-px bg-white/6" />
            <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-[#0a0a0b] px-3 text-[10px] text-gray-600 uppercase tracking-wider">or continue with</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button type="button" onClick={() => handleOAuth("google")} className="flex items-center justify-center gap-2 border border-white/6 bg-white/2 rounded-xl py-2.5 text-sm text-gray-300 hover:bg-white/5 hover:border-white/10 transition-all">
              <svg className="h-4 w-4" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google
            </button>
            <button type="button" onClick={() => handleOAuth("github")} className="flex items-center justify-center gap-2 border border-white/6 bg-white/2 rounded-xl py-2.5 text-sm text-gray-300 hover:bg-white/5 hover:border-white/10 transition-all">
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              GitHub
            </button>
          </div>
        </motion.form>
      </AnimatePresence>
    </div>
  );
}
