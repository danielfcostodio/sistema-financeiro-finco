/**
 * Sistema Financeiro Finco - Autenticação
 * Verifica se usuário está logado e gerencia sessão
 */

// Verificar autenticação ao carregar a página
(function() {
    const token = localStorage.getItem('token');
    const paginaAtual = window.location.pathname.split('/').pop();
    
    // Se não está logado e não está na página de login, redireciona
    if (!token && paginaAtual !== 'login.html') {
        window.location.href = 'login.html';
    }
})();

// Função para fazer logout
function fazerLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    window.location.href = 'login.html';
}

// Função para obter nome do usuário logado
function getUsuarioLogado() {
    return localStorage.getItem('usuario') || 'Admin';
}

// Função para verificar se está autenticado
function estaAutenticado() {
    return !!localStorage.getItem('token');
}

// Função para busca global
function buscarGlobal() {
    const termo = document.getElementById('busca-global').value.trim();
    if (termo.length >= 2) {
        // Salva o termo e redireciona para lançamentos
        localStorage.setItem('busca-termo', termo);
        window.location.href = 'lancamentos.html';
    }
}
