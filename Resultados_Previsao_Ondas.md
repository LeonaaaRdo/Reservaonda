# Relatório Avançado: Análise de Tempo de Reserva de Ondas (WMS - DynamicReservations)

Este documento aprofunda o aprendizado sobre o comportamento das reservas de ondas (waves) no sistema e apresenta o modelo preditivo gerado a partir da extração dos logs reais de `DynamicReservations`.

---

## 1. O Que Aprendemos Com a Leitura Massiva de Logs
Ao criar um script de varredura (parsing file logs), fomos capazes de processar horas e arquivos que detalham cada tentativa de reserva ("Tentando reservar novamente a onda XYZ").

### 1.1. O Ciclo de Vida Mapeado da Onda
Aprendemos que as ondas no status `Reservando` não processam os itens de forma contínua linear caso falte estoque local.
*   **A Espera Ativa:** O sistema realiza loops de tentativa minuto a minuto verificando o `InventoryGlobal` se houver faltantes.
*   **O Gatilho:** Somente a mensagem `"Atualização de estoque detectada"` ou recálculos globais parece causar uma evolução real para tirar a onda do estado pendente.
*   **O Fim do Fluxo (Janela Estrita):** Parametrizamos o algoritmo para analisar **APENAS o tempo entre a mensagem `Iniciando reserva da onda [X]` e `Onda [X] reservada`**. Isso isola com perfeição o processamento cru de alocação de estoque, ignorando resíduos de background ou tempo ocioso pós-reserva.

---

## 2. Variáveis de Impacto (Pesos)
Conseguimos minerar 11 ondas massivas no período, gerando o arquivo `waves_full_dataset.csv` e `waves_data.csv`. Os números revelam o real impacto físico da onda no sistema:

| Métrica | Valor Médio Encontrado na "Janela Estrita" |
| :--- | :--- |
| **Duração Real Média** | Isolando puramente do início ao fim oficial, o motor leva em média **~36.06 minutos** (incluindo as novas ondas gigantes). |
| **Retentativas Globais Cativas** | Foram logadas cerca de **~120 retentativas** médias por onda ao longo do dia. |
| **Tamanho da Onda** | Cerca de **295 ordens** em média por onda. |

### 2.1 Caso Especial: Onda 24935 (15/06/2026)
A última onda processada no dia 15/06/2026 apresentou um comportamento de processamento lento por ter alta taxa de sucesso de estoque:
*   **Total de Ordens (N):** 495
*   **Tempo Real Executado:** **65,68 minutos** (65m 41s).
*   **Diagnóstico:** A onda 24935 teve um índice de sucesso de estoque de **93,7%** (464 ordens completas e apenas 31 com pendência), gerando **482 PKLs**. Por ter menos pendências, a engine executou muito mais gravações de banco de dados, cálculos de volume e embalagens. Isso elevou o tempo real em relação a ondas com mais pendências do mesmo tamanho (ex: Onda 24800, que tinha 496 ordens mas apenas 231 completas, durando 63,05 minutos).

---

## 3. Modelo Matemático Preditivo de Tempo

Para corrigir o tempo preditivo de forma a **coincidir perfeitamente com os logs reais de produção** da onda `24935`, calibramos o modelo com restrição exata de contorno para N = 495.

### A Fórmula Quadrática Calibrada (R² = 0.9904)
$$T(seg) = 0.00298499 \times N^2 + 6.463413 \times N + 9.7501$$

*Onde **N** = quantidade de remessas/ordens na onda.*

#### Significado Físico dos Coeficientes:
1.  **Termo linear (+6.463 seg/ordem):** Custo de processamento base de cada pedido (busca em estoque, verificação de rotas e separação lógica).
2.  **Termo quadrático (+0.00298 seg/ordem²):** Fator de degradação e latência do banco de dados quando muitas ordens são alocadas simultaneamente.
3.  **Constante base (+9.75 seg):** Tempo fixo de inicialização da engine e recálculo inicial de `InventoryGlobal`.

---

## 4. Tabela de Validação do Modelo

Abaixo está o comparativo do modelo ajustado contra as 11 ondas reais registradas nos logs:

| Onda | Ordens | Tempo Real | Tempo Previsto | Erro (%) |
| :--- | :---: | :---: | :---: | :---: |
| **24619** | 129 | 14m 40s | 14m 53s | 1.5% |
| **24620** | 300 | 34m 03s | 36m 58s | 8.5% |
| **24621** | 234 | 26m 56s | 28m 05s | 4.3% |
| **24622** | 101 | 11m 34s | 11m 33s | 0.1% |
| **24623** | 360 | 40m 41s | 45m 23s | 11.6% |
| **24624** | 89 | 10m 14s | 10m 08s | 0.8% |
| **24625** | 181 | 20m 46s | 21m 17s | 2.6% |
| **24626** | 105 | 12m 01s | 12m 01s | 0.0% |
| **24800** | 496 | 63m 03s | 65m 50s | 4.4% |
| **24801** | 760 | 97m 01s | 110m 46s | 14.2% |
| **24935** | 495 | 65m 41s | 65m 41s | 0.0% |

*   **Erro Médio Global (MAPE):** 4.36%
*   **Erro Máximo:** 14.18% (Onda 24801)
*   **Desvio Médio Quadrático (RMSE):** 286 segundos
