import requests
from bs4 import BeautifulSoup
import re
import json
import time

# MISQ基础URL
BASE_URL = "https://aisel.aisnet.org"
# 所有期数页面的完整URL
ALL_ISSUES_URL = f"{BASE_URL}/misq/all_issues.html"
# 当前年份，用于筛选
CURRENT_YEAR = 2025
# 筛选过去一年内的期数，这里指2025年和2024年
YEARS_TO_SCRAPE = [CURRENT_YEAR, CURRENT_YEAR - 1]

def get_issue_links(url):
    print(f"正在访问所有期数页面: {url}")
    response = requests.get(url)
    response.raise_for_status() # 如果请求失败，抛出HTTPError
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
    filtered_urls = []
    print(f"正在筛选 {years} 年的期数...")
    for link_info in issue_links:
        if link_info['year'] in years:
            full_url = requests.compat.urljoin(BASE_URL, link_info['href'])
            filtered_urls.append(full_url)
    return filtered_urls

def get_article_urls_from_issue(issue_url):
    response = requests.get(issue_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    article_urls = set() # 使用set去重
    # 查找所有class为"doc"的div，其中包含文章链接
    doc_divs = soup.find_all('div', class_='doc')

    for doc_div in doc_divs:
        # 在每个doc_div中查找所有<a>标签
        links_in_doc = doc_div.find_all('a', href=True)
        for link in links_in_doc:
            href = link.get('href')
            # 从完整URL中提取路径部分进行匹配
            path = requests.utils.urlparse(href).path if href else None
            # 筛选出文章链接，它应该匹配 /misq/volXX/issYY/ZZ 模式，而不是PDF下载链接或期数主页链接
            if path and "cgi/viewcontent.cgi" not in path and re.match(r'/misq/vol\d+/iss\d+/\d+/?', path):
                full_url = requests.compat.urljoin(BASE_URL, href)
                article_urls.add(full_url)
    return list(article_urls)
    return list(article_urls)

def scrape_article_details(article_url):
    print(f"正在抓取文章详情: {article_url}")
    try:
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title = "N/A"
        abstract = "N/A"

        # 提取标题 (div id='title' h1)
        title_div = soup.find('div', id='title')
        if title_div:
            title_h1 = title_div.find('h1')
            if title_h1:
                title = title_h1.get_text(strip=True)

        # 提取摘要 (div id='abstract' p)
        abstract_div = soup.find('div', id='abstract')
        if abstract_div:
            abstract_p = abstract_div.find('p')
            if abstract_p:
                abstract = abstract_p.get_text(strip=True)

        if not title or not abstract:
            print(f"警告: 未能找到 {article_url} 的标题或摘要。请检查选择器模式。")

        return {
            "title": title,
            "link": article_url,
            "abstract": abstract
        }
    except requests.exceptions.RequestException as e:
        print(f"访问 {article_url} 时发生错误: {e}")
        return None

def main():
    all_misq_articles = []

    # 1. 获取所有期数链接
    issue_links_raw = get_issue_links(ALL_ISSUES_URL)

    # 2. 筛选过去一年内的期数
    filtered_issue_urls = filter_issues_by_year(issue_links_raw, YEARS_TO_SCRAPE)
    print(f"筛选出 {len(filtered_issue_urls)} 个符合年份条件的期数。")

    # 3. 提取所有文章URL
    all_article_urls_to_scrape = []
    for issue_url in filtered_issue_urls:
        article_urls_from_issue = get_article_urls_from_issue(issue_url)
        all_article_urls_to_scrape.extend(article_urls_from_issue)
        time.sleep(1) # 增加延迟，避免频繁请求

    # 去重
    all_article_urls_to_scrape = list(set(all_article_urls_to_scrape))
    print(f"总共收集到 {len(all_article_urls_to_scrape)} 篇需要抓取的文章链接。")

    # 4. 抓取每篇文章的详细信息
    for article_url in all_article_urls_to_scrape:
        article_data = scrape_article_details(article_url)
        if article_data:
            all_misq_articles.append(article_data)
        time.sleep(1) # 增加延迟，避免频繁请求

    print("\n抓取完成！")
    print(f"共抓取到 {len(all_misq_articles)} 篇文章。")

    # 5. 结构化存储抓取到的数据（这里选择打印JSON格式）
    print("\n--- 抓取到的数据 (JSON格式) ---")
    print(json.dumps(all_misq_articles, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
