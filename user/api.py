"""
用户自定义程序验证接口
将网址修改为自己的程序验证接口格式即可，也可以直接修改你的web程序新增一个此类型api接口
"""

import httpx
from retrying import retry


@retry(stop_max_attempt_number=3)
def add_meta(domain, content):
    """
    调用web程序api meta文件验证
    使程序首页生成对应meta标签内容
    """
    url = f"http://{domain}/verify.php?type=add&bd={content}"
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
               ' (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
    resp = httpx.get(url, headers=headers, timeout=30)
    print(f"{domain} 调用API[{resp.status_code}] 生成验证meta标签 {content}")
