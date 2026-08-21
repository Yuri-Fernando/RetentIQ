import fs from "node:fs";
import path from "node:path";

/**
 * Leitor de CSV minimalista (sem dependência externa) para os arquivos gerados
 * pelos scripts de ML em data-platform/ml/ (churn_scores.csv, demand_forecast.csv).
 * Assume CSV simples, sem vírgulas dentro de campos — suficiente para os dados
 * numéricos/tabulares que esses scripts produzem.
 */
export function readCsv(relativeOrEnvPath: string): Record<string, string>[] {
  const filePath = path.resolve(__dirname, "../../", relativeOrEnvPath);
  if (!fs.existsSync(filePath)) {
    throw new Error(
      `CSV não encontrado em ${filePath}. Rode os scripts em data-platform/ml/ primeiro.`
    );
  }

  const raw = fs.readFileSync(filePath, "utf-8").trim();
  const [headerLine, ...lines] = raw.split(/\r?\n/);
  const headers = headerLine.split(",");

  return lines.map((line) => {
    const values = line.split(",");
    const row: Record<string, string> = {};
    headers.forEach((h, i) => {
      row[h] = values[i];
    });
    return row;
  });
}
