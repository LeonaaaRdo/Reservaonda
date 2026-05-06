"""
Extrator completo de variáveis das ondas dos logs DynamicReservations.
Varre todos os arquivos de log em múltiplos diretórios e extrai:
- wave_id, start_time, end_time, duration_seconds
- total_orders, orders_complete, orders_pending
- total_reservations (linhas "Reservando X unidades")
- total_units_reserved (soma das unidades reservadas)
- total_missing_units (soma de "Unid. Faltantes")
- unique_items_reserved, unique_items_missing
- unique_positions, unique_zones
- total_volumes (soma de volumes PKL)
- total_pkl_created (contagem de PKLs)
- avg_time_per_order (duration / total_orders)
- distinct_missing_items (itens únicos com pendência)
- missing_lines_count (total de linhas de pendência)
"""

import re
import os
import json
import csv
from datetime import datetime, timedelta
from collections import defaultdict

# Diretórios de logs
LOG_DIRS = [
    r"C:\Users\leonardo.oliveira\Documents\Logs de onda\2026_03_04\DynamicReservations",
    r"C:\Users\leonardo.oliveira\Documents\Logs de onda\2026_03_05\DynamicReservations",
    r"C:\Users\leonardo.oliveira\Documents\Logs de onda\2026_03_06\DynamicReservations",
    r"C:\Users\leonardo.oliveira\Documents\Logs de onda\2026_05_06\DynamicReservations",
]

# Regex patterns
RE_TIME = re.compile(r'^\[(\d{2}:\d{2}:\d{2}\.\d{3})\]')
RE_WAVE_START = re.compile(r'Iniciando reserva da onda (\d+)')
RE_WAVE_END = re.compile(r'Onda (\d+) reservada\.\s*(\d+)\s*ordens processadas totalmente e\s*(\d+)\s*com pend')
RE_ORDER_COMPLETE = re.compile(r'Ordem (\d+) processada completa')
RE_ORDER_PENDING = re.compile(r'Ordem (\d+) processada com pendências nas linhas:\s*\[(.+)')
RE_RESERVING = re.compile(r'Reservando (\d+) unidades da UA "(\d+)" e Item "(\d+)" da posição "([^"]+)" da zona "([^"]+)" para o pedido "(\d+)"')
RE_PKL = re.compile(r'Criando PKL da zona de? (.+?) com (\d+) volume\(s\) para o pedido "(\d+)"')
RE_MISSING = re.compile(r'Item:\s*(\d+);.*?Unid\. Faltantes:\s*(\d+)')

def parse_time(ts_str):
    """Parse HH:MM:SS.mmm to timedelta"""
    h, m, rest = ts_str.split(':')
    s, ms = rest.split('.')
    return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

def get_sorted_files(directories):
    """Get all log files sorted by name (chronological)"""
    files = []
    for d in directories:
        if not os.path.exists(d):
            print(f"WARN: Directory not found: {d}")
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.txt'):
                files.append(os.path.join(d, f))
    return sorted(files, key=lambda x: os.path.basename(x))

def extract_date_from_filename(filepath):
    """Extract date string from filename like DynamicReservations_2026030407.txt"""
    base = os.path.basename(filepath)
    m = re.search(r'(\d{8})\d{2}\.txt', base)
    if m:
        ds = m.group(1)
        return f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}"
    return "unknown"

def process_all_logs():
    files = get_sorted_files(LOG_DIRS)
    print(f"Total de arquivos de log encontrados: {len(files)}")
    
    # State machine for tracking waves
    waves = {}  # wave_id -> wave_data
    current_wave = None
    current_wave_data = None
    current_date = None
    
    for filepath in files:
        file_date = extract_date_from_filename(filepath)
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                time_match = RE_TIME.match(line)
                if not time_match:
                    # Continuation line (multi-line pending items)
                    if current_wave_data and RE_MISSING.search(line):
                        for mm in RE_MISSING.finditer(line):
                            item_id = mm.group(1)
                            missing_qty = int(mm.group(2))
                            current_wave_data['total_missing_units'] += missing_qty
                            current_wave_data['missing_items_set'].add(item_id)
                            current_wave_data['missing_lines_count'] += 1
                    continue
                
                ts_str = time_match.group(1)
                
                # Check wave start
                ws = RE_WAVE_START.search(line)
                if ws:
                    wave_id = int(ws.group(1))
                    current_wave = wave_id
                    current_date = file_date
                    current_wave_data = {
                        'wave_id': wave_id,
                        'date': file_date,
                        'start_time': ts_str,
                        'end_time': None,
                        'start_td': parse_time(ts_str),
                        'end_td': None,
                        'total_orders': 0,
                        'orders_complete': 0,
                        'orders_pending': 0,
                        'total_reservations': 0,
                        'total_units_reserved': 0,
                        'total_missing_units': 0,
                        'unique_items_reserved': set(),
                        'unique_items_missing': set(),
                        'unique_positions': set(),
                        'unique_zones': set(),
                        'unique_orders': set(),
                        'total_volumes': 0,
                        'total_pkl': 0,
                        'missing_items_set': set(),
                        'missing_lines_count': 0,
                        'order_times': [],  # timestamps per order
                        'reservations_per_order': defaultdict(int),
                        'units_per_order': defaultdict(int),
                    }
                    waves[wave_id] = current_wave_data
                    continue
                
                if current_wave_data is None:
                    continue
                
                # Check wave end
                we = RE_WAVE_END.search(line)
                if we:
                    wid = int(we.group(1))
                    if wid == current_wave:
                        current_wave_data['end_time'] = ts_str
                        current_wave_data['end_td'] = parse_time(ts_str)
                        oc = int(we.group(2))
                        op = int(we.group(3))
                        current_wave_data['orders_complete'] = oc
                        current_wave_data['orders_pending'] = op
                        current_wave_data['total_orders'] = oc + op
                        current_wave = None
                        current_wave_data = None
                    continue
                
                # Check reservation
                rv = RE_RESERVING.search(line)
                if rv:
                    qty = int(rv.group(1))
                    item_id = rv.group(3)
                    position = rv.group(4)
                    zone = rv.group(5)
                    order_id = rv.group(6)
                    
                    current_wave_data['total_reservations'] += 1
                    current_wave_data['total_units_reserved'] += qty
                    current_wave_data['unique_items_reserved'].add(item_id)
                    current_wave_data['unique_positions'].add(position)
                    current_wave_data['unique_zones'].add(zone)
                    current_wave_data['reservations_per_order'][order_id] += 1
                    current_wave_data['units_per_order'][order_id] += qty
                    continue
                
                # Check order complete
                oc = RE_ORDER_COMPLETE.search(line)
                if oc:
                    order_id = oc.group(1)
                    current_wave_data['unique_orders'].add(order_id)
                    current_wave_data['order_times'].append(parse_time(ts_str))
                    continue
                
                # Check order pending
                op = RE_ORDER_PENDING.search(line)
                if op:
                    order_id = op.group(1)
                    pending_text = op.group(2)
                    current_wave_data['unique_orders'].add(order_id)
                    current_wave_data['order_times'].append(parse_time(ts_str))
                    
                    for mm in RE_MISSING.finditer(pending_text):
                        item_id = mm.group(1)
                        missing_qty = int(mm.group(2))
                        current_wave_data['total_missing_units'] += missing_qty
                        current_wave_data['missing_items_set'].add(item_id)
                        current_wave_data['missing_lines_count'] += 1
                    continue
                
                # Check PKL
                pk = RE_PKL.search(line)
                if pk:
                    volumes = int(pk.group(2))
                    current_wave_data['total_volumes'] += volumes
                    current_wave_data['total_pkl'] += 1
                    continue
    
    return waves

def compute_derived_features(waves):
    """Compute derived features for each wave"""
    results = []
    
    for wid, w in sorted(waves.items()):
        if w['end_td'] is None or w['start_td'] is None:
            print(f"  SKIP wave {wid}: incomplete (no end marker)")
            continue
        
        # Handle day crossover
        duration_td = w['end_td'] - w['start_td']
        if duration_td.total_seconds() < 0:
            duration_td += timedelta(days=1)
        duration_sec = duration_td.total_seconds()
        
        total_orders = w['total_orders']
        if total_orders == 0:
            total_orders = len(w['unique_orders'])
        
        if total_orders == 0:
            print(f"  SKIP wave {wid}: 0 orders")
            continue
        
        # Avg time between orders
        order_times = sorted(w['order_times'])
        intervals = []
        for i in range(1, len(order_times)):
            diff = (order_times[i] - order_times[i-1]).total_seconds()
            if diff > 0:
                intervals.append(diff)
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        
        # Reservations per order stats
        res_per_order = list(w['reservations_per_order'].values())
        avg_res_per_order = sum(res_per_order) / len(res_per_order) if res_per_order else 0
        max_res_per_order = max(res_per_order) if res_per_order else 0
        
        # Units per order stats
        units_per_order = list(w['units_per_order'].values())
        avg_units_per_order = sum(units_per_order) / len(units_per_order) if units_per_order else 0
        
        row = {
            'wave_id': wid,
            'date': w['date'],
            'start_time': w['start_time'],
            'end_time': w['end_time'],
            'duration_sec': round(duration_sec, 3),
            'total_orders': total_orders,
            'orders_complete': w['orders_complete'],
            'orders_pending': w['orders_pending'],
            'pct_pending': round(w['orders_pending'] / total_orders * 100, 1) if total_orders else 0,
            'total_reservations': w['total_reservations'],
            'total_units_reserved': w['total_units_reserved'],
            'total_missing_units': w['total_missing_units'],
            'unique_items_reserved': len(w['unique_items_reserved']),
            'unique_items_missing': len(w['missing_items_set']),
            'unique_positions': len(w['unique_positions']),
            'unique_zones': len(w['unique_zones']),
            'total_volumes': w['total_volumes'],
            'total_pkl': w['total_pkl'],
            'missing_lines_count': w['missing_lines_count'],
            'avg_time_per_order': round(duration_sec / total_orders, 4),
            'avg_interval_between_orders': round(avg_interval, 4),
            'avg_reservations_per_order': round(avg_res_per_order, 2),
            'max_reservations_per_order': max_res_per_order,
            'avg_units_per_order': round(avg_units_per_order, 1),
        }
        results.append(row)
    
    return results

def main():
    print("=" * 70)
    print("EXTRATOR DE VARIÁVEIS DAS ONDAS - DynamicReservations")
    print("=" * 70)
    
    waves = process_all_logs()
    print(f"\nOndas encontradas: {len(waves)}")
    for wid in sorted(waves.keys()):
        w = waves[wid]
        status = "COMPLETA" if w['end_td'] else "INCOMPLETA"
        print(f"  Onda {wid}: {status} | Orders: {w['total_orders']} | Start: {w['start_time']}")
    
    results = compute_derived_features(waves)
    
    # Save CSV
    out_csv = os.path.join(os.path.dirname(__file__), 'waves_full_dataset.csv')
    if results:
        fieldnames = list(results[0].keys())
        with open(out_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nDataset salvo: {out_csv}")
    
    # Print table
    print("\n" + "=" * 70)
    print("DATASET COMPLETO:")
    print("=" * 70)
    for r in results:
        print(f"\n--- Onda {r['wave_id']} ({r['date']}) ---")
        for k, v in r.items():
            print(f"  {k:35s} = {v}")
    
    # Print summary for regression
    print("\n" + "=" * 70)
    print("TABELA RESUMO PARA REGRESSÃO:")
    print("=" * 70)
    header = f"{'Wave':>6} {'Orders':>7} {'Compl':>6} {'Pend':>6} {'%Pend':>6} {'Reserv':>7} {'UndRes':>8} {'UndFalt':>8} {'ItRes':>5} {'ItFalt':>6} {'Pos':>4} {'Vols':>6} {'PKLs':>5} {'MissLn':>6} {'AvgR/O':>6} {'AvgU/O':>7} {'T(seg)':>8} {'seg/ord':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['wave_id']:>6} {r['total_orders']:>7} {r['orders_complete']:>6} {r['orders_pending']:>6} {r['pct_pending']:>5.1f}% {r['total_reservations']:>7} {r['total_units_reserved']:>8} {r['total_missing_units']:>8} {r['unique_items_reserved']:>5} {r['unique_items_missing']:>6} {r['unique_positions']:>4} {r['total_volumes']:>6} {r['total_pkl']:>5} {r['missing_lines_count']:>6} {r['avg_reservations_per_order']:>6.2f} {r['avg_units_per_order']:>7.1f} {r['duration_sec']:>8.1f} {r['avg_time_per_order']:>8.4f}")

if __name__ == '__main__':
    main()
