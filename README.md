# 💰 Sistema Financeiro Finco

Sistema de controle financeiro com dashboard, gestão de caixa (Miller-Orr) e automações.

## 🎨 Visual
- Cores: Verde `#00AE78` | Azul `#00BAE2`
- Layout limpo e profissional
- Responsivo

## 📋 Funcionalidades

### ✅ Fase 1 - Implementado
- [x] Banco de dados SQLite
- [x] Importação automática das planilhas Excel
- [x] CRUD de lançamentos (criar, ler, editar, excluir)
- [x] Filtros por tipo, categoria, classificação, situação, mês
- [x] Status BAIXADA / NÃO BAIXADA
- [x] Autocomplete de itens/fornecedores
- [x] Dashboard com indicadores
- [x] Gráficos de evolução mensal e top despesas
- [x] Indicador Miller-Orr (gestão de caixa)
- [x] Alertas visuais de caixa baixo/alto
- [x] API REST completa

### 🔜 Próximas Fases
- [ ] Fluxo de caixa diário
- [ ] Relatórios detalhados
- [ ] Exportação Excel
- [ ] Backup automático

## 🚀 Como Usar

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

1. **Extraia os arquivos** para uma pasta de sua preferência

2. **Coloque suas planilhas** na pasta `data/`:
   - `CONTROLE_DE_ENTRADAS_E_SAÍDAS_25.xlsx`
   - `FLUXO_DE_CAIXA_25.xlsx`

3. **Coloque a logo** da Finco em `frontend/assets/`:
   - `logo-finco.png`

4. **Execute o sistema:**

   **Windows:**
   ```
   Dê duplo clique em iniciar.bat
   ```

   **Linux/Mac:**
   ```bash
   chmod +x iniciar.sh
   ./iniciar.sh
   ```

5. **Acesse no navegador:**
   - http://localhost:8000

### Importar Dados das Planilhas

Se você ainda não importou os dados:

```bash
cd backend
python importador.py
```

## 📁 Estrutura de Pastas

```
sistema-financeiro-finco/
├── backend/
│   ├── main.py           # API FastAPI
│   ├── database.py       # Modelos do banco
│   └── importador.py     # Importador de planilhas
├── frontend/
│   ├── index.html        # Dashboard
│   ├── lancamentos.html  # Gestão de lançamentos
│   ├── css/
│   │   └── style.css     # Estilos
│   ├── js/
│   │   ├── api.js        # Cliente API
│   │   ├── dashboard.js  # Lógica do dashboard
│   │   └── lancamentos.js # Lógica de lançamentos
│   └── assets/
│       └── logo-finco.png
├── data/
│   ├── financeiro_finco.db  # Banco de dados
│   └── [planilhas Excel]
├── requirements.txt
├── iniciar.sh           # Script Linux/Mac
├── iniciar.bat          # Script Windows
└── README.md
```

## 🔧 API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/dashboard` | Dados do dashboard |
| GET | `/api/lancamentos` | Listar lançamentos |
| POST | `/api/lancamentos` | Criar lançamento |
| PUT | `/api/lancamentos/{id}` | Atualizar lançamento |
| DELETE | `/api/lancamentos/{id}` | Excluir lançamento |
| PATCH | `/api/lancamentos/{id}/baixar` | Alternar situação |
| GET | `/api/classificacoes` | Listar classificações |
| GET | `/api/autocomplete/itens` | Buscar itens |
| GET | `/api/fluxo-caixa` | Fluxo de caixa |
| GET | `/api/configuracoes` | Configurações |

## 📊 Miller-Orr

O sistema implementa o modelo Miller-Orr para gestão de caixa:

- **Mínimo**: R$ 55.000 (abaixo disso = alerta vermelho)
- **Ponto de Retorno**: R$ 100.000 (ideal)
- **Máximo**: R$ 355.000 (acima disso = considerar investir)

## 🎯 Classificações Disponíveis

### Custos (Produção)
- **Fixos**: Salários Fábrica, Aluguel, Manutenção, etc.
- **Variáveis**: Matéria-Prima, Componentes, Anodização, etc.

### Despesas (Administrativo)
- **Fixas**: Contabilidade, Limpeza, Assistência Médica, etc.
- **Variáveis**: Comissão de Vendas, Fretes, Correio, etc.

### Outros
- **Impostos**: ICMS, COFINS, IRPJ, FGTS, etc.
- **Financeiro**: Juros, Tarifas, Empréstimos, etc.
- **Investimento**: Máquinas, Softwares, TI, etc.

## 📞 Suporte

Desenvolvido para Finco Ind. Com. Ltda.

---

**Versão**: 1.0.0  
**Data**: Dezembro 2025
