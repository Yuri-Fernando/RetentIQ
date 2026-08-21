"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { login } from "../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@retentiq.dev");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 p-8">
        <h1 className="mb-1 text-2xl font-bold">RetentIQ</h1>
        <p className="mb-6 text-sm text-gray-400">
          Inteligência de receita &amp; retenção para e-commerce.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm"
            type="email"
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm"
            type="password"
            placeholder="senha"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-risk-alto">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="mt-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <p className="mt-4 text-xs text-gray-500">
          Credenciais de demo definidas em <code>apps/api/.env</code> (
          <code>DEMO_ADMIN_EMAIL</code> / <code>DEMO_ADMIN_PASSWORD</code>).
        </p>
      </div>
    </main>
  );
}
