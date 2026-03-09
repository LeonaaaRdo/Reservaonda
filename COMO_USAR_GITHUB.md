# 📘 Como Usar o GitHub neste Projeto

Este guia explica os comandos básicos para manter o repositório **Reservaonda** atualizado.

---

## 🔧 Configuração Inicial (feita uma vez)

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

---

## 📋 Fluxo Diário

### 1. Ver o que mudou
```bash
git status
```

### 2. Adicionar arquivos alterados
```bash
# Adicionar um arquivo específico
git add previsao_onda.html

# Adicionar tudo de uma vez
git add .
```

### 3. Confirmar as mudanças (commit)
```bash
git commit -m "Descreva o que você fez aqui"
```

> **Boas mensagens de commit:**
> - ✅ `"Atualiza formula de previsao para 6.86 seg/ordem"`
> - ✅ `"Corrige parser para capturar total de ordens da linha final"`
> - ❌ `"mudancas"` ou `"update"`

### 4. Enviar para o GitHub
```bash
git push origin main
```

### 5. Baixar atualizações do GitHub
```bash
git pull origin main
```

---

## 🔍 Comandos Úteis

| Comando | O que faz |
|---|---|
| `git log --oneline -10` | Ver os últimos 10 commits |
| `git diff` | Ver o que mudou antes de fazer commit |
| `git restore <arquivo>` | Desfazer alterações em um arquivo |
| `git stash` | Guardar mudanças temporariamente |
| `git stash pop` | Recuperar mudanças guardadas |

---

## 🔐 Autenticação

O projeto usa um **Personal Access Token (PAT)** do GitHub para autenticar.

> ⚠️ **NUNCA compartilhe seu token em código ou mensagens.** Guarde-o em local seguro.

Para configurar o token localmente (só precisa fazer uma vez):
```bash
git remote set-url origin https://<SEU_TOKEN>@github.com/LeonaaaRdo/Reservaonda.git
```

---

## 🌿 Branches (Ramificações)

Para trabalhar em novas funcionalidades sem afetar o código principal:

```bash
# Criar e entrar em uma branch nova
git checkout -b feature/nova-funcionalidade

# Voltar para a branch principal
git checkout main

# Mesclar a branch na principal
git merge feature/nova-funcionalidade
```

---

## 📂 Estrutura do Repositório

```
Reservaonda/
├── previsao_onda.html      # Interface web de previsão
├── parse_logs.py           # Parser dos logs DynamicReservations
├── train_model.py          # Script de treinamento do modelo
├── waves_data.csv          # Dados extraídos dos logs
├── dynamicreservation.txt  # Amostra de log para referência
├── Resultados_Previsao_Ondas.md  # Relatório de análise
├── COMO_USAR_GITHUB.md     # Este guia
└── BOAS_PRATICAS.md        # Boas práticas de código
```
