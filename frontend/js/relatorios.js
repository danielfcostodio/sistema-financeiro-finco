/**
 * Sistema Financeiro Finco - Relatórios
 * Evolução Mensal e Análises
 */

let graficoEvolucao = null;

const MESES_COMPLETOS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const MESES_CURTOS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    carregarRelatorios();
});

async function carregarRelatorios() {
    const ano = document.getElementById('filtro-ano').value;
    
    try {
        // Buscar todos os lançamentos do ano
        const lancamentos = await getLancamentos({ ano: ano, limit: 10000 });
        const lancamentosAtivos = lancamentos.filter(l => l.situacao !== 'OBSOLETO');
        const classificacoes = await getClassificacoes();
        
        // Carregar todas as seções
        carregarResumoAnual(lancamentosAtivos);
        carregarEvolucaoMensal(lancamentosAtivos);
        carregarGraficoEvolucao(lancamentosAtivos);
        carregarEvolucaoPorTipo(lancamentosAtivos, classificacoes);
        carregarTopFornecedores(lancamentosAtivos);
        carregarTopClientes(lancamentosAtivos);
        carregarTopClassificacoes(lancamentosAtivos, classificacoes);
        
    } catch (error) {
        console.error('Erro ao carregar relatórios:', error);
    }
}

// ============================================
// RESUMO ANUAL
// ============================================

function carregarResumoAnual(lancamentos) {
    const totalEntradas = lancamentos
        .filter(l => l.tipo === 'ENTRADA')
        .reduce((sum, l) => sum + l.valor, 0);
    
    const totalSaidas = lancamentos
        .filter(l => l.tipo === 'SAIDA')
        .reduce((sum, l) => sum + l.valor, 0);
    
    const resultado = totalEntradas - totalSaidas;
    
    // Calcular média mensal (meses com movimentação)
    const mesesComMovimentacao = new Set(lancamentos.map(l => l.mes)).size;
    const mediaMensal = mesesComMovimentacao > 0 ? resultado / mesesComMovimentacao : 0;
    
    document.getElementById('total-entradas-ano').textContent = formatarMoeda(totalEntradas);
    document.getElementById('total-saidas-ano').textContent = formatarMoeda(totalSaidas);
    
    const resultadoEl = document.getElementById('resultado-ano');
    resultadoEl.textContent = formatarMoeda(resultado);
    resultadoEl.className = 'indicador-valor ' + (resultado >= 0 ? 'positivo' : 'negativo');
    
    const mediaEl = document.getElementById('media-mensal');
    mediaEl.textContent = formatarMoeda(mediaMensal);
    mediaEl.className = 'indicador-valor ' + (mediaMensal >= 0 ? 'positivo' : 'negativo');
}

// ============================================
// EVOLUÇÃO MENSAL - TABELA
// ============================================

function carregarEvolucaoMensal(lancamentos) {
    const tbody = document.getElementById('tabela-evolucao-mensal');
    const tfoot = document.getElementById('tabela-evolucao-total');
    
    // Agrupar por mês
    const dadosMensais = [];
    let acumulado = 0;
    let totalEntradas = 0;
    let totalSaidas = 0;
    
    for (let mes = 1; mes <= 12; mes++) {
        const lancsMes = lancamentos.filter(l => l.mes === mes);
        
        const entradas = lancsMes
            .filter(l => l.tipo === 'ENTRADA')
            .reduce((sum, l) => sum + l.valor, 0);
        
        const saidas = lancsMes
            .filter(l => l.tipo === 'SAIDA')
            .reduce((sum, l) => sum + l.valor, 0);
        
        const resultado = entradas - saidas;
        acumulado += resultado;
        
        totalEntradas += entradas;
        totalSaidas += saidas;
        
        dadosMensais.push({
            mes: MESES_COMPLETOS[mes - 1],
            entradas,
            saidas,
            resultado,
            acumulado
        });
    }
    
    tbody.innerHTML = dadosMensais.map(d => `
        <tr>
            <td>${d.mes}</td>
            <td class="text-right valor-positivo">${formatarMoeda(d.entradas)}</td>
            <td class="text-right valor-negativo">${formatarMoeda(d.saidas)}</td>
            <td class="text-right ${d.resultado >= 0 ? 'valor-positivo' : 'valor-negativo'}">${formatarMoeda(d.resultado)}</td>
            <td class="text-right ${d.acumulado >= 0 ? 'valor-positivo' : 'valor-negativo'}" style="font-weight: bold;">${formatarMoeda(d.acumulado)}</td>
        </tr>
    `).join('');
    
    const resultadoTotal = totalEntradas - totalSaidas;
    tfoot.innerHTML = `
        <tr style="font-weight: bold; background: var(--cor-fundo);">
            <td>TOTAL</td>
            <td class="text-right valor-positivo">${formatarMoeda(totalEntradas)}</td>
            <td class="text-right valor-negativo">${formatarMoeda(totalSaidas)}</td>
            <td class="text-right ${resultadoTotal >= 0 ? 'valor-positivo' : 'valor-negativo'}">${formatarMoeda(resultadoTotal)}</td>
            <td class="text-right">-</td>
        </tr>
    `;
}

// ============================================
// EVOLUÇÃO MENSAL - GRÁFICO
// ============================================

function carregarGraficoEvolucao(lancamentos) {
    const ctx = document.getElementById('grafico-evolucao-mensal');
    if (!ctx) return;
    
    // Agrupar por mês
    const entradasPorMes = Array(12).fill(0);
    const saidasPorMes = Array(12).fill(0);
    const resultadoPorMes = Array(12).fill(0);
    
    lancamentos.forEach(l => {
        const mes = l.mes - 1;
        if (l.tipo === 'ENTRADA') {
            entradasPorMes[mes] += l.valor;
        } else {
            saidasPorMes[mes] += l.valor;
        }
    });
    
    for (let i = 0; i < 12; i++) {
        resultadoPorMes[i] = entradasPorMes[i] - saidasPorMes[i];
    }
    
    // Destruir gráfico anterior se existir
    if (graficoEvolucao) {
        graficoEvolucao.destroy();
    }
    
    graficoEvolucao = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: MESES_CURTOS,
            datasets: [
                {
                    label: 'Entradas',
                    data: entradasPorMes,
                    backgroundColor: 'rgba(0, 174, 120, 0.7)',
                    borderColor: 'rgba(0, 174, 120, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Saídas',
                    data: saidasPorMes,
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: 'rgba(220, 53, 69, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Resultado',
                    data: resultadoPorMes,
                    type: 'line',
                    borderColor: 'rgba(0, 123, 255, 1)',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.3
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
                            return 'R$ ' + (value / 1000).toFixed(0) + 'k';
                        }
                    }
                }
            }
        }
    });
}

// ============================================
// EVOLUÇÃO POR TIPO DE DESPESA
// ============================================

function carregarEvolucaoPorTipo(lancamentos, classificacoes) {
    const tbody = document.getElementById('tabela-evolucao-tipo');
    
    // Tipos permitidos
    const tiposPermitidos = ['CUSTO_FIXO', 'CUSTO_VARIAVEL', 'DESPESA_FIXA', 'DESPESA_VARIAVEL', 'IMPOSTO'];
    
    // Filtrar apenas saídas
    const saidas = lancamentos.filter(l => l.tipo === 'SAIDA');
    
    // Agrupar por tipo e mês
    const tiposMap = {};
    
    saidas.forEach(l => {
        const classif = classificacoes.find(c => c.nome === l.classificacao_nome);
        const tipo = classif ? classif.tipo : 'Outros';
        
        // Ignorar tipos não permitidos
        if (!tiposPermitidos.includes(tipo)) return;
        
        const mes = l.mes - 1;
        
        if (!tiposMap[tipo]) {
            tiposMap[tipo] = Array(12).fill(0);
        }
        tiposMap[tipo][mes] += l.valor;
    });
    
    if (Object.keys(tiposMap).length === 0) {
        tbody.innerHTML = '<tr><td colspan="14" class="text-center text-muted">Nenhum dado disponível</td></tr>';
        return;
    }
    
    // Calcular totais
    const tiposComTotal = Object.entries(tiposMap).map(([tipo, valores]) => ({
        tipo,
        valores,
        total: valores.reduce((a, b) => a + b, 0)
    }));
    
    // Ordenar por total
    tiposComTotal.sort((a, b) => b.total - a.total);
    
    tbody.innerHTML = tiposComTotal.map(item => `
        <tr>
            <td><strong>${item.tipo}</strong></td>
            ${item.valores.map(v => `<td class="text-right">${v > 0 ? formatarMoedaCurto(v) : '-'}</td>`).join('')}
            <td class="text-right" style="font-weight: bold;">${formatarMoeda(item.total)}</td>
        </tr>
    `).join('');
}

// ============================================
// TOP FORNECEDORES
// ============================================

function carregarTopFornecedores(lancamentos) {
    const tbody = document.getElementById('tabela-top-fornecedores');
    
    const saidas = lancamentos.filter(l => l.tipo === 'SAIDA' && l.item);
    
    // Agrupar por fornecedor
    const fornecedoresMap = {};
    let totalGeral = 0;
    
    saidas.forEach(l => {
        if (!fornecedoresMap[l.item]) {
            fornecedoresMap[l.item] = 0;
        }
        fornecedoresMap[l.item] += l.valor;
        totalGeral += l.valor;
    });
    
    // Ordenar e pegar top 10
    const sorted = Object.entries(fornecedoresMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Nenhum dado disponível</td></tr>';
        return;
    }
    
    tbody.innerHTML = sorted.map((item, index) => {
        const percentual = totalGeral > 0 ? ((item[1] / totalGeral) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td>${index + 1}º</td>
                <td>${item[0]}</td>
                <td class="text-right valor-negativo">${formatarMoeda(item[1])}</td>
                <td class="text-right">${percentual}%</td>
            </tr>
        `;
    }).join('');
}

// ============================================
// TOP CLIENTES
// ============================================

function carregarTopClientes(lancamentos) {
    const tbody = document.getElementById('tabela-top-clientes');
    
    const entradas = lancamentos.filter(l => l.tipo === 'ENTRADA' && l.item);
    
    // Agrupar por cliente
    const clientesMap = {};
    let totalGeral = 0;
    
    entradas.forEach(l => {
        if (!clientesMap[l.item]) {
            clientesMap[l.item] = 0;
        }
        clientesMap[l.item] += l.valor;
        totalGeral += l.valor;
    });
    
    // Ordenar e pegar top 10
    const sorted = Object.entries(clientesMap)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);
    
    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Nenhum dado disponível</td></tr>';
        return;
    }
    
    tbody.innerHTML = sorted.map((item, index) => {
        const percentual = totalGeral > 0 ? ((item[1] / totalGeral) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td>${index + 1}º</td>
                <td>${item[0]}</td>
                <td class="text-right valor-positivo">${formatarMoeda(item[1])}</td>
                <td class="text-right">${percentual}%</td>
            </tr>
        `;
    }).join('');
}

// ============================================
// TOP CLASSIFICAÇÕES
// ============================================

function carregarTopClassificacoes(lancamentos, classificacoes) {
    const tbody = document.getElementById('tabela-top-classificacoes');
    
    const saidas = lancamentos.filter(l => l.tipo === 'SAIDA');
    
    // Agrupar por classificação
    const classificacoesMap = {};
    let totalGeral = 0;
    
    saidas.forEach(l => {
        const classifNome = l.classificacao_nome || 'Sem classificação';
        if (!classificacoesMap[classifNome]) {
            const classif = classificacoes.find(c => c.nome === classifNome);
            classificacoesMap[classifNome] = {
                valor: 0,
                tipo: classif ? classif.tipo : '-'
            };
        }
        classificacoesMap[classifNome].valor += l.valor;
        totalGeral += l.valor;
    });
    
    // Ordenar e pegar top 10
    const sorted = Object.entries(classificacoesMap)
        .sort((a, b) => b[1].valor - a[1].valor)
        .slice(0, 10);
    
    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhum dado disponível</td></tr>';
        return;
    }
    
    tbody.innerHTML = sorted.map((item, index) => {
        const percentual = totalGeral > 0 ? ((item[1].valor / totalGeral) * 100).toFixed(1) : 0;
        return `
            <tr>
                <td>${index + 1}º</td>
                <td>${item[0]}</td>
                <td><span class="badge badge-operacional">${item[1].tipo}</span></td>
                <td class="text-right valor-negativo">${formatarMoeda(item[1].valor)}</td>
                <td class="text-right">${percentual}%</td>
            </tr>
        `;
    }).join('');
}

// ============================================
// EXPORTAR EXCEL
// ============================================

function exportarRelatorioExcel() {
    const ano = document.getElementById('filtro-ano').value;
    const url = `${API_URL}/lancamentos/exportar/excel?ano=${ano}`;
    window.open(url, '_blank');
}

// ============================================
// FUNÇÕES AUXILIARES
// ============================================

function formatarMoedaCurto(valor) {
    if (valor >= 1000000) {
        return 'R$ ' + (valor / 1000000).toFixed(1) + 'M';
    } else if (valor >= 1000) {
        return 'R$ ' + (valor / 1000).toFixed(1) + 'k';
    }
    return formatarMoeda(valor);
}
