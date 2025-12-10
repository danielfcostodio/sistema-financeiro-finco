"""
Sistema Financeiro Finco - Backend FastAPI
API completa para gerenciamento financeiro
"""
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from backend.database import (
    get_db, criar_tabelas, inicializar_configuracoes, inicializar_classificacoes,
    Lancamento, Classificacao, ItemFornecedor, SaldoDiario, ResumoMensal, 
    Configuracao, Usuario, SessionLocal
)
import hashlib
import pandas as pd
import tempfile
import shutil
import secrets


# ============== APP ==============
app = FastAPI(
    title="Sistema Financeiro Finco",
    description="API de controle financeiro",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos do frontend
import os
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


# ============== SCHEMAS ==============
class LancamentoCreate(BaseModel):
    data: date
    tipo: str  # ENTRADA ou SAIDA
    categoria: str  # OPERACIONAL, FINANCEIRO, INVESTIMENTO
    classificacao_nome: str
    item: Optional[str] = None
    valor: float
    situacao: str = "BAIXADA"


class LancamentoUpdate(BaseModel):
    data: Optional[date] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    classificacao_nome: Optional[str] = None
    item: Optional[str] = None
    valor: Optional[float] = None
    situacao: Optional[str] = None


class LancamentoResponse(BaseModel):
    id: int
    data: date
    dia: int
    mes: int
    ano: int
    tipo: str
    categoria: str
    classificacao_nome: Optional[str]
    item: Optional[str]
    valor: float
    situacao: str
    
    class Config:
        from_attributes = True


class ConfiguracaoUpdate(BaseModel):
    valor: str


class DashboardResponse(BaseModel):
    saldo_atual: float
    miller_orr_status: str  # BAIXO, NORMAL, ALTO
    miller_orr_minimo: float
    miller_orr_retorno: float
    miller_orr_maximo: float
    entradas_mes: float
    saidas_mes: float
    resultado_mes: float
    entradas_dia: float
    saidas_dia: float


# ============== INICIALIZAÇÃO ==============
@app.on_event("startup")
async def startup():
    """Inicializa banco de dados na startup"""
    criar_tabelas()
    db = SessionLocal()
    try:
        inicializar_configuracoes(db)
        inicializar_classificacoes(db)
        
        # Criar usuário admin padrão se não existir
        admin = db.query(Usuario).filter(Usuario.username == "admin").first()
        if not admin:
            senha_hash = hashlib.sha256("170724".encode()).hexdigest()
            admin = Usuario(username="admin", senha_hash=senha_hash, nome="Administrador")
            db.add(admin)
            db.commit()
    finally:
        db.close()


# ============== ROTAS - AUTENTICAÇÃO ==============

class LoginRequest(BaseModel):
    username: str
    senha: str

class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    senha_nova: str

# Armazenamento simples de tokens (em produção, usar Redis ou banco)
tokens_ativos = {}

@app.post("/api/login")
def fazer_login(dados: LoginRequest, db: Session = Depends(get_db)):
    """Realiza login do usuário"""
    usuario = db.query(Usuario).filter(
        Usuario.username == dados.username,
        Usuario.ativo == True
    ).first()
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    
    senha_hash = hashlib.sha256(dados.senha.encode()).hexdigest()
    
    if usuario.senha_hash != senha_hash:
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    
    # Gerar token simples
    token = secrets.token_hex(32)
    tokens_ativos[token] = usuario.username
    
    return {
        "token": token,
        "usuario": usuario.nome or usuario.username,
        "mensagem": "Login realizado com sucesso"
    }


@app.post("/api/logout")
def fazer_logout(token: str = None):
    """Realiza logout do usuário"""
    if token and token in tokens_ativos:
        del tokens_ativos[token]
    return {"mensagem": "Logout realizado com sucesso"}


@app.post("/api/alterar-senha")
def alterar_senha(dados: AlterarSenhaRequest, db: Session = Depends(get_db)):
    """Altera a senha do usuário admin"""
    usuario = db.query(Usuario).filter(Usuario.username == "admin").first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    senha_atual_hash = hashlib.sha256(dados.senha_atual.encode()).hexdigest()
    
    if usuario.senha_hash != senha_atual_hash:
        raise HTTPException(status_code=401, detail="Senha atual incorreta")
    
    usuario.senha_hash = hashlib.sha256(dados.senha_nova.encode()).hexdigest()
    db.commit()
    
    return {"mensagem": "Senha alterada com sucesso"}


@app.get("/api/verificar-auth")
def verificar_autenticacao(token: str = None):
    """Verifica se o token é válido"""
    if token and token in tokens_ativos:
        return {"autenticado": True, "usuario": tokens_ativos[token]}
    return {"autenticado": False}


# ============== ROTAS - DASHBOARD ==============
@app.get("/api/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Retorna dados do dashboard"""
    hoje = date.today()
    mes_atual = hoje.month
    ano_atual = hoje.year
    
    # Buscar configurações Miller-Orr
    config_min = db.query(Configuracao).filter(Configuracao.chave == "miller_orr_minimo").first()
    config_ret = db.query(Configuracao).filter(Configuracao.chave == "miller_orr_retorno").first()
    config_max = db.query(Configuracao).filter(Configuracao.chave == "miller_orr_maximo").first()
    
    miller_min = float(config_min.valor) if config_min else 55000
    miller_ret = float(config_ret.valor) if config_ret else 100000
    miller_max = float(config_max.valor) if config_max else 355000
    
    # Calcular saldo atual (soma de todas entradas - soma de todas saídas BAIXADAS)
    total_entradas = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.tipo == "ENTRADA",
        Lancamento.situacao == "BAIXADA"
    ).scalar() or 0
    
    total_saidas = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.tipo == "SAIDA",
        Lancamento.situacao == "BAIXADA"
    ).scalar() or 0
    
    saldo_atual = total_entradas - total_saidas
    
    # Status Miller-Orr
    if saldo_atual < miller_min:
        miller_status = "BAIXO"
    elif saldo_atual > miller_max:
        miller_status = "ALTO"
    else:
        miller_status = "NORMAL"
    
    # Entradas e saídas do mês atual (excluindo OBSOLETO)
    entradas_mes = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.tipo == "ENTRADA",
        Lancamento.mes == mes_atual,
        Lancamento.ano == ano_atual,
        Lancamento.situacao != "OBSOLETO"
    ).scalar() or 0
    
    saidas_mes = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.tipo == "SAIDA",
        Lancamento.mes == mes_atual,
        Lancamento.ano == ano_atual,
        Lancamento.situacao != "OBSOLETO"
    ).scalar() or 0
    
    # Entradas e saídas do dia (apenas BAIXADAS)
    entradas_dia = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.tipo == "ENTRADA",
        Lancamento.data == hoje,
        Lancamento.situacao == "BAIXADA"
    ).scalar() or 0
    
    saidas_dia = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.tipo == "SAIDA",
        Lancamento.data == hoje,
        Lancamento.situacao == "BAIXADA"
    ).scalar() or 0
    
    return DashboardResponse(
        saldo_atual=saldo_atual,
        miller_orr_status=miller_status,
        miller_orr_minimo=miller_min,
        miller_orr_retorno=miller_ret,
        miller_orr_maximo=miller_max,
        entradas_mes=entradas_mes,
        saidas_mes=saidas_mes,
        resultado_mes=entradas_mes - saidas_mes,
        entradas_dia=entradas_dia,
        saidas_dia=saidas_dia
    )


@app.get("/api/dashboard/grafico-mensal")
def get_grafico_mensal(ano: int = 2025, db: Session = Depends(get_db)):
    """Retorna dados para gráfico de evolução mensal"""
    resumos = db.query(ResumoMensal).filter(ResumoMensal.ano == ano).order_by(ResumoMensal.mes).all()
    
    return {
        "meses": [r.mes for r in resumos],
        "entradas": [r.total_entradas for r in resumos],
        "saidas": [r.total_saidas for r in resumos],
        "saldos": [r.saldo_final for r in resumos]
    }


@app.get("/api/dashboard/top-despesas")
def get_top_despesas(mes: int = None, ano: int = 2025, limite: int = 10, db: Session = Depends(get_db)):
    """Retorna top despesas por classificação"""
    if mes is None:
        mes = date.today().month
    
    resultado = db.query(
        Lancamento.classificacao_nome,
        func.sum(Lancamento.valor).label('total')
    ).filter(
        Lancamento.tipo == "SAIDA",
        Lancamento.mes == mes,
        Lancamento.ano == ano
    ).group_by(
        Lancamento.classificacao_nome
    ).order_by(
        func.sum(Lancamento.valor).desc()
    ).limit(limite).all()
    
    return [{"classificacao": r[0] or "Sem classificação", "valor": r[1]} for r in resultado]


# ============== ROTAS - LANÇAMENTOS ==============
@app.get("/api/lancamentos", response_model=List[LancamentoResponse])
def listar_lancamentos(
    tipo: Optional[str] = None,
    categoria: Optional[str] = None,
    classificacao: Optional[str] = None,
    situacao: Optional[str] = None,
    mes: Optional[int] = None,
    dia: Optional[int] = None,
    ano: Optional[int] = None,
    item: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db)
):
    """Lista lançamentos com filtros"""
    query = db.query(Lancamento)
    
    if tipo:
        query = query.filter(Lancamento.tipo == tipo)
    if categoria:
        query = query.filter(Lancamento.categoria == categoria)
    if classificacao:
        query = query.filter(Lancamento.classificacao_nome == classificacao)
    if situacao:
        query = query.filter(Lancamento.situacao == situacao)
    if mes:
        query = query.filter(Lancamento.mes == mes)
    if dia:
        query = query.filter(Lancamento.dia == dia)
    if ano:
        query = query.filter(Lancamento.ano == ano)
    if item:
        query = query.filter(Lancamento.item.ilike(f"%{item}%"))
    if data_inicio:
        query = query.filter(Lancamento.data >= data_inicio)
    if data_fim:
        query = query.filter(Lancamento.data <= data_fim)
    
    return query.order_by(Lancamento.data.asc(), Lancamento.id.asc()).offset(skip).limit(limit).all()


@app.get("/api/lancamentos/exportar/excel")
def exportar_lancamentos_excel(
    tipo: Optional[str] = None,
    categoria: Optional[str] = None,
    classificacao: Optional[str] = None,
    situacao: Optional[str] = None,
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    item: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Exporta lançamentos para Excel"""
    from fastapi.responses import StreamingResponse
    import io
    
    query = db.query(Lancamento)
    
    if tipo:
        query = query.filter(Lancamento.tipo == tipo)
    if categoria:
        query = query.filter(Lancamento.categoria == categoria)
    if classificacao:
        query = query.filter(Lancamento.classificacao_nome == classificacao)
    if situacao:
        query = query.filter(Lancamento.situacao == situacao)
    if mes:
        query = query.filter(Lancamento.mes == mes)
    if ano:
        query = query.filter(Lancamento.ano == ano)
    if item:
        query = query.filter(Lancamento.item.ilike(f"%{item}%"))
    
    lancamentos = query.order_by(Lancamento.data.asc()).all()
    
    # Criar DataFrame
    dados = []
    for l in lancamentos:
        dados.append({
            'Data': l.data.strftime('%d/%m/%Y') if l.data else '',
            'Tipo': 'Entrada' if l.tipo == 'ENTRADA' else 'Saída',
            'Categoria': l.categoria,
            'Classificação': l.classificacao_nome or '',
            'Item/Fornecedor': l.item or '',
            'Valor': l.valor,
            'Situação': 'Baixado' if l.situacao == 'BAIXADA' else 'Não Baixado'
        })
    
    df = pd.DataFrame(dados)
    
    # Criar arquivo Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Lançamentos', index=False)
        
        # Ajustar largura das colunas
        worksheet = writer.sheets['Lançamentos']
        for idx, col in enumerate(df.columns):
            max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
    
    output.seek(0)
    
    # Nome do arquivo
    nome_arquivo = f"lancamentos_{ano or 'todos'}_{mes or 'todos'}.xlsx"
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename={nome_arquivo}'}
    )


@app.get("/api/lancamentos/{lancamento_id}", response_model=LancamentoResponse)
def obter_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    """Obtém um lançamento específico"""
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    return lancamento


@app.post("/api/lancamentos", response_model=LancamentoResponse)
def criar_lancamento(lancamento: LancamentoCreate, db: Session = Depends(get_db)):
    """Cria novo lançamento"""
    # Obter classificação
    classif = db.query(Classificacao).filter(Classificacao.nome == lancamento.classificacao_nome).first()
    classif_id = classif.id if classif else None
    
    # Registrar item para autocomplete
    if lancamento.item:
        item_existente = db.query(ItemFornecedor).filter(ItemFornecedor.nome == lancamento.item.upper()).first()
        if item_existente:
            item_existente.vezes_usado += 1
            item_existente.ultima_vez = datetime.utcnow()
            if classif_id:
                item_existente.classificacao_id = classif_id
        else:
            novo_item = ItemFornecedor(nome=lancamento.item.upper(), classificacao_id=classif_id)
            db.add(novo_item)
    
    # Criar lançamento
    novo = Lancamento(
        data=lancamento.data,
        dia=lancamento.data.day,
        mes=lancamento.data.month,
        ano=lancamento.data.year,
        tipo=lancamento.tipo,
        categoria=lancamento.categoria,
        classificacao_id=classif_id,
        classificacao_nome=lancamento.classificacao_nome,
        item=lancamento.item,
        valor=lancamento.valor,
        situacao=lancamento.situacao
    )
    
    db.add(novo)
    db.commit()
    db.refresh(novo)
    
    return novo


@app.put("/api/lancamentos/{lancamento_id}", response_model=LancamentoResponse)
def atualizar_lancamento(lancamento_id: int, dados: LancamentoUpdate, db: Session = Depends(get_db)):
    """Atualiza um lançamento"""
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    if dados.data:
        lancamento.data = dados.data
        lancamento.dia = dados.data.day
        lancamento.mes = dados.data.month
        lancamento.ano = dados.data.year
    if dados.tipo:
        lancamento.tipo = dados.tipo
    if dados.categoria:
        lancamento.categoria = dados.categoria
    if dados.classificacao_nome:
        lancamento.classificacao_nome = dados.classificacao_nome
        classif = db.query(Classificacao).filter(Classificacao.nome == dados.classificacao_nome).first()
        lancamento.classificacao_id = classif.id if classif else None
    if dados.item is not None:
        lancamento.item = dados.item
    if dados.valor is not None:
        lancamento.valor = dados.valor
    if dados.situacao:
        lancamento.situacao = dados.situacao
    
    db.commit()
    db.refresh(lancamento)
    
    return lancamento


@app.delete("/api/lancamentos/{lancamento_id}")
def excluir_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    """Exclui um lançamento"""
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    db.delete(lancamento)
    db.commit()
    
    return {"message": "Lançamento excluído com sucesso"}


@app.patch("/api/lancamentos/{lancamento_id}/baixar")
def baixar_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    """Alterna situação do lançamento (BAIXADA/NAO_BAIXADA)"""
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    
    if lancamento.situacao == "BAIXADA":
        lancamento.situacao = "NAO_BAIXADA"
    else:
        lancamento.situacao = "BAIXADA"
    
    db.commit()
    
    return {"message": f"Situação alterada para {lancamento.situacao}"}


# ============== ROTAS - CLASSIFICAÇÕES ==============

class ClassificacaoCreate(BaseModel):
    nome: str
    tipo: str
    categoria_padrao: str = "OPERACIONAL"

class ClassificacaoUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None
    categoria_padrao: Optional[str] = None

@app.get("/api/classificacoes")
def listar_classificacoes(tipo: Optional[str] = None, db: Session = Depends(get_db)):
    """Lista todas as classificações"""
    query = db.query(Classificacao).filter(Classificacao.ativo == True)
    
    if tipo:
        query = query.filter(Classificacao.tipo == tipo)
    
    return query.order_by(Classificacao.nome).all()


@app.post("/api/classificacoes")
def criar_classificacao(dados: ClassificacaoCreate, db: Session = Depends(get_db)):
    """Cria uma nova classificação"""
    # Verificar se já existe
    existente = db.query(Classificacao).filter(Classificacao.nome == dados.nome.upper()).first()
    if existente:
        raise HTTPException(status_code=400, detail="Classificação já existe com este nome")
    
    classificacao = Classificacao(
        nome=dados.nome.upper(),
        tipo=dados.tipo,
        categoria_padrao=dados.categoria_padrao,
        ativo=True
    )
    db.add(classificacao)
    db.commit()
    db.refresh(classificacao)
    
    return classificacao


@app.put("/api/classificacoes/{classificacao_id}")
def atualizar_classificacao(classificacao_id: int, dados: ClassificacaoUpdate, db: Session = Depends(get_db)):
    """Atualiza uma classificação existente"""
    classificacao = db.query(Classificacao).filter(Classificacao.id == classificacao_id).first()
    if not classificacao:
        raise HTTPException(status_code=404, detail="Classificação não encontrada")
    
    if dados.nome:
        # Verificar se já existe outra com este nome
        existente = db.query(Classificacao).filter(
            Classificacao.nome == dados.nome.upper(),
            Classificacao.id != classificacao_id
        ).first()
        if existente:
            raise HTTPException(status_code=400, detail="Já existe outra classificação com este nome")
        classificacao.nome = dados.nome.upper()
    
    if dados.tipo:
        classificacao.tipo = dados.tipo
    
    if dados.categoria_padrao:
        classificacao.categoria_padrao = dados.categoria_padrao
    
    db.commit()
    db.refresh(classificacao)
    
    return classificacao


@app.delete("/api/classificacoes/{classificacao_id}")
def excluir_classificacao(classificacao_id: int, db: Session = Depends(get_db)):
    """Exclui uma classificação (soft delete)"""
    classificacao = db.query(Classificacao).filter(Classificacao.id == classificacao_id).first()
    if not classificacao:
        raise HTTPException(status_code=404, detail="Classificação não encontrada")
    
    # Soft delete - apenas marca como inativo
    classificacao.ativo = False
    db.commit()
    
    return {"message": f"Classificação '{classificacao.nome}' excluída com sucesso"}


@app.get("/api/classificacoes/tipos")
def listar_tipos_classificacao():
    """Lista tipos de classificação disponíveis"""
    return [
        {"codigo": "CUSTO_FIXO", "nome": "Custo Fixo"},
        {"codigo": "CUSTO_VARIAVEL", "nome": "Custo Variável"},
        {"codigo": "DESPESA_FIXA", "nome": "Despesa Fixa"},
        {"codigo": "DESPESA_VARIAVEL", "nome": "Despesa Variável"},
        {"codigo": "IMPOSTO", "nome": "Imposto"},
        {"codigo": "RECEITA", "nome": "Receita"},
        {"codigo": "FINANCEIRO", "nome": "Financeiro"},
        {"codigo": "INVESTIMENTO", "nome": "Investimento"},
    ]


# ============== ROTAS - AUTOCOMPLETE ==============
@app.get("/api/autocomplete/itens")
def autocomplete_itens(q: str = "", limite: int = 10, db: Session = Depends(get_db)):
    """Autocomplete de itens/fornecedores"""
    if len(q) < 2:
        return []
    
    itens = db.query(ItemFornecedor).filter(
        ItemFornecedor.nome.ilike(f"%{q}%")
    ).order_by(
        ItemFornecedor.vezes_usado.desc()
    ).limit(limite).all()
    
    resultado = []
    for item in itens:
        classif = None
        if item.classificacao_id:
            classif_obj = db.query(Classificacao).filter(Classificacao.id == item.classificacao_id).first()
            classif = classif_obj.nome if classif_obj else None
        
        resultado.append({
            "nome": item.nome,
            "classificacao_sugerida": classif,
            "vezes_usado": item.vezes_usado
        })
    
    return resultado


# ============== ROTAS - CONFIGURAÇÕES ==============
@app.get("/api/configuracoes")
def listar_configuracoes(db: Session = Depends(get_db)):
    """Lista todas as configurações"""
    return db.query(Configuracao).all()


@app.put("/api/configuracoes/{chave}")
def atualizar_configuracao(chave: str, dados: ConfiguracaoUpdate, db: Session = Depends(get_db)):
    """Atualiza uma configuração"""
    config = db.query(Configuracao).filter(Configuracao.chave == chave).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    
    config.valor = dados.valor
    db.commit()
    
    return {"message": "Configuração atualizada", "chave": chave, "valor": dados.valor}


# ============== ROTAS - FLUXO DE CAIXA ==============
@app.get("/api/fluxo-caixa")
def get_fluxo_caixa(mes: int = None, ano: int = 2025, db: Session = Depends(get_db)):
    """Retorna fluxo de caixa diário do mês"""
    if mes is None:
        mes = date.today().month
    
    # Buscar saldo inicial do mês
    saldo_inicial = 0
    if mes > 1:
        resumo_anterior = db.query(ResumoMensal).filter(
            ResumoMensal.mes == mes - 1,
            ResumoMensal.ano == ano
        ).first()
        if resumo_anterior:
            saldo_inicial = resumo_anterior.saldo_final
    
    # Buscar lançamentos do mês agrupados por dia
    lancamentos = db.query(Lancamento).filter(
        Lancamento.mes == mes,
        Lancamento.ano == ano
    ).order_by(Lancamento.dia).all()
    
    # Agrupar por dia
    dias = {}
    for l in lancamentos:
        if l.dia not in dias:
            dias[l.dia] = {"entradas": 0, "saidas": 0}
        
        if l.tipo == "ENTRADA":
            dias[l.dia]["entradas"] += l.valor
        else:
            dias[l.dia]["saidas"] += l.valor
    
    # Calcular saldos
    fluxo = []
    saldo_acumulado = saldo_inicial
    
    for dia in sorted(dias.keys()):
        entradas = dias[dia]["entradas"]
        saidas = dias[dia]["saidas"]
        saldo_dia = entradas - saidas
        saldo_acumulado += saldo_dia
        
        fluxo.append({
            "dia": dia,
            "entradas": entradas,
            "saidas": saidas,
            "saldo_dia": saldo_dia,
            "saldo_acumulado": saldo_acumulado
        })
    
    return {
        "mes": mes,
        "ano": ano,
        "saldo_inicial": saldo_inicial,
        "fluxo_diario": fluxo,
        "saldo_final": saldo_acumulado
    }


# ============== ROTAS - RESUMOS ==============
@app.get("/api/resumos/mensal")
def get_resumo_mensal(mes: int = None, ano: int = 2025, db: Session = Depends(get_db)):
    """Retorna resumo de um mês específico"""
    if mes is None:
        mes = date.today().month
    
    resumo = db.query(ResumoMensal).filter(
        ResumoMensal.mes == mes,
        ResumoMensal.ano == ano
    ).first()
    
    if not resumo:
        return {"message": "Resumo não encontrado para este período"}
    
    return resumo


@app.get("/api/resumos/anual")
def get_resumo_anual(ano: int = 2025, db: Session = Depends(get_db)):
    """Retorna resumo anual consolidado"""
    resumos = db.query(ResumoMensal).filter(ResumoMensal.ano == ano).all()
    
    return {
        "ano": ano,
        "total_entradas": sum(r.total_entradas for r in resumos),
        "total_saidas": sum(r.total_saidas for r in resumos),
        "custo_fixo_total": sum(r.custo_fixo for r in resumos),
        "custo_variavel_total": sum(r.custo_variavel for r in resumos),
        "despesa_fixa_total": sum(r.despesa_fixa for r in resumos),
        "despesa_variavel_total": sum(r.despesa_variavel for r in resumos),
        "impostos_total": sum(r.impostos for r in resumos),
        "meses": [
            {
                "mes": r.mes,
                "entradas": r.total_entradas,
                "saidas": r.total_saidas,
                "saldo": r.saldo_final
            }
            for r in sorted(resumos, key=lambda x: x.mes)
        ]
    }


# ============== ROTA DE SAÚDE ==============
@app.get("/api/health")
def health_check():
    """Verifica se a API está funcionando"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ============== ROTAS PARA SERVIR HTML ==============
from fastapi.responses import FileResponse

@app.get("/")
async def serve_index():
    """Serve a página principal"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{page}.html")
async def serve_page(page: str):
    """Serve páginas HTML"""
    file_path = os.path.join(FRONTEND_DIR, f"{page}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "Página não encontrada"}


# ============== ROTAS - IMPORTAÇÃO ==============

# Mapeamento de meses
MESES_ABAS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
              'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']

def limpar_valor(valor):
    """Converte valor para float"""
    if pd.isna(valor) or valor == '' or valor == 0:
        return 0.0
    try:
        return float(valor)
    except:
        return 0.0

def limpar_texto(texto):
    """Limpa texto removendo espaços extras"""
    if pd.isna(texto) or texto is None:
        return None
    return str(texto).strip()

def obter_classificacao_id(db, nome_classificacao):
    """Obtém o ID da classificação pelo nome"""
    if not nome_classificacao or pd.isna(nome_classificacao):
        return None, None
    nome = limpar_texto(nome_classificacao)
    classif = db.query(Classificacao).filter(Classificacao.nome == nome).first()
    if classif:
        return classif.id, nome
    return None, nome

def registrar_item_fornecedor(db, nome_item, classificacao_id):
    """Registra item/fornecedor para autocomplete"""
    if not nome_item or pd.isna(nome_item):
        return
    nome = limpar_texto(nome_item).upper()
    if not nome or nome == '0' or nome == 'NAN':
        return
    item_existente = db.query(ItemFornecedor).filter(ItemFornecedor.nome == nome).first()
    if item_existente:
        item_existente.vezes_usado += 1
        item_existente.ultima_vez = datetime.utcnow()
        if classificacao_id:
            item_existente.classificacao_id = classificacao_id
    else:
        novo_item = ItemFornecedor(
            nome=nome,
            classificacao_id=classificacao_id,
            vezes_usado=1
        )
        db.add(novo_item)

def lancamento_existe(db, data, tipo, item, valor):
    """Verifica se um lançamento já existe (para evitar duplicatas)"""
    return db.query(Lancamento).filter(
        Lancamento.data == data,
        Lancamento.tipo == tipo,
        Lancamento.item == item,
        Lancamento.valor == valor
    ).first()

def importar_lancamentos_mes(db, df, mes_num, ano, modo):
    """Importa lançamentos de um mês específico"""
    lancamentos_novos = 0
    lancamentos_atualizados = 0
    lancamentos_ignorados = 0
    
    # Encontrar linha de cabeçalho
    header_row = None
    for idx, row in df.iterrows():
        if 'DIA' in str(row.values):
            header_row = idx
            break
    
    if header_row is None:
        return 0, 0, 0
    
    # Processar ENTRADAS
    for idx in range(header_row + 1, len(df)):
        row = df.iloc[idx]
        valor_entrada = limpar_valor(row.iloc[5]) if len(row) > 5 else 0
        
        if valor_entrada > 0:
            dia = int(row.iloc[1]) if not pd.isna(row.iloc[1]) else None
            if dia is None:
                continue
            
            categoria = limpar_texto(row.iloc[2]) or "OPERACIONAL"
            classificacao_nome = limpar_texto(row.iloc[3])
            item = limpar_texto(row.iloc[4])
            situacao = limpar_texto(row.iloc[6]) or "BAIXADA"
            situacao = situacao.replace(" ", "_").replace("Ã", "A").upper()
            
            classif_id, classif_nome = obter_classificacao_id(db, classificacao_nome)
            registrar_item_fornecedor(db, item, classif_id)
            
            data_lanc = date(ano, mes_num, dia)
            existente = lancamento_existe(db, data_lanc, "ENTRADA", item, valor_entrada)
            
            if existente:
                if modo == "merge":
                    existente.categoria = categoria
                    existente.classificacao_id = classif_id
                    existente.classificacao_nome = classif_nome
                    existente.situacao = situacao
                    lancamentos_atualizados += 1
                else:
                    lancamentos_ignorados += 1
            else:
                lancamento = Lancamento(
                    data=data_lanc,
                    dia=dia,
                    mes=mes_num,
                    ano=ano,
                    tipo="ENTRADA",
                    categoria=categoria,
                    classificacao_id=classif_id,
                    classificacao_nome=classif_nome,
                    item=item,
                    valor=valor_entrada,
                    situacao=situacao
                )
                db.add(lancamento)
                lancamentos_novos += 1
        
        # Processar SAÍDAS
        if len(row) > 11:
            valor_saida = limpar_valor(row.iloc[11]) if len(row) > 11 else 0
            
            if valor_saida > 0:
                dia_saida = row.iloc[7] if not pd.isna(row.iloc[7]) else None
                if dia_saida is not None:
                    try:
                        dia_saida = int(dia_saida)
                    except:
                        continue
                    
                    categoria_saida = limpar_texto(row.iloc[8]) or "OPERACIONAL"
                    classificacao_saida = limpar_texto(row.iloc[9])
                    item_saida = limpar_texto(row.iloc[10])
                    situacao_saida = limpar_texto(row.iloc[12]) if len(row) > 12 else "BAIXADA"
                    situacao_saida = situacao_saida.replace(" ", "_").replace("Ã", "A").upper() if situacao_saida else "BAIXADA"
                    
                    classif_id_saida, classif_nome_saida = obter_classificacao_id(db, classificacao_saida)
                    registrar_item_fornecedor(db, item_saida, classif_id_saida)
                    
                    data_lanc_saida = date(ano, mes_num, dia_saida)
                    existente_saida = lancamento_existe(db, data_lanc_saida, "SAIDA", item_saida, valor_saida)
                    
                    if existente_saida:
                        if modo == "merge":
                            existente_saida.categoria = categoria_saida
                            existente_saida.classificacao_id = classif_id_saida
                            existente_saida.classificacao_nome = classif_nome_saida
                            existente_saida.situacao = situacao_saida
                            lancamentos_atualizados += 1
                        else:
                            lancamentos_ignorados += 1
                    else:
                        lancamento_saida = Lancamento(
                            data=data_lanc_saida,
                            dia=dia_saida,
                            mes=mes_num,
                            ano=ano,
                            tipo="SAIDA",
                            categoria=categoria_saida,
                            classificacao_id=classif_id_saida,
                            classificacao_nome=classif_nome_saida,
                            item=item_saida,
                            valor=valor_saida,
                            situacao=situacao_saida
                        )
                        db.add(lancamento_saida)
                        lancamentos_novos += 1
    
    return lancamentos_novos, lancamentos_atualizados, lancamentos_ignorados


@app.post("/api/importar")
async def importar_planilha(
    arquivo: UploadFile = File(...),
    modo: str = Form("incremental"),
    ano: int = Form(2025),
    db: Session = Depends(get_db)
):
    """
    Importa planilha Excel
    Modos:
    - incremental: apenas adiciona novos (não duplica)
    - merge: atualiza existentes e adiciona novos
    - substituir: apaga tudo e reimporta
    """
    
    if not arquivo.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Arquivo deve ser Excel (.xlsx ou .xls)")
    
    # Salvar arquivo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        shutil.copyfileobj(arquivo.file, tmp)
        tmp_path = tmp.name
    
    try:
        total_novos = 0
        total_atualizados = 0
        total_ignorados = 0
        meses_processados = []
        
        # Se modo substituir, apagar tudo primeiro
        if modo == "substituir":
            db.query(Lancamento).filter(Lancamento.ano == ano).delete()
            db.commit()
        
        # Processar cada aba (mês)
        for mes_idx, mes_nome in enumerate(MESES_ABAS):
            try:
                df = pd.read_excel(tmp_path, sheet_name=mes_nome, header=None)
                mes_num = mes_idx + 1
                
                novos, atualizados, ignorados = importar_lancamentos_mes(db, df, mes_num, ano, modo)
                
                if novos > 0 or atualizados > 0:
                    meses_processados.append(mes_nome)
                
                total_novos += novos
                total_atualizados += atualizados
                total_ignorados += ignorados
                
            except Exception as e:
                print(f"Erro ao processar {mes_nome}: {e}")
                continue
        
        db.commit()
        
        # Limpar arquivo temporário
        os.unlink(tmp_path)
        
        return {
            "sucesso": True,
            "modo": modo,
            "ano": ano,
            "lancamentos_novos": total_novos,
            "lancamentos_atualizados": total_atualizados,
            "lancamentos_ignorados": total_ignorados,
            "meses_processados": meses_processados,
            "mensagem": f"Importação concluída! {total_novos} novos, {total_atualizados} atualizados, {total_ignorados} ignorados."
        }
        
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Erro na importação: {str(e)}")


# ============== NFE - INTEGRAÇÃO SEFAZ ==============

@app.get("/api/nfe/status")
async def nfe_status():
    """Verifica status da configuração do certificado"""
    try:
        from backend.sefaz_service import SefazService
        
        service = SefazService()
        return service.get_status()
        
    except Exception as e:
        return {
            "certificado_configurado": False,
            "senha_configurada": False,
            "ambiente": "producao",
            "erro": str(e)
        }


@app.get("/api/nfe/consultar")
async def nfe_consultar(ultimo_nsu: str = "0"):
    """
    Consulta NFe destinadas ao CNPJ na SEFAZ
    
    Args:
        ultimo_nsu: Último NSU para paginação (default: 0 = desde o início)
    """
    try:
        from backend.sefaz_service import SefazService
        
        service = SefazService()
        resultado = service.consultar_nfe(ultimo_nsu)
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na consulta: {str(e)}")


@app.get("/api/nfe/consultar-chave/{chave}")
async def nfe_consultar_chave(chave: str):
    """
    Consulta NFe específica por chave de acesso
    
    Args:
        chave: Chave de acesso da NFe (44 dígitos)
    """
    if len(chave) != 44:
        raise HTTPException(status_code=400, detail="Chave de acesso deve ter 44 dígitos")
    
    try:
        from backend.sefaz_service import SefazService
        
        service = SefazService()
        resultado = service.consultar_por_chave(chave)
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na consulta: {str(e)}")


@app.post("/api/nfe/upload-xml")
async def nfe_upload_xml(files: List[UploadFile] = File(...)):
    """
    Processa upload de arquivos XML de NFe
    
    Args:
        files: Lista de arquivos XML
    """
    try:
        from backend.sefaz_service import processar_xml_upload
        
        resultados = []
        
        for file in files:
            if not file.filename.endswith('.xml'):
                continue
                
            content = await file.read()
            xml_content = content.decode('utf-8')
            
            dados = processar_xml_upload(xml_content)
            if dados:
                dados['arquivo'] = file.filename
                resultados.append(dados)
        
        return {
            "success": True,
            "total": len(resultados),
            "documentos": resultados
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")


class ImportarNFeRequest(BaseModel):
    documentos: List[dict]
    categoria: str = "OPERACIONAL"
    classificacao: Optional[str] = None


@app.post("/api/nfe/importar")
async def nfe_importar(request: ImportarNFeRequest, db: Session = Depends(get_db)):
    """
    Importa documentos NFe como lançamentos
    
    Args:
        request: Lista de documentos para importar
    """
    try:
        importados = 0
        duplicados = []
        erros = []
        
        for doc in request.documentos:
            try:
                numero_nf = doc.get('numero_nf', '')
                
                # Verificar se já existe lançamento com esta NF
                if numero_nf:
                    existe = db.query(Lancamento).filter(
                        Lancamento.item.like(f"% - NF {numero_nf}")
                    ).first()
                    
                    if existe:
                        duplicados.append({
                            "documento": numero_nf,
                            "mensagem": f"NF {numero_nf} já existe no sistema"
                        })
                        continue
                
                # Determinar tipo (ENTRADA = receber, SAIDA = pagar)
                tipo = doc.get('tipo_lancamento', 'SAIDA')
                
                # Determinar data
                data_str = doc.get('data_vencimento') or doc.get('data_emissao')
                if data_str:
                    data_lanc = datetime.strptime(data_str[:10], '%Y-%m-%d').date()
                else:
                    data_lanc = date.today()
                
                # Buscar classificação
                classificacao_nome = request.classificacao if request.classificacao else None
                if not classificacao_nome:
                    # Usar classificação padrão baseada no tipo
                    classificacao_nome = "FORNECEDORES" if tipo == "SAIDA" else "CLIENTES"
                
                # Verificar se classificação existe
                classif = db.query(Classificacao).filter(
                    Classificacao.nome == classificacao_nome
                ).first()
                
                # Criar lançamento
                lancamento = Lancamento(
                    data=data_lanc,
                    dia=data_lanc.day,
                    mes=data_lanc.month,
                    ano=data_lanc.year,
                    tipo=tipo,
                    categoria=request.categoria,
                    classificacao_nome=classificacao_nome if classif else None,
                    item=f"{doc.get('fornecedor_cliente', '')[:150]} - NF {numero_nf}",
                    valor=doc.get('valor_total', 0),
                    situacao='NAO_BAIXADA'
                )
                
                db.add(lancamento)
                importados += 1
                
            except Exception as e:
                erros.append({
                    "documento": doc.get('numero_nf', 'desconhecido'),
                    "erro": str(e)
                })
        
        db.commit()
        
        return {
            "success": True,
            "importados": importados,
            "duplicados": duplicados,
            "erros": erros
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro na importação: {str(e)}")


# ============== MAIN ==============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
