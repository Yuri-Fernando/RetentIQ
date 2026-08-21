"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { API_URL, apiFetch } from "../lib/api";
import { NotionEditor, type Block } from "./NotionEditor";
import { RetentionCardChat } from "./RetentionCardChat";

// Painel lateral de detalhe de um card do kanban de retenção. Reúne três ideias do
// PDF de origem num único lugar: recomendação de win-back (ML), notas estilo Notion
// (idea dev #4) e chat em tempo real (idea dev #3) — tudo escopado à ação selecionada.

export interface RetentionAction {
  id: number;
  customer_id: number;
  title: string;
  status: "todo" | "in_progress" | "done";
  notes_json: Block[] | null;
  created_at: string;
  updated_at: string;
}

interface Recommendation {
  recommended_stock_code: string;
  recommended_description: string;
  score: number;
}

const fetcher = <T,>(path: string) => apiFetch<T>(path);
const NOTES_SAVE_DEBOUNCE_MS = 800;

export function RetentionCardDetail({
  action,
  onClose,
  onUpdated,
}: {
  action: RetentionAction;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [title, setTitle] = useState(action.title);
  const [blocks, setBlocks] = useState<Block[]>(action.notes_json ?? []);
  const [toast, setToast] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: recommendations } = useSWR<Recommendation[]>(
    `/api/retention/recommendations/${action.customer_id}`,
    fetcher
  );

  // Recarrega estado local sempre que trocamos de card (usuário clicou noutro).
  useEffect(() => {
    setTitle(action.title);
    setBlocks(action.notes_json ?? []);
  }, [action.id]); // eslint-disable-line react-hooks/exhaustive-deps

  function scheduleNotesSave(nextBlocks: Block[]) {
    setBlocks(nextBlocks);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      await fetch(`${API_URL}/api/retention/actions/${action.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes_json: nextBlocks }),
      });
      onUpdated();
    }, NOTES_SAVE_DEBOUNCE_MS);
  }

  // Cancela o debounce pendente ao desmontar, pra não salvar depois do painel fechado.
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  async function saveTitle() {
    if (title === action.title) return;
    await fetch(`${API_URL}/api/retention/actions/${action.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    onUpdated();
  }

  async function sendWinback() {
    try {
      await fetch(`${API_URL}/api/retention/actions/${action.id}/winback`, {
        method: "POST",
      });
      setToast("Oferta enfileirada.");
    } catch {
      setToast("Falha ao enfileirar oferta.");
    } finally {
      setTimeout(() => setToast(null), 3000);
    }
  }

  return (
    <div className="fixed right-0 top-0 z-40 flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto border-l border-white/10 bg-gray-950 p-5 shadow-2xl">
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-wide text-gray-500">
          Cliente {action.customer_id}
        </p>
        <button
          onClick={onClose}
          className="rounded-lg border border-white/10 px-2 py-1 text-xs text-gray-300 hover:bg-white/5"
        >
          Fechar ✕
        </button>
      </div>

      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={saveTitle}
        className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-lg font-semibold text-gray-100 outline-none focus:border-white/30"
      />

      {toast && (
        <div className="rounded-lg border border-risk-baixo/40 bg-risk-baixo/10 px-3 py-2 text-xs text-green-300">
          {toast}
        </div>
      )}

      <section>
        <p className="mb-2 text-sm font-medium text-gray-300">Recomendação de win-back</p>
        <div className="space-y-1.5">
          {recommendations && recommendations.length > 0 ? (
            recommendations.map((r) => (
              <div
                key={r.recommended_stock_code}
                className="flex items-center justify-between rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs"
              >
                <span className="truncate pr-2 text-gray-300">
                  {r.recommended_description}
                </span>
                <span className="shrink-0 text-gray-500">{r.score.toFixed(2)}</span>
              </div>
            ))
          ) : (
            <p className="text-xs text-gray-500">
              Nenhuma recomendação disponível ainda (rode{" "}
              <code className="text-gray-400">data-platform/ml/recommendation.py</code>).
            </p>
          )}
        </div>
        <button
          onClick={sendWinback}
          className="mt-3 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-gray-200 hover:bg-white/10"
        >
          Enviar oferta de win-back
        </button>
      </section>

      <section>
        <p className="mb-2 text-sm font-medium text-gray-300">
          Notas (editor estilo Notion)
        </p>
        <NotionEditor value={blocks} onChange={scheduleNotesSave} />
      </section>

      <section>
        <RetentionCardChat actionId={action.id} />
      </section>
    </div>
  );
}
