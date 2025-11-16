import requests
from bs4 import BeautifulSoup
import re
import json
import time
import csv
import os

# MISQ基础URL
BASE_URL = "https://aisel.aisnet.org"
# 所有期数页面的完整URL
ALL_ISSUES_URL = f"{BASE_URL}/misq/all_issues.html"
# 当前年份，用于筛选
CURRENT_YEAR = 2025
# 筛选过去一年内的期数，这里指2025年和2024年
YEARS_TO_SCRAPE = [CURRENT_YEAR]

def get_issue_links(url):
    print(f"正在访问所有期数页面: {url}")
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    issue_links = []
    item_divs = soup.find_all('div', class_='item')

    for item_div in item_divs:
        vol_link_tag = item_div.find('h2', class_='vol')
        if vol_link_tag:
            vol_a_tag = vol_link_tag.find('a', href=True)
            if vol_a_tag:
                vol_href = vol_a_tag.get('href')
                vol_text = vol_a_tag.get_text(strip=True)

                year_match = re.search(r'\((\d{4})\)', vol_text)
                year = int(year_match.group(1)) if year_match else None

                issue_link_tags = item_div.find_all('h3', class_='issue')
                for issue_h3 in issue_link_tags:
                    issue_a_tag = issue_h3.find('a', href=True)
                    if issue_a_tag:
                        issue_href = issue_a_tag.get('href')
                        issue_text = issue_a_tag.get_text(strip=True)
                        if issue_href and issue_text and year:
                            issue_links.append({'href': issue_href, 'text': issue_text, 'year': year})
    return issue_links

def filter_issues_by_year(issue_links, years):
    filtered_links = [] # 返回包含年份信息的完整字典
    print(f"正在筛选 {years} 年的期数...")
    for link_info in issue_links:
        if link_info['year'] in years:
            full_url = requests.compat.urljoin(BASE_URL, link_info['href'])
            filtered_links.append({'url': full_url, 'year': link_info['year']})
    return filtered_links

def get_article_urls_from_issue(issue_url):
    response = requests.get(issue_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    article_urls = set()
    doc_divs = soup.find_all('div', class_='doc')

    for doc_div in doc_divs:
        links_in_doc = doc_div.find_all('a', href=True)
        for link in links_in_doc:
            href = link.get('href')
            path = requests.utils.urlparse(href).path if href else None
            if path and "cgi/viewcontent.cgi" not in path and re.match(r'/misq/vol\d+/iss\d+/\d+/?', path):
                full_url = requests.compat.urljoin(BASE_URL, href)
                article_urls.add(full_url)
    return list(article_urls)

def scrape_article_details(article_url, year): # <--- 接收 year 参数
    print(f"正在抓取文章详情 ({year}): {article_url}")
    try:
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title = "N/A"
        abstract = "N/A"

        title_div = soup.find('div', id='title')
        if title_div:
            title_h1 = title_div.find('h1')
            if title_h1:
                title = title_h1.get_text(strip=True)

        abstract_div = soup.find('div', id='abstract')
        if abstract_div:
            abstract_p = abstract_div.find('p')
            if abstract_p:
                abstract = abstract_p.get_text(strip=True)

        if not title or not abstract:
            print(f"警告: 未能找到 {article_url} 的标题或摘要。请检查选择器模式。")

        return {
            "year": year, # <--- 增加 year 字段
            "title": title,
            "link": article_url,
            "abstract": abstract
        }
    except requests.exceptions.RequestException as e:
        print(f"访问 {article_url} 时发生错误: {e}")
        return None

def main():
    all_misq_articles = []
    output_filename = "misq_articles.csv"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, output_filename)

    # 1. 获取所有期数链接
    issue_links_raw = get_issue_links(ALL_ISSUES_URL)

    # 2. 筛选过去一年内的期数
    filtered_issues = filter_issues_by_year(issue_links_raw, YEARS_TO_SCRAPE)
    print(f"筛选出 {len(filtered_issues)} 个符合年份条件的期数。")

    # 3. 提取所有文章URL
    all_articles_to_scrape = [] # 创建一个列表来存储 (url, year) 对
    for issue_info in filtered_issues:
        article_urls_from_issue = get_article_urls_from_issue(issue_info['url'])
        for url in article_urls_from_issue:
            all_articles_to_scrape.append({'url': url, 'year': issue_info['year']})
        time.sleep(1)

    print(f"总共收集到 {len(all_articles_to_scrape)} 篇需要抓取的文章链接。")

    # 4. 抓取每篇文章的详细信息
    for article_info in all_articles_to_scrape:
        article_data = scrape_article_details(article_info['url'], article_info['year']) # <--- 传递 year
        if article_data:
            all_misq_articles.append(article_data)
        time.sleep(1)

    print("\n抓取完成！")
    print(f"共抓取到 {len(all_misq_articles)} 篇文章。")

    if all_misq_articles:
        print(f"\n正在将 {len(all_misq_articles)} 篇文章写入到 {output_path}...")
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                # --- 核心改动：在 fieldnames 中增加 'year' ---
                fieldnames = ['year', 'title', 'link', 'abstract']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                writer.writerows(all_misq_articles)
            
            print("成功将数据保存到 CSV 文件！")
        except Exception as e:
            print(f"写入 CSV 文件时发生错误: {e}")
    else:
        print("没有收集到任何数据可以保存。")

if __name__ == "__main__":
    main()