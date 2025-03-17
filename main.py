# coding:utf-8

import datetime
import codecs
import requests
import os
import time
import schedule
from pyquery import PyQuery as pq


def git_add_commit_push(date):
    cmd_git_add = 'git add .'
    cmd_git_commit = 'git commit -m "{date}"'.format(date=date)
    cmd_git_push = 'git push -u origin main'

    os.system(cmd_git_add)
    os.system(cmd_git_commit)
    os.system(cmd_git_push)


def createMarkdown(date, filename):
    with open(filename, 'w') as f:
        f.write("## " + date + "\n")


def scrape(type, filename):
    HEADERS = {
        'User-Agent'	: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
        'Accept'			: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding'	: 'gzip,deflate,sdch',
        'Accept-Language'	: 'zh-CN,zh;q=0.8'
    }
    url = 'https://github.com/trending/?since={type}'.format(type=type)
    r = requests.get(url, headers=HEADERS)
    assert r.status_code == 200

    d = pq(r.content)
    items = d('div.Box article.Box-row')

    # codecs to solve the problem utf-8 codec like chinese
    with codecs.open(filename, "a", "utf-8") as f:
        f.write('\n#### {type}\n'.format(type=type))

        for item in items:
            i = pq(item)
            title = i(".lh-condensed a").text()
            owner = i(".lh-condensed span.text-normal").text()
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
            
            f.write(u"* [{title}]({url}):{description} star_count:{star_count} fork_count:{fork_count}\n".format(title=title, url=url, description=description,star_count=star_count,fork_count=fork_count))


def job():
    print(f"任务执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
    
    # 抓取数据并写入markdown
    scrape('daily', file_path)
    scrape('weekly', file_path)
    scrape('monthly', file_path)

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