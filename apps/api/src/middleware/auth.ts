import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";

export interface AuthedRequest extends Request {
  user?: { email: string };
}

/**
 * Middleware de autenticação JWT (idea "6/12 — Sistema de autenticação completo /
 * JWT" do repertório dev). Espera header `Authorization: Bearer <token>`.
 *
 * PENDENTE (ver .env.example e docs/HISTORICO.md): hoje só existe um usuário demo
 * lido de variável de ambiente. Antes de produção real, trocar por tabela de
 * usuários com senha hasheada (bcrypt/argon2) + refresh token.
 */
export function requireAuth(req: AuthedRequest, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header?.startsWith("Bearer ")) {
    return res.status(401).json({ error: "Token ausente. Faça login em POST /auth/login." });
  }

  const token = header.slice("Bearer ".length);
  try {
    const secret = process.env.JWT_SECRET ?? "";
    const payload = jwt.verify(token, secret) as { email: string };
    req.user = { email: payload.email };
    next();
  } catch {
    return res.status(401).json({ error: "Token inválido ou expirado." });
  }
}
