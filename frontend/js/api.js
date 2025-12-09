/**
 * Sistema Financeiro Finco - API Client
 * Comunicação com o backend
 */

const API_URL = 'http://localhost:8000/api';

// ============================================
// FUNÇÕES AUXILIARES
// ============================================

function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

function formatarData(dataString) {
    const data = new Date(dataString + 'T00:00:00');
    return data.toLocaleDateString('pt-BR');
}

function formatarDataInput(dataString) {
    if (dataString.includes('/')) {
        const partes = dataString.split('/');
        return `${partes[2]}-${partes[1]}-${partes[0]}`;
    }
    return dataString;
}

// ============================================
// REQUISIÇÕES HTTP
// ============================================

async function apiGet(endpoint) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`);
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição GET:', error);
        throw error;
    }
}

async function apiPost(endpoint, dados) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        if (!response.ok) {
            const erro = await response.json();
            throw new Error(erro.detail || 'Erro ao criar registro');
        }
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição POST:', error);
        throw error;
    }
}

async function apiPut(endpoint, dados) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });
        if (!response.ok) {
            const erro = await response.json();
            throw new Error(erro.detail || 'Erro ao atualizar registro');
        }
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição PUT:', error);
        throw error;
    }
}

async function apiPatch(endpoint) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, { method: 'PATCH' });
        if (!response.ok) throw new Error('Erro ao atualizar registro');
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição PATCH:', error);
        throw error;
    }
}

async function apiDelete(endpoint) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Erro ao excluir registro');
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição DELETE:', error);
        throw error;
    }
}

// ============================================
// FUNÇÕES DE DASHBOARD
// ============================================

async function getDashboard() {
    return await apiGet('/dashboard');
}

async function getGraficoMensal(ano = 2025) {
    return await apiGet(`/dashboard/grafico-mensal?ano=${ano}`);
}

async function getTopDespesas(mes = null, limite = 10) {
    let url = `/dashboard/top-despesas?limite=${limite}`;
    if (mes) url += `&mes=${mes}`;
    return await apiGet(url);
}

// ============================================
// FUNÇÕES DE LANÇAMENTOS
// ============================================

async function getLancamentos(filtros = {}) {
    const params = new URLSearchParams();
    
    if (filtros.tipo) params.append('tipo', filtros.tipo);
    if (filtros.categoria) params.append('categoria', filtros.categoria);
    if (filtros.classificacao) params.append('classificacao', filtros.classificacao);
    if (filtros.situacao) params.append('situacao', filtros.situacao);
    if (filtros.mes) params.append('mes', filtros.mes);
    if (filtros.dia) params.append('dia', filtros.dia);
    if (filtros.ano) params.append('ano', filtros.ano);
    if (filtros.item) params.append('item', filtros.item);
    if (filtros.data_inicio) params.append('data_inicio', filtros.data_inicio);
    if (filtros.data_fim) params.append('data_fim', filtros.data_fim);
    if (filtros.limit) params.append('limit', filtros.limit);
    
    const queryString = params.toString();
    return await apiGet(`/lancamentos${queryString ? '?' + queryString : ''}`);
}

async function getLancamento(id) {
    return await apiGet(`/lancamentos/${id}`);
}

async function criarLancamento(dados) {
    return await apiPost('/lancamentos', dados);
}

async function atualizarLancamento(id, dados) {
    return await apiPut(`/lancamentos/${id}`, dados);
}

async function excluirLancamento(id) {
    return await apiDelete(`/lancamentos/${id}`);
}

async function baixarLancamento(id) {
    return await apiPatch(`/lancamentos/${id}/baixar`);
}

// ============================================
// FUNÇÕES DE CLASSIFICAÇÕES
// ============================================

async function getClassificacoes(tipo = null) {
    let url = '/classificacoes';
    if (tipo) url += `?tipo=${tipo}`;
    return await apiGet(url);
}

async function getTiposClassificacao() {
    return await apiGet('/classificacoes/tipos');
}

// ============================================
// FUNÇÕES DE AUTOCOMPLETE
// ============================================

async function autocompleteItens(query) {
    if (query.length < 2) return [];
    return await apiGet(`/autocomplete/itens?q=${encodeURIComponent(query)}`);
}

// ============================================
// FUNÇÕES DE CONFIGURAÇÕES
// ============================================

async function getConfiguracoes() {
    return await apiGet('/configuracoes');
}

async function atualizarConfiguracao(chave, valor) {
    return await apiPut(`/configuracoes/${chave}`, { valor });
}

// ============================================
// FUNÇÕES DE FLUXO DE CAIXA
// ============================================

async function getFluxoCaixa(mes = null, ano = 2025) {
    let url = `/fluxo-caixa?ano=${ano}`;
    if (mes) url += `&mes=${mes}`;
    return await apiGet(url);
}

// ============================================
// FUNÇÕES DE RESUMOS
// ============================================

async function getResumoMensal(mes = null, ano = 2025) {
    let url = `/resumos/mensal?ano=${ano}`;
    if (mes) url += `&mes=${mes}`;
    return await apiGet(url);
}

async function getResumoAnual(ano = 2025) {
    return await apiGet(`/resumos/anual?ano=${ano}`);
}

// ============================================
// FUNÇÕES DE UTILIDADE UI
// ============================================

function mostrarAlerta(mensagem, tipo = 'sucesso') {
    const container = document.getElementById('alerta-container') || document.body;
    
    const alerta = document.createElement('div');
    alerta.className = `alerta alerta-${tipo}`;
    alerta.innerHTML = `<span>${mensagem}</span>`;
    
    container.prepend(alerta);
    setTimeout(() => alerta.remove(), 5000);
}

function mostrarLoading(container) {
    container.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `;
}
