# Relatório Avançado: Análise de Tempo de Reserva de Ondas (WMS - DynamicReservations)

Este documento aprofunda o aprendizado sobre o comportamento das reservas de ondas (waves) no sistema e apresenta o modelo preditivo gerado a partir da extração dos logs reais de `DynamicReservations`. 

## 1. O Que Aprendemos Com a Leitura Massiva de Logs
Ao criar um script de varredura (parsing file logs), fomos capazes de processar horas e arquivos que detalham cada tentativa de reserva ("Tentando reservar novamente a onda XYZ").

### 1.1. O Ciclo de Vida Mapeado da Onda
Aprendemos que as ondas no status `Reservando` não processam os itens de forma contínua linear caso falte estoque local.
*   **A Espera Ativa:** O sistema realiza loops de tentativa minuto a minuto verificando o `InventoryGlobal` se houver faltantes.
*   **O Gatilho:** Somente a mensagem `"Atualização de estoque detectada"` ou recálculos globais parece causar uma evolução real para tirar a onda do estado pendente.
*   **O Fim do Fluxo:** **(Correção Aplicada - Janela Estrita)** Conforme seu direcionamento, parametrizamos o algoritmo para analisar **APENAS o tempo entre a mensagem `Iniciando reserva da onda [X]` e `Onda [X] reservada`**. Isso isola com perfeição o processamento cru de alocação de estoque, ignorando resíduos de background.

## 2. Variáveis de Impacto (Pesos)
Conseguimos minerar 8 ondas massivas no período, gerando o arquivo `waves_data.csv`. Os números revelam o real impacto físico da onda no sistema:

| Métrica | Valor Médio Encontrado na "Janela Estrita" |
| :--- | :--- |
| **Duração Real Média** | Isolando puramente do início ao fim oficial (em ondas gigantes), o motor leva em média **~21.37 minutos**! |
| **Retentativas Globais Cativas** | Foram logadas cerca de ~131 retentativas por onda, mas rodando soltas pelo dia. |
| **Tamanho da Onda** | Cerca de 43 ordens pendentes. |

### 2.1 Análise Isolada de "Pesos":
Fizemos uma correlação de impacto linear focada nos instantes de processamento fechado da onda:
*   **Peso do Tamanho da Onda:** Cada ordem processada toma cerca de **0.50 minutos** perante dificuldades. Ignorando interferências massivas, a taxa real de capacidade do WMS é **~0.17 minutos (10 segundos) por Ordem** neste intervalo!
*   **Peso de Retentativas:** O gargalo no banco (tentativas falhas em fila) pesa em torno de **0.16 minutos (9,6 segundos)** por loop falho.

---

## 3. Modelo Matemático Preditivo de Tempo

Com base na heurística dos dados agrupados, criamos a seguinte regra matemática para **prever quanto tempo** uma onda vai ficar em estado 'Reservando':

### A Fórmula de Previsão na Janela Estrita
**Tempo Oficial Estimado (em minutos) = (Quantidade de Ordens * 0.17) + (Estimativa Média de Loops * 0.16)**

*Obs:* Isolando apenas o evento `Iniciando reserva da onda` até `Onda ... reservada`, obtemos os indicadores de processamento bruto sem "gordura" de latência paralela.

**"Se você tiver uma onda de 50 pedidos (Ordens), o custo *real* de processamento na engine será de apenas ~8.5 minutos (50 * 0.17). Porém, se houver falta de estoque, a cada vez que o loop bater e falhar aguardando reposição, haverá um acréscimo de quase ~10 segundos de engasgo pontual (retentativa) estendendo o tempo."**

## 4. Recomendações Técnicas Imediatas
1.  **Alarme Visual WMS:** Para prever ativamente, o BI pode usar a fórmula: `Ordens * 0.17`. Quando travar com pendências de estoque, sabemos o impacto adicional de 0.16 min/loop. 
2.  Caso a reserva atrase para ser "*colocada em curso*", observar de perto as ondas sem "Atualização de estoque" detectada no log, limitando loops para que a operação física atue abastecendo a linha.
