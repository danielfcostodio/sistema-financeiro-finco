/**
 * Sistema Financeiro Finco - Fluxo de Caixa
 * Exibe apenas lançamentos BAIXADOS com saldo acumulado
 */

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Definir mês atual
    const mesAtual = new Date().getMonth() + 1;
    document.getElementById('filtro-mes').value = mesAtual;
    
    carregarFluxoCaixa();
});

// ============================================
// CARREGAR FLUXO DE CAIXA
// ============================================

async function carregarFluxoCaixa() {
    const ano = document.getElementById('filtro-ano').value;
    const mes = document.getElementById('filtro-mes').value;
    
    try {
        // Buscar lançamentos BAIXADOS do mês
        const lancamentos = await getLancamentos({
            ano: ano,
            mes: mes,
            situacao: 'BAIXADA',
            limit: 1000
        });
        
        // Buscar saldo inicial do mês (resumo do mês anterior)
        let saldoInicial = 0;
        if (parseInt(mes) > 1) {
            try {
                const resumoAnterior = await getResumoMensal(parseInt(mes) - 1, ano);
                if (resumoAnterior && resumoAnterior.saldo_final) {
                    saldoInicial = resumoAnterior.saldo_final;
                }
            } catch (e) {
                console.log('Sem resumo do mês anterior');
            }
        }
        
        // Calcular totais
        const totalEntradas = lancamentos
            .filter(l => l.tipo === 'ENTRADA')
            .reduce((sum, l) => sum + l.valor, 0);
        
        const totalSaidas = lancamentos
            .filter(l => l.tipo === 'SAIDA')
            .reduce((sum, l) => sum + l.valor, 0);
        
        const saldoFinal = saldoInicial + totalEntradas - totalSaidas;
        
        // Atualizar indicadores
        document.getElementById('saldo-inicial').textContent = formatarMoeda(saldoInicial);
        document.getElementById('total-entradas').textContent = formatarMoeda(totalEntradas);
        document.getElementById('total-saidas').textContent = formatarMoeda(totalSaidas);
        document.getElementById('saldo-final').textContent = formatarMoeda(saldoFinal);
        
        // Colorir saldo final
        const saldoFinalEl = document.getElementById('saldo-final');
        saldoFinalEl.classList.remove('positivo', 'negativo');
        if (saldoFinal >= 0) {
            saldoFinalEl.classList.add('positivo');
        } else {
            saldoFinalEl.classList.add('negativo');
        }
        
        // Renderizar tabela
        renderizarTabelaFluxo(lancamentos, saldoInicial);
        
    } catch (error) {
        console.error('Erro ao carregar fluxo de caixa:', error);
        mostrarAlerta('Erro ao carregar fluxo de caixa', 'erro');
    }
}

// ============================================
// RENDERIZAR TABELA
// ============================================

function renderizarTabelaFluxo(lancamentos, saldoInicial) {
    const tbody = document.getElementById('tabela-fluxo');
    const contador = document.getElementById('contador-fluxo');
    
    contador.textContent = `${lancamentos.length} registros`;
    
    if (lancamentos.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="8" class="text-center text-muted">Nenhuma movimentação baixada neste período</td></tr>
        `;
        return;
    }
    
    // Ordenar por data
    lancamentos.sort((a, b) => new Date(a.data) - new Date(b.data));
    
    let saldoAcumulado = saldoInicial;
    
    tbody.innerHTML = lancamentos.map(l => {
        const isEntrada = l.tipo === 'ENTRADA';
        const valorEntrada = isEntrada ? l.valor : 0;
        const valorSaida = !isEntrada ? l.valor : 0;
        
        // Atualizar saldo acumulado
        if (isEntrada) {
            saldoAcumulado += l.valor;
        } else {
            saldoAcumulado -= l.valor;
        }
        
        const tipoLabel = isEntrada ? 'Entrada' : 'Saída';
        
        return `
        <tr>
            <td>${formatarData(l.data)}</td>
            <td>
                <span class="badge badge-${isEntrada ? 'entrada' : 'saida'}">
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
            <td class="text-right valor-positivo">
                ${valorEntrada > 0 ? formatarMoeda(valorEntrada) : '-'}
            </td>
            <td class="text-right valor-negativo">
                ${valorSaida > 0 ? formatarMoeda(valorSaida) : '-'}
            </td>
            <td class="text-right ${saldoAcumulado >= 0 ? 'valor-positivo' : 'valor-negativo'}" style="font-weight: bold;">
                ${formatarMoeda(saldoAcumulado)}
            </td>
        </tr>
    `}).join('');
}

// ============================================
// EXPORTAR EXCEL
// ============================================

function exportarFluxoExcel() {
    const ano = document.getElementById('filtro-ano').value;
    const mes = document.getElementById('filtro-mes').value;
    
    const params = new URLSearchParams();
    params.append('ano', ano);
    params.append('mes', mes);
    params.append('situacao', 'BAIXADA');
    
    const url = `${API_URL}/lancamentos/exportar/excel?${params.toString()}`;
    window.open(url, '_blank');
}
