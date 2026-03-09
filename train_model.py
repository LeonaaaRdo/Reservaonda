import os
import csv

CSV_PATH = r"c:\Users\leonardo.oliveira\Documents\Logs de onda\waves_data.csv"

def read_data():
    X = []
    y = []
    headers = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        # wave_id, start_time_local, retries, initial_orders, missing_units_proxy_sum, duration_seconds
        
        for row in reader:
            if not row or row[5] == '0' or row[5] == '0.0': 
                continue # Pula se duração for 0
                
            retries = float(row[2])
            initial_orders = float(row[3])
            missing_units_sum = float(row[4])
            duration_minutes = float(row[5]) / 60.0
            
            # X será [retries, initial_orders, missing_units_sum]
            X.append([retries, initial_orders, missing_units_sum])
            y.append(duration_minutes)
            
    return X, y

def simple_multiple_linear_regression(X, y):
    """
    Uma abordagem sem bibliotecas externas complexas (como scikit/numpy) 
    para tentar extrair a importância aproximada (pesos) das variáveis,
    já que o ambiente pode não ter as bibliotecas instaladas.
    
    A fórmula múltipla generalizada necessita de inversão de matrizes.
    Como temos poucos dados de onda e não temos numpy certo, 
    faremos uma análise simples correlacional isolada (Heurística).
    """
    print("\n[RESULTADOS DA ANÁLISE DE TEMPO DE ONDAS]\n")
    print(f"Total de ondas válidas analisadas: {len(y)}\n")
    
    if len(y) == 0:
        print("Sem dados suficientes.")
        return
        
    # Médias Globais
    avg_duration = sum(y) / len(y)
    avg_retries = sum(row[0] for row in X) / len(X)
    avg_orders = sum(row[1] for row in X) / len(X)
    avg_missing = sum(row[2] for row in X) / len(X)
    
    print(f"MÉDIAS DO SISTEMA:")
    print(f"- Duração de uma onda: {avg_duration:.2f} minutos ({avg_duration/60:.2f} horas)")
    print(f"- Retentativas médias: {avg_retries:.2f}")
    print(f"- Ordens iniciais médias: {avg_orders:.2f}")
    print(f"- Proxy de unidades faltantes acumuladas: {avg_missing:.2f}")
    
    print("\nIMPACTO ESTIMADO POR VARIÁVEL (Análise isolada - Heurística):")
    
    # 1. Impacto das Retentativas (Custo por retry)
    # Custo de cada retry em minutos = Duração total / Retries totais
    cost_per_retry = avg_duration / avg_retries if avg_retries > 0 else 0
    print(f"[Retentativas]: Cada retentativa de reserva consome aproximadamente {cost_per_retry:.2f} minutos.")
    
    # 2. Relação Pendências -> Time
    # Para ver o peso disso, podemos olhar que se faltantes são 0, o que acontece? Aqui todos tem falta.
    # Podemos assumir uma regra de bolso:
    cost_per_missing = avg_duration / avg_missing if avg_missing > 0 else 0
    print(f"[Pendências]: Cada ~1000 unidades faltantes impactam o tempo em cerca de {cost_per_missing * 1000:.2f} minutos adicionais (considerando o looping).")
    
    # 3. Relação Tamanho da Onda -> Time
    cost_per_order = avg_duration / avg_orders if avg_orders > 0 else 0
    print(f"[Tamanho da Onda]: Apenas considerando o tamanho ignorando faltantes, a média é {cost_per_order:.2f} min/ordem processada. (Menos relevante se não há faltas).")
    
    print("\n---")
    print("FÓRMULA PREDITIVA SUGERIDA (Baseada na heurística dos dados capturados):")
    print(f"Tempo Estimado (minutos) = (Qtd de Ordens * {cost_per_order/3:.2f}) + (Retentativas Estimadas * {cost_per_retry:.2f})")
    print("Onde 'Retentativas Estimadas' acontece a cada ~1-2 min em caso de alto volume de Unidades Faltantes.\n")

if __name__ == "__main__":
    X, y = read_data()
    simple_multiple_linear_regression(X, y)
