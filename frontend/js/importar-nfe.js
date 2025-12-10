/**
 * Sistema Financeiro Finco - Importar NFe
 * Integração com SEFAZ e upload de XML
 */

// Variáveis globais
let documentosEncontrados = [];

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    verificarStatus();
    carregarClassificacoes();
    configurarDragDrop();
});

// ============================================
// VERIFICAR STATUS
// ============================================

async function verificarStatus() {
    try {
        const response = await fetch(`${API_URL}/nfe/status`);
        const status = await response.json();
        
        // Atualizar indicadores
        const certEl = document.getElementById('status-certificado');
        const senhaEl = document.getElementById('status-senha');
        const ambienteEl = document.getElementById('status-ambiente');
        
        if (status.certificado_configurado) {
            const origem = status.certificado_origem === 'base64' ? '(Base64)' : '(Arquivo)';
            certEl.innerHTML = `<span class="badge badge-sucesso">✅ Configurado ${origem}</span>`;
        } else {
            certEl.innerHTML = '<span class="badge badge-alerta">⚠️ Não configurado</span>';
        }
        
        if (status.senha_configurada) {
            senhaEl.innerHTML = '<span class="badge badge-sucesso">✅ Configurada</span>';
        } else {
            senhaEl.innerHTML = '<span class="badge badge-alerta">⚠️ Não configurada</span>';
        }
        
        ambienteEl.textContent = status.ambiente === 'producao' ? 'Produção' : 'Homologação';
        
    } catch (error) {
        console.error('Erro ao verificar status:', error);
    }
}

// ============================================
// CARREGAR CLASSIFICAÇÕES
// ============================================

async function carregarClassificacoes() {
    try {
        const classificacoes = await getClassificacoes();
        const select = document.getElementById('classificacao-importar');
        
        classificacoes.forEach(c => {
            const option = document.createElement('option');
            option.value = c.nome;
            option.textContent = c.nome;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Erro ao carregar classificações:', error);
    }
}

// ============================================
// ABAS
// ============================================

function trocarAba(aba) {
    // Remover active de todos os botões
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    // Esconder todas as abas
    document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
    
    // Ativar aba selecionada
    if (aba === 'sefaz') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('aba-sefaz').style.display = 'block';
    } else {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('aba-upload').style.display = 'block';
    }
}

// ============================================
// CONSULTAR SEFAZ
// ============================================

async function consultarSefaz() {
    const btn = document.getElementById('btn-consultar');
    const ultimoNsu = document.getElementById('ultimo-nsu').value || '0';
    
    btn.disabled = true;
    btn.textContent = '⏳ Consultando...';
    
    try {
        const response = await fetch(`${API_URL}/nfe/consultar?ultimo_nsu=${ultimoNsu}`);
        const resultado = await response.json();
        
        if (!resultado.success) {
            alert(`Erro: ${resultado.error}`);
            return;
        }
        
        // Mostrar resultado
        document.getElementById('sefaz-resultado').style.display = 'block';
        document.getElementById('resultado-ult-nsu').textContent = resultado.ultNSU || '-';
        document.getElementById('resultado-max-nsu').textContent = resultado.maxNSU || '-';
        document.getElementById('resultado-total').textContent = resultado.total || 0;
        
        // Adicionar documentos encontrados
        if (resultado.documentos && resultado.documentos.length > 0) {
            documentosEncontrados = resultado.documentos;
            renderizarDocumentos();
        } else {
            addLog('Nenhum documento novo encontrado.', 'info');
        }
        
    } catch (error) {
        console.error('Erro na consulta:', error);
        alert(`Erro na consulta: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Consultar SEFAZ';
    }
}

// ============================================
// UPLOAD DE XML
// ============================================

function configurarDragDrop() {
    const area = document.getElementById('upload-area');
    
    area.addEventListener('dragover', (e) => {
        e.preventDefault();
        area.classList.add('drag-over');
    });
    
    area.addEventListener('dragleave', () => {
        area.classList.remove('drag-over');
    });
    
    area.addEventListener('drop', (e) => {
        e.preventDefault();
        area.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        processarArquivos(files);
    });
}

async function processarUpload() {
    const input = document.getElementById('input-xml');
    const files = input.files;
    
    if (files.length === 0) return;
    
    await processarArquivos(files);
}

async function processarArquivos(files) {
    const formData = new FormData();
    
    for (let i = 0; i < files.length; i++) {
        if (files[i].name.endsWith('.xml')) {
            formData.append('files', files[i]);
        }
    }
    
    try {
        addLog(`Processando ${files.length} arquivo(s)...`, 'info');
        
        const response = await fetch(`${API_URL}/nfe/upload-xml`, {
            method: 'POST',
            body: formData
        });
        
        const resultado = await response.json();
        
        if (!resultado.success) {
            addLog(`Erro: ${resultado.error}`, 'erro');
            return;
        }
        
        addLog(`${resultado.total} documento(s) processado(s)`, 'sucesso');
        
        if (resultado.documentos && resultado.documentos.length > 0) {
            documentosEncontrados = resultado.documentos;
            renderizarDocumentos();
        }
        
    } catch (error) {
        console.error('Erro no upload:', error);
        addLog(`Erro no upload: ${error.message}`, 'erro');
    }
}

// ============================================
// RENDERIZAR DOCUMENTOS
// ============================================

function renderizarDocumentos() {
    const tbody = document.getElementById('tabela-documentos');
    const contador = document.getElementById('contador-docs');
    const secao = document.getElementById('secao-documentos');
    
    secao.style.display = 'block';
    contador.textContent = `${documentosEncontrados.length} documentos`;
    
    if (documentosEncontrados.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Nenhum documento</td></tr>';
        return;
    }
    
    tbody.innerHTML = documentosEncontrados.map((doc, index) => {
        const tipoLabel = doc.tipo_lancamento === 'ENTRADA' ? 'A Receber' : 'A Pagar';
        const tipoBadge = doc.tipo_lancamento === 'ENTRADA' ? 'entrada' : 'saida';
        
        return `
        <tr data-index="${index}">
            <td><input type="checkbox" class="check-doc" data-index="${index}" checked></td>
            <td><span class="badge badge-${tipoBadge}">${tipoLabel}</span></td>
            <td>${doc.numero_nf || '-'}</td>
            <td>${doc.fornecedor_cliente || doc.nome_emitente || '-'}</td>
            <td>${formatarData(doc.data_emissao)}</td>
            <td>${formatarData(doc.data_vencimento)}</td>
            <td class="text-right">${formatarMoeda(doc.valor_total || 0)}</td>
            <td>
                <button class="btn btn-sm" onclick="verDetalhes(${index})" title="Ver detalhes">
                    👁️
                </button>
            </td>
        </tr>
        `;
    }).join('');
}

function toggleTodos() {
    const checkTodos = document.getElementById('check-todos').checked;
    document.querySelectorAll('.check-doc').forEach(check => {
        check.checked = checkTodos;
    });
}

function verDetalhes(index) {
    const doc = documentosEncontrados[index];
    
    let detalhes = `
NÚMERO NF: ${doc.numero_nf || '-'}
SÉRIE: ${doc.serie || '-'}
CHAVE: ${doc.chave || '-'}

EMITENTE: ${doc.nome_emitente || '-'}
CNPJ EMITENTE: ${doc.cnpj_emitente || '-'}

DESTINATÁRIO: ${doc.nome_destinatario || '-'}
CNPJ DESTINATÁRIO: ${doc.cnpj_destinatario || '-'}

DATA EMISSÃO: ${doc.data_emissao || '-'}
DATA VENCIMENTO: ${doc.data_vencimento || '-'}
VALOR TOTAL: ${formatarMoeda(doc.valor_total || 0)}

TIPO LANÇAMENTO: ${doc.tipo_lancamento || '-'}
FORNECEDOR/CLIENTE: ${doc.fornecedor_cliente || '-'}
    `;
    
    alert(detalhes);
}

// ============================================
// IMPORTAR SELECIONADOS
// ============================================

async function importarSelecionados() {
    const checkboxes = document.querySelectorAll('.check-doc:checked');
    
    if (checkboxes.length === 0) {
        alert('Selecione pelo menos um documento para importar.');
        return;
    }
    
    const categoria = document.getElementById('categoria-importar').value;
    const classificacao = document.getElementById('classificacao-importar').value;
    
    const docsParaImportar = [];
    checkboxes.forEach(check => {
        const index = parseInt(check.dataset.index);
        docsParaImportar.push(documentosEncontrados[index]);
    });
    
    if (!confirm(`Deseja importar ${docsParaImportar.length} documento(s) como lançamentos?`)) {
        return;
    }
    
    try {
        addLog(`Importando ${docsParaImportar.length} documento(s)...`, 'info');
        
        const response = await fetch(`${API_URL}/nfe/importar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                documentos: docsParaImportar,
                categoria: categoria,
                classificacao: classificacao || null
            })
        });
        
        const resultado = await response.json();
        
        if (!resultado.success) {
            addLog(`Erro: ${resultado.error}`, 'erro');
            return;
        }
        
        addLog(`✅ ${resultado.importados} lançamento(s) criado(s) com sucesso!`, 'sucesso');
        
        if (resultado.erros && resultado.erros.length > 0) {
            resultado.erros.forEach(err => {
                addLog(`⚠️ Erro no doc ${err.documento}: ${err.erro}`, 'alerta');
            });
        }
        
        // Limpar documentos importados
        const indicesImportados = Array.from(checkboxes).map(c => parseInt(c.dataset.index));
        documentosEncontrados = documentosEncontrados.filter((_, i) => !indicesImportados.includes(i));
        renderizarDocumentos();
        
    } catch (error) {
        console.error('Erro na importação:', error);
        addLog(`Erro na importação: ${error.message}`, 'erro');
    }
}

// ============================================
// LOG
// ============================================

function addLog(mensagem, tipo = 'info') {
    const log = document.getElementById('log-importacao');
    const secao = document.getElementById('secao-log');
    
    secao.style.display = 'block';
    
    const hora = new Date().toLocaleTimeString('pt-BR');
    const classe = tipo === 'erro' ? 'log-erro' : (tipo === 'sucesso' ? 'log-sucesso' : (tipo === 'alerta' ? 'log-alerta' : 'log-info'));
    
    log.innerHTML += `<div class="log-item ${classe}">[${hora}] ${mensagem}</div>`;
    log.scrollTop = log.scrollHeight;
}

// ============================================
// UTILITÁRIOS
// ============================================

function formatarData(data) {
    if (!data) return '-';
    
    const d = new Date(data + 'T00:00:00');
    return d.toLocaleDateString('pt-BR');
}
