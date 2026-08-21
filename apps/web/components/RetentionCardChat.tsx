"use client";

import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import { API_URL, apiFetch } from "../lib/api";

// idea dev #3 "Chat em tempo real": aqui reaproveitada como comentários ao vivo por
// card de retenção — o time de CS discute a estratégia de retenção do cliente em
// tempo real, sem sair do card. Mesmo padrão de WebSocket já usado em
// app/dashboard/page.tsx (evento churn-alert): useEffect com socket.io-client e
// cleanup via socket.disconnect().

interface Comment {
  id: number;
  action_id: number;
  author: string;
  message: string;
  created_at: string;
}

export function RetentionCardChat({ actionId }: { actionId: number }) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [author, setAuthor] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  // Carrega histórico inicial via REST.
  useEffect(() => {
    let cancelled = false;
    apiFetch<Comment[]>(`/api/retention/actions/${actionId}/comments`)
      .then((data) => {
        if (!cancelled) setComments(data);
      })
      .catch(() => {
        // Se o backend ainda não tiver a rota pronta (paralelo em desenvolvimento),
        // apenas mantém a lista vazia em vez de quebrar o painel.
      });
    return () => {
      cancelled = true;
    };
  }, [actionId]);

  // Conecta ao Socket.io e entra na "sala" da ação para receber comentários ao vivo.
  useEffect(() => {
    const socket = io(API_URL);
    socket.emit("join-action", actionId);
    socket.on("retention-comment", (comment: Comment) => {
      if (comment.action_id !== actionId) return;
      setComments((prev) => [...prev, comment]);
    });
    return () => {
      socket.disconnect();
    };
  }, [actionId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!author.trim() || !message.trim()) return;
    setSending(true);
    try {
      await fetch(`${API_URL}/api/retention/actions/${actionId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ author, message }),
      });
      // Não adicionamos otimisticamente: o próprio POST dispara o evento
      // `retention-comment` via socket, que já atualiza a lista acima.
      setMessage("");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium text-gray-300">Chat da ação (tempo real)</p>
      <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-white/10 bg-black/20 p-2">
        {comments.length === 0 && (
          <p className="text-xs text-gray-500">Nenhum comentário ainda.</p>
        )}
        {comments.map((c) => (
          <div key={c.id} className="text-xs">
            <span className="font-semibold text-gray-300">{c.author}</span>{" "}
            <span className="text-gray-500">
              {new Date(c.created_at).toLocaleTimeString("pt-BR")}
            </span>
            <p className="text-gray-300">{c.message}</p>
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-1.5">
        <input
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="Seu nome"
          className="rounded-lg border border-white/10 bg-black/30 px-2 py-1 text-xs text-gray-200 outline-none placeholder:text-gray-600"
        />
        <div className="flex gap-1.5">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Escreva uma mensagem..."
            className="flex-1 rounded-lg border border-white/10 bg-black/30 px-2 py-1 text-xs text-gray-200 outline-none placeholder:text-gray-600"
          />
          <button
            type="submit"
            disabled={sending}
            className="shrink-0 rounded-lg border border-white/10 px-3 py-1 text-xs text-gray-300 hover:bg-white/5 disabled:opacity-50"
          >
            Enviar
          </button>
        </div>
      </form>
    </div>
  );
}
