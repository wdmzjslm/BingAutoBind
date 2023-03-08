"""必应站长平台自动绑定提交 """

import threading
import time
import random
import datetime
import configparser
import linecache
from pprint import pprint
import httpx
from lxml import etree
from retrying import retry
import tldextract
from user import api


class BingBind():
    """必应站长平台自动绑定提交"""

    def __init__(self):
        self.conf = configparser.ConfigParser()
        self.conf.read('user/config.ini')
        self.urls = self.get_urls()
        self.sitemap = self.get_sitemap()
        csrf, cookie = linecache.getlines(self.conf['filePath']['cookie'])[
            0].strip().split('||')
        self.headers = {'Referer': 'https://www.bing.com/webmasters/',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
                        "cookie": cookie,
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
                        'x-csrf-token': csrf}
        self.webs = []
        self.need_push_webs = []
        self.need_add_sites = []
        self.lock = threading.Lock()
        self.init_urls()

    def init_urls(self):
        """初始化自动生成二级域名"""
        if int(self.conf['user']['domain_count']) > 0:
            self.urls = self.auto_create_son_url(self.urls)

    def random_str(self, min_count, max_count):
        """随机字符"""
        abc = "abcdefghijklmnopqrstuvwxyz0123456789"
        count = random.randint(min_count, max_count)
        return "".join(random.choices(abc, k=count))

    def auto_create_son_url(self, urls):
        """自动生成二级域名"""
        root_domains = []
        for url in urls:
            root_domain = self.get_domain_info(url)[-1]
            root_domains.append(root_domain)
        son_domains = []
        for rdomain in root_domains:
            for i in range(int(self.conf["user"]["domain_count"])):
                son_domain = f"{self.random_str(5,8)}.{rdomain}"
                son_domains.append(son_domain)
        print(f'自动生成二级域名：{len(son_domains)}个')
        print(son_domains)
        urls.extend(son_domains)
        return list(set(urls))

    def get_domain_info(self, domain):
        """获取域名前后缀"""
        tld = tldextract.extract(domain)
        subdomain = tld.subdomain
        full_domain = ".".join([tld.subdomain, tld.domain, tld.suffix])
        root_domain = ".".join([tld.domain, tld.suffix])
        return subdomain, full_domain, root_domain

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

    @retry(stop_max_attempt_number=3)
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
        return result

    @retry(stop_max_attempt_number=3)
    def get_apikey(self):
        """获取账号apikey"""
        url = "https://www.bing.com/webmasters/api/apikey/get"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        return resp.text.replace('"', '')

    @retry(stop_max_attempt_number=3)
    def get_quota(self, domain):
        """获取网站提交额度"""
        url = f"https://www.bing.com/webmasters/api/submiturls/quotadetails?siteurl=http://{domain}"
        resp = httpx.get(url, headers=self.headers, timeout=30)
        return resp.json()['DailySubmissionsRemaining']

    @retry(stop_max_attempt_number=3)
    def add_site(self, domain, tname):
        """添加网站"""
        url = f"https://www.bing.com/webmasters/api/site/add?siteUrl=http://{domain}"
        data = {"SiteUrl": f"http://{domain}"}
        print(f'[{tname}]开始添加网站：{domain}')
        httpx.post(url, json=data, headers=self.headers, timeout=60)
        # print('添加完成 等待数据刷新...')

    @retry(stop_max_attempt_number=3)
    def verify_site(self, domain):
        """验证网站"""
        url = "https://www.bing.com/webmasters/api/site/verify"
        data = {
            "siteUrl": f"http://{domain}",
            "VerificationMethod": 0
        }
        resp = httpx.post(url, json=data, headers=self.headers, timeout=30)
        print(resp.status_code)

    @retry(stop_max_attempt_number=3)
    def push_urls(self, domain, urls, apikey):
        """推送网址"""
        url = f'https://www.bing.com/webmaster/api.svc/json/SubmitUrlbatch?apikey={apikey}'
        data = {
            "siteUrl": f"http://{domain}",
            "urlList": urls
        }
        resp = httpx.post(url, json=data, timeout=30)
        if resp.text == '{"d":null}':
            return True
        return False

    def add_go(self, tname):
        """添加·线程"""
        while len(self.need_add_sites) > 0:
            try:
                with self.lock:
                    url = self.need_add_sites.pop(0)
                self.add_site(url, tname)
            except Exception as error:
                print(error)

    def bind_site(self):
        """绑定网站"""
        # 获取所有网站
        webs_dict = self.get_webs()
        self.webs = webs_dict['webs']
        for url in self.urls:
            if url in self.webs:
                print(f'{url} 已绑定')
            else:
                # 开始添加网站
                if url not in webs_dict['webs_verify']:
                    self.need_add_sites.append(url)

        threads = [threading.Thread(
            target=self.add_go, args=(f't{i}',)) for i in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        time.sleep(6)
        webs_dict = self.get_webs()
        self.webs = webs_dict['webs']
        for url in self.urls:
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

    @retry(stop_max_attempt_number=3)
    def get_url_from_sitemap_link(self, sitemap_link, count):
        """获取目标网址的sitemap.xml中的链接"""
        resp = httpx.get(sitemap_link, headers={
                         "User_Agent": "Mozilla/5.0 (compatible; Baiduspider/2.0;"
                         "+http://www.baidu.com/search/spider.html)"}, timeout=30)
        tree = etree.HTML(resp.text)
        links = tree.xpath('//loc/text()')
        result = links[:count]
        return result

    def push_go(self, tname):
        """推送·线程"""
        while len(self.need_push_webs) > 0:
            try:
                with self.lock:
                    web = self.need_push_webs.pop(0)
                # 获取网站提交额度
                push_count = self.get_quota(web)
                if push_count < 1:
                    print(f'[{tname}] {web} 今日推送额度不足 跳过')
                    continue
                sitemap_url = f"http://{web}/sitemap.xml"
                need_push_urls = self.get_url_from_sitemap_link(
                    sitemap_url, push_count)
                # 获取账号apikey
                apikey = self.get_apikey()
                # 推送网址
                push_result = self.push_urls(web, need_push_urls, apikey)
                if push_result:
                    print(f"[{tname}] {web} 网址{len(need_push_urls)}个 推送成功")
                    # 写入推送日志
                    with open(f'log/{datetime.date.today()}.txt', 'a', encoding='utf-8')as txt_f:
                        txt_f.write("\n".join(need_push_urls)+"\n")
                else:
                    print(f"[{tname}] {web} 网址推送失败")
            except Exception as error:
                print(error)

    def push_site(self):
        """推送网站"""
        webs_dict = self.get_webs()
        self.webs = webs_dict['webs']

        if int(self.conf['user']['ping_all']):
            # 推送账号中所有已绑定的网站
            self.need_push_webs = self.webs
            print('本次将推送更新账号中所有网站')
        else:
            # 仅推送urls.txt中的网站
            self.need_push_webs = [
                url for url in self.urls if url in self.webs]

        threads = [threading.Thread(
            target=self.push_go, args=(f't{i}',)) for i in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()


def main():
    """主程"""
    bing = BingBind()
    print('## 开始绑定网站')
    bing.bind_site()
    print('## 开始推送网站')
    bing.push_site()


if __name__ == "__main__":
    main()
