/**
 * Sistema Financeiro Finco - Contas a Pagar/Receber
 */

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    carregarResumoContas();
    carregarContas();
});

// ============================================
// CARREGAR RESUMO
// ============================================

async function carregarResumoContas() {
    try {
        // Buscar todas as contas pendentes (NAO_BAIXADA)
        const contas = await getLancamentos({ situacao: 'NAO_BAIXADA', limit: 5000 });
        // Filtrar para excluir OBSOLETO
        const contasAtivas = contas.filter(c => c.situacao !== 'OBSOLETO');
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        
        // Calcular totais
        let totalReceber = 0, qtdReceber = 0;
        let totalPagar = 0, qtdPagar = 0;
        let totalVencidas = 0, qtdVencidas = 0;
        let totalVenceHoje = 0, qtdVenceHoje = 0;
        
        contasAtivas.forEach(c => {
            const dataVenc = new Date(c.data + 'T00:00:00');
            dataVenc.setHours(0, 0, 0, 0);
            
            if (c.tipo === 'ENTRADA') {
                totalReceber += c.valor;
                qtdReceber++;
            } else {
                totalPagar += c.valor;
                qtdPagar++;
            }
            
            // Vencidas (antes de hoje)
            if (dataVenc < hoje) {
                totalVencidas += c.valor;
                qtdVencidas++;
            }
            
            // Vence hoje
            if (dataVenc.getTime() === hoje.getTime()) {
                totalVenceHoje += c.valor;
                qtdVenceHoje++;
            }
        });
        
        // Atualizar indicadores
        document.getElementById('total-receber').textContent = formatarMoeda(totalReceber);
        document.getElementById('qtd-receber').textContent = `${qtdReceber} conta${qtdReceber !== 1 ? 's' : ''}`;
        
        document.getElementById('total-pagar').textContent = formatarMoeda(totalPagar);
        document.getElementById('qtd-pagar').textContent = `${qtdPagar} conta${qtdPagar !== 1 ? 's' : ''}`;
        
        // Mostrar card de vencidas se houver
        const cardVencidas = document.getElementById('card-vencidas');
        if (qtdVencidas > 0) {
            cardVencidas.style.display = 'block';
            document.getElementById('total-vencidas').textContent = formatarMoeda(totalVencidas);
            document.getElementById('qtd-vencidas').textContent = `${qtdVencidas} conta${qtdVencidas !== 1 ? 's' : ''}`;
        } else {
            cardVencidas.style.display = 'none';
        }
        
        // Mostrar card de vence hoje se houver
        const cardVenceHoje = document.getElementById('card-vence-hoje');
        if (qtdVenceHoje > 0) {
            cardVenceHoje.style.display = 'block';
            document.getElementById('total-vence-hoje').textContent = formatarMoeda(totalVenceHoje);
            document.getElementById('qtd-vence-hoje').textContent = `${qtdVenceHoje} conta${qtdVenceHoje !== 1 ? 's' : ''}`;
        } else {
            cardVenceHoje.style.display = 'none';
        }
        
        // Mostrar alertas
        mostrarAlertas(qtdVencidas, qtdVenceHoje, totalVencidas, totalVenceHoje);
        
    } catch (error) {
        console.error('Erro ao carregar resumo:', error);
    }
}

// ============================================
// MOSTRAR ALERTAS
// ============================================

function mostrarAlertas(qtdVencidas, qtdVenceHoje, totalVencidas, totalVenceHoje) {
    const container = document.getElementById('alertas-vencimento');
    let html = '';
    
    if (qtdVencidas > 0) {
        html += `
            <div class="alerta alerta-perigo mb-2">
                <strong>Atenção!</strong> Você tem ${qtdVencidas} conta${qtdVencidas !== 1 ? 's' : ''} vencida${qtdVencidas !== 1 ? 's' : ''} 
                no valor total de ${formatarMoeda(totalVencidas)}.
            </div>
        `;
    }
    
    if (qtdVenceHoje > 0) {
        html += `
            <div class="alerta alerta-aviso mb-2">
                <strong>Lembrete!</strong> ${qtdVenceHoje} conta${qtdVenceHoje !== 1 ? 's' : ''} vence${qtdVenceHoje === 1 ? '' : 'm'} hoje 
                no valor total de ${formatarMoeda(totalVenceHoje)}.
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// ============================================
// CARREGAR CONTAS
// ============================================

async function carregarContas() {
    try {
        const tipo = document.getElementById('filtro-tipo').value;
        const periodo = document.getElementById('filtro-periodo').value;
        const ordem = document.getElementById('filtro-ordem').value;
        
        // Buscar contas pendentes
        const filtros = { situacao: 'NAO_BAIXADA', limit: 5000 };
        if (tipo) filtros.tipo = tipo;
        
        let contas = await getLancamentos(filtros);
        
        // Filtrar para excluir OBSOLETO
        contas = contas.filter(c => c.situacao !== 'OBSOLETO');
        
        // Filtrar por período
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        
        contas = contas.filter(c => {
            const dataVenc = new Date(c.data + 'T00:00:00');
            dataVenc.setHours(0, 0, 0, 0);
            
            switch (periodo) {
                case 'vencidas':
                    return dataVenc < hoje;
                case 'hoje':
                    return dataVenc.getTime() === hoje.getTime();
                case '7dias':
                    const em7dias = new Date(hoje);
                    em7dias.setDate(em7dias.getDate() + 7);
                    return dataVenc >= hoje && dataVenc <= em7dias;
                case '15dias':
                    const em15dias = new Date(hoje);
                    em15dias.setDate(em15dias.getDate() + 15);
                    return dataVenc >= hoje && dataVenc <= em15dias;
                case '30dias':
                    const em30dias = new Date(hoje);
                    em30dias.setDate(em30dias.getDate() + 30);
                    return dataVenc >= hoje && dataVenc <= em30dias;
                case 'mes':
                    return dataVenc.getMonth() === hoje.getMonth() && dataVenc.getFullYear() === hoje.getFullYear();
                case 'todas':
                default:
                    return true;
            }
        });
        
        // Ordenar
        if (ordem === 'valor') {
            contas.sort((a, b) => b.valor - a.valor);
        } else {
            contas.sort((a, b) => new Date(a.data) - new Date(b.data));
        }
        
        renderizarTabelaContas(contas);
        
    } catch (error) {
        console.error('Erro ao carregar contas:', error);
    }
}

// ============================================
// RENDERIZAR TABELA
// ============================================

function renderizarTabelaContas(contas) {
    const tbody = document.getElementById('tabela-contas');
    const contador = document.getElementById('contador-contas');
    
    contador.textContent = `${contas.length} registro${contas.length !== 1 ? 's' : ''}`;
    
    if (contas.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7" class="text-center text-muted">Nenhuma conta encontrada para este filtro</td></tr>
        `;
        return;
    }
    
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    
    tbody.innerHTML = contas.map(c => {
        const dataVenc = new Date(c.data + 'T00:00:00');
        dataVenc.setHours(0, 0, 0, 0);
        
        // Determinar status
        let statusClass = '';
        let statusText = '';
        
        if (dataVenc < hoje) {
            statusClass = 'badge-perigo';
            statusText = 'Vencida';
        } else if (dataVenc.getTime() === hoje.getTime()) {
            statusClass = 'badge-aviso';
            statusText = 'Vence Hoje';
        } else {
            const diffDias = Math.ceil((dataVenc - hoje) / (1000 * 60 * 60 * 24));
            statusClass = 'badge-operacional';
            statusText = `${diffDias} dia${diffDias !== 1 ? 's' : ''}`;
        }
        
        const tipoClass = c.tipo === 'ENTRADA' ? 'badge-entrada' : 'badge-saida';
        const tipoLabel = c.tipo === 'ENTRADA' ? 'A Receber' : 'A Pagar';
        const valorClass = c.tipo === 'ENTRADA' ? 'valor-positivo' : 'valor-negativo';
        
        return `
        <tr>
            <td>${formatarData(c.data)}</td>
            <td><span class="badge ${statusClass}">${statusText}</span></td>
            <td><span class="badge ${tipoClass}">${tipoLabel}</span></td>
            <td>${c.classificacao_nome || '-'}</td>
            <td>${c.item || '-'}</td>
            <td class="text-right ${valorClass}">${formatarMoeda(c.valor)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="baixarConta(${c.id})" title="Baixar">
                    Baixar
                </button>
            </td>
        </tr>
    `}).join('');
}

// ============================================
// BAIXAR CONTA
// ============================================

async function baixarConta(id) {
    if (!confirm('Deseja marcar esta conta como baixada/paga?')) {
        return;
    }
    
    try {
        await apiPatch(`/lancamentos/${id}/baixar`);
        carregarResumoContas();
        carregarContas();
    } catch (error) {
        console.error('Erro ao baixar conta:', error);
        alert('Erro ao baixar conta');
    }
}
