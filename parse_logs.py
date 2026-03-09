import os
import re
import csv
from collections import defaultdict
from datetime import datetime

# Diretório base dos logs
BASE_LOG_DIR = r"c:\Users\leonardo.oliveira\Documents\Logs de onda"
CSV_OUTPUT = os.path.join(BASE_LOG_DIR, "waves_data.csv")

# Padrões de Regex (baseados no log do WMS)
# [07:38:40.358] Iniciando reserva da onda 24619
REGEX_WAVE_START = re.compile(r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\] Iniciando reserva da onda (\d+)")

# [07:53:20.661] Onda 24619 reservada. 102 ordens processadas totalmente e 27 com pendências.
REGEX_WAVE_END = re.compile(r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\] Onda (\d+) reservada\.")
REGEX_WAVE_END_FULL = re.compile(r"Onda (\d+) reservada\. (\d+) ordens processadas totalmente e (\d+) com pend")

# [10:01:23.578] Tentando reservar novamente a onda 24619
REGEX_WAVE_RETRY = re.compile(r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\] Tentando reservar novamente a onda (\d+)")

# [10:01:23.951] Ordens pendentes da onda 24619: 9 [4332016,...]
REGEX_PENDING_ORDERS = re.compile(r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\] Ordens pendentes da onda (\d+): (\d+) ")

# [10:01:30.502] Ordem 4332016 processada com pendências nas linhas: [...] Unid. Faltantes: 480]
REGEX_MISSING_UNITS = re.compile(r"Unid\. Faltantes:\s*(\d+)")

# [10:01:23.539] Recalculating InventoryGlobal
REGEX_RECALC = re.compile(r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\] Recalculating InventoryGlobal")

def parse_time(time_str):
    """Converte a hora do log para objeto datetime para cálular duração, usando data de referência base."""
    # Assumimos uma data base apenas para calcular deltas
    return datetime.strptime("2000-01-01 " + time_str, "%Y-%m-%d %H:%M:%S.%f")

def process_logs():
    print("Iniciando varredura e extração de dados dos logs de DynamicReservations...")
    
    # Estrutura para armazenar dados por onda (wave_id)
    # Ex: { '24619': {'start': dt, 'end': dt, 'retries': 5, 'missing_units_sum': 1000, 'initial_orders': 9, 'recalcs': 2} }
    waves_data = defaultdict(lambda: {
        'start': None, 
        'end': None, 
        'retries': 0, 
        'missing_units_sum': 0, 
        'initial_orders': 0,  # total de ordens (completas + pendentes) - obtido da linha final
        'ordens_completas': 0,
        'ordens_pendentes': 0,
        'has_ended' : False
    })
    
    total_recalcs_in_period = 0

    # Percorrer dirs de data
    for item in sorted(os.listdir(BASE_LOG_DIR)):
        item_path = os.path.join(BASE_LOG_DIR, item)
        if os.path.isdir(item_path) and re.match(r"^\d{4}_\d{2}_\d{2}$", item):
            dyn_path = os.path.join(item_path, "DynamicReservations")
            if os.path.exists(dyn_path):
                # Ler os arquivos por hora, ordenados
                log_files = sorted([f for f in os.listdir(dyn_path) if f.startswith("DynamicReservations") and f.endswith(".txt")])
                
                for log_file in log_files:
                    file_path = os.path.join(dyn_path, log_file)
                    print(f"Processando arquivo: {file_path}")
                    
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        
                        # Processamento linha a linha
                        for line in lines:
                            # 1. Checa recálculo global
                            if REGEX_RECALC.search(line):
                                total_recalcs_in_period += 1
                                continue
                                
                            # NOVO: Início e Fim exatos
                            m_start = REGEX_WAVE_START.search(line)
                            if m_start:
                                t_str, wave_id = m_start.groups()
                                if waves_data[wave_id]['start'] is None:
                                    waves_data[wave_id]['start'] = parse_time(t_str)
                                continue
                                
                            m_end = REGEX_WAVE_END.search(line)
                            if m_end:
                                t_str, wave_id = m_end.groups()
                                waves_data[wave_id]['end'] = parse_time(t_str)
                                # Tenta extrair contagem de ordens da linha completa
                                m_full = REGEX_WAVE_END_FULL.search(line)
                                if m_full:
                                    wid2, completas, pendentes = m_full.groups()
                                    total = int(completas) + int(pendentes)
                                    waves_data[wave_id]['initial_orders'] = total
                                    waves_data[wave_id]['ordens_completas'] = int(completas)
                                    waves_data[wave_id]['ordens_pendentes'] = int(pendentes)
                                continue
                                
                            # 2. Checa retentativa de onda para contagem (independente do marco de tempo)
                            m_retry = REGEX_WAVE_RETRY.search(line)
                            if m_retry:
                                t_str, wave_id = m_retry.groups()
                                waves_data[wave_id]['retries'] += 1
                                continue
                                
                            # 3. Checa ordens pendentes apenas para extrair o tamanho inicial
                            m_orders = REGEX_PENDING_ORDERS.search(line)
                            if m_orders:
                                t_str, wave_id, orders_count = m_orders.groups()
                                orders_count = int(orders_count)
                                
                                # Tamanho inicial logado
                                if waves_data[wave_id]['initial_orders'] == 0 and orders_count > 0:
                                    waves_data[wave_id]['initial_orders'] = orders_count
                                continue
                            
                            # 4. Checa unidades faltantes. Como são impressas após o log da ordem, 
                            # precisamos apenas de uma aproximação agregando a soma de faltas. 
                            # Nota: no futuro, podemos querer vincular exatamente à onda correta.
                            # Para fins de extração rápida, vamos atribuir as faltas à "última onda" que teve retry.
                            # (O parser pode ser aprofundado se essa métrica ficar ruidosa).
    
    # -----------------------------
    # Passagem 2 (Refino): Uma forma mais segura de atrelar as pendências a uma onda 
    # é ler as linhas em bloco. Como fizemos um "for" simples, vamos fazer uma leitura de contexto.
    print("Iniciando Passagem 2 com contexto para mapear Unid Faltantes corretamente...")
    
    current_wave = None
    
    for item in sorted(os.listdir(BASE_LOG_DIR)):
        item_path = os.path.join(BASE_LOG_DIR, item)
        if os.path.isdir(item_path) and re.match(r"^\d{4}_\d{2}_\d{2}$", item):
            dyn_path = os.path.join(item_path, "DynamicReservations")
            if os.path.exists(dyn_path):
                log_files = sorted([f for f in os.listdir(dyn_path) if f.startswith("DynamicReservations") and f.endswith(".txt")])
                for log_file in log_files:
                    with open(os.path.join(dyn_path, log_file), "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            m_retry = REGEX_WAVE_RETRY.search(line)
                            if m_retry:
                                current_wave = m_retry.group(2)
                            
                            # Se achamos unidades faltantes, atribuímos à ultima onda em contexto.
                            # Para evitar contar duplicado em cada retentativa(!), vamos apenas pegar 
                            # o pior caso ou estimar o tamanho da dor. Uma approach melhor é gravar o 'max'.
                            m_miss = REGEX_MISSING_UNITS.findall(line)
                            if m_miss and current_wave:
                                miss_count = sum(int(x) for x in m_miss)
                                # Nós vamos acumular e depois o modelo lidará com o viés,
                                # pois mais retentativas inflarão a soma natural dos itens repetidos.
                                # Isso acaba sendo uma freature combinada de (falta total no tempo)
                                waves_data[current_wave]['missing_units_sum'] += miss_count

    # Salvando em CSV
    print(f"\nEscrevendo dados agrupados em {CSV_OUTPUT}...")
    headers = ["wave_id", "start_time_local", "retries", "initial_orders", "missing_units_proxy_sum", "duration_seconds"]
    
    with open(CSV_OUTPUT, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for w_id, data in waves_data.items():
            if data['start'] and data['end']:
                duration = (data['end'] - data['start']).total_seconds()
                
                # Para evitar loops mortos que atravessaram dias, delimitamos 
                # (isso corrige discrepâncias de rollover em parse_time)
                if duration < 0:
                    duration += 86400
            else:
                duration = 0
            
            # Se a duração é 0, significa que não houveram retries cobrindo um período detectável.
            # Filtrar as que importam (com gargalos)
            writer.writerow([
                w_id,
                data['start'].strftime("%H:%M:%S") if data['start'] else "",
                data['retries'],
                data['initial_orders'],
                data['missing_units_sum'],
                duration
            ])
            
    print("Processo finalizado!")

if __name__ == "__main__":
    process_logs()
