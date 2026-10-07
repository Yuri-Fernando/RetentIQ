"""
RetentIQ — experimentation/

Pacote de experimentação de produto (gap "9 — Data Science / Experimentation" da
auditoria de portfólio): A/B testing, cálculo de amostra/poder, CUPED, teste
sequencial, A/B bayesiano e uplift/CATE.

Decisão de stack: implementado em Python (não TypeScript), porque:
  - O repo já tem um precedente de computação estatística/ML em Python
    (`data-platform/ml/` — scikit-learn, statsmodels, pandas) com as mesmas
    dependências que este pacote precisa (scipy, statsmodels, scikit-learn).
  - As rotinas aqui são bibliotecas de cálculo puras (entram arrays/DataFrames,
    saem estatísticas), não endpoints HTTP — não há ganho real em reescrever em
    TS, e o ecossistema estatístico do Python (scipy.stats, statsmodels) é mais
    maduro para isso do que o equivalente em Node.
  - Mantém o padrão já estabelecido no README: "Dados / ML" = Python,
    "Backend" = Node/TS. Este pacote é "Dados / ML", não "Backend".

Cada submódulo é standalone e testado isoladamente (ver `experimentation/tests/`).
"""
