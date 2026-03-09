# ✅ Boas Práticas de Programação — Projeto Reservaonda

Guia de boas práticas adotadas neste projeto para manutenção e evolução do código.

---

## 🐍 Python (`parse_logs.py`, `train_model.py`)

### Nomenclatura
- **Variáveis e funções**: `snake_case` → `parse_time()`, `waves_data`
- **Constantes**: `MAIUSCULO` → `BASE_LOG_DIR`, `CSV_OUTPUT`
- **Classes**: `PascalCase` → `WaveData`

### Estrutura
```python
# ✅ Bom: constantes no topo, separadas da lógica
BASE_LOG_DIR = r"c:\Users\...\Logs de onda"
CSV_OUTPUT   = os.path.join(BASE_LOG_DIR, "waves_data.csv")

# ✅ Bom: funções pequenas com uma responsabilidade
def parse_time(time_str: str) -> datetime:
    """Converte string HH:MM:SS.mmm para datetime."""
    return datetime.strptime("2000-01-01 " + time_str, "%Y-%m-%d %H:%M:%S.%f")
```

### Comentários
```python
# ✅ Explique o PORQUÊ, não o QUE
# A engine processa ~1 ordem a cada 6.86 seg (validado em 8 ondas reais)
MIN_POR_ORDEM = 6.86 / 60

# ❌ Ruim: comentário óbvio
# Divide 6.86 por 60
MIN_POR_ORDEM = 6.86 / 60
```

### Tratamento de Erros
```python
# ✅ Sempre use encoding explícito ao abrir arquivos de log
with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    ...
```

---

## 🌐 HTML/JavaScript (`previsao_onda.html`)

### Organização
- CSS no `<head>`, JavaScript no final do `<body>`
- IDs descritivos: `id="ordens"`, `id="resultTime"`
- Use variáveis `const`/`let` em vez de `var`

### Fórmula documentada no código
```javascript
// Constante validada contra 8 ondas reais — erro médio: 0.5%
// Fonte: DynamicReservations logs, onda 24626 (105 ordens → 12 min)
const MIN_POR_ORDEM = 6.86 / 60;
```

---

## 📁 Arquivos e Diretórios

| Arquivo | Responsabilidade |
|---|---|
| `parse_logs.py` | **Somente** leitura e extração de dados dos logs |
| `train_model.py` | **Somente** análise estatística e geração da fórmula |
| `previsao_onda.html` | **Somente** interface do usuário |
| `waves_data.csv` | Dados intermediários (gerado automaticamente) |

> **Regra:** Cada arquivo tem uma responsabilidade única. Não misture lógica de parsing com lógica de apresentação.

---

## 🔄 Integração Contínua (Git)

### Antes de cada commit
1. Teste o script: `py -3 parse_logs.py`
2. Abra o HTML no navegador e verifique o cálculo
3. Documente o que mudou na mensagem do commit

### Nunca commitar
- Tokens e senhas (use variáveis de ambiente)
- Logs de produção (já no `.gitignore`)
- Arquivos `*.pyc`

---

## 🔐 Segurança

```bash
# ❌ NUNCA faça isso:
TOKEN = "ghp_xxxxxxxxxxxxx"  # hardcoded no código

# ✅ Use variável de ambiente:
import os
TOKEN = os.environ.get("GITHUB_TOKEN")
```

Configure no Windows:
```powershell
$env:GITHUB_TOKEN = "seu_token_aqui"
```
