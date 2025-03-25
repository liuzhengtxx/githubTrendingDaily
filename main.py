# coding:utf-8

import datetime
import codecs
import requests
import os
import time
import schedule
import urllib3
import random
import hashlib
import json
from pyquery import PyQuery as pq

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 添加翻译缓存
TRANSLATION_CACHE_FILE = '/log/translation_cache.json'

def load_translation_cache():
    """加载翻译缓存"""
    try:
        if os.path.exists(TRANSLATION_CACHE_FILE):
            with open(TRANSLATION_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载翻译缓存失败: {e}")
    return {}

def save_translation_cache(cache):
    """保存翻译缓存"""
    try:
        with open(TRANSLATION_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存翻译缓存失败: {e}")

def get_cached_translation(text, translation_cache):
    """从缓存中获取翻译"""
    return translation_cache.get(text)

def git_add_commit_push(date):
    cmd_git_add = 'git add .'
    cmd_git_commit = 'git commit -m "{date}"'.format(date=date)
    cmd_git_push = 'git push -u origin main'

    os.system(cmd_git_add)
    os.system(cmd_git_commit)
    os.system(cmd_git_push)


def createMarkdown(date, filename):
    # 检查文件是否存在，如果存在则删除
    if os.path.exists(filename):
        try:
            os.remove(filename)
            print(f"已删除现有文件: {filename}")
        except Exception as e:
            print(f"删除文件失败: {e}")
    
    # 创建新文件
    with open(filename, 'w') as f:
        f.write("## " + date + "\n")
    print(f"已创建新文件: {filename}")

def translate_text(text, translation_cache):
    """带缓存的翻译函数"""
    # 检查缓存
    cached_translation = get_cached_translation(text, translation_cache)
    if cached_translation:
        print(f"从缓存获取翻译: {text[:30]}...")
        return cached_translation

    appid = ''
    secret_key = ''
    api_url = 'http://api.fanyi.baidu.com/api/trans/vip/translate'
    salt = random.randint(32768, 65536)

    # 生成签名
    sign = appid + text + str(salt) + secret_key
    sign = hashlib.md5(sign.encode()).hexdigest()

    params = {
        'q': text,
        'from': 'en',
        'to': 'zh',
        'appid': appid,
        'salt': salt,
        'sign': sign
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        result = response.json()
        time.sleep(1)

        if 'trans_result' in result:
            translations = [item['dst'] for item in result['trans_result']]
            if translations:
                translated_text = translations[0]
                # 将新翻译添加到缓存
                translation_cache[text] = translated_text
                print(f"新翻译已缓存: {text[:30]}...")
                return translated_text
            else:
                return text
        else:
            print(f"翻译失败，错误信息: {result.get('error_msg', '未知错误')}")
            return text

    except requests.RequestException as e:
        print(f"请求出错: {e}")
        return text
    except (KeyError, json.JSONDecodeError):
        print("解析响应数据出错")
        return text


def scrape(type, filename, translation_cache):
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    # 使用备用URL - 尝试使用镜像站点或API
    # 方法1: 直接访问GitHub (可能会失败)
    urls = [
        f'https://github.com/trending/?since={type}',
    ]
    
    content = None
    error_msg = ""
    
    # 尝试所有可能的URL
    for url in urls:
        try:
            print(f"尝试请求: {url}")
            # 禁用SSL验证
            r = requests.get(url, headers=HEADERS, verify=False, timeout=30)
            if r.status_code == 200 and r.content:
                content = r.content
                print(f"成功从 {url} 获取数据")
                break
        except Exception as e:
            error_msg = str(e)
            print(f"请求 {url} 失败: {e}")
            continue
    
    # 如果所有URL都失败了
    if content is None:
        with codecs.open(filename, "a", "utf-8") as f:
            f.write(f"\n#### {type} - 获取数据失败\n")
            f.write(f"* 错误信息: {error_msg}\n")
        return
    
    try:
        d = pq(content)
        items = d('div.Box article.Box-row')
        
        # 如果没有找到项目
        if not items:
            with codecs.open(filename, "a", "utf-8") as f:
                f.write(f"\n#### {type} - 未找到项目\n")
            return
        
        # 写入找到的项目
        with codecs.open(filename, "a", "utf-8") as f:
            f.write(f'\n#### {type}\n')
            
            for item in items:
                i = pq(item)
                title = i(".lh-condensed a").text()
                language = i('span[itemprop="programmingLanguage"]').text()
                description = i("p.col-9").text()
                url = i(".lh-condensed a").attr("href")
                url = "https://github.com" + url
                
                # 修改选择器，避免使用:has()伪类
                # fork count - 查找包含fork图标的链接
                fork_count = ""
                links = i('a.Link--muted')
                for link in links.items():
                    if link.find('svg.octicon-repo-forked').length > 0:
                        fork_count = link.text().strip()
                        break
                
                # star count - 查找包含star图标的链接
                star_count = ""
                for link in links.items():
                    if link.find('svg.octicon-star').length > 0:
                        star_count = link.text().strip()
                        break
                # if description:
                #     description = translate_text(description, translation_cache)
                
                f.write(f"* [{title}]({url}):{description} star_count:{star_count} fork_count:{fork_count} language:{language}\n")
    except Exception as e:
        print(f"解析数据失败: {e}")
        with codecs.open(filename, "a", "utf-8") as f:
            f.write(f"\n#### {type} - 解析数据失败\n")
            f.write(f"* 错误信息: {str(e)}\n")


def job():
    print(f"任务执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载翻译缓存
    # translation_cache = load_translation_cache()
    
    # 获取当前年份
    current_year = datetime.datetime.now().year
    # 构建年份目录路径
    year_directory = str(current_year)

    # 检查年份目录是否存在，如果不存在则创建
    if not os.path.exists(year_directory):
        os.makedirs(year_directory)

    strdate = datetime.datetime.now().strftime('%Y-%m-%d')
    filename = '{date}.md'.format(date=strdate)
    # 构建文件路径
    file_path = os.path.join(year_directory, filename)

    # 创建markdown文件
    createMarkdown(strdate, file_path)
    
    # # 抓取数据并写入markdown
    # scrape('daily', file_path, translation_cache)
    # scrape('weekly', file_path, translation_cache)
    # scrape('monthly', file_path, translation_cache)
    #
    # # 保存更新后的翻译缓存
    # save_translation_cache(translation_cache)
    
    # git add commit push
    git_add_commit_push(strdate)
    
    print(f"任务完成: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    job()
    # # 设置每天凌晨2点执行任务
    # schedule.every().day.at("02:00").do(job)
    #
    # print(f"程序启动时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # print("已设置每天凌晨2:00执行任务")
    #
    # # 持续运行，等待定时任务
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)  # 每分钟检查一次是否有待执行的任务
