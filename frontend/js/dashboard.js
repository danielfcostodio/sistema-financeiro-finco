/**
 * Sistema Financeiro Finco - Dashboard
 * Gráficos e Indicadores
 */

// Variáveis globais para os gráficos
let graficoEntradasSaidas = null;
let graficoDespesasTipo = null;
let graficoTopGastos = null;

// Cores padrão
const CORES = {
    verde: 'rgba(0, 174, 120, 0.8)',
    verdeClaro: 'rgba(0, 174, 120, 0.2)',
    vermelho: 'rgba(220, 53, 69, 0.8)',
    vermelhoClaro: 'rgba(220, 53, 69, 0.2)',
    azul: 'rgba(0, 186, 226, 0.8)',
    azulClaro: 'rgba(0, 186, 226, 0.2)',
    laranja: 'rgba(255, 159, 64, 0.8)',
    amarelo: 'rgba(255, 205, 86, 0.8)',
    roxo: 'rgba(153, 102, 255, 0.8)',
    rosa: 'rgba(255, 99, 132, 0.8)',
    cinza: 'rgba(108, 117, 125, 0.8)'
};

const CORES_PIZZA = [
    'rgba(220, 53, 69, 0.8)',   // Vermelho - Custo Fixo
    'rgba(255, 159, 64, 0.8)',  // Laranja - Custo Variável
    'rgba(0, 123, 255, 0.8)',   // Azul - Despesa Fixa
    'rgba(255, 205, 86, 0.8)',  // Amarelo - Despesa Variável
    'rgba(153, 102, 255, 0.8)', // Roxo - Imposto
    'rgba(108, 117, 125, 0.8)'  // Cinza - Outros
];

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    carregarDashboard();
});

function carregarDashboard() {
    // Carregar cada parte independentemente
    carregarIndicadores().catch(e => console.error('Erro indicadores:', e));
    carregarAlertasVencimento().catch(e => console.error('Erro alertas:', e));
    carregarContasPendentes().catch(e => console.error('Erro contas:', e));
    carregarGraficoEntradasSaidas().catch(e => console.error('Erro gráfico entradas/saídas:', e));
    carregarGraficoDespesasTipo().catch(e => console.error('Erro gráfico despesas:', e));
    carregarGraficoTopGastos().catch(e => console.error('Erro gráfico top gastos:', e));
    carregarTopFornecedores().catch(e => console.error('Erro top fornecedores:', e));
    carregarTopClientes().catch(e => console.error('Erro top clientes:', e));
    carregarResumoTipos().catch(e => console.error('Erro resumo tipos:', e));
}

function getAnoSelecionado() {
    const select = document.getElementById('filtro-ano-dashboard');
    return select ? parseInt(select.value) : new Date().getFullYear();
}

// ============================================
// INDICADORES PRINCIPAIS
// ============================================

async function carregarIndicadores() {
    try {
        const dados = await getDashboard();
        
        // Atualizar valores
        document.getElementById('saldo-atual').textContent = formatarMoeda(dados.saldo_atual);
        document.getElementById('entradas-mes').textContent = formatarMoeda(dados.entradas_mes);
        document.getElementById('saidas-mes').textContent = formatarMoeda(dados.saidas_mes);
        
        const resultado = dados.entradas_mes - dados.saidas_mes;
        const resultadoEl = document.getElementById('resultado-mes');
        resultadoEl.textContent = formatarMoeda(resultado);
        resultadoEl.className = 'indicador-valor ' + (resultado >= 0 ? 'positivo' : 'negativo');
        
        document.getElementById('entradas-dia').textContent = formatarMoeda(dados.entradas_dia);
        document.getElementById('saidas-dia').textContent = formatarMoeda(dados.saidas_dia);
        
        // Miller-Orr
        atualizarMillerOrr(dados);
        
    } catch (error) {
        console.error('Erro ao carregar indicadores:', error);
    }
}

function atualizarMillerOrr(dados) {
    const marker = document.getElementById('miller-marker');
    const statusEl = document.getElementById('miller-status');
    
    document.getElementById('miller-min').textContent = `Mínimo: ${formatarMoeda(dados.miller_orr_min)}`;
    document.getElementById('miller-ret').textContent = `Retorno: ${formatarMoeda(dados.miller_orr_retorno)}`;
    document.getElementById('miller-max').textContent = `Máximo: ${formatarMoeda(dados.miller_orr_max)}`;
    
    // Calcular posição do marcador
    const range = dados.miller_orr_max - dados.miller_orr_min;
    let posicao = ((dados.saldo_atual - dados.miller_orr_min) / range) * 100;
    posicao = Math.max(0, Math.min(100, posicao));
    
    marker.style.left = `${posicao}%`;
    
    // Status
    if (dados.miller_orr_status === 'BAIXO') {
        statusEl.innerHTML = '<span style="color: var(--cor-perigo);">⚠️ Saldo abaixo do mínimo - Considere buscar recursos</span>';
        document.getElementById('card-saldo').classList.add('alerta-baixo');
    } else if (dados.miller_orr_status === 'ALTO') {
        statusEl.innerHTML = '<span style="color: var(--cor-alerta);">📈 Saldo acima do máximo - Considere investir o excedente</span>';
        document.getElementById('card-saldo').classList.add('alerta-alto');
    } else {
        statusEl.innerHTML = '<span style="color: var(--cor-sucesso);">✓ Saldo dentro da faixa ideal</span>';
        document.getElementById('card-saldo').classList.remove('alerta-baixo', 'alerta-alto');
    }
}

// ============================================
// ALERTAS DE VENCIMENTO
// ============================================

async function carregarAlertasVencimento() {
    const container = document.getElementById('alertas-vencimento');
    if (!container) return;
    
    try {
        const contas = await getLancamentos({ situacao: 'NAO_BAIXADA', limit: 5000 });
        const contasAtivas = contas.filter(c => c.situacao !== 'OBSOLETO');
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        
        let qtdVencidas = 0, totalVencidas = 0;
        let qtdVenceHoje = 0, totalVenceHoje = 0;
        
        contasAtivas.forEach(c => {
            const dataVenc = new Date(c.data + 'T00:00:00');
            dataVenc.setHours(0, 0, 0, 0);
            
            if (dataVenc < hoje) {
                qtdVencidas++;
                totalVencidas += c.valor;
            } else if (dataVenc.getTime() === hoje.getTime()) {
                qtdVenceHoje++;
                totalVenceHoje += c.valor;
            }
        });
        
        let html = '';
        
        if (qtdVencidas > 0) {
            html += `
                <div class="alerta alerta-perigo mb-2">
                    <strong>Atenção!</strong> Você tem <strong>${qtdVencidas}</strong> conta${qtdVencidas !== 1 ? 's' : ''} vencida${qtdVencidas !== 1 ? 's' : ''} 
                    no valor total de <strong>${formatarMoeda(totalVencidas)}</strong>.
                    <a href="contas.html" style="margin-left: 10px;">Ver contas</a>
                </div>
            `;
        }
        
        if (qtdVenceHoje > 0) {
            html += `
                <div class="alerta alerta-aviso mb-2">
                    <strong>Lembrete!</strong> <strong>${qtdVenceHoje}</strong> conta${qtdVenceHoje !== 1 ? 's' : ''} vence${qtdVenceHoje === 1 ? '' : 'm'} hoje 
                    no valor total de <strong>${formatarMoeda(totalVenceHoje)}</strong>.
                    <a href="contas.html" style="margin-left: 10px;">Ver contas</a>
                </div>
            `;
        }
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Erro ao carregar alertas:', error);
        container.innerHTML = '';
    }
}

// ============================================
// CONTAS PENDENTES
// ============================================

async function carregarContasPendentes() {
    const listaPagar = document.getElementById('lista-contas-pagar');
    const listaReceber = document.getElementById('lista-contas-receber');
    
    if (!listaPagar || !listaReceber) return;
    
    try {
        const contas = await getLancamentos({ situacao: 'NAO_BAIXADA', limit: 5000 });
        const contasAtivas = contas.filter(c => c.situacao !== 'OBSOLETO');
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        
        const em7dias = new Date(hoje);
        em7dias.setDate(em7dias.getDate() + 7);
        
        const contasFiltradas = contasAtivas.filter(c => {
            const dataVenc = new Date(c.data + 'T00:00:00');
            dataVenc.setHours(0, 0, 0, 0);
            return dataVenc <= em7dias;
        });
        
        const contasPagar = contasFiltradas.filter(c => c.tipo === 'SAIDA');
        const contasReceber = contasFiltradas.filter(c => c.tipo === 'ENTRADA');
        
        contasPagar.sort((a, b) => new Date(a.data) - new Date(b.data));
        contasReceber.sort((a, b) => new Date(a.data) - new Date(b.data));
        
        renderizarListaContas('lista-contas-pagar', contasPagar.slice(0, 5), 'pagar');
        renderizarListaContas('lista-contas-receber', contasReceber.slice(0, 5), 'receber');
        
    } catch (error) {
        console.error('Erro ao carregar contas pendentes:', error);
        listaPagar.innerHTML = '<div class="contas-vazio">Erro ao carregar</div>';
        listaReceber.innerHTML = '<div class="contas-vazio">Erro ao carregar</div>';
    }
}

function renderizarListaContas(elementId, contas, tipo) {
    const container = document.getElementById(elementId);
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    
    if (contas.length === 0) {
        container.innerHTML = `<div class="contas-vazio">Nenhuma conta ${tipo === 'pagar' ? 'a pagar' : 'a receber'} nos próximos 7 dias</div>`;
        return;
    }
    
    container.innerHTML = contas.map(c => {
        const dataVenc = new Date(c.data + 'T00:00:00');
        dataVenc.setHours(0, 0, 0, 0);
        
        let statusClass = '';
        let statusText = formatarData(c.data);
        
        if (dataVenc < hoje) {
            statusClass = 'conta-item-vencida';
            statusText = 'VENCIDA - ' + formatarData(c.data);
        } else if (dataVenc.getTime() === hoje.getTime()) {
            statusClass = 'conta-item-hoje';
            statusText = 'HOJE';
        }
        
        const valorClass = tipo === 'receber' ? 'valor-positivo' : 'valor-negativo';
        
        return `
            <div class="conta-item ${statusClass}">
                <div class="conta-info">
                    <div class="conta-item-nome">${c.item || c.classificacao_nome || 'Sem descrição'}</div>
                    <div class="conta-item-data">${statusText}</div>
                </div>
                <div class="conta-item-valor ${valorClass}">${formatarMoeda(c.valor)}</div>
            </div>
        `;
    }).join('');
}

// ============================================
// GRÁFICO 1: ENTRADAS X SAÍDAS POR MÊS
// ============================================

async function carregarGraficoEntradasSaidas() {
    const ctx = document.getElementById('grafico-entradas-saidas');
    if (!ctx) return;
    
    const ano = getAnoSelecionado();
    
    try {
        const lancamentos = await getLancamentos({ ano: ano, limit: 10000 });
        const lancamentosAtivos = lancamentos.filter(l => l.situacao !== 'OBSOLETO');
        
        // Agrupar por mês
        const entradasPorMes = Array(12).fill(0);
        const saidasPorMes = Array(12).fill(0);
        
        lancamentosAtivos.forEach(l => {
            const mes = l.mes - 1;
            if (l.tipo === 'ENTRADA') {
                entradasPorMes[mes] += l.valor;
            } else {
                saidasPorMes[mes] += l.valor;
            }
        });
        
        // Destruir gráfico anterior se existir
        if (graficoEntradasSaidas) {
            graficoEntradasSaidas.destroy();
        }
        
        graficoEntradasSaidas = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: MESES,
                datasets: [
                    {
                        label: 'Entradas',
                        data: entradasPorMes,
                        backgroundColor: CORES.verde,
                        borderColor: CORES.verde,
                        borderWidth: 1
                    },
                    {
                        label: 'Saídas',
                        data: saidasPorMes,
                        backgroundColor: CORES.vermelho,
                        borderColor: CORES.vermelho,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + formatarMoeda(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + value.toLocaleString('pt-BR');
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar gráfico entradas/saídas:', error);
    }
}

// ============================================
// GRÁFICO 2: SAÍDAS POR TIPO (PIZZA)
// ============================================

async function carregarGraficoDespesasTipo() {
    const ctx = document.getElementById('grafico-despesas-tipo');
    if (!ctx) return;
    
    const ano = getAnoSelecionado();
    
    // Tipos permitidos
    const tiposPermitidos = ['CUSTO_FIXO', 'CUSTO_VARIAVEL', 'DESPESA_FIXA', 'DESPESA_VARIAVEL', 'IMPOSTO'];
    
    try {
        const classificacoes = await getClassificacoes();
        const lancamentos = await getLancamentos({ ano: ano, tipo: 'SAIDA', limit: 10000 });
        const lancamentosAtivos = lancamentos.filter(l => l.situacao !== 'OBSOLETO');
        
        // Agrupar por tipo de classificação
        const tiposMap = {};
        
        lancamentosAtivos.forEach(l => {
            const classif = classificacoes.find(c => c.nome === l.classificacao_nome);
            const tipo = classif ? classif.tipo : 'Outros';
            
            // Ignorar tipos não permitidos
            if (!tiposPermitidos.includes(tipo)) return;
            
            if (!tiposMap[tipo]) {
                tiposMap[tipo] = 0;
            }
            tiposMap[tipo] += l.valor;
        });
        
        const labels = Object.keys(tiposMap);
        const valores = Object.values(tiposMap);
        
        // Destruir gráfico anterior se existir
        if (graficoDespesasTipo) {
            graficoDespesasTipo.destroy();
        }
        
        graficoDespesasTipo = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: CORES_PIZZA.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percent = ((context.raw / total) * 100).toFixed(1);
                                return `${context.label}: ${formatarMoeda(context.raw)} (${percent}%)`;
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar gráfico despesas por tipo:', error);
    }
}

// ============================================
// GRÁFICO 3: TOP 10 MAIORES GASTOS
// ============================================

async function carregarGraficoTopGastos() {
    const ctx = document.getElementById('grafico-top-gastos');
    if (!ctx) return;
    
    const ano = getAnoSelecionado();
    
    try {
        const lancamentos = await getLancamentos({ ano: ano, tipo: 'SAIDA', limit: 10000 });
        const lancamentosAtivos = lancamentos.filter(l => l.situacao !== 'OBSOLETO');
        
        // Agrupar por classificação
        const gastosMap = {};
        
        lancamentosAtivos.forEach(l => {
            const classif = l.classificacao_nome || 'Sem classificação';
            if (!gastosMap[classif]) {
                gastosMap[classif] = 0;
            }
            gastosMap[classif] += l.valor;
        });
        
        // Ordenar e pegar top 10
        const sorted = Object.entries(gastosMap)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        const labels = sorted.map(s => s[0]);
        const valores = sorted.map(s => s[1]);
        
        // Destruir gráfico anterior se existir
        if (graficoTopGastos) {
            graficoTopGastos.destroy();
        }
        
        graficoTopGastos = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Gasto',
                    data: valores,
                    backgroundColor: CORES.vermelho,
                    borderColor: CORES.vermelho,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return formatarMoeda(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + (value / 1000).toFixed(0) + 'k';
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar gráfico top gastos:', error);
    }
}

// ============================================
// TOP 10 FORNECEDORES
// ============================================

async function carregarTopFornecedores() {
    const container = document.getElementById('lista-top-fornecedores');
    if (!container) return;
    
    const ano = getAnoSelecionado();
    
    try {
        const lancamentos = await getLancamentos({ ano: ano, tipo: 'SAIDA', limit: 10000 });
        const lancamentosAtivos = lancamentos.filter(l => l.situacao !== 'OBSOLETO' && l.item);
        
        // Agrupar por fornecedor (item)
        const fornecedoresMap = {};
        
        lancamentosAtivos.forEach(l => {
            const fornecedor = l.item;
            if (!fornecedoresMap[fornecedor]) {
                fornecedoresMap[fornecedor] = 0;
            }
            fornecedoresMap[fornecedor] += l.valor;
        });
        
        // Ordenar e pegar top 10
        const sorted = Object.entries(fornecedoresMap)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        if (sorted.length === 0) {
            container.innerHTML = '<div class="contas-vazio">Nenhum fornecedor encontrado</div>';
            return;
        }
        
        container.innerHTML = sorted.map((item, index) => `
            <div class="ranking-item">
                <span class="ranking-posicao">${index + 1}º</span>
                <span class="ranking-nome">${item[0]}</span>
                <span class="ranking-valor valor-negativo">${formatarMoeda(item[1])}</span>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Erro ao carregar top fornecedores:', error);
        container.innerHTML = '<div class="contas-vazio">Erro ao carregar</div>';
    }
}

// ============================================
// TOP 10 CLIENTES
// ============================================

async function carregarTopClientes() {
    const container = document.getElementById('lista-top-clientes');
    if (!container) return;
    
    const ano = getAnoSelecionado();
    
    try {
        const lancamentos = await getLancamentos({ ano: ano, tipo: 'ENTRADA', limit: 10000 });
        const lancamentosAtivos = lancamentos.filter(l => l.situacao !== 'OBSOLETO' && l.item);
        
        // Agrupar por cliente (item)
        const clientesMap = {};
        
        lancamentosAtivos.forEach(l => {
            const cliente = l.item;
            if (!clientesMap[cliente]) {
                clientesMap[cliente] = 0;
            }
            clientesMap[cliente] += l.valor;
        });
        
        // Ordenar e pegar top 10
        const sorted = Object.entries(clientesMap)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        if (sorted.length === 0) {
            container.innerHTML = '<div class="contas-vazio">Nenhum cliente encontrado</div>';
            return;
        }
        
        container.innerHTML = sorted.map((item, index) => `
            <div class="ranking-item">
                <span class="ranking-posicao">${index + 1}º</span>
                <span class="ranking-nome">${item[0]}</span>
                <span class="ranking-valor valor-positivo">${formatarMoeda(item[1])}</span>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Erro ao carregar top clientes:', error);
        container.innerHTML = '<div class="contas-vazio">Erro ao carregar</div>';
    }
}

// ============================================
// RESUMO POR CATEGORIAS (OPERACIONAL, INVESTIMENTO, FINANCEIRO)
// ============================================

async function carregarResumoTipos() {
    const tbody = document.getElementById('tabela-resumo');
    if (!tbody) return;
    
    // Categorias permitidas
    const categoriasPermitidas = ['OPERACIONAL', 'INVESTIMENTO', 'FINANCEIRO'];
    
    try {
        const mesAtual = new Date().getMonth() + 1;
        const anoAtual = new Date().getFullYear();
        
        const lancamentos = await getLancamentos({ 
            ano: anoAtual, 
            mes: mesAtual, 
            tipo: 'SAIDA', 
            limit: 5000 
        });
        
        const lancamentosAtivos = lancamentos.filter(l => l.situacao !== 'OBSOLETO');
        
        // Agrupar por categoria
        const categoriasMap = {};
        let total = 0;
        
        lancamentosAtivos.forEach(l => {
            const categoria = l.categoria || 'Outros';
            
            // Ignorar categorias não permitidas
            if (!categoriasPermitidas.includes(categoria)) return;
            
            if (!categoriasMap[categoria]) {
                categoriasMap[categoria] = 0;
            }
            categoriasMap[categoria] += l.valor;
            total += l.valor;
        });
        
        if (Object.keys(categoriasMap).length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Nenhum dado disponível</td></tr>';
            return;
        }
        
        // Ordenar por valor
        const sorted = Object.entries(categoriasMap).sort((a, b) => b[1] - a[1]);
        
        tbody.innerHTML = sorted.map(([categoria, valor]) => {
            const percentual = total > 0 ? ((valor / total) * 100).toFixed(1) : 0;
            return `
                <tr>
                    <td>${categoria}</td>
                    <td class="text-right">${formatarMoeda(valor)}</td>
                    <td class="text-right">${percentual}%</td>
                </tr>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Erro ao carregar resumo categorias:', error);
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Erro ao carregar</td></tr>';
    }
}

// ============================================
// FUNÇÕES AUXILIARES
// ============================================

function mostrarAlerta(mensagem, tipo = 'info') {
    const container = document.getElementById('alerta-container');
    if (!container) return;
    
    const tipoClasse = tipo === 'erro' ? 'alerta-perigo' : tipo === 'sucesso' ? 'alerta-sucesso' : 'alerta-aviso';
    
    container.innerHTML = `
        <div class="alerta ${tipoClasse} mb-2">
            ${mensagem}
        </div>
    `;
    
    setTimeout(() => {
        container.innerHTML = '';
    }, 5000);
}
