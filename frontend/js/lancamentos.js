/**
 * Sistema Financeiro Finco - Lançamentos
 */

let classificacoesCache = [];
let timeoutAutocomplete = null;

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    carregarClassificacoes();
    configurarAutocomplete();
    
    // Verificar se veio busca global
    const buscaTermo = localStorage.getItem('busca-termo');
    if (buscaTermo) {
        document.getElementById('filtro-item').value = buscaTermo;
        document.getElementById('filtro-mes').value = '';
        localStorage.removeItem('busca-termo');
        carregarLancamentos();
    } else {
        // Definir mês atual no filtro
        const mesAtual = new Date().getMonth() + 1;
        document.getElementById('filtro-mes').value = mesAtual;
        carregarLancamentos();
    }
});

// ============================================
// CARREGAR CLASSIFICAÇÕES
// ============================================

async function carregarClassificacoes() {
    try {
        classificacoesCache = await getClassificacoes();
        
        // Popular select de filtro
        const selectFiltro = document.getElementById('filtro-classificacao');
        const selectForm = document.getElementById('lancamento-classificacao');
        
        const options = classificacoesCache.map(c => 
            `<option value="${c.nome}">${c.nome}</option>`
        ).join('');
        
        selectFiltro.innerHTML = '<option value="">Todas</option>' + options;
        selectForm.innerHTML = '<option value="">Selecione...</option>' + options;
        
    } catch (error) {
        console.error('Erro ao carregar classificações:', error);
    }
}

// ============================================
// CARREGAR LANÇAMENTOS
// ============================================

async function carregarLancamentos() {
    const filtros = obterFiltros();
    
    try {
        const lancamentos = await getLancamentos(filtros);
        renderizarTabela(lancamentos);
    } catch (error) {
        console.error('Erro ao carregar lançamentos:', error);
        document.getElementById('tabela-lancamentos').innerHTML = `
            <tr><td colspan="8" class="text-center text-muted">Erro ao carregar dados</td></tr>
        `;
    }
}

function obterFiltros() {
    return {
        tipo: document.getElementById('filtro-tipo').value,
        categoria: document.getElementById('filtro-categoria').value,
        classificacao: document.getElementById('filtro-classificacao').value,
        situacao: document.getElementById('filtro-situacao').value,
        ano: document.getElementById('filtro-ano').value,
        mes: document.getElementById('filtro-mes').value,
        dia: document.getElementById('filtro-dia').value,
        item: document.getElementById('filtro-item').value,
        limit: 500
    };
}

function filtrarLancamentos() {
    carregarLancamentos();
}

function limparFiltros() {
    document.getElementById('filtro-tipo').value = '';
    document.getElementById('filtro-categoria').value = '';
    document.getElementById('filtro-classificacao').value = '';
    document.getElementById('filtro-situacao').value = '';
    document.getElementById('filtro-ano').value = new Date().getFullYear();
    document.getElementById('filtro-mes').value = '';
    document.getElementById('filtro-dia').value = '';
    document.getElementById('filtro-item').value = '';
    carregarLancamentos();
}

// ============================================
// RENDERIZAR TABELA
// ============================================

function renderizarTabela(lancamentos) {
    const tbody = document.getElementById('tabela-lancamentos');
    const contador = document.getElementById('contador-lancamentos');
    
    contador.textContent = `${lancamentos.length} registros`;
    
    if (lancamentos.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="8" class="text-center text-muted">Nenhum lançamento encontrado</td></tr>
        `;
        return;
    }
    
    tbody.innerHTML = lancamentos.map(l => {
        const tipoLabel = l.tipo === 'ENTRADA' ? 'A receber' : 'A pagar';
        const tipoBadgeClass = l.tipo === 'ENTRADA' ? 'entrada' : 'saida';
        const situacaoClasse = obterClasseSituacao(l.situacao);
        const situacaoLabel = obterLabelSituacao(l.situacao);
        
        // Debug - remover depois
        console.log(`ID ${l.id}: situacao="${l.situacao}" -> label="${situacaoLabel}"`);
        
        return `
        <tr data-id="${l.id}">
            <td>${formatarData(l.data)}</td>
            <td>
                <span class="badge badge-${tipoBadgeClass}">
                    ${tipoLabel}
                </span>
            </td>
            <td>
                <span class="badge badge-${l.categoria.toLowerCase()}">
                    ${l.categoria}
                </span>
            </td>
            <td>${l.classificacao_nome || '-'}</td>
            <td>${l.item || '-'}</td>
            <td class="text-right ${l.tipo === 'ENTRADA' ? 'valor-positivo' : 'valor-negativo'}">
                ${formatarMoeda(l.valor)}
            </td>
            <td>
                <span class="badge ${situacaoClasse}"
                      style="cursor: pointer" onclick="abrirMenuSituacao(${l.id}, '${l.situacao}')" title="Clique para alterar">
                    ${situacaoLabel}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="editarLancamento(${l.id})" title="Editar">
                    Editar
                </button>
                <button class="btn btn-sm btn-danger" onclick="confirmarExclusao(${l.id})" title="Excluir">
                    Excluir
                </button>
            </td>
        </tr>
    `}).join('');
}

// ============================================
// MODAL
// ============================================

function abrirModalNovo() {
    document.getElementById('modal-titulo').textContent = 'Novo Lançamento';
    document.getElementById('form-lancamento').reset();
    document.getElementById('lancamento-id').value = '';
    
    // Data padrão = hoje
    document.getElementById('lancamento-data').value = new Date().toISOString().split('T')[0];
    
    document.getElementById('modal-lancamento').classList.add('active');
}

async function editarLancamento(id) {
    try {
        const lancamento = await getLancamento(id);
        
        document.getElementById('modal-titulo').textContent = 'Editar Lançamento';
        document.getElementById('lancamento-id').value = lancamento.id;
        document.getElementById('lancamento-data').value = lancamento.data;
        document.getElementById('lancamento-tipo').value = lancamento.tipo;
        document.getElementById('lancamento-categoria').value = lancamento.categoria;
        document.getElementById('lancamento-classificacao').value = lancamento.classificacao_nome || '';
        document.getElementById('lancamento-item').value = lancamento.item || '';
        document.getElementById('lancamento-valor').value = lancamento.valor;
        document.getElementById('lancamento-situacao').value = lancamento.situacao;
        
        document.getElementById('modal-lancamento').classList.add('active');
        
    } catch (error) {
        mostrarAlerta('Erro ao carregar lançamento', 'erro');
    }
}

function fecharModal() {
    document.getElementById('modal-lancamento').classList.remove('active');
}

// ============================================
// SALVAR LANÇAMENTO
// ============================================

async function salvarLancamento() {
    const id = document.getElementById('lancamento-id').value;
    
    const dados = {
        data: document.getElementById('lancamento-data').value,
        tipo: document.getElementById('lancamento-tipo').value,
        categoria: document.getElementById('lancamento-categoria').value,
        classificacao_nome: document.getElementById('lancamento-classificacao').value,
        item: document.getElementById('lancamento-item').value || null,
        valor: parseFloat(document.getElementById('lancamento-valor').value),
        situacao: document.getElementById('lancamento-situacao').value
    };
    
    // Validação
    if (!dados.data || !dados.tipo || !dados.categoria || !dados.classificacao_nome || !dados.valor) {
        mostrarAlerta('Preencha todos os campos obrigatórios', 'erro');
        return;
    }
    
    try {
        if (id) {
            await atualizarLancamento(id, dados);
            mostrarAlerta('Lançamento atualizado com sucesso!');
        } else {
            await criarLancamento(dados);
            mostrarAlerta('Lançamento criado com sucesso!');
        }
        
        fecharModal();
        carregarLancamentos();
        
    } catch (error) {
        mostrarAlerta('Erro ao salvar lançamento: ' + error.message, 'erro');
    }
}

// ============================================
// EXCLUIR LANÇAMENTO
// ============================================

function confirmarExclusao(id) {
    if (confirm('Tem certeza que deseja excluir este lançamento?')) {
        excluirLancamentoConfirmado(id);
    }
}

async function excluirLancamentoConfirmado(id) {
    try {
        await excluirLancamento(id);
        mostrarAlerta('Lançamento excluído com sucesso!');
        carregarLancamentos();
    } catch (error) {
        mostrarAlerta('Erro ao excluir lançamento', 'erro');
    }
}

// ============================================
// FUNÇÕES DE SITUAÇÃO
// ============================================

function obterClasseSituacao(situacao) {
    switch (situacao) {
        case 'BAIXADA': return 'badge-baixada';
        case 'NAO_BAIXADA': return 'badge-pendente';
        case 'OBSOLETO': return 'badge-obsoleto';
        default: return 'badge-pendente';
    }
}

function obterLabelSituacao(situacao) {
    switch (situacao) {
        case 'BAIXADA': return 'Baixado';
        case 'NAO_BAIXADA': return 'Não Baixado';
        case 'OBSOLETO': return 'Obsoleto';
        default: return situacao;
    }
}

function abrirMenuSituacao(id, situacaoAtual) {
    // Criar modal de seleção de situação
    const modal = document.createElement('div');
    modal.id = 'modal-situacao';
    modal.className = 'modal-overlay active';
    modal.innerHTML = `
        <div class="modal" style="max-width: 350px;">
            <div class="modal-header">
                <h3>Alterar Situação</h3>
                <button class="modal-close" onclick="fecharModalSituacao()">&times;</button>
            </div>
            <div class="modal-body">
                <p style="margin-bottom: 16px;">Situação atual: <strong>${obterLabelSituacao(situacaoAtual)}</strong></p>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <button class="btn ${situacaoAtual === 'BAIXADA' ? 'btn-primary' : 'btn-secondary'}" 
                            onclick="confirmarAlteracaoSituacao(${id}, 'BAIXADA')" 
                            ${situacaoAtual === 'BAIXADA' ? 'disabled' : ''}>
                        ✓ Baixado
                    </button>
                    <button class="btn ${situacaoAtual === 'NAO_BAIXADA' ? 'btn-primary' : 'btn-secondary'}" 
                            onclick="confirmarAlteracaoSituacao(${id}, 'NAO_BAIXADA')"
                            ${situacaoAtual === 'NAO_BAIXADA' ? 'disabled' : ''}>
                        ○ Não Baixado
                    </button>
                    <button class="btn ${situacaoAtual === 'OBSOLETO' ? 'btn-primary' : 'btn-secondary'}" 
                            onclick="confirmarAlteracaoSituacao(${id}, 'OBSOLETO')"
                            ${situacaoAtual === 'OBSOLETO' ? 'disabled' : ''}>
                        ✗ Obsoleto
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function fecharModalSituacao() {
    const modal = document.getElementById('modal-situacao');
    if (modal) {
        modal.remove();
    }
}

async function confirmarAlteracaoSituacao(id, novaSituacao) {
    try {
        await apiPut(`/lancamentos/${id}`, { situacao: novaSituacao });
        fecharModalSituacao();
        carregarLancamentos();
        mostrarAlerta('Situação alterada com sucesso!', 'sucesso');
    } catch (error) {
        mostrarAlerta('Erro ao alterar situação', 'erro');
    }
}

async function alternarSituacao(id) {
    try {
        await baixarLancamento(id);
        carregarLancamentos();
    } catch (error) {
        mostrarAlerta('Erro ao alterar situação', 'erro');
    }
}

// ============================================
// AUTOCOMPLETE
// ============================================

function configurarAutocomplete() {
    const input = document.getElementById('lancamento-item');
    const lista = document.getElementById('autocomplete-lista');
    
    input.addEventListener('input', async (e) => {
        const valor = e.target.value;
        
        clearTimeout(timeoutAutocomplete);
        
        if (valor.length < 2) {
            lista.style.display = 'none';
            return;
        }
        
        timeoutAutocomplete = setTimeout(async () => {
            try {
                const resultados = await autocompleteItens(valor);
                
                if (resultados.length === 0) {
                    lista.style.display = 'none';
                    return;
                }
                
                lista.innerHTML = resultados.map(r => `
                    <div style="padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #eee;"
                         onmouseover="this.style.background='#f0f0f0'"
                         onmouseout="this.style.background='#fff'"
                         onclick="selecionarAutocomplete('${r.nome}', '${r.classificacao_sugerida || ''}')">
                        <strong>${r.nome}</strong>
                        ${r.classificacao_sugerida ? `<br><small style="color:#666">→ ${r.classificacao_sugerida}</small>` : ''}
                    </div>
                `).join('');
                
                lista.style.display = 'block';
                lista.style.width = input.offsetWidth + 'px';
                
            } catch (error) {
                console.error('Erro no autocomplete:', error);
            }
        }, 300);
    });
    
    // Fechar ao clicar fora
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !lista.contains(e.target)) {
            lista.style.display = 'none';
        }
    });
}

function selecionarAutocomplete(nome, classificacao) {
    document.getElementById('lancamento-item').value = nome;
    document.getElementById('autocomplete-lista').style.display = 'none';
    
    // Sugerir classificação se disponível
    if (classificacao) {
        const selectClassif = document.getElementById('lancamento-classificacao');
        const opcaoExiste = Array.from(selectClassif.options).some(o => o.value === classificacao);
        
        if (opcaoExiste) {
            selectClassif.value = classificacao;
        }
    }
}

// ============================================
// EXPORTAR EXCEL
// ============================================

function exportarExcel() {
    const filtros = obterFiltros();
    const params = new URLSearchParams();
    
    if (filtros.tipo) params.append('tipo', filtros.tipo);
    if (filtros.categoria) params.append('categoria', filtros.categoria);
    if (filtros.classificacao) params.append('classificacao', filtros.classificacao);
    if (filtros.situacao) params.append('situacao', filtros.situacao);
    if (filtros.mes) params.append('mes', filtros.mes);
    if (filtros.ano) params.append('ano', filtros.ano);
    if (filtros.item) params.append('item', filtros.item);
    
    const url = `${API_URL}/lancamentos/exportar/excel?${params.toString()}`;
    window.open(url, '_blank');
}
