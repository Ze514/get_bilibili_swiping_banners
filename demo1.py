import asyncio
import requests
from io import BytesIO
from PIL import Image
import html
import os
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%m-%d %H:%M:%S")
import re
from datetime import datetime

def sanitize_filename(name: str):
    # 替换非法字符为下划线（跨平台兼容）
    return re.sub(r'[\\/:*?"<>|]', '_', name.strip())
def original_filename_saver(unchanged_filename: str, output_path: str, img_bytes: bytes, source_url: str):
    """
    :param unchanged_filename: 原文件名（未经合法化的文件名）
    :param output_path: 保存路径（文件名为合法化的文件名）
    :param img_bytes: 图片字节流
    :param source_url: 图片来源URL
    """
    if os.path.exists(output_path): return
    with Image.open(BytesIO(img_bytes)) as img:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        escaped_filename = html.escape(unchanged_filename)
        escaped_url = html.escape(source_url)
        xmp_data = f'''<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
      xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:description>{escaped_filename}</dc:description>
      <dc:source>{escaped_url}</dc:source>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''
        save_params = {
                "format": "webp",
                "lossless": True,
                "xmp": xmp_data}
        try:
            exif = img.getexif()
            if exif:
                save_params["exif"] = exif
        except: pass
        img.save(output_path, **save_params)
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / 1024
            logger.info(f"保存成功: {output_path} ({file_size:.2f} KB)")
            return output_path
        else:
            logger.error(f"保存失败，文件未创建: {output_path}")
            return None
async def f_work(key, value, headers):
    name = key
    url = value
    if "@" in url:
        url = re.search(r"//(.*?)@", url).group()
        url = "https:" + url.strip("@")
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        img_data = resp.content
        saved_name = sanitize_filename(name)
        current_month = datetime.now().strftime("%Y%m")
        original_filename_saver(name, f"{current_month}/{saved_name}.webp", img_data, url)
#        logger.info(f"使用UA：{headers['User-Agent']}")
        return f"{saved_name} 下载完成。使用UA：{headers['User-Agent']}"
    except Exception as e:
        print(e)
        return


#f_work(key, value, headers)