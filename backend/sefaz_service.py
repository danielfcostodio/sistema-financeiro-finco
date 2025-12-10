"""
Sistema Financeiro Finco - Integração SEFAZ
Consulta NFe destinadas ao CNPJ via Distribuição DFe
"""

import os
import base64
import gzip
import tempfile
from datetime import datetime
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET

# Configurações
CNPJ_FINCO = "21630948000109"
UF_FINCO = "41"  # Paraná

# URLs dos webservices
SEFAZ_URLS = {
    "producao": "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    "homologacao": "https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
}

# Namespace XML
NS_NFE = "http://www.portalfiscal.inf.br/nfe"
NS_DIST = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe"
NS_SOAP = "http://www.w3.org/2003/05/soap-envelope"


class SefazService:
    """Serviço de integração com SEFAZ para consulta de NFe"""
    
    def __init__(self, certificado_path: str = None, certificado_senha: str = None):
        """
        Inicializa o serviço
        
        Args:
            certificado_path: Caminho para o arquivo .pfx/.p12
            certificado_senha: Senha do certificado
        """
        self.certificado_senha = certificado_senha or os.getenv("CERTIFICADO_SENHA", "")
        self.ambiente = os.getenv("SEFAZ_AMBIENTE", "producao")
        self.url = SEFAZ_URLS.get(self.ambiente, SEFAZ_URLS["producao"])
        
        # Tentar obter certificado do Base64 primeiro
        self.certificado_base64 = os.getenv("CERTIFICADO_BASE64", "")
        self.certificado_path = None
        self._temp_cert_file = None
        
        if self.certificado_base64:
            # Decodificar Base64 e salvar em arquivo temporário
            self._preparar_certificado_base64()
        else:
            # Fallback para arquivo direto
            self.certificado_path = certificado_path or os.getenv("CERTIFICADO_PATH", "/etc/secrets/certificado.pfx")
    
    def _preparar_certificado_base64(self):
        """Decodifica o certificado Base64 e salva em arquivo temporário"""
        try:
            # Decodificar Base64
            cert_bytes = base64.b64decode(self.certificado_base64)
            
            # Criar arquivo temporário
            self._temp_cert_file = tempfile.NamedTemporaryFile(
                mode='wb', 
                suffix='.pfx', 
                delete=False
            )
            self._temp_cert_file.write(cert_bytes)
            self._temp_cert_file.close()
            
            self.certificado_path = self._temp_cert_file.name
            
        except Exception as e:
            print(f"Erro ao preparar certificado Base64: {e}")
            self.certificado_path = None
    
    def _certificado_configurado(self) -> bool:
        """Verifica se o certificado está configurado corretamente"""
        if self.certificado_base64:
            return bool(self.certificado_path and os.path.exists(self.certificado_path))
        else:
            return bool(self.certificado_path and os.path.exists(self.certificado_path))
    
    def get_status(self) -> Dict:
        """Retorna status da configuração"""
        return {
            "certificado_configurado": self._certificado_configurado(),
            "certificado_origem": "base64" if self.certificado_base64 else "arquivo",
            "senha_configurada": bool(self.certificado_senha),
            "ambiente": self.ambiente
        }
        
    def _criar_envelope_dist_nsu(self, ultimo_nsu: str = "0") -> str:
        """
        Cria envelope SOAP para consulta por NSU
        
        Args:
            ultimo_nsu: Último NSU consultado (para paginação)
            
        Returns:
            XML do envelope SOAP
        """
        # NSU deve ter 15 dígitos
        nsu_formatado = str(ultimo_nsu).zfill(15)
        
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Header>
        <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
            <cUF>{UF_FINCO}</cUF>
            <versaoDados>1.01</versaoDados>
        </nfeCabecMsg>
    </soap12:Header>
    <soap12:Body>
        <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
            <nfeDadosMsg>
                <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
                    <tpAmb>1</tpAmb>
                    <cUFAutor>{UF_FINCO}</cUFAutor>
                    <CNPJ>{CNPJ_FINCO}</CNPJ>
                    <distNSU>
                        <ultNSU>{nsu_formatado}</ultNSU>
                    </distNSU>
                </distDFeInt>
            </nfeDadosMsg>
        </nfeDistDFeInteresse>
    </soap12:Body>
</soap12:Envelope>"""
        return envelope
    
    def _criar_envelope_cons_chave(self, chave_nfe: str) -> str:
        """
        Cria envelope SOAP para consulta por chave de acesso
        
        Args:
            chave_nfe: Chave de acesso da NFe (44 dígitos)
            
        Returns:
            XML do envelope SOAP
        """
        envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
    <soap12:Header>
        <nfeCabecMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
            <cUF>{UF_FINCO}</cUF>
            <versaoDados>1.01</versaoDados>
        </nfeCabecMsg>
    </soap12:Header>
    <soap12:Body>
        <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
            <nfeDadosMsg>
                <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
                    <tpAmb>1</tpAmb>
                    <cUFAutor>{UF_FINCO}</cUFAutor>
                    <CNPJ>{CNPJ_FINCO}</CNPJ>
                    <consChNFe>
                        <chNFe>{chave_nfe}</chNFe>
                    </consChNFe>
                </distDFeInt>
            </nfeDadosMsg>
        </nfeDistDFeInteresse>
    </soap12:Body>
</soap12:Envelope>"""
        return envelope

    def consultar_nfe(self, ultimo_nsu: str = "0") -> Dict:
        """
        Consulta NFe destinadas ao CNPJ na SEFAZ
        
        Args:
            ultimo_nsu: Último NSU para paginação
            
        Returns:
            Dict com status e lista de documentos
        """
        try:
            import requests_pkcs12
        except ImportError:
            return {
                "success": False,
                "error": "Biblioteca requests_pkcs12 não instalada. Execute: pip install requests-pkcs12"
            }
        
        # Verificar se certificado existe
        if not self.certificado_path or not os.path.exists(self.certificado_path):
            return {
                "success": False,
                "error": "Certificado não configurado. Configure CERTIFICADO_BASE64 no Render."
            }
        
        if not self.certificado_senha:
            return {
                "success": False,
                "error": "Senha do certificado não configurada. Configure CERTIFICADO_SENHA no Render."
            }
        
        try:
            # Criar envelope SOAP
            envelope = self._criar_envelope_dist_nsu(ultimo_nsu)
            
            # Headers da requisição
            headers = {
                "Content-Type": "application/soap+xml; charset=utf-8",
                "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"
            }
            
            # Fazer requisição com certificado
            response = requests_pkcs12.post(
                self.url,
                data=envelope.encode('utf-8'),
                headers=headers,
                pkcs12_filename=self.certificado_path,
                pkcs12_password=self.certificado_senha,
                timeout=60
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Erro HTTP {response.status_code}: {response.text[:500]}"
                }
            
            # Parsear resposta
            return self._parsear_resposta(response.text)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro na consulta: {str(e)}"
            }
    
    def consultar_por_chave(self, chave_nfe: str) -> Dict:
        """
        Consulta NFe específica por chave de acesso
        
        Args:
            chave_nfe: Chave de acesso (44 dígitos)
            
        Returns:
            Dict com status e documento
        """
        try:
            import requests_pkcs12
        except ImportError:
            return {
                "success": False,
                "error": "Biblioteca requests_pkcs12 não instalada"
            }
        
        if not self.certificado_path or not os.path.exists(self.certificado_path):
            return {
                "success": False,
                "error": "Certificado não configurado. Configure CERTIFICADO_BASE64 no Render."
            }
        
        try:
            envelope = self._criar_envelope_cons_chave(chave_nfe)
            
            headers = {
                "Content-Type": "application/soap+xml; charset=utf-8",
                "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"
            }
            
            response = requests_pkcs12.post(
                self.url,
                data=envelope.encode('utf-8'),
                headers=headers,
                pkcs12_filename=self.certificado_path,
                pkcs12_password=self.certificado_senha,
                timeout=60
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Erro HTTP {response.status_code}"
                }
            
            return self._parsear_resposta(response.text)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro na consulta: {str(e)}"
            }
    
    def _parsear_resposta(self, xml_response: str) -> Dict:
        """
        Parseia a resposta XML da SEFAZ
        
        Args:
            xml_response: XML de resposta
            
        Returns:
            Dict com dados parseados
        """
        try:
            # Remover BOM se existir
            if xml_response.startswith('\ufeff'):
                xml_response = xml_response[1:]
            
            root = ET.fromstring(xml_response)
            
            # Buscar retorno
            # O retorno pode estar em diferentes namespaces
            ret_dist = None
            for elem in root.iter():
                if 'retDistDFeInt' in elem.tag:
                    ret_dist = elem
                    break
            
            if ret_dist is None:
                return {
                    "success": False,
                    "error": "Resposta inválida da SEFAZ"
                }
            
            # Extrair status
            cStat = None
            xMotivo = None
            ultNSU = None
            maxNSU = None
            
            for elem in ret_dist.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'cStat':
                    cStat = elem.text
                elif tag == 'xMotivo':
                    xMotivo = elem.text
                elif tag == 'ultNSU':
                    ultNSU = elem.text
                elif tag == 'maxNSU':
                    maxNSU = elem.text
            
            # Status 138 = Documento localizado
            # Status 137 = Nenhum documento localizado
            if cStat not in ['137', '138']:
                return {
                    "success": False,
                    "error": f"SEFAZ retornou: {cStat} - {xMotivo}",
                    "cStat": cStat,
                    "xMotivo": xMotivo
                }
            
            # Extrair documentos
            documentos = []
            
            for elem in ret_dist.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'docZip':
                    # Documento está compactado em base64+gzip
                    nsu = elem.get('NSU', '')
                    schema = elem.get('schema', '')
                    
                    try:
                        # Decodificar base64 e descompactar gzip
                        compressed = base64.b64decode(elem.text)
                        xml_doc = gzip.decompress(compressed).decode('utf-8')
                        
                        # Parsear documento
                        doc_info = self._extrair_dados_nfe(xml_doc, nsu, schema)
                        if doc_info:
                            documentos.append(doc_info)
                    except Exception as e:
                        print(f"Erro ao processar documento NSU {nsu}: {e}")
                        continue
            
            return {
                "success": True,
                "cStat": cStat,
                "xMotivo": xMotivo,
                "ultNSU": ultNSU,
                "maxNSU": maxNSU,
                "documentos": documentos,
                "total": len(documentos)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro ao parsear resposta: {str(e)}"
            }
    
    def _extrair_dados_nfe(self, xml_doc: str, nsu: str, schema: str) -> Optional[Dict]:
        """
        Extrai dados relevantes de um XML de NFe
        
        Args:
            xml_doc: XML do documento
            nsu: NSU do documento
            schema: Schema do documento
            
        Returns:
            Dict com dados ou None
        """
        try:
            root = ET.fromstring(xml_doc)
            
            # Identificar tipo de documento
            is_nfe = 'procNFe' in xml_doc or 'NFe' in xml_doc
            is_resumo = 'resNFe' in xml_doc
            is_evento = 'procEventoNFe' in xml_doc
            
            dados = {
                "nsu": nsu,
                "schema": schema,
                "xml": xml_doc,
                "tipo_documento": "NFe" if is_nfe else ("Resumo" if is_resumo else "Evento")
            }
            
            # Extrair dados comuns
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                
                # Dados da NFe
                if tag == 'chNFe':
                    dados['chave'] = elem.text
                elif tag == 'nNF':
                    dados['numero_nf'] = elem.text
                elif tag == 'serie':
                    dados['serie'] = elem.text
                elif tag == 'dhEmi':
                    dados['data_emissao'] = elem.text[:10] if elem.text else None
                elif tag == 'vNF':
                    dados['valor_total'] = float(elem.text) if elem.text else 0
                elif tag == 'tpNF':
                    # 0 = Entrada, 1 = Saída
                    dados['tipo_operacao'] = 'ENTRADA' if elem.text == '0' else 'SAIDA'
                
                # Dados do emitente
                elif tag == 'emit':
                    for child in elem.iter():
                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if child_tag == 'CNPJ':
                            dados['cnpj_emitente'] = child.text
                        elif child_tag == 'xNome':
                            dados['nome_emitente'] = child.text
                        elif child_tag == 'xFant':
                            dados['fantasia_emitente'] = child.text
                
                # Dados do destinatário
                elif tag == 'dest':
                    for child in elem.iter():
                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if child_tag == 'CNPJ':
                            dados['cnpj_destinatario'] = child.text
                        elif child_tag == 'xNome':
                            dados['nome_destinatario'] = child.text
                
                # Dados de cobrança (vencimento)
                elif tag == 'dup':
                    for child in elem.iter():
                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if child_tag == 'dVenc':
                            dados['data_vencimento'] = child.text
                        elif child_tag == 'vDup':
                            dados['valor_duplicata'] = float(child.text) if child.text else 0
            
            # Determinar se é compra ou venda para a Finco
            cnpj_emit = dados.get('cnpj_emitente', '')
            cnpj_dest = dados.get('cnpj_destinatario', '')
            
            if cnpj_emit == CNPJ_FINCO:
                dados['tipo_lancamento'] = 'ENTRADA'  # Finco vendeu = vai receber
                dados['fornecedor_cliente'] = dados.get('nome_destinatario', dados.get('fantasia_emitente', ''))
            elif cnpj_dest == CNPJ_FINCO:
                dados['tipo_lancamento'] = 'SAIDA'  # Finco comprou = vai pagar
                dados['fornecedor_cliente'] = dados.get('nome_emitente', dados.get('fantasia_emitente', ''))
            else:
                dados['tipo_lancamento'] = 'INDEFINIDO'
                dados['fornecedor_cliente'] = dados.get('nome_emitente', '')
            
            return dados
            
        except Exception as e:
            print(f"Erro ao extrair dados NFe: {e}")
            return None


def processar_xml_upload(xml_content: str) -> Dict:
    """
    Processa um XML de NFe enviado por upload
    
    Args:
        xml_content: Conteúdo do XML
        
    Returns:
        Dict com dados extraídos
    """
    service = SefazService()
    return service._extrair_dados_nfe(xml_content, "", "upload")


def processar_multiplos_xml(xml_files: List[str]) -> List[Dict]:
    """
    Processa múltiplos arquivos XML
    
    Args:
        xml_files: Lista de conteúdos XML
        
    Returns:
        Lista de dicts com dados extraídos
    """
    resultados = []
    service = SefazService()
    
    for i, xml_content in enumerate(xml_files):
        dados = service._extrair_dados_nfe(xml_content, f"upload_{i}", "upload")
        if dados:
            resultados.append(dados)
    
    return resultados
