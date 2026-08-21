"use client";

// Kanban de Ações de Retenção — /dashboard/retention
//
// Este componente concentra três ideias do PDF de origem que fazem mais sentido
// juntas do que separadas:
//   - idea dev #8  "Kanban estilo Trello": board com 3 colunas (A Contatar / Em
//     Andamento / Resolvido), drag-and-drop nativo (sem lib nova — ver nota abaixo).
//   - idea dev #4  "Editor visual estilo Notion": embutido em cada card como notas em
//     blocos (ver components/NotionEditor.tsx), dentro do painel de detalhe.
//   - idea dev #3  "Chat em tempo real": comentários ao vivo por card via WebSocket
//     (ver components/RetentionCardChat.tsx).
//   - idea dados #7 "Funil de recrutamento" (reformulada): no domínio de RH um funil
//     de recrutamento não faz sentido aqui — reaproveitamos o CONCEITO de funil (etapas
//     com queda de volume) pra rastrear clientes de Alto risco de churn desde a detecção
//     até a resolução: Alto risco total → Sem ação → Em andamento → Resolvido.
//   - idea dev #2 "Sistema de busca avançada" (versão enxuta): sem Algolia/ElasticSearch
//     (não haveria volume de dados que justifique isso aqui) — filtro client-side por
//     cliente ou título do card, o suficiente pro tamanho real do board.
//
// Nota de engenharia: o drag-and-drop é HTML5 nativo (draggable/onDragStart/onDragOver
// /onDrop), não uma lib de terceiros — este ambiente tem um bug de sandbox conhecido
// com EBADF/TAR_ENTRY_ERROR durante `npm install` (ver docs/HISTORICO.md), então
// evitamos qualquer dependência nova em todo este pacote de telas.

import { useState } from "react";
import useSWR from "swr";
import { apiFetch, API_URL } from "../../../lib/api";
import { KpiCard } from "../../../components/KpiCard";
import {
  RetentionCardDetail,
  type RetentionAction,
} from "../../../components/RetentionCardDetail";

const fetcher = <T,>(path: string) => apiFetch<T>(path);

interface Funnel {
  alto_risco_total: number;
  sem_acao: number;
  todo: number;
  in_progress: number;
  done: number;
}

const COLUMNS: { status: RetentionAction["status"]; label: string }[] = [
  { status: "todo", label: "A Contatar" },
  { status: "in_progress", label: "Em Andamento" },
  { status: "done", label: "Resolvido" },
];

export default function RetentionPage() {
  const { data: actions, mutate } = useSWR<RetentionAction[]>(
    "/api/retention/actions",
    fetcher
  );
  const { data: funnel } = useSWR<Funnel>("/api/retention/funnel", fetcher);

  const [selected, setSelected] = useState<RetentionAction | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newCustomerId, setNewCustomerId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [search, setSearch] = useState("");

  const filteredActions = (actions ?? []).filter((a) => {
    if (!search.trim()) return true;
    const term = search.trim().toLowerCase();
    return (
      String(a.customer_id).includes(term) || a.title.toLowerCase().includes(term)
    );
  });

  async function patchStatus(id: number, status: RetentionAction["status"]) {
    await fetch(`${API_URL}/api/retention/actions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    mutate();
  }

  async function createAction(e: React.FormEvent) {
    e.preventDefault();
    const customerId = Number(newCustomerId);
    if (!newCustomerId.trim() || !newTitle.trim() || Number.isNaN(customerId)) return;
    // O schema zod do backend (`createActionSchema`) exige customer_id numérico
    // (z.number().int()) — o input do formulário é sempre string, então
    // convertemos aqui antes de enviar, senão a API responde 400.
    await fetch(`${API_URL}/api/retention/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ customer_id: customerId, title: newTitle }),
    });
    setNewCustomerId("");
    setNewTitle("");
    setShowNewForm(false);
    mutate();
  }

  function handleDrop(status: RetentionAction["status"]) {
    if (!dragId) return;
    patchStatus(dragId, status);
    setDragId(null);
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Ações de Retenção</h1>
          <p className="text-sm text-gray-400">
            Kanban de contato com clientes em risco de churn — do alerta à resolução.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por cliente ou título..."
            className="w-56 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-gray-200 outline-none placeholder:text-gray-600 focus:border-white/30"
          />
          <button
            onClick={() => setShowNewForm((v) => !v)}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-gray-200 hover:bg-white/10"
          >
            + Nova ação
          </button>
        </div>
      </div>

      {showNewForm && (
        <form
          onSubmit={createAction}
          className="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-white/10 bg-white/5 p-4"
        >
          <div className="flex flex-col gap-1">
            <label htmlFor="new-action-customer-id" className="text-xs text-gray-400">
              Customer ID
            </label>
            <input
              id="new-action-customer-id"
              value={newCustomerId}
              onChange={(e) => setNewCustomerId(e.target.value)}
              className="rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-gray-200 outline-none"
            />
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="new-action-title" className="text-xs text-gray-400">
              Título da ação
            </label>
            <input
              id="new-action-title"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/30 px-2 py-1.5 text-sm text-gray-200 outline-none"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg border border-white/10 bg-white/10 px-3 py-1.5 text-xs font-medium text-gray-100 hover:bg-white/20"
          >
            Criar
          </button>
        </form>
      )}

      {/* Funil de retenção: reformulação da idea dados #7, ver comentário de topo. */}
      <section className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiCard
          label="Alto risco (total)"
          value={funnel ? String(funnel.alto_risco_total) : "..."}
        />
        <KpiCard label="Sem ação" value={funnel ? String(funnel.sem_acao) : "..."} />
        <KpiCard label="Em andamento" value={funnel ? String(funnel.in_progress) : "..."} />
        <KpiCard label="Resolvido" value={funnel ? String(funnel.done) : "..."} />
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {COLUMNS.map((col) => {
          const cards = filteredActions.filter((a) => a.status === col.status);
          return (
            <div
              key={col.status}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop(col.status)}
              className="rounded-xl border border-white/10 bg-white/5 p-3"
            >
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-medium text-gray-300">{col.label}</p>
                <span className="rounded-full bg-black/30 px-2 py-0.5 text-xs text-gray-400">
                  {cards.length}
                </span>
              </div>
              <div className="space-y-2">
                {cards.map((card) => (
                  <div
                    key={card.id}
                    draggable
                    onDragStart={() => setDragId(card.id)}
                    onClick={() => setSelected(card)}
                    className="cursor-pointer rounded-lg border border-white/10 bg-black/30 p-3 text-xs hover:border-white/30"
                  >
                    <p className="mb-1 text-[11px] uppercase tracking-wide text-gray-500">
                      Cliente {card.customer_id}
                    </p>
                    <p className="text-sm text-gray-200">{card.title}</p>
                  </div>
                ))}
                {cards.length === 0 && (
                  <p className="text-xs text-gray-600">Nenhum card nesta coluna.</p>
                )}
              </div>
            </div>
          );
        })}
      </section>

      {selected && (
        <RetentionCardDetail
          action={selected}
          onClose={() => setSelected(null)}
          onUpdated={() => mutate()}
        />
      )}
    </main>
  );
}
