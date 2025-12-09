"""
Sistema Financeiro Finco - Importador de Dados do Excel
Importa dados das planilhas existentes para o banco de dados
"""
import pandas as pd
from datetime import datetime, date
from backend.database import (
    SessionLocal, criar_tabelas, inicializar_configuracoes, 
    inicializar_classificacoes, Lancamento, Classificacao,
    ItemFornecedor, SaldoDiario, ResumoMensal, Configuracao
)
import os

# Mapeamento de meses
MESES = {
    'JANEIRO': 1, 'FEVEREIRO': 2, 'MARÇO': 3, 'ABRIL': 4,
    'MAIO': 5, 'JUNHO': 6, 'JULHO': 7, 'AGOSTO': 8,
    'SETEMBRO': 9, 'OUTUBRO': 10, 'NOVEMBRO': 11, 'DEZEMBRO': 12
}

MESES_ABAS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO',
              'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']


def limpar_valor(valor):
    """Converte valor para float, tratando casos especiais"""
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
    """Registra item/fornecedor para autocomplete futuro"""
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


def importar_lancamentos_mes(db, df, mes_num, ano=2025):
    """Importa lançamentos de um mês específico"""
    lancamentos_importados = 0
    
    # Encontrar linha de cabeçalho (onde tem 'DIA')
    header_row = None
    for idx, row in df.iterrows():
        if 'DIA' in str(row.values):
            header_row = idx
            break
    
    if header_row is None:
        print(f"  ⚠️ Cabeçalho não encontrado para mês {mes_num}")
        return 0
    
    # Processar ENTRADAS (colunas B-G, índices 1-6)
    # Estrutura: DIA | CATEGORIA | CLASSIFICAÇÃO | ITEM | VALOR | SITUAÇÃO
    for idx in range(header_row + 1, len(df)):
        row = df.iloc[idx]
        
        # Verificar se há entrada (coluna E - VALOR de entrada)
        valor_entrada = limpar_valor(row.iloc[5]) if len(row) > 5 else 0
        
        if valor_entrada > 0:
            dia = int(row.iloc[1]) if not pd.isna(row.iloc[1]) else None
            
            # Se não tem dia, pegar o último dia válido
            if dia is None:
                continue
                
            categoria = limpar_texto(row.iloc[2]) or "OPERACIONAL"
            classificacao_nome = limpar_texto(row.iloc[3])
            item = limpar_texto(row.iloc[4])
            situacao = limpar_texto(row.iloc[6]) or "BAIXADA"
            
            classif_id, classif_nome = obter_classificacao_id(db, classificacao_nome)
            
            # Registrar item para autocomplete
            registrar_item_fornecedor(db, item, classif_id)
            
            lancamento = Lancamento(
                data=date(ano, mes_num, dia),
                dia=dia,
                mes=mes_num,
                ano=ano,
                tipo="ENTRADA",
                categoria=categoria,
                classificacao_id=classif_id,
                classificacao_nome=classif_nome,
                item=item,
                valor=valor_entrada,
                situacao=situacao.replace(" ", "_").upper() if situacao else "BAIXADA"
            )
            db.add(lancamento)
            lancamentos_importados += 1
        
        # Verificar se há saída (colunas H-M, índices 7-12)
        # Estrutura: DIA | CATEGORIA | CLASSIFICAÇÃO | ITEM | VALOR | SITUAÇÃO
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
                    
                    classif_id_saida, classif_nome_saida = obter_classificacao_id(db, classificacao_saida)
                    
                    # Registrar item para autocomplete
                    registrar_item_fornecedor(db, item_saida, classif_id_saida)
                    
                    lancamento_saida = Lancamento(
                        data=date(ano, mes_num, dia_saida),
                        dia=dia_saida,
                        mes=mes_num,
                        ano=ano,
                        tipo="SAIDA",
                        categoria=categoria_saida,
                        classificacao_id=classif_id_saida,
                        classificacao_nome=classif_nome_saida,
                        item=item_saida,
                        valor=valor_saida,
                        situacao=situacao_saida.replace(" ", "_").upper() if situacao_saida else "BAIXADA"
                    )
                    db.add(lancamento_saida)
                    lancamentos_importados += 1
    
    return lancamentos_importados


def importar_configuracoes_miller_orr(db, df_cabecalho):
    """Importa configurações do Miller-Orr da planilha FLUXO DE CAIXA"""
    try:
        # Procurar valores na planilha de cabeçalho
        for idx, row in df_cabecalho.iterrows():
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).strip().upper()
                
                if 'MÍNIMO' in cell_str or 'MINIMO' in cell_str:
                    valor = df_cabecalho.iloc[idx, col_idx + 1] if col_idx + 1 < len(row) else None
                    if valor and not pd.isna(valor):
                        config = db.query(Configuracao).filter(Configuracao.chave == "miller_orr_minimo").first()
                        if config:
                            config.valor = str(int(float(valor)))
                
                if 'RETORNO' in cell_str:
                    valor = df_cabecalho.iloc[idx, col_idx + 1] if col_idx + 1 < len(row) else None
                    if valor and not pd.isna(valor):
                        config = db.query(Configuracao).filter(Configuracao.chave == "miller_orr_retorno").first()
                        if config:
                            config.valor = str(int(float(valor)))
                
                if 'MÁXIMO' in cell_str or 'MAXIMO' in cell_str:
                    valor = df_cabecalho.iloc[idx, col_idx + 1] if col_idx + 1 < len(row) else None
                    if valor and not pd.isna(valor):
                        config = db.query(Configuracao).filter(Configuracao.chave == "miller_orr_maximo").first()
                        if config:
                            config.valor = str(int(float(valor)))
        
        db.commit()
        print("  ✅ Configurações Miller-Orr importadas")
    except Exception as e:
        print(f"  ⚠️ Erro ao importar Miller-Orr: {e}")


def calcular_resumos_mensais(db, ano=2025):
    """Calcula e salva resumos mensais baseado nos lançamentos"""
    print("\n📊 Calculando resumos mensais...")
    
    for mes in range(1, 13):
        # Buscar lançamentos do mês
        lancamentos = db.query(Lancamento).filter(
            Lancamento.mes == mes,
            Lancamento.ano == ano
        ).all()
        
        if not lancamentos:
            continue
        
        # Calcular totais
        total_entradas = sum(l.valor for l in lancamentos if l.tipo == "ENTRADA")
        total_saidas = sum(l.valor for l in lancamentos if l.tipo == "SAIDA")
        
        # Por categoria
        fluxo_op = sum(l.valor if l.tipo == "ENTRADA" else -l.valor 
                      for l in lancamentos if l.categoria == "OPERACIONAL")
        fluxo_fin = sum(l.valor if l.tipo == "ENTRADA" else -l.valor 
                       for l in lancamentos if l.categoria == "FINANCEIRO")
        fluxo_inv = sum(l.valor if l.tipo == "ENTRADA" else -l.valor 
                       for l in lancamentos if l.categoria == "INVESTIMENTO")
        
        # Por tipo de custo/despesa
        custo_fixo = sum(l.valor for l in lancamentos 
                        if l.tipo == "SAIDA" and l.classificacao_rel and l.classificacao_rel.tipo == "CUSTO_FIXO")
        custo_var = sum(l.valor for l in lancamentos 
                       if l.tipo == "SAIDA" and l.classificacao_rel and l.classificacao_rel.tipo == "CUSTO_VARIAVEL")
        desp_fixa = sum(l.valor for l in lancamentos 
                       if l.tipo == "SAIDA" and l.classificacao_rel and l.classificacao_rel.tipo == "DESPESA_FIXA")
        desp_var = sum(l.valor for l in lancamentos 
                      if l.tipo == "SAIDA" and l.classificacao_rel and l.classificacao_rel.tipo == "DESPESA_VARIAVEL")
        impostos = sum(l.valor for l in lancamentos 
                      if l.tipo == "SAIDA" and l.classificacao_rel and l.classificacao_rel.tipo == "IMPOSTO")
        
        # Saldo inicial (do mês anterior)
        saldo_inicial = 0
        if mes > 1:
            resumo_anterior = db.query(ResumoMensal).filter(
                ResumoMensal.mes == mes - 1,
                ResumoMensal.ano == ano
            ).first()
            if resumo_anterior:
                saldo_inicial = resumo_anterior.saldo_final
        
        saldo_final = saldo_inicial + total_entradas - total_saidas
        
        # Salvar ou atualizar
        resumo = db.query(ResumoMensal).filter(
            ResumoMensal.mes == mes,
            ResumoMensal.ano == ano
        ).first()
        
        if not resumo:
            resumo = ResumoMensal(mes=mes, ano=ano)
            db.add(resumo)
        
        resumo.total_entradas = total_entradas
        resumo.total_saidas = total_saidas
        resumo.saldo_inicial = saldo_inicial
        resumo.saldo_final = saldo_final
        resumo.custo_fixo = custo_fixo
        resumo.custo_variavel = custo_var
        resumo.despesa_fixa = desp_fixa
        resumo.despesa_variavel = desp_var
        resumo.impostos = impostos
        resumo.fluxo_operacional = fluxo_op
        resumo.fluxo_financeiro = fluxo_fin
        resumo.fluxo_investimento = fluxo_inv
        
        print(f"  Mês {mes:02d}: Entradas R$ {total_entradas:,.2f} | Saídas R$ {total_saidas:,.2f} | Saldo R$ {saldo_final:,.2f}")
    
    db.commit()
    print("  ✅ Resumos mensais calculados!")


def importar_planilha_controle(caminho_arquivo, db, ano=2025):
    """Importa dados da planilha CONTROLE DE ENTRADAS E SAÍDAS"""
    print(f"\n📥 Importando: {caminho_arquivo}")
    
    try:
        xlsx = pd.ExcelFile(caminho_arquivo)
        total_importados = 0
        
        for mes_nome in MESES_ABAS:
            if mes_nome in xlsx.sheet_names:
                print(f"  📅 Processando {mes_nome}...")
                df = pd.read_excel(xlsx, sheet_name=mes_nome, header=None)
                mes_num = MESES[mes_nome]
                
                importados = importar_lancamentos_mes(db, df, mes_num, ano)
                total_importados += importados
                print(f"     ✅ {importados} lançamentos importados")
        
        db.commit()
        print(f"\n✅ Total importado da planilha Controle: {total_importados} lançamentos")
        return total_importados
        
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        import traceback
        traceback.print_exc()
        return 0


def importar_planilha_fluxo(caminho_arquivo, db):
    """Importa configurações da planilha FLUXO DE CAIXA"""
    print(f"\n📥 Importando configurações de: {caminho_arquivo}")
    
    try:
        xlsx = pd.ExcelFile(caminho_arquivo)
        
        if 'CABEÇALHO' in xlsx.sheet_names:
            df_cab = pd.read_excel(xlsx, sheet_name='CABEÇALHO', header=None)
            importar_configuracoes_miller_orr(db, df_cab)
        
        print("✅ Configurações do Fluxo de Caixa importadas")
        
    except Exception as e:
        print(f"❌ Erro ao importar fluxo: {e}")


def executar_importacao_completa(caminho_controle, caminho_fluxo):
    """Executa importação completa das duas planilhas"""
    print("=" * 60)
    print("🚀 IMPORTAÇÃO COMPLETA - SISTEMA FINANCEIRO FINCO")
    print("=" * 60)
    
    # Criar banco e tabelas
    print("\n📦 Criando banco de dados...")
    criar_tabelas()
    
    db = SessionLocal()
    
    try:
        # Inicializar dados base
        print("⚙️ Inicializando configurações...")
        inicializar_configuracoes(db)
        inicializar_classificacoes(db)
        db.commit()
        print("  ✅ Configurações e classificações criadas")
        
        # Importar planilha de controle
        total = importar_planilha_controle(caminho_controle, db)
        
        # Importar configurações do fluxo
        importar_planilha_fluxo(caminho_fluxo, db)
        
        # Calcular resumos
        calcular_resumos_mensais(db)
        
        # Estatísticas finais
        print("\n" + "=" * 60)
        print("📊 ESTATÍSTICAS DA IMPORTAÇÃO")
        print("=" * 60)
        
        total_lancamentos = db.query(Lancamento).count()
        total_entradas = db.query(Lancamento).filter(Lancamento.tipo == "ENTRADA").count()
        total_saidas = db.query(Lancamento).filter(Lancamento.tipo == "SAIDA").count()
        total_classificacoes = db.query(Classificacao).count()
        total_itens = db.query(ItemFornecedor).count()
        
        print(f"  📝 Lançamentos: {total_lancamentos}")
        print(f"     ├─ Entradas: {total_entradas}")
        print(f"     └─ Saídas: {total_saidas}")
        print(f"  📋 Classificações: {total_classificacoes}")
        print(f"  🏢 Itens/Fornecedores cadastrados: {total_itens}")
        
        # Mostrar configurações Miller-Orr
        configs = db.query(Configuracao).all()
        print(f"\n  ⚙️ Configurações Miller-Orr:")
        for c in configs:
            if 'miller' in c.chave:
                print(f"     {c.descricao}: R$ {float(c.valor):,.2f}")
        
        print("\n" + "=" * 60)
        print("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        
    finally:
        db.close()


if __name__ == "__main__":
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
    
    # Caminhos das planilhas
    CAMINHO_CONTROLE = os.path.join(DATA_DIR, "CONTROLE_DE_ENTRADAS_E_SAÍDAS_25.xlsx")
    CAMINHO_FLUXO = os.path.join(DATA_DIR, "FLUXO_DE_CAIXA_25.xlsx")
    
    # Verificar se arquivos existem
    if not os.path.exists(CAMINHO_CONTROLE):
        print(f"❌ Arquivo não encontrado: {CAMINHO_CONTROLE}")
        print("   Copie as planilhas para a pasta 'data/'")
    elif not os.path.exists(CAMINHO_FLUXO):
        print(f"❌ Arquivo não encontrado: {CAMINHO_FLUXO}")
        print("   Copie as planilhas para a pasta 'data/'")
    else:
        executar_importacao_completa(CAMINHO_CONTROLE, CAMINHO_FLUXO)
