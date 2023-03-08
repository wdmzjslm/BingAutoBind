"""必应站长平台自动绑定提交 """

import time
import datetime
import configparser
import linecache
from pprint import pprint
import httpx
from lxml import etree
from user import api


class BingBind():
    """必应站长平台自动绑定提交"""

    def __init__(self):
        self.conf = configparser.ConfigParser()
        self.conf.read('user/config.ini')
        self.cookie = linecache.getlines(
            self.conf['filePath']['cookie'])[0].strip()
        self.urls = self.get_urls()
        self.sitemap = self.get_sitemap()
        self.headers = {'Referer': 'https://www.bing.com/webmasters/',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
                        "cookie": self.cookie,
                        'accept': 'application/json, text/javascript, */*; q=0.01',
                        'content-type': 'application/json;charset=UTF-8',
                        'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google '
                        'Chrome";v="110"',
                        'sec-ch-ua-arch': '"x86"',
                        'sec-ch-ua-bitness': '"64"',
                        'sec-ch-ua-full-version': '"110.0.5481.78"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'sec-ch-ua-platform-version': '"14.0.0"',
                        'x-csrf-token': "035be031f6ec43d1bdc538882553a45a"}
        self.webs = []

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
        # print(resp.json())
        webs = []
        webs_verify = []
        verify_code = {}
        for i in resp.json()["UserSites"]:
            if i['Verification']['IsVerified']:
                webs.append(i["DisplayUrl"])
            else:
                webs_verify.append(i["DisplayUrl"])
                verify_code[i["DisplayUrl"]
                            ] = i['Verification']["AuthenticationCode"]
        result = {"webs": webs, "webs_verify": webs_verify,
                  "verify_code": verify_code}
        # print(result)
        return result

    def get_apikey(self):
        """获取账号apikey"""
        url = "https://www.bing.com/webmasters/api/apikey/get"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        return resp.text.replace('"', '')

    def get_quota(self, domain):
        """获取网站提交额度"""
        url = f"https://www.bing.com/webmasters/api/submiturls/quotadetails?siteurl=http://{domain}"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        return resp.json()['DailySubmissionsRemaining']

    def add_site(self, domain):
        """添加网站"""
        url = f"https://www.bing.com/webmasters/api/site/add?siteUrl=http://{domain}"
        data = {"SiteUrl": f"http://{domain}"}
        print(f'开始添加网站：{domain}')
        httpx.post(url, json=data, headers=self.headers, timeout=60)
        print(f'添加完成 等待数据刷新...')

    def verify_site(self, domain):
        """验证网站"""
        url = "https://www.bing.com/webmasters/api/site/verify"
        data = {
            "siteUrl": f"http://{domain}",
            "VerificationMethod": 0
        }
        resp = httpx.post(url, json=data, headers=self.headers, timeout=30)
        print(resp.status_code)

    def push_urls(self, domain, urls, apikey):
        """推送网址"""
        url = f'https://www.bing.com/webmaster/api.svc/json/SubmitUrlbatch?apikey={apikey}'
        data = {
            "siteUrl": f"http://{domain}",
            "urlList": urls
        }
        resp = httpx.post(url, json=data)
        if resp.text == '{"d":null}':
            return True
        return False

    def bind_site(self):
        """绑定网站"""
        # 获取所有网站
        webs_dict = self.get_webs()
        self.webs = webs_dict['webs']
        for url in self.urls:
            if url not in self.webs:
                # 开始添加网站
                if url not in webs_dict['webs_verify']:
                    self.add_site(url)
                    time.sleep(8)
                webs_dict = self.get_webs()
                self.webs = webs_dict['webs']
                webs_verify = webs_dict['webs_verify']
                if url in self.webs:
                    print(f'{url} 添加成功 验证绑定成功')
                elif url in webs_verify:
                    print(f'{url} 添加成功 开始验证绑定')
                    # 调用api 向用户自己的网站首页加meta验证标签
                    meta_code = webs_dict["verify_code"][url]
                    api.add_meta(url, meta_code)
                    self.verify_site(url)
                    print(f'{url} 验证绑定成功')
                else:
                    print(f'{url} 添加失败 跳过')
                    continue

    def get_url_from_sitemap_link(self, sitemap_link, count):
        """获取目标网址的sitemap.xml中的链接"""
        resp = httpx.get(sitemap_link, headers={
                         "User_Agent": "Mozilla/5.0 (compatible; Baiduspider/2.0;"
                         "+http://www.baidu.com/search/spider.html)"})
        tree = etree.HTML(resp.text)
        links = tree.xpath('//loc/text()')
        result = links[:count]
        return result

    def push_site(self):
        """推送网站"""
        webs_dict = self.get_webs()
        self.webs = webs_dict['webs']

        if int(self.conf['user']['ping_all']):
            # 推送账号中所有已绑定的网站
            need_push_webs = self.webs
        else:
            # 仅推送urls.txt中的网站
            need_push_webs = [url for url in self.urls if url in self.webs]

        for web in need_push_webs:
            # 获取网站提交额度
            push_count = self.get_quota(web)
            if push_count < 1:
                print(f'{web} 今日推送额度不足 跳过')
                continue
            sitemap_url = f"http://{web}/sitemap.xml"
            need_push_urls = self.get_url_from_sitemap_link(
                sitemap_url, push_count)
            # 获取账号apikey
            apikey = self.get_apikey()
            # 推送网址
            push_result = self.push_urls(web, need_push_urls, apikey)
            if push_result:
                print(f"{web} 网址{len(need_push_urls)}个 推送成功")
                # 写入推送日志
                with open(f'log/{datetime.date.today()}.txt', 'a', encoding='utf-8')as txt_f:
                    txt_f.write("\n".join(need_push_urls)+"\n")
            else:
                print(f"{web} 网址推送失败")


def main():
    """主程"""
    bing = BingBind()
    print('## 开始绑定网站')
    bing.bind_site()
    print('## 开始推送网站')
    bing.push_site()


if __name__ == "__main__":
    main()
