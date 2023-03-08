"""必应站长平台自动绑定提交 """

import configparser
import linecache
from pprint import pprint
import httpx


class BindBind():
    """必应站长平台自动绑定提交"""

    def __init__(self):
        self.conf = configparser.ConfigParser()
        self.conf.read('user/config.ini')
        self.cookie = linecache.getline(self.conf['filePath']['cookie'], 1)
        self.urls = self.get_urls()
        self.sitemap = self.get_sitemap()
        self.headers = {
            "User_Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "cookie": self.cookie
        }

    def get_urls(self):
        """获取用户urls"""
        urls = [i.strip() for i in linecache.getlines(
            self.conf['filePath']['urls']) if i.strip() != ""]
        return urls

    def get_sitemap(self):
        """获取用户自定义的sitemap"""
        sitemap = [i.strip() for i in linecache.getlines(
            self.conf['filePath']['sitemap']) if i.strip() != ""]
        return sitemap

    def get_webs(self):
        """获取平台已绑定网站列表"""
        url = 'https://www.bing.com/webmasters/api/globalelements/globalinfo'
        resp = httpx.get(url, headers=self.headers, timeout=30)
        pprint(resp.json())
        # for i in resp.json()["UserSites"]:
        #     pprint(i)
        #     print('\n')

    def get_apikey(self):
        """获取账号apikey"""
        url = "https://www.bing.com/webmasters/api/apikey/get"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        print(resp.text)

    def get_quota(self, domain):
        """获取网站提交额度"""
        url = f"https://www.bing.com/webmasters/api/submiturls/quotadetails?siteurl=http://{domain}"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        print(resp.text)
    
    def add_site(self,domain):
        """添加网站"""
        url = f"https://www.bing.com/webmasters/api/site/add?siteUrl=http://{domain}"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        print(resp.text)

    def bind_site(self):
        """绑定网站"""
        # 获取所有网站
        self.get_webs()

def main():
    """主程"""
    BB = BindBind()
    print('## 开始绑定网站')
    BB.bind_site()
    # 获取所有网站
    # BB.get_webs()
    # 比对当前urls中没有绑定的网站进行绑定
    # 添加网站
    # 验证网站
    # 获取所有网站 已经绑定成功的网站
    # 获取apikey 和 当前网站的剩余提交额度
    # sitemap.xml中获得网址 进行提交
    # 直接提交sitemap.xml

    # BB.get_apikey()


if __name__ == "__main__":
    main()
