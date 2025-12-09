"""
Sistema Financeiro Finco - Modelo de Banco de Dados
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date
import enum

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'financeiro_finco.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Enums
class TipoLancamento(str, enum.Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class Categoria(str, enum.Enum):
    OPERACIONAL = "OPERACIONAL"
    FINANCEIRO = "FINANCEIRO"
    INVESTIMENTO = "INVESTIMENTO"


class TipoClassificacao(str, enum.Enum):
    CUSTO_FIXO = "CUSTO_FIXO"
    CUSTO_VARIAVEL = "CUSTO_VARIAVEL"
    DESPESA_FIXA = "DESPESA_FIXA"
    DESPESA_VARIAVEL = "DESPESA_VARIAVEL"
    IMPOSTO = "IMPOSTO"
    RECEITA = "RECEITA"
    FINANCEIRO = "FINANCEIRO"
    INVESTIMENTO = "INVESTIMENTO"


class Situacao(str, enum.Enum):
    BAIXADA = "BAIXADA"
    NAO_BAIXADA = "NAO_BAIXADA"


# Tabelas
class Classificacao(Base):
    """Tabela de classificações padronizadas"""
    __tablename__ = "classificacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)
    tipo = Column(String(50), nullable=False)  # CUSTO_FIXO, CUSTO_VARIAVEL, etc.
    categoria_padrao = Column(String(50), default="OPERACIONAL")
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    lancamentos = relationship("Lancamento", back_populates="classificacao_rel")
    itens = relationship("ItemFornecedor", back_populates="classificacao_rel")


class ItemFornecedor(Base):
    """Tabela para autocomplete - mapeia item/fornecedor para classificação"""
    __tablename__ = "itens_fornecedores"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    classificacao_id = Column(Integer, ForeignKey("classificacoes.id"))
    vezes_usado = Column(Integer, default=1)
    ultima_vez = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamento
    classificacao_rel = relationship("Classificacao", back_populates="itens")


class Lancamento(Base):
    """Tabela principal de lançamentos (entradas e saídas)"""
    __tablename__ = "lancamentos"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Dados do lançamento
    data = Column(Date, nullable=False)
    dia = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    
    # Tipo e categoria
    tipo = Column(String(20), nullable=False)  # ENTRADA ou SAIDA
    categoria = Column(String(50), nullable=False)  # OPERACIONAL, FINANCEIRO, INVESTIMENTO
    
    # Classificação
    classificacao_id = Column(Integer, ForeignKey("classificacoes.id"))
    classificacao_nome = Column(String(100))  # Redundância para performance
    
    # Detalhes
    item = Column(String(200))  # Descrição ou fornecedor
    valor = Column(Float, nullable=False)
    situacao = Column(String(20), default="BAIXADA")  # BAIXADA ou NAO_BAIXADA
    
    # Metadados
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    classificacao_rel = relationship("Classificacao", back_populates="lancamentos")


class SaldoDiario(Base):
    """Tabela de saldos diários para fluxo de caixa"""
    __tablename__ = "saldos_diarios"
    
    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, unique=True, nullable=False)
    dia = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    
    saldo_inicial = Column(Float, default=0)
    total_entradas = Column(Float, default=0)
    total_saidas = Column(Float, default=0)
    saldo_do_dia = Column(Float, default=0)
    saldo_final = Column(Float, default=0)
    
    # Fluxos por categoria
    fluxo_operacional = Column(Float, default=0)
    fluxo_financeiro = Column(Float, default=0)
    fluxo_investimento = Column(Float, default=0)
    
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResumoMensal(Base):
    """Tabela de resumos mensais"""
    __tablename__ = "resumos_mensais"
    
    id = Column(Integer, primary_key=True, index=True)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    
    # Totais
    total_entradas = Column(Float, default=0)
    total_saidas = Column(Float, default=0)
    saldo_inicial = Column(Float, default=0)
    saldo_final = Column(Float, default=0)
    
    # Por tipo de custo/despesa
    custo_fixo = Column(Float, default=0)
    custo_variavel = Column(Float, default=0)
    despesa_fixa = Column(Float, default=0)
    despesa_variavel = Column(Float, default=0)
    impostos = Column(Float, default=0)
    
    # Fluxos
    fluxo_operacional = Column(Float, default=0)
    fluxo_financeiro = Column(Float, default=0)
    fluxo_investimento = Column(Float, default=0)
    
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class Config:
        unique_together = ('mes', 'ano')


class Configuracao(Base):
    """Tabela de configurações do sistema"""
    __tablename__ = "configuracoes"
    
    id = Column(Integer, primary_key=True, index=True)
    chave = Column(String(50), unique=True, nullable=False)
    valor = Column(String(200))
    descricao = Column(String(500))
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Usuario(Base):
    """Tabela de usuários"""
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    senha_hash = Column(String(200), nullable=False)
    nome = Column(String(100))
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)


# Funções auxiliares
def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas():
    """Cria todas as tabelas no banco"""
    Base.metadata.create_all(bind=engine)


def inicializar_configuracoes(db):
    """Inicializa configurações padrão do Miller-Orr"""
    configs_padrao = [
        ("miller_orr_minimo", "55000", "Saldo mínimo do caixa (Miller-Orr)"),
        ("miller_orr_retorno", "100000", "Ponto de retorno do caixa (Miller-Orr)"),
        ("miller_orr_maximo", "355000", "Saldo máximo do caixa (Miller-Orr)"),
        ("saldo_inicial_ano", "0", "Saldo inicial do ano"),
        ("ano_vigente", "2025", "Ano vigente do sistema"),
    ]
    
    for chave, valor, descricao in configs_padrao:
        existe = db.query(Configuracao).filter(Configuracao.chave == chave).first()
        if not existe:
            config = Configuracao(chave=chave, valor=valor, descricao=descricao)
            db.add(config)
    
    db.commit()


# Lista de classificações padrão baseadas na planilha
CLASSIFICACOES_PADRAO = [
    # CUSTO FIXO (Produção)
    ("SALÁRIOS FÁBRICA", "CUSTO_FIXO", "OPERACIONAL"),
    ("ALUGUEL / SEGUROS / ETC", "CUSTO_FIXO", "OPERACIONAL"),
    ("MANUTENÇÃO MÁQ / FERRAM", "CUSTO_FIXO", "OPERACIONAL"),
    ("MATERIAL DE CONSUMO", "CUSTO_FIXO", "OPERACIONAL"),
    ("REFEIÇÃO LOCAL", "CUSTO_FIXO", "OPERACIONAL"),
    ("SEGURANÇA DO TRABALHO", "CUSTO_FIXO", "OPERACIONAL"),
    ("VALE ALIMENTAÇÃO", "CUSTO_FIXO", "OPERACIONAL"),
    ("VALE TRANSPORTE", "CUSTO_FIXO", "OPERACIONAL"),
    
    # CUSTO VARIÁVEL (Produção)
    ("MATÉRIA-PRIMA", "CUSTO_VARIAVEL", "OPERACIONAL"),
    ("ANODIZAÇÃO", "CUSTO_VARIAVEL", "OPERACIONAL"),
    ("COMPONENTES", "CUSTO_VARIAVEL", "OPERACIONAL"),
    ("GALVANIZAÇÃO", "CUSTO_VARIAVEL", "OPERACIONAL"),
    ("MATERIAL EMBALAGENS", "CUSTO_VARIAVEL", "OPERACIONAL"),
    ("PINTURA EXTERNA", "CUSTO_VARIAVEL", "OPERACIONAL"),
    ("PINTURA INTERNA", "CUSTO_VARIAVEL", "OPERACIONAL"),
    
    # DESPESA FIXA (Administrativa)
    ("LIMPEZA", "DESPESA_FIXA", "OPERACIONAL"),
    ("ABRAVA", "DESPESA_FIXA", "OPERACIONAL"),
    ("AÇÕES TRABALHISTAS", "DESPESA_FIXA", "OPERACIONAL"),
    ("ASSISTÊNCIA MÉDICA", "DESPESA_FIXA", "OPERACIONAL"),
    ("CARTORIOS/ LICENÇAS", "DESPESA_FIXA", "OPERACIONAL"),
    ("CATÁLOGOS", "DESPESA_FIXA", "OPERACIONAL"),
    ("CONTABILIDADE", "DESPESA_FIXA", "OPERACIONAL"),
    ("DESP. ADMISSÃO", "DESPESA_FIXA", "OPERACIONAL"),
    ("DESP. DEMISSÃO", "DESPESA_FIXA", "OPERACIONAL"),
    ("FEIRAS / EXIBIÇÕES/ASSOCIAÇÕES", "DESPESA_FIXA", "OPERACIONAL"),
    ("MANUTENÇÃO PREDIAL", "DESPESA_FIXA", "OPERACIONAL"),
    ("MATERIAL ESCRITÓRIO", "DESPESA_FIXA", "OPERACIONAL"),
    ("PASSAGENS / ESTADIAS", "DESPESA_FIXA", "OPERACIONAL"),
    ("SALÁRIOS ESCRITÓRIO", "DESPESA_FIXA", "OPERACIONAL"),
    ("SERVIÇO TERCEIROS", "DESPESA_FIXA", "OPERACIONAL"),
    ("SERVIÇOS DIVERSOS", "DESPESA_FIXA", "OPERACIONAL"),
    ("SINDICATO", "DESPESA_FIXA", "OPERACIONAL"),
    ("SISA", "DESPESA_FIXA", "OPERACIONAL"),
    ("SISTEMAS", "DESPESA_FIXA", "OPERACIONAL"),
    ("SITE INTERNET", "DESPESA_FIXA", "OPERACIONAL"),
    ("TELEFONE / COMUNICAÇÃO", "DESPESA_FIXA", "OPERACIONAL"),
    ("TREINAMENTOS", "DESPESA_FIXA", "OPERACIONAL"),
    
    # DESPESA VARIÁVEL
    ("COMISSÃO DE VENDAS", "DESPESA_VARIAVEL", "OPERACIONAL"),
    ("FRETES", "DESPESA_VARIAVEL", "OPERACIONAL"),
    ("CORREIO/MOTOBOY/ETC", "DESPESA_VARIAVEL", "OPERACIONAL"),
    
    # IMPOSTOS
    ("FGTS", "IMPOSTO", "OPERACIONAL"),
    ("COFINS+PIS+IPI", "IMPOSTO", "OPERACIONAL"),
    ("CSLL", "IMPOSTO", "OPERACIONAL"),
    ("DARF REPRES", "IMPOSTO", "OPERACIONAL"),
    ("DIFAL", "IMPOSTO", "OPERACIONAL"),
    ("GPS", "IMPOSTO", "OPERACIONAL"),
    ("ICMS", "IMPOSTO", "OPERACIONAL"),
    ("INSS", "IMPOSTO", "OPERACIONAL"),
    ("IRPJ", "IMPOSTO", "OPERACIONAL"),
    ("IRRF", "IMPOSTO", "OPERACIONAL"),
    
    # FINANCEIRO
    ("AMORTIZAÇÃO", "FINANCEIRO", "FINANCEIRO"),
    ("APORTE DE CAPITAL", "FINANCEIRO", "FINANCEIRO"),
    ("DIVIDENDOS", "FINANCEIRO", "FINANCEIRO"),
    ("EMPRÉSTIMO", "FINANCEIRO", "FINANCEIRO"),
    ("FINANCIAMENTO", "FINANCEIRO", "FINANCEIRO"),
    ("JUROS", "FINANCEIRO", "FINANCEIRO"),
    ("TARIFA BANCÁRIA", "FINANCEIRO", "FINANCEIRO"),
    
    # INVESTIMENTO
    ("AMPLIAÇÃO/OBRA/REFORMA", "INVESTIMENTO", "INVESTIMENTO"),
    ("COMPONENTES DE MÁQUINAS", "INVESTIMENTO", "INVESTIMENTO"),
    ("FERRAMENTAS/ DISPOSITIVOS", "INVESTIMENTO", "INVESTIMENTO"),
    ("IMOBILIZADO", "INVESTIMENTO", "INVESTIMENTO"),
    ("MÁQUINAS", "INVESTIMENTO", "INVESTIMENTO"),
    ("MOBILIÁRIO", "INVESTIMENTO", "INVESTIMENTO"),
    ("NORMAS", "INVESTIMENTO", "INVESTIMENTO"),
    ("RENDIMENTO DE APLICAÇÃO", "INVESTIMENTO", "INVESTIMENTO"),
    ("SOFTWARES", "INVESTIMENTO", "INVESTIMENTO"),
    ("TESTES / DESENVOLVIMENTOS", "INVESTIMENTO", "INVESTIMENTO"),
    ("TI", "INVESTIMENTO", "INVESTIMENTO"),
    
    # RECEITA
    ("VENDA DE PRODUTOS", "RECEITA", "OPERACIONAL"),
    
    # EXTRAS identificados na planilha
    ("ALIMENTAÇÃO", "DESPESA_FIXA", "OPERACIONAL"),
]


def inicializar_classificacoes(db):
    """Inicializa classificações padrão"""
    for nome, tipo, categoria in CLASSIFICACOES_PADRAO:
        existe = db.query(Classificacao).filter(Classificacao.nome == nome).first()
        if not existe:
            classif = Classificacao(nome=nome, tipo=tipo, categoria_padrao=categoria)
            db.add(classif)
    
    db.commit()


if __name__ == "__main__":
    # Teste de criação do banco
    criar_tabelas()
    db = SessionLocal()
    inicializar_configuracoes(db)
    inicializar_classificacoes(db)
    db.close()
    print("✅ Banco de dados criado e inicializado!")
