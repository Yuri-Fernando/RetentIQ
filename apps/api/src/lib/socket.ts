import type { Server as HttpServer } from "node:http";
import { Server as SocketIOServer } from "socket.io";

/**
 * Módulo dedicado ao Socket.io (extraído de `server.ts`) para que rotas — como
 * `routes/retention.ts` — possam importar a instância `io` já criada sem gerar
 * import circular com `server.ts` (que é o ponto de entrada da aplicação).
 *
 * Uso do quadro Kanban em tempo real (idea dev "8 — Kanban estilo Trello"):
 * o cliente entra numa "sala" por card (`retention-action-${id}`) para receber
 * comentários novos ao vivo, sem precisar dar polling na API.
 */
let io: SocketIOServer | null = null;

export function createSocketServer(httpServer: HttpServer): SocketIOServer {
  io = new SocketIOServer(httpServer, {
    cors: { origin: process.env.WEB_ORIGIN ?? "http://localhost:3000" },
  });

  io.on("connection", (socket) => {
    // Cliente pede para entrar na sala de um card específico de Ações de Retenção.
    socket.on("join-action", (actionId: number | string) => {
      socket.join(`retention-action-${actionId}`);
    });

    socket.on("leave-action", (actionId: number | string) => {
      socket.leave(`retention-action-${actionId}`);
    });
  });

  return io;
}

/**
 * Getter para módulos que precisam emitir eventos (ex.: rotas) sem depender
 * diretamente de `server.ts`. Lança erro claro se chamado antes da inicialização
 * — isso só aconteceria em uso incorreto (ex.: em testes que não sobem o server).
 */
export function getIo(): SocketIOServer {
  if (!io) {
    throw new Error(
      "Socket.io ainda não foi inicializado. Chame createSocketServer(httpServer) em server.ts primeiro."
    );
  }
  return io;
}
