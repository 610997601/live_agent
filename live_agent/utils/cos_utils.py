import hashlib
import os
import datetime
from pathlib import Path
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

# --- COS 配置 (通过环境变量读取，防止密钥泄露) ---
SECRET_ID = os.environ.get('COS_SECRET_ID', 'YOUR_SECRET_ID')
SECRET_KEY = os.environ.get('COS_SECRET_KEY', 'YOUR_SECRET_KEY')
REGION = os.environ.get('COS_REGION', 'ap-beijing')
BUCKET = os.environ.get('COS_BUCKET', 'xuanyuan-cdn-1302719795')
CDN_BASE_URL = os.environ.get('COS_CDN_URL', 'https://cdn.hsuanyuen.com')

def calculate_md5(file_path):
    """计算文件的 MD5 值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def upload_to_cos(file_path: str | Path, prefix: str = "ai-montage/dev") -> tuple[str, str]:
    """
    上传文件到腾讯云 COS，返回 (CDN_URL, MD5)
    
    路径规则: {prefix}/{YYYY}/{MM}/{DD}/{md5}.{ext}
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    md5 = calculate_md5(file_path)
    ext = file_path.suffix.lower()
    
    # 构建远程路径
    now = datetime.datetime.now()
    key = f"{prefix}/{now.year}/{now.month:02d}/{now.day:02d}/{md5}{ext}"
    
    config = CosConfig(Region=REGION, SecretId=SECRET_ID, SecretKey=SECRET_KEY)
    client = CosS3Client(config)
    
    with open(file_path, 'rb') as fp:
        client.put_object(
            Bucket=BUCKET,
            Body=fp,
            Key=key,
            StorageClass='STANDARD',
            ContentType='audio/mpeg' if ext == '.mp3' else 'audio/wav'
        )
    
    cdn_url = f"{CDN_BASE_URL}/{key}"
    return cdn_url, md5

def download_from_url(url: str, dest_path: str | Path) -> bool:
    """从指定 URL 下载音频到本地"""
    import requests
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"[COS Utils] Download error: {e}")
    return False
