"use client";

import { useState } from "react";

// idea dev #4 "Editor visual estilo Notion": aqui reimplementado como um editor de
// blocos minimalista e 100% React/Tailwind (sem lib externa — nada de tiptap/slate),
// suficiente pra anotações estruturadas dentro de um card do kanban de retenção.
// Cada bloco é independente (texto solto, título ou item de checklist) e o componente
// é totalmente controlado: quem usa `NotionEditor` decide como/quando persistir.

export type BlockType = "text" | "heading" | "checklist";

export interface Block {
  id: string;
  type: BlockType;
  content: string;
  checked?: boolean;
}

interface NotionEditorProps {
  value: Block[];
  onChange: (blocks: Block[]) => void;
}

function newBlockId(): string {
  return `blk_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

const TYPE_LABEL: Record<BlockType, string> = {
  text: "Texto",
  heading: "Título",
  checklist: "Checklist",
};

export function NotionEditor({ value, onChange }: NotionEditorProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  function updateBlock(id: string, patch: Partial<Block>) {
    onChange(value.map((b) => (b.id === id ? { ...b, ...patch } : b)));
  }

  function removeBlock(id: string) {
    onChange(value.filter((b) => b.id !== id));
  }

  function addBlock(type: BlockType) {
    onChange([...value, { id: newBlockId(), type, content: "", checked: false }]);
    setMenuOpen(false);
  }

  return (
    <div className="space-y-2">
      {value.length === 0 && (
        <p className="text-xs text-gray-500">Nenhuma nota ainda — adicione um bloco abaixo.</p>
      )}

      {value.map((block) => (
        <div
          key={block.id}
          className="flex items-start gap-2 rounded-lg border border-white/10 bg-white/5 p-2"
        >
          <select
            value={block.type}
            onChange={(e) => updateBlock(block.id, { type: e.target.value as BlockType })}
            className="shrink-0 rounded border border-white/10 bg-black/30 px-1.5 py-1 text-[11px] text-gray-300"
          >
            {(Object.keys(TYPE_LABEL) as BlockType[]).map((t) => (
              <option key={t} value={t}>
                {TYPE_LABEL[t]}
              </option>
            ))}
          </select>

          {block.type === "checklist" && (
            <input
              type="checkbox"
              checked={!!block.checked}
              onChange={(e) => updateBlock(block.id, { checked: e.target.checked })}
              className="mt-1.5 shrink-0"
            />
          )}

          {block.type === "heading" ? (
            <input
              value={block.content}
              onChange={(e) => updateBlock(block.id, { content: e.target.value })}
              placeholder="Título..."
              className="flex-1 bg-transparent text-sm font-semibold text-gray-100 outline-none placeholder:text-gray-600"
            />
          ) : (
            <textarea
              value={block.content}
              onChange={(e) => updateBlock(block.id, { content: e.target.value })}
              placeholder={block.type === "checklist" ? "Item da checklist..." : "Escreva algo..."}
              rows={1}
              className={`flex-1 resize-none bg-transparent text-sm text-gray-200 outline-none placeholder:text-gray-600 ${
                block.type === "checklist" && block.checked ? "text-gray-500 line-through" : ""
              }`}
            />
          )}

          <button
            onClick={() => removeBlock(block.id)}
            title="Remover bloco"
            className="shrink-0 rounded px-1.5 py-0.5 text-xs text-gray-500 hover:bg-white/10 hover:text-red-300"
          >
            ✕
          </button>
        </div>
      ))}

      <div className="relative">
        <button
          onClick={() => setMenuOpen((o) => !o)}
          className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-gray-300 hover:bg-white/5"
        >
          + Adicionar bloco
        </button>
        {menuOpen && (
          <div className="absolute left-0 top-full z-10 mt-1 w-36 overflow-hidden rounded-lg border border-white/10 bg-gray-900 shadow-lg">
            {(Object.keys(TYPE_LABEL) as BlockType[]).map((t) => (
              <button
                key={t}
                onClick={() => addBlock(t)}
                className="block w-full px-3 py-2 text-left text-xs text-gray-300 hover:bg-white/10"
              >
                {TYPE_LABEL[t]}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
