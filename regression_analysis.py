"""
Regressão multivariável para encontrar a função que descreve o tempo
de reserva de uma onda com erro tendendo a zero.

Testa múltiplos modelos:
1. Regressão linear simples (T = a*orders + b)
2. Regressão linear múltipla (com todas variáveis)
3. Regressão polinomial
4. Modelo com termos de interação
5. Busca exaustiva do melhor subconjunto

Usa os dados do waves_full_dataset.csv
"""

import csv
import os
import math
from itertools import combinations

def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), 'waves_full_dataset.csv')
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            row = {}
            for k, v in r.items():
                try:
                    row[k] = float(v)
                except:
                    row[k] = v
            rows.append(row)
    return rows

# ---- Minimal linear algebra (no numpy needed) ----

def mat_mult(A, B):
    """Multiply matrices A (m×n) × B (n×p) = C (m×p)"""
    m, n = len(A), len(A[0])
    p = len(B[0])
    C = [[0.0]*p for _ in range(m)]
    for i in range(m):
        for j in range(p):
            s = 0.0
            for k in range(n):
                s += A[i][k] * B[k][j]
            C[i][j] = s
    return C

def mat_transpose(A):
    m, n = len(A), len(A[0])
    return [[A[i][j] for i in range(m)] for j in range(n)]

def mat_inverse(M):
    """Gauss-Jordan inverse for small matrices"""
    n = len(M)
    A = [row[:] + [1.0 if i==j else 0.0 for j in range(n)] for i, row in enumerate(M)]
    for col in range(n):
        max_row = max(range(col, n), key=lambda r: abs(A[r][col]))
        A[col], A[max_row] = A[max_row], A[col]
        pivot = A[col][col]
        if abs(pivot) < 1e-12:
            return None
        for j in range(2*n):
            A[col][j] /= pivot
        for row in range(n):
            if row != col:
                factor = A[row][col]
                for j in range(2*n):
                    A[row][j] -= factor * A[col][j]
    return [row[n:] for row in A]

def ols_fit(X_data, y_data):
    """Ordinary Least Squares: beta = (X'X)^-1 X'y
    X_data: list of feature vectors (each row is a sample)
    y_data: list of target values
    Returns: coefficients, r_squared, rmse, max_error, predictions
    """
    n = len(y_data)
    p = len(X_data[0])
    
    # Add intercept column
    X = [[1.0] + list(row) for row in X_data]
    p1 = p + 1
    
    Xt = mat_transpose(X)
    XtX = mat_mult(Xt, X)
    XtX_inv = mat_inverse(XtX)
    if XtX_inv is None:
        return None
    
    y_col = [[y] for y in y_data]
    Xty = mat_mult(Xt, y_col)
    beta = mat_mult(XtX_inv, Xty)
    beta = [b[0] for b in beta]
    
    # Predictions
    preds = []
    for row in X:
        pred = sum(b * x for b, x in zip(beta, row))
        preds.append(pred)
    
    # Metrics
    y_mean = sum(y_data) / n
    ss_tot = sum((y - y_mean)**2 for y in y_data)
    ss_res = sum((y - p)**2 for y, p in zip(y_data, preds))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    rmse = math.sqrt(ss_res / n)
    errors = [abs(y - p) for y, p in zip(y_data, preds)]
    max_err = max(errors)
    pct_errors = [abs(y - p) / y * 100 for y, p in zip(y_data, preds) if y > 0]
    max_pct = max(pct_errors) if pct_errors else 0
    mean_pct = sum(pct_errors) / len(pct_errors) if pct_errors else 0
    
    return {
        'beta': beta,
        'r2': r2,
        'rmse': rmse,
        'max_error': max_err,
        'max_pct_error': max_pct,
        'mean_pct_error': mean_pct,
        'predictions': preds,
        'errors': errors,
    }

def main():
    data = load_data()
    n = len(data)
    print(f"Ondas carregadas: {n}\n")
    
    # Target
    y = [d['duration_sec'] for d in data]
    
    # Feature candidates
    feature_names = [
        'total_orders',
        'orders_complete', 
        'orders_pending',
        'pct_pending',
        'total_reservations',
        'total_units_reserved',
        'total_missing_units',
        'unique_items_reserved',
        'unique_items_missing',
        'unique_positions',
        'total_volumes',
        'total_pkl',
        'missing_lines_count',
        'avg_reservations_per_order',
        'avg_units_per_order',
    ]
    
    all_features = {name: [d[name] for d in data] for name in feature_names}
    
    # ================================================================
    # MODEL 1: Simple linear T = a * total_orders + b
    # ================================================================
    print("=" * 70)
    print("MODELO 1: Linear simples — T = a × orders + b")
    print("=" * 70)
    X1 = [[d['total_orders']] for d in data]
    r1 = ols_fit(X1, y)
    if r1:
        print(f"  T = {r1['beta'][1]:.6f} × orders + {r1['beta'][0]:.4f}")
        print(f"  R² = {r1['r2']:.8f}")
        print(f"  RMSE = {r1['rmse']:.2f} seg")
        print(f"  Erro médio = {r1['mean_pct_error']:.2f}%")
        print(f"  Erro máximo = {r1['max_pct_error']:.2f}%")
        print(f"  Previsões:")
        for i, d in enumerate(data):
            e_pct = abs(y[i] - r1['predictions'][i]) / y[i] * 100
            print(f"    Onda {int(d['wave_id'])}: real={y[i]:.1f}s  prev={r1['predictions'][i]:.1f}s  erro={e_pct:.2f}%")
    
    # ================================================================
    # MODEL 2: T = a * orders + b * orders² (quadratic)
    # ================================================================
    print("\n" + "=" * 70)
    print("MODELO 2: Quadrático — T = a × orders² + b × orders + c")
    print("=" * 70)
    X2 = [[d['total_orders'], d['total_orders']**2] for d in data]
    r2 = ols_fit(X2, y)
    if r2:
        print(f"  T = {r2['beta'][2]:.8f} × orders² + {r2['beta'][1]:.6f} × orders + {r2['beta'][0]:.4f}")
        print(f"  R² = {r2['r2']:.8f}")
        print(f"  RMSE = {r2['rmse']:.2f} seg")
        print(f"  Erro médio = {r2['mean_pct_error']:.2f}%")
        print(f"  Erro máximo = {r2['max_pct_error']:.2f}%")
        for i, d in enumerate(data):
            e_pct = abs(y[i] - r2['predictions'][i]) / y[i] * 100
            print(f"    Onda {int(d['wave_id'])}: real={y[i]:.1f}s  prev={r2['predictions'][i]:.1f}s  erro={e_pct:.2f}%")
    
    # ================================================================
    # MODEL 3: Multi-variable — best subset search
    # ================================================================
    print("\n" + "=" * 70)
    print("MODELO 3: Busca exaustiva do melhor subconjunto de variáveis")
    print("=" * 70)
    
    best_model = None
    best_score = float('inf')
    
    # Try all combinations of 1 to 5 features
    for k in range(1, min(6, len(feature_names) + 1)):
        for combo in combinations(range(len(feature_names)), k):
            names = [feature_names[j] for j in combo]
            X = [[all_features[name][i] for name in names] for i in range(n)]
            result = ols_fit(X, y)
            if result and result['mean_pct_error'] < best_score:
                best_score = result['mean_pct_error']
                best_model = {
                    'names': names,
                    'result': result,
                    'k': k,
                }
    
    if best_model:
        r = best_model['result']
        print(f"  Melhor combinação ({best_model['k']} variáveis): {best_model['names']}")
        print(f"  R² = {r['r2']:.8f}")
        print(f"  RMSE = {r['rmse']:.2f} seg")
        print(f"  Erro médio = {r['mean_pct_error']:.2f}%")
        print(f"  Erro máximo = {r['max_pct_error']:.2f}%")
        print(f"  Coeficientes:")
        print(f"    intercept = {r['beta'][0]:.6f}")
        for j, name in enumerate(best_model['names']):
            print(f"    {name} = {r['beta'][j+1]:.8f}")
        print(f"  Previsões:")
        for i, d in enumerate(data):
            e_pct = abs(y[i] - r['predictions'][i]) / y[i] * 100
            print(f"    Onda {int(d['wave_id'])}: real={y[i]:.1f}s  prev={r['predictions'][i]:.1f}s  erro={e_pct:.2f}%")
    
    # ================================================================
    # MODEL 4: Quadratic + multi-variable (orders + orders² + best features)
    # ================================================================
    print("\n" + "=" * 70)
    print("MODELO 4: Polinomial + multivariável (busca exaustiva)")
    print("=" * 70)
    
    extra_features = [f for f in feature_names if f != 'total_orders' and f != 'orders_complete']
    
    best4 = None
    best4_score = float('inf')
    
    for k in range(0, min(4, len(extra_features) + 1)):
        combos = [()]  if k == 0 else combinations(range(len(extra_features)), k)
        for combo in combos:
            names = ['total_orders', 'total_orders²'] + [extra_features[j] for j in combo]
            X = []
            for i in range(n):
                row = [data[i]['total_orders'], data[i]['total_orders']**2]
                for j in combo:
                    row.append(all_features[extra_features[j]][i])
                X.append(row)
            result = ols_fit(X, y)
            if result and result['mean_pct_error'] < best4_score:
                best4_score = result['mean_pct_error']
                best4 = {
                    'names': names,
                    'result': result,
                }
    
    if best4:
        r = best4['result']
        print(f"  Melhor modelo: {best4['names']}")
        print(f"  R² = {r['r2']:.8f}")
        print(f"  RMSE = {r['rmse']:.2f} seg")
        print(f"  Erro médio = {r['mean_pct_error']:.2f}%")
        print(f"  Erro máximo = {r['max_pct_error']:.2f}%")
        print(f"  Coeficientes:")
        print(f"    intercept = {r['beta'][0]:.6f}")
        for j, name in enumerate(best4['names']):
            print(f"    {name} = {r['beta'][j+1]:.8f}")
        print(f"  Previsões:")
        for i, d in enumerate(data):
            e_pct = abs(y[i] - r['predictions'][i]) / y[i] * 100
            print(f"    Onda {int(d['wave_id'])}: real={y[i]:.1f}s  prev={r['predictions'][i]:.1f}s  erro={e_pct:.2f}%")
    
    # ================================================================
    # MODEL 5: Cross-products and polynomial terms
    # ================================================================
    print("\n" + "=" * 70)
    print("MODELO 5: Termos de interação orders × variáveis")
    print("=" * 70)
    
    # orders, orders², orders × pct_pending, orders × avg_reservations
    best5 = None
    best5_score = float('inf')
    
    interaction_candidates = ['pct_pending', 'orders_pending', 'total_missing_units',
                              'missing_lines_count', 'avg_reservations_per_order',
                              'unique_items_missing', 'total_reservations', 'total_units_reserved']
    
    for k in range(1, min(4, len(interaction_candidates)+1)):
        for combo in combinations(range(len(interaction_candidates)), k):
            names_direct = ['total_orders']
            names_interact = [f'orders×{interaction_candidates[j]}' for j in combo]
            all_names = names_direct + names_interact
            
            X = []
            for i in range(n):
                o = data[i]['total_orders']
                row = [o]
                for j in combo:
                    row.append(o * all_features[interaction_candidates[j]][i])
                X.append(row)
            result = ols_fit(X, y)
            if result and result['mean_pct_error'] < best5_score:
                best5_score = result['mean_pct_error']
                best5 = {'names': all_names, 'result': result, 'combo': combo}
    
    if best5:
        r = best5['result']
        print(f"  Melhor modelo: {best5['names']}")
        print(f"  R² = {r['r2']:.8f}")
        print(f"  RMSE = {r['rmse']:.2f} seg")
        print(f"  Erro médio = {r['mean_pct_error']:.2f}%")
        print(f"  Erro máximo = {r['max_pct_error']:.2f}%")
        print(f"  Coeficientes:")
        print(f"    intercept = {r['beta'][0]:.6f}")
        for j, name in enumerate(best5['names']):
            print(f"    {name} = {r['beta'][j+1]:.10f}")
        print(f"  Previsões:")
        for i, d in enumerate(data):
            e_pct = abs(y[i] - r['predictions'][i]) / y[i] * 100
            print(f"    Onda {int(d['wave_id'])}: real={y[i]:.1f}s  prev={r['predictions'][i]:.1f}s  erro={e_pct:.2f}%")
    
    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    print("\n" + "=" * 70)
    print("RESUMO COMPARATIVO DOS MODELOS")
    print("=" * 70)
    models = [
        ("1. Linear simples", r1),
        ("2. Quadrático", r2),
        ("3. Melhor subconjunto", best_model['result'] if best_model else None),
        ("4. Polinomial+multi", best4['result'] if best4 else None),
        ("5. Interação", best5['result'] if best5 else None),
    ]
    
    print(f"{'Modelo':<25s} {'R²':>10s} {'RMSE':>10s} {'Err.Méd%':>10s} {'Err.Max%':>10s}")
    print("-" * 65)
    for name, r in models:
        if r:
            print(f"{name:<25s} {r['r2']:>10.6f} {r['rmse']:>10.2f} {r['mean_pct_error']:>10.4f} {r['max_pct_error']:>10.4f}")

if __name__ == '__main__':
    main()
