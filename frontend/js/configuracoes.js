/**
 * Sistema Financeiro Finco - Configurações
 */

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    carregarConfiguracoes();
    carregarClassificacoes();
});

// ============================================
// CARREGAR CONFIGURAÇÕES
// ============================================

async function carregarConfiguracoes() {
    try {
        const configs = await getConfiguracoes();
        
        configs.forEach(c => {
            if (c.chave === 'miller_orr_minimo') {
                document.getElementById('miller-minimo').value = c.valor;
            } else if (c.chave === 'miller_orr_retorno') {
                document.getElementById('miller-retorno').value = c.valor;
            } else if (c.chave === 'miller_orr_maximo') {
                document.getElementById('miller-maximo').value = c.valor;
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar configurações:', error);
        mostrarAlerta('Erro ao carregar configurações', 'erro');
    }
}

// ============================================
// SALVAR MILLER-ORR
// ============================================

async function salvarMillerOrr() {
    const minimo = document.getElementById('miller-minimo').value;
    const retorno = document.getElementById('miller-retorno').value;
    const maximo = document.getElementById('miller-maximo').value;
    
    // Validações
    if (!minimo || !retorno || !maximo) {
        mostrarAlerta('Preencha todos os campos', 'erro');
        return;
    }
    
    if (parseFloat(minimo) >= parseFloat(retorno)) {
        mostrarAlerta('O mínimo deve ser menor que o ponto de retorno', 'erro');
        return;
    }
    
    if (parseFloat(retorno) >= parseFloat(maximo)) {
        mostrarAlerta('O ponto de retorno deve ser menor que o máximo', 'erro');
        return;
    }
    
    try {
        await atualizarConfiguracao('miller_orr_minimo', minimo);
        await atualizarConfiguracao('miller_orr_retorno', retorno);
        await atualizarConfiguracao('miller_orr_maximo', maximo);
        
        mostrarAlerta('Parâmetros salvos com sucesso!', 'sucesso');
        
    } catch (error) {
        console.error('Erro ao salvar:', error);
        mostrarAlerta('Erro ao salvar parâmetros', 'erro');
    }
}

// ============================================
// CARREGAR CLASSIFICAÇÕES
// ============================================

async function carregarClassificacoes() {
    try {
        const filtroTipo = document.getElementById('filtro-tipo-class').value;
        let url = `${API_URL}/classificacoes`;
        if (filtroTipo) {
            url += `?tipo=${filtroTipo}`;
        }
        
        const response = await fetch(url);
        const classificacoes = await response.json();
        
        document.getElementById('total-classificacoes').textContent = 
            `${classificacoes.length} classificações`;
        
        const tipoLabels = {
            'CUSTO_FIXO': 'Custo Fixo',
            'CUSTO_VARIAVEL': 'Custo Variável',
            'DESPESA_FIXA': 'Despesa Fixa',
            'DESPESA_VARIAVEL': 'Despesa Variável',
            'IMPOSTO': 'Imposto',
            'FINANCEIRO': 'Financeiro',
            'INVESTIMENTO': 'Investimento',
            'RECEITA': 'Receita'
        };
        
        const tbody = document.getElementById('tabela-classificacoes');
        
        if (classificacoes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Nenhuma classificação encontrada</td></tr>';
            return;
        }
        
        tbody.innerHTML = classificacoes.map(c => `
            <tr>
                <td>${c.nome}</td>
                <td><span class="badge badge-operacional">${tipoLabels[c.tipo] || c.tipo}</span></td>
                <td>${c.categoria_padrao}</td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="editarClassificacao(${c.id}, '${c.nome}', '${c.tipo}', '${c.categoria_padrao}')" title="Editar">
                        Editar
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="excluirClassificacao(${c.id}, '${c.nome}')" title="Excluir">
                        Excluir
                    </button>
                </td>
            </tr>
        `).join('');
        
    } catch (error) {
        console.error('Erro ao carregar classificações:', error);
    }
}

// ============================================
// MODAL CLASSIFICAÇÃO
// ============================================

function abrirModalClassificacao() {
    document.getElementById('modal-class-titulo').textContent = 'Nova Classificação';
    document.getElementById('class-id').value = '';
    document.getElementById('class-nome').value = '';
    document.getElementById('class-tipo').value = 'CUSTO_FIXO';
    document.getElementById('class-categoria').value = 'OPERACIONAL';
    document.getElementById('modal-classificacao').classList.add('active');
}

function fecharModalClassificacao() {
    document.getElementById('modal-classificacao').classList.remove('active');
}

function editarClassificacao(id, nome, tipo, categoria) {
    document.getElementById('modal-class-titulo').textContent = 'Editar Classificação';
    document.getElementById('class-id').value = id;
    document.getElementById('class-nome').value = nome;
    document.getElementById('class-tipo').value = tipo;
    document.getElementById('class-categoria').value = categoria;
    document.getElementById('modal-classificacao').classList.add('active');
}

async function salvarClassificacao() {
    const id = document.getElementById('class-id').value;
    const nome = document.getElementById('class-nome').value.trim().toUpperCase();
    const tipo = document.getElementById('class-tipo').value;
    const categoria = document.getElementById('class-categoria').value;
    
    if (!nome) {
        mostrarAlerta('Informe o nome da classificação', 'erro');
        return;
    }
    
    try {
        let response;
        
        if (id) {
            // Editar
            response = await fetch(`${API_URL}/classificacoes/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome, tipo, categoria_padrao: categoria })
            });
        } else {
            // Criar
            response = await fetch(`${API_URL}/classificacoes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome, tipo, categoria_padrao: categoria })
            });
        }
        
        if (response.ok) {
            mostrarAlerta(id ? 'Classificação atualizada!' : 'Classificação criada!', 'sucesso');
            fecharModalClassificacao();
            carregarClassificacoes();
        } else {
            const erro = await response.json();
            throw new Error(erro.detail || 'Erro ao salvar');
        }
        
    } catch (error) {
        console.error('Erro ao salvar classificação:', error);
        mostrarAlerta('Erro ao salvar: ' + error.message, 'erro');
    }
}

async function excluirClassificacao(id, nome) {
    if (!confirm(`Deseja excluir a classificação "${nome}"?\n\nATENÇÃO: Lançamentos que usam esta classificação não serão excluídos, mas perderão o vínculo.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/classificacoes/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            mostrarAlerta('Classificação excluída!', 'sucesso');
            carregarClassificacoes();
        } else {
            const erro = await response.json();
            throw new Error(erro.detail || 'Erro ao excluir');
        }
        
    } catch (error) {
        console.error('Erro ao excluir classificação:', error);
        mostrarAlerta('Erro ao excluir: ' + error.message, 'erro');
    }
}

// ============================================
// ABRIR PASTA
// ============================================

function abrirPastaData() {
    mostrarAlerta('Abra manualmente a pasta "data" dentro da pasta do sistema', 'aviso');
}

// ============================================
// ALTERAR SENHA
// ============================================

async function alterarSenha() {
    const senhaAtual = document.getElementById('senha-atual').value;
    const senhaNova = document.getElementById('senha-nova').value;
    const senhaConfirmar = document.getElementById('senha-confirmar').value;
    
    if (!senhaAtual || !senhaNova || !senhaConfirmar) {
        mostrarAlerta('Preencha todos os campos', 'erro');
        return;
    }
    
    if (senhaNova !== senhaConfirmar) {
        mostrarAlerta('A nova senha e a confirmação não coincidem', 'erro');
        return;
    }
    
    if (senhaNova.length < 4) {
        mostrarAlerta('A nova senha deve ter pelo menos 4 caracteres', 'erro');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/alterar-senha`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                senha_atual: senhaAtual,
                senha_nova: senhaNova
            })
        });
        
        const resultado = await response.json();
        
        if (response.ok) {
            mostrarAlerta('Senha alterada com sucesso!', 'sucesso');
            document.getElementById('senha-atual').value = '';
            document.getElementById('senha-nova').value = '';
            document.getElementById('senha-confirmar').value = '';
        } else {
            throw new Error(resultado.detail || 'Erro ao alterar senha');
        }
        
    } catch (error) {
        console.error('Erro ao alterar senha:', error);
        mostrarAlerta(error.message, 'erro');
    }
}

// ============================================
// IMPORTAR PLANILHA
// ============================================

async function importarPlanilha() {
    const arquivoInput = document.getElementById('arquivo-importar');
    const ano = document.getElementById('ano-importar').value;
    const modo = document.getElementById('modo-importar').value;
    const btnImportar = document.getElementById('btn-importar');
    const resultadoDiv = document.getElementById('resultado-importacao');
    const msgSpan = document.getElementById('msg-importacao');
    
    if (!arquivoInput.files || arquivoInput.files.length === 0) {
        mostrarAlerta('Selecione um arquivo Excel', 'erro');
        return;
    }
    
    const arquivo = arquivoInput.files[0];
    
    // Confirmar se modo é substituir
    if (modo === 'substituir') {
        if (!confirm(`ATENÇÃO: Isso irá APAGAR todos os lançamentos de ${ano} e reimportar. Deseja continuar?`)) {
            return;
        }
    }
    
    // Desabilitar botão e mostrar loading
    btnImportar.disabled = true;
    btnImportar.textContent = 'Importando...';
    resultadoDiv.style.display = 'none';
    
    try {
        const formData = new FormData();
        formData.append('arquivo', arquivo);
        formData.append('modo', modo);
        formData.append('ano', ano);
        
        const response = await fetch(`${API_URL}/importar`, {
            method: 'POST',
            body: formData
        });
        
        const resultado = await response.json();
        
        if (resultado.sucesso) {
            msgSpan.innerHTML = `
                <strong>Importação concluída com sucesso!</strong><br>
                Novos: ${resultado.lancamentos_novos}<br>
                Atualizados: ${resultado.lancamentos_atualizados}<br>
                Ignorados (já existiam): ${resultado.lancamentos_ignorados}<br>
                Meses processados: ${resultado.meses_processados.join(', ') || 'Nenhum'}
            `;
            resultadoDiv.style.display = 'block';
            mostrarAlerta('Importação concluída com sucesso!', 'sucesso');
        } else {
            throw new Error(resultado.detail || 'Erro na importação');
        }
        
    } catch (error) {
        console.error('Erro ao importar:', error);
        mostrarAlerta('Erro ao importar: ' + error.message, 'erro');
    } finally {
        btnImportar.disabled = false;
        btnImportar.textContent = 'Importar Planilha';
    }
}
