import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { readCsv } from "./csv";

// readCsv resolve o caminho relativo a partir de src/lib/../../ (raiz de apps/api),
// então o fixture precisa existir nesse ponto de resolução.
const FIXTURE_RELATIVE = "__fixtures__/sample.csv";
const FIXTURE_ABSOLUTE = path.resolve(__dirname, "../../", FIXTURE_RELATIVE);

describe("readCsv", () => {
  beforeAll(() => {
    fs.mkdirSync(path.dirname(FIXTURE_ABSOLUTE), { recursive: true });
    fs.writeFileSync(
      FIXTURE_ABSOLUTE,
      "customer_id,score,description\n1,0.82,Alto risco\n2,0.31,Baixo risco\n"
    );
  });

  afterAll(() => {
    // Remove o arquivo e a pasta __fixtures__ criada em beforeAll — sem isso,
    // sobra uma pasta vazia na raiz de apps/api a cada `npm test`.
    fs.rmSync(path.dirname(FIXTURE_ABSOLUTE), { recursive: true, force: true });
  });

  it("parseia header e linhas em objetos chave/valor", () => {
    const rows = readCsv(FIXTURE_RELATIVE);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({ customer_id: "1", score: "0.82", description: "Alto risco" });
    expect(rows[1].description).toBe("Baixo risco");
  });

  it("devolve valores como string (conversão de tipo é responsabilidade de quem consome)", () => {
    // Regressão do bug documentado em docs/HISTORICO.md: `score` chega como string
    // do CSV, então quem consome (ex.: retention.ts) precisa converter com Number()
    // antes de usar métodos como toFixed(). Este teste fixa o contrato atual.
    const rows = readCsv(FIXTURE_RELATIVE);
    expect(typeof rows[0].score).toBe("string");
  });

  it("lança erro claro quando o arquivo não existe", () => {
    expect(() => readCsv("__fixtures__/nao-existe.csv")).toThrow(/não encontrado/);
  });
});
