"""
Sistema Financeiro Finco - Serviço de Backup S3
Backup automático com criptografia AES-256
"""

import os
import boto3
import hashlib
import base64
import gzip
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from botocore.exceptions import ClientError

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações de caminho
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
DATABASE_PATH = os.path.join(DATA_DIR, "financeiro_finco.db")

# Configurações S3
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "finco-backup")
S3_KEY_PREFIX = os.getenv("S3_KEY_PREFIX", "financeiro")
ENCRYPTION_KEY = os.getenv("BACKUP_ENCRYPTION_KEY", "")


def get_s3_client():
    """Cria cliente S3 com credenciais das variáveis de ambiente"""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )


def get_encryption_key():
    """Obtém ou gera chave de criptografia"""
    key = os.getenv("BACKUP_ENCRYPTION_KEY", "")
    if not key:
        # Gerar chave baseada em um segredo
        secret = os.getenv("SECRET_KEY", "finco-financeiro-2025")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        return key
    return key.encode() if isinstance(key, str) else key


def encrypt_data(data: bytes) -> bytes:
    """Criptografa dados usando Fernet (AES-256)"""
    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.encrypt(data)


def decrypt_data(encrypted_data: bytes) -> bytes:
    """Descriptografa dados"""
    key = get_encryption_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data)


def compress_data(data: bytes) -> bytes:
    """Comprime dados usando gzip"""
    return gzip.compress(data)


def decompress_data(compressed_data: bytes) -> bytes:
    """Descomprime dados"""
    return gzip.decompress(compressed_data)


def backup_to_s3() -> dict:
    """
    Faz backup do banco de dados para o S3
    
    Returns:
        dict com status do backup
    """
    try:
        # Verificar se banco existe
        if not os.path.exists(DATABASE_PATH):
            return {
                "success": False,
                "error": f"Banco de dados não encontrado: {DATABASE_PATH}"
            }
        
        # Ler arquivo do banco
        with open(DATABASE_PATH, 'rb') as f:
            db_data = f.read()
        
        # Comprimir e criptografar
        compressed = compress_data(db_data)
        encrypted = encrypt_data(compressed)
        
        # Nome do arquivo no S3
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{S3_KEY_PREFIX}/backup_{timestamp}.db.enc"
        s3_key_latest = f"{S3_KEY_PREFIX}/backup_latest.db.enc"
        
        # Upload para S3
        s3 = get_s3_client()
        
        # Upload com timestamp
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=encrypted,
            ContentType='application/octet-stream',
            Metadata={
                'original_size': str(len(db_data)),
                'compressed_size': str(len(compressed)),
                'timestamp': timestamp
            }
        )
        
        # Upload como "latest" (para restauração rápida)
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key_latest,
            Body=encrypted,
            ContentType='application/octet-stream',
            Metadata={
                'original_size': str(len(db_data)),
                'compressed_size': str(len(compressed)),
                'timestamp': timestamp
            }
        )
        
        logger.info(f"Backup realizado com sucesso: {s3_key}")
        
        return {
            "success": True,
            "s3_key": s3_key,
            "original_size": len(db_data),
            "compressed_size": len(compressed),
            "encrypted_size": len(encrypted),
            "timestamp": timestamp
        }
        
    except ClientError as e:
        logger.error(f"Erro S3: {e}")
        return {
            "success": False,
            "error": f"Erro S3: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Erro no backup: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def restore_from_s3(s3_key: str = None) -> dict:
    """
    Restaura banco de dados do S3
    
    Args:
        s3_key: Chave específica ou None para usar o último backup
        
    Returns:
        dict com status da restauração
    """
    try:
        s3 = get_s3_client()
        
        # Usar último backup se não especificado
        if not s3_key:
            s3_key = f"{S3_KEY_PREFIX}/backup_latest.db.enc"
        
        # Verificar se backup existe
        try:
            response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {
                    "success": False,
                    "error": "Nenhum backup encontrado no S3"
                }
            raise
        
        # Baixar e descriptografar
        encrypted = response['Body'].read()
        compressed = decrypt_data(encrypted)
        db_data = decompress_data(compressed)
        
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
        # Salvar banco restaurado
        with open(DATABASE_PATH, 'wb') as f:
            f.write(db_data)
        
        metadata = response.get('Metadata', {})
        logger.info(f"Banco restaurado do S3: {s3_key}")
        
        return {
            "success": True,
            "s3_key": s3_key,
            "restored_size": len(db_data),
            "timestamp": metadata.get('timestamp', 'unknown')
        }
        
    except Exception as e:
        logger.error(f"Erro na restauração: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def list_backups(limit: int = 10) -> dict:
    """
    Lista backups disponíveis no S3
    
    Args:
        limit: Número máximo de backups para listar
        
    Returns:
        dict com lista de backups
    """
    try:
        s3 = get_s3_client()
        
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_KEY_PREFIX}/backup_",
            MaxKeys=limit + 1  # +1 para excluir o "latest"
        )
        
        backups = []
        for obj in response.get('Contents', []):
            if 'latest' not in obj['Key']:
                backups.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat()
                })
        
        # Ordenar por data (mais recente primeiro)
        backups.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return {
            "success": True,
            "backups": backups[:limit],
            "total": len(backups)
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar backups: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def auto_restore_on_startup():
    """
    Restaura automaticamente o banco se não existir
    Chamado na inicialização do servidor
    """
    if not os.path.exists(DATABASE_PATH):
        logger.info("Banco de dados não encontrado. Tentando restaurar do S3...")
        result = restore_from_s3()
        if result["success"]:
            logger.info(f"Banco restaurado automaticamente: {result.get('restored_size', 0)} bytes")
        else:
            logger.warning(f"Não foi possível restaurar: {result.get('error')}")
        return result
    else:
        logger.info("Banco de dados existente encontrado.")
        return {"success": True, "message": "Banco já existe"}


def cleanup_old_backups(keep_count: int = 30):
    """
    Remove backups antigos, mantendo apenas os mais recentes
    
    Args:
        keep_count: Quantidade de backups para manter
    """
    try:
        s3 = get_s3_client()
        
        # Listar todos os backups
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_KEY_PREFIX}/backup_"
        )
        
        backups = []
        for obj in response.get('Contents', []):
            if 'latest' not in obj['Key']:
                backups.append(obj)
        
        # Ordenar por data (mais antigo primeiro)
        backups.sort(key=lambda x: x['LastModified'])
        
        # Remover backups excedentes
        to_delete = backups[:-keep_count] if len(backups) > keep_count else []
        
        for backup in to_delete:
            s3.delete_object(Bucket=S3_BUCKET, Key=backup['Key'])
            logger.info(f"Backup antigo removido: {backup['Key']}")
        
        return {
            "success": True,
            "deleted": len(to_delete),
            "kept": min(len(backups), keep_count)
        }
        
    except Exception as e:
        logger.error(f"Erro na limpeza: {e}")
        return {
            "success": False,
            "error": str(e)
        }
