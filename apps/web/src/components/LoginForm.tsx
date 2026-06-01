"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@aims.local");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMsg("");
    try {
      const res = await api.login(email, password);
      window.localStorage.setItem("aims_token", res.access_token);
      setMsg(`已登录：${res.email}`);
      router.push("/");
      router.refresh();
    } catch (err) {
      setMsg(String(err));
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    window.localStorage.removeItem("aims_token");
    setMsg("已退出登录");
    router.refresh();
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <label className="block text-sm">
        <span className="text-gray-400">邮箱</span>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded border border-aims-border bg-black/30 px-3 py-2"
          required
        />
      </label>
      <label className="block text-sm">
        <span className="text-gray-400">口令（AUTH_PASSWORD）</span>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded border border-aims-border bg-black/30 px-3 py-2"
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-aims-accent px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {loading ? "登录中…" : "登录"}
        </button>
        <button
          type="button"
          onClick={logout}
          className="rounded border border-aims-border px-4 py-2 text-sm"
        >
          退出
        </button>
      </div>
      {msg && <p className="text-xs text-gray-400">{msg}</p>}
      <p className="text-xs text-gray-500">
        启用 API_KEY 时，登录获得的 JWT 可与 X-API-Key 二选一访问接口。
      </p>
    </form>
  );
}
