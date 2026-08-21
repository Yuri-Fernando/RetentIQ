import { Router } from "express";
import jwt from "jsonwebtoken";
import { z } from "zod";

export const authRouter = Router();

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

/**
 * Login de demonstração — valida contra as credenciais em .env
 * (DEMO_ADMIN_EMAIL / DEMO_ADMIN_PASSWORD) e devolve um JWT.
 *
 * PENDENTE: substituir por tabela de usuários real + hash de senha antes de
 * qualquer uso além de portfólio/demo local. Ver docs/HISTORICO.md.
 */
authRouter.post("/login", (req, res) => {
  const parsed = loginSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: "Payload inválido", details: parsed.error.flatten() });
  }

  const { email, password } = parsed.data;
  const validEmail = process.env.DEMO_ADMIN_EMAIL;
  const validPassword = process.env.DEMO_ADMIN_PASSWORD;

  if (email !== validEmail || password !== validPassword) {
    return res.status(401).json({ error: "Credenciais inválidas." });
  }

  const secret = process.env.JWT_SECRET ?? "";
  const expiresIn = (process.env.JWT_EXPIRES_IN ?? "8h") as jwt.SignOptions["expiresIn"];
  const token = jwt.sign({ email }, secret, { expiresIn });

  res.json({ token, expiresIn });
});
