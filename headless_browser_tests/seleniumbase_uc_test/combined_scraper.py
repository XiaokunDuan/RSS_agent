import os
import csv
from time import sleep
from seleniumbase import Driver
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime

# --- 全局配置 ---
# 定义每个期刊的基础URL和抓取类型
JOURNALS_CONFIG = {
    "EJIS": {
        "base_url": "https://www.tandfonline.com/loi/tjis20",
        "scraper_type": "selenium"
    },
    "MISQ": {
        "base_url": "https://aisel.aisnet.org/misq/all_issues.html",
        "scraper_type": "requests"
    },
    "MMIS": {
        "base_url": "https://www.tandfonline.com/loi/mmis20",
        "scraper_type": "selenium"
    },
    "ISR": {
        "base_url": "https://pubsonline.informs.org/journal/isre",
        "scraper_type": "selenium"
    },
}

# 对于使用 Selenium 抓取“最新N期”的网站，默认抓取的期数
DEFAULT_NUM_LATEST_ISSUES = 2

# --- 辅助函数：初始化Selenium Driver ---
def get_selenium_driver():
    """初始化并返回一个Selenium Driver实例。"""
    # uc=True 启用 undetected_chromedriver，headless=True 无头模式
    return Driver(uc=True, headless=True)

# --- JMIS 抓取函数 (Selenium) ---
def scrape_jmis(target_year, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES):
    """
    抓取 JMIS 期刊指定年份最新的 N 期文章数据。
    """
    journal_name = "EJIS"
    print(f"[{journal_name}] 正在开始抓取，目标年份：{target_year}，最新期数：{num_latest_issues}。")
    base_url = JOURNALS_CONFIG[journal_name]["base_url"]
    all_articles_data = []
    driver = None

    try:
        driver = get_selenium_driver()
        print(f"[{journal_name}] 正在打开主列表页面: {base_url}")
        driver.uc_open_with_reconnect(base_url, reconnect_time=10) # 尝试重连以绕过安全检查
        print(f"[{journal_name}] 等待15秒页面加载和安全检查...")
        sleep(15) # 等待页面加载和安全检查

        issue_urls_to_visit = []
        try:
            # 定位并点击年份按钮以展开内容
            year_button_selector = f'//button[contains(text(), "{target_year}")]'
            print(f"[{journal_name}] 尝试点击 {target_year} 年份按钮...")
            driver.click(year_button_selector)
            sleep(5) # 等待 issues 列表加载

            page_source = driver.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')

            volume_button = soup.find('button', string=lambda t: t and str(target_year) in t)
            if volume_button:
                issue_list_ul = volume_button.find_next_sibling('ul')
                if issue_list_ul:
                    links = issue_list_ul.find_all('a', href=True)
                    latest_links = links[:num_latest_issues]
                    print(f"[{journal_name}] 找到 {len(links)} 期，选择最新的 {len(latest_links)} 期。")

                    for link in latest_links:
                        full_url = "https://www.tandfonline.com" + link['href']
                        issue_urls_to_visit.append(full_url)
                else:
                    print(f"[{journal_name}] 未找到 {target_year} 年的期数列表。")
            else:
                print(f"[{journal_name}] 未找到年份按钮 {target_year}。")

        except Exception as e:
            print(f"[{journal_name}] 处理年份 {target_year} 时发生错误: {e}")

        for issue_url in issue_urls_to_visit:
            try:
                print(f"[{journal_name}] 导航到期数目录页: {issue_url}")
                driver.get(issue_url)
                sleep(10)

                issue_html = driver.get_page_source()
                issue_soup = BeautifulSoup(issue_html, 'html.parser')

                article_entries = issue_soup.find_all('div', class_='tocArticleEntry')
                print(f"[{journal_name}] 在当前期数中找到 {len(article_entries)} 篇文章。")

                for entry in article_entries:
                    title_tag = entry.find('a', class_='ref')
                    if title_tag and title_tag.has_attr('href'):
                        title = title_tag.get_text(strip=True)
                        link = "https://www.tandfonline.com" + title_tag['href']

                        try:
                            print(f"[{journal_name}] -> 抓取文章: {title[:70]}...")
                            driver.get(link)
                            sleep(5)
                            article_html = driver.get_page_source()
                            article_soup = BeautifulSoup(article_html, 'html.parser')

                            abstract_div = article_soup.find('div', class_='hlFld-Abstract')
                            if abstract_div:
                                paragraphs = abstract_div.find_all('p')
                                abstract = ' '.join(p.get_text(strip=True) for p in paragraphs)
                            else:
                                abstract = "Abstract not found"

                            all_articles_data.append({
                                'journal': journal_name,
                                'year': target_year,
                                'title': title,
                                'link': link,
                                'abstract': abstract
                            })
                        except Exception as article_error:
                            print(f"[{journal_name}] -! ERROR 抓取文章 '{title[:50]}...' 时发生错误: {article_error}")
                            if "tab crashed" in str(article_error):
                                print(f"[{journal_name}] -> 浏览器标签页崩溃。尝试重启 driver 并继续下一个期数...")
                                driver.quit()
                                driver = get_selenium_driver()
                                driver.uc_open_with_reconnect(base_url, reconnect_time=10)
                                sleep(15)
                                break # 跳到下一个 issue
                            continue # 继续尝试抓取本期下一篇文章

            except Exception as issue_error:
                print(f"[{journal_name}] -! ERROR 处理期数 URL {issue_url} 时发生错误: {issue_error}")
                continue # 跳到下一个 issue

    finally:
        if driver:
            driver.quit()
            print(f"[{journal_name}] 浏览器已关闭。")
    return all_articles_data

# --- MISQ 抓取函数 (Requests + BeautifulSoup) ---
def scrape_misq(target_year):
    """
    抓取 MISQ 期刊指定年份的所有文章数据。
    """
    journal_name = "MISQ"
    print(f"[{journal_name}] 正在开始抓取，目标年份：{target_year}。")
    ALL_ISSUES_URL = JOURNALS_CONFIG[journal_name]["base_url"]
    MISQ_BASE_DOMAIN = "https://aisel.aisnet.org" # MISQ 页面链接拼接需要

    all_misq_articles = []

    def get_issue_links_misq(url):
        """获取所有期数的链接及年份信息"""
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

    def filter_issues_by_year_misq(issue_links, years, base_url_for_joining):
        """根据年份筛选期数链接"""
        filtered_links = []
        for link_info in issue_links:
            if link_info['year'] in years:
                full_url = requests.compat.urljoin(base_url_for_joining, link_info['href'])
                filtered_links.append({'url': full_url, 'year': link_info['year']})
        return filtered_links

    def get_article_urls_from_issue_misq(issue_url, base_url_for_joining):
        """从单个期数页获取所有文章链接"""
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
                    full_url = requests.compat.urljoin(base_url_for_joining, href)
                    article_urls.add(full_url)
        return list(article_urls)

    def scrape_article_details_misq(article_url, year):
        """抓取单篇文章的标题和摘要"""
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

            if title == "N/A" or abstract == "N/A":
                print(f"[{journal_name}] 警告: 未能找到 {article_url} 的标题或摘要。")

            return {
                "journal": journal_name,
                "year": year,
                "title": title,
                "link": article_url,
                "abstract": abstract
            }
        except requests.exceptions.RequestException as e:
            print(f"[{journal_name}] 访问 {article_url} 时发生错误: {e}")
            return None

    try:
        issue_links_raw = get_issue_links_misq(ALL_ISSUES_URL)
        filtered_issues = filter_issues_by_year_misq(issue_links_raw, [target_year], MISQ_BASE_DOMAIN)

        all_articles_to_scrape = []
        for issue_info in filtered_issues:
            print(f"[{journal_name}] 正在处理期数: {issue_info['url']}")
            article_urls_from_issue = get_article_urls_from_issue_misq(issue_info['url'], MISQ_BASE_DOMAIN)
            for url in article_urls_from_issue:
                all_articles_to_scrape.append({'url': url, 'year': issue_info['year']})
            sleep(1) # 礼貌性等待

        for article_info in all_articles_to_scrape:
            article_data = scrape_article_details_misq(article_info['url'], article_info['year'])
            if article_data:
                all_misq_articles.append(article_data)
            sleep(1) # 礼貌性等待

    except Exception as e:
        print(f"[{journal_name}] 抓取过程中发生错误: {e}")
    return all_misq_articles

# --- MMIS 抓取函数 (Selenium) ---
def scrape_mmis(target_year, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES):
    """
    抓取 MMIS 期刊指定年份最新的 N 期文章数据。
    """
    journal_name = "MMIS"
    print(f"[{journal_name}] 正在开始抓取，目标年份：{target_year}，最新期数：{num_latest_issues}。")
    base_url = JOURNALS_CONFIG[journal_name]["base_url"]
    all_articles_data = []
    driver = None

    try:
        driver = get_selenium_driver()
        print(f"[{journal_name}] 正在打开主列表页面: {base_url}")
        driver.uc_open_with_reconnect(base_url, reconnect_time=10)
        print(f"[{journal_name}] 等待15秒页面加载和安全检查...")
        sleep(15)

        issue_urls_to_visit = []
        try:
            year_button_selector = f'//button[contains(text(), "{target_year}")]'
            print(f"[{journal_name}] 尝试点击 {target_year} 年份按钮...")
            driver.click(year_button_selector)
            sleep(5)

            page_source = driver.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')

            volume_button = soup.find('button', string=lambda t: t and str(target_year) in t)
            if volume_button:
                # 修正：查找按钮的父级<li>标签，然后在该父级标签内部查找<ul>
                parent_li = volume_button.find_parent('li', class_='vol_li')
                issue_list_ul = parent_li.find('ul') if parent_li else None

                if issue_list_ul:
                    links = issue_list_ul.find_all('a', href=True)
                    latest_links = links[:num_latest_issues]
                    print(f"[{journal_name}] 找到 {len(links)} 期，选择最新的 {len(latest_links)} 期。")

                    for link in latest_links:
                        full_url = "https://www.tandfonline.com" + link['href']
                        issue_urls_to_visit.append(full_url)
                else:
                    print(f"[{journal_name}] 未找到 {target_year} 年的期数列表。")
            else:
                print(f"[{journal_name}] 未找到年份按钮 {target_year}。")

        except Exception as e:
            print(f"[{journal_name}] 处理年份 {target_year} 时发生错误: {e}")

        for issue_url in issue_urls_to_visit:
            try:
                print(f"[{journal_name}] 导航到期数目录页: {issue_url}")
                driver.get(issue_url)
                sleep(10)

                issue_html = driver.get_page_source()
                issue_soup = BeautifulSoup(issue_html, 'html.parser')

                article_entries = issue_soup.find_all('div', class_='tocArticleEntry')
                print(f"[{journal_name}] 在当前期数中找到 {len(article_entries)} 篇文章。")

                for entry in article_entries:
                    title_tag = entry.find('a', class_='ref')
                    if title_tag and title_tag.has_attr('href'):
                        title = title_tag.get_text(strip=True)
                        link = "https://www.tandfonline.com" + title_tag['href']

                        try:
                            print(f"[{journal_name}] -> 抓取文章: {title[:70]}...")
                            driver.get(link)
                            sleep(5)
                            article_html = driver.get_page_source()
                            article_soup = BeautifulSoup(article_html, 'html.parser')

                            abstract_div = article_soup.find('div', class_='hlFld-Abstract')
                            if abstract_div:
                                paragraphs = abstract_div.find_all('p')
                                abstract = ' '.join(p.get_text(strip=True) for p in paragraphs)
                            else:
                                abstract = "Abstract not found"

                            all_articles_data.append({
                                'journal': journal_name,
                                'year': target_year,
                                'title': title,
                                'link': link,
                                'abstract': abstract
                            })
                        except Exception as article_error:
                            print(f"[{journal_name}] -! ERROR 抓取文章 '{title[:50]}...' 时发生错误: {article_error}")
                            if "tab crashed" in str(article_error):
                                print(f"[{journal_name}] -> 浏览器标签页崩溃。尝试重启 driver 并继续下一个期数...")
                                driver.quit()
                                driver = get_selenium_driver()
                                driver.uc_open_with_reconnect(base_url, reconnect_time=10)
                                sleep(15)
                                break # 跳到下一个 issue
                            continue

            except Exception as issue_error:
                print(f"[{journal_name}] -! ERROR 处理期数 URL {issue_url} 时发生错误: {issue_error}")
                continue

    finally:
        if driver:
            driver.quit()
            print(f"[{journal_name}] 浏览器已关闭。")
    return all_articles_data

# --- ISR 抓取函数 (Selenium) ---
def scrape_isr(target_year, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES):
    """
    抓取 ISR 期刊指定年份最新的 N 期文章数据。
    """
    journal_name = "ISR"
    print(f"[{journal_name}] 正在开始抓取，目标年份：{target_year}，最新期数：{num_latest_issues}。")
    base_url = JOURNALS_CONFIG[journal_name]["base_url"]
    all_articles_data = []
    driver = None

    try:
        driver = get_selenium_driver()
        print(f"[{journal_name}] 正在打开期刊主页: {base_url}")
        driver.get(base_url) # 直接访问期刊主页
        print(f"[{journal_name}] 等待20秒页面加载...")
        sleep(20) # 等待页面加载

        issue_urls_to_visit = []
        try:
            # 模拟点击 "ARCHIVES" 按钮
            archives_button_selector = 'a.loi__archive'
            print(f"[{journal_name}] 尝试点击 'ARCHIVES' 按钮...")
            driver.click(archives_button_selector)

            # 模拟点击十年按钮 (例如 2020-2029)
            decade = str(target_year)[:3] + "0"
            decade_selector = f'a[data-url="d{decade}"]'
            print(f"[{journal_name}] 等待十年标签 ('{decade}s') 可见...")
            driver.wait_for_element_visible(decade_selector, timeout=10)
            print(f"[{journal_name}] 尝试点击十年标签: '{decade}s'...")
            driver.click(decade_selector)
            sleep(3)

            # 模拟点击年份按钮
            year_selector = f'a[data-url="d{decade}.y{target_year}"]'
            print(f"[{journal_name}] 等待年份标签 ('{target_year}') 可见...")
            driver.wait_for_element_visible(year_selector, timeout=10)
            print(f"[{journal_name}] 尝试点击年份标签: '{target_year}'...")
            driver.click(year_selector)

            # 等待期数列表出现
            issues_list_selector = "ul.issue-items"
            print(f"[{journal_name}] 等待期数列表出现...")
            driver.wait_for_element_visible(issues_list_selector, timeout=15)
            sleep(2)

            page_source = driver.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')

            issue_list_container = soup.find('ul', class_='issue-items')
            if issue_list_container:
                issue_links = issue_list_container.find_all('a', class_='issue-info__vol-issue')
                latest_links = issue_links[:num_latest_issues]
                print(f"[{journal_name}] 找到 {len(issue_links)} 期，选择最新的 {len(latest_links)} 期。")

                for link in latest_links:
                    full_url = "https://pubsonline.informs.org" + link['href']
                    issue_urls_to_visit.append(full_url)
            else:
                print(f"[{journal_name}] 未找到期数列表容器。")

        except Exception as e:
            print(f"[{journal_name}] 处理年份 {target_year} 时发生错误: {e}")

        for issue_url in issue_urls_to_visit:
            try:
                print(f"[{journal_name}] 导航到期数目录页: {issue_url}")
                driver.get(issue_url)
                sleep(10)

                issue_html = driver.get_page_source()
                issue_soup = BeautifulSoup(issue_html, 'html.parser')

                article_entries = issue_soup.select('div.issue-item')
                print(f"[{journal_name}] 在当前期数中找到 {len(article_entries)} 篇文章。")

                for entry in article_entries:
                    title_tag = entry.select_one('h5.issue-item__title > a')
                    if title_tag and title_tag.has_attr('href'):
                        title = title_tag.get_text(strip=True)
                        link = "https://pubsonline.informs.org" + title_tag['href']

                        try:
                            print(f"[{journal_name}] -> 抓取文章: {title[:70]}...")
                            # 通常访问文章的摘要页 (abs) 比完整页 (full) 更快更稳定
                            abs_link = link.replace('/full/', '/abs/')
                            driver.get(abs_link)
                            sleep(5)

                            article_html = driver.get_page_source()
                            article_soup = BeautifulSoup(article_html, 'html.parser')

                            # 摘要在 div.abstractSection p 标签中
                            abstract_div = article_soup.find('div', class_='abstractSection')
                            abstract = abstract_div.find('p').get_text(strip=True) if abstract_div and abstract_div.find('p') else "Abstract not found"

                            all_articles_data.append({
                                'journal': journal_name,
                                'year': target_year,
                                'title': title,
                                'link': link,
                                'abstract': abstract
                            })
                        except Exception as article_error:
                            print(f"[{journal_name}] -! ERROR 抓取文章 '{title[:50]}...' 时发生错误: {article_error}")
                            continue
            except Exception as issue_error:
                print(f"[{journal_name}] -! ERROR 处理期数 URL {issue_url} 时发生错误: {issue_error}")
                continue

    finally:
        if driver:
            driver.quit()
            print(f"[{journal_name}] 浏览器已关闭。")
    return all_articles_data

# --- 主协调函数 ---
def run_all_scrapers(target_year=None, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES, output_filename=None):
    """
    运行所有期刊的抓取器，并将所有数据合并保存到一个 CSV 文件中。

    :param target_year: 目标年份 (整数)。如果为 None，则默认为当前年份。
    :param num_latest_issues: 对于支持抓取最新N期的网站 (JMIS, MMIS, ISR)，指定N的值。
                              对于MISQ，此参数不适用，因为它总是抓取指定年份的所有期数。
    :param output_filename: 输出 CSV 文件的名称。如果为 None，则自动生成。
    """
    current_year = datetime.now().year
    if target_year is None:
        target_year = current_year
        print(f"未指定目标年份，默认为当前年份: {target_year}")

    if output_filename is None:
        # 自动生成文件名，包含年份和是否抓取最新N期 (如果不是默认N期)
        if num_latest_issues != DEFAULT_NUM_LATEST_ISSUES:
            output_filename = f"combined_articles_{target_year}_custom_latest_{num_latest_issues}_issues.csv"
        else:
            output_filename = f"combined_articles_{target_year}.csv" if target_year == current_year and num_latest_issues == DEFAULT_NUM_LATEST_ISSUES else f"combined_articles_{target_year}_latest_{num_latest_issues}_issues.csv"

    output_dir = "scraped_articles_data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    output_path = os.path.join(output_dir, output_filename)
    all_combined_articles = []

    print(f"\n--- 正在开始统一抓取，目标年份: {target_year} --- ")
    print(f"所有数据将保存到: {output_path}\n")

    # JMIS
    jmis_data = scrape_jmis(target_year, num_latest_issues)
    all_combined_articles.extend(jmis_data)

    # MISQ (总是抓取指定年份的所有期数，不使用 num_latest_issues)
    misq_data = scrape_misq(target_year)
    all_combined_articles.extend(misq_data)

    # MMIS
    mmis_data = scrape_mmis(target_year, num_latest_issues)
    all_combined_articles.extend(mmis_data)

    # ISR
    isr_data = scrape_isr(target_year, num_latest_issues)
    all_combined_articles.extend(isr_data)

    # 将所有数据写入单个 CSV 文件
    if all_combined_articles:
        print(f"\n--- 正在将所有 {len(all_combined_articles)} 篇文章写入到 {output_path} ---")
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['journal', 'year', 'title', 'link', 'abstract']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_combined_articles)
            print("--- 所有数据成功保存到 CSV 文件！ --- ")
        except Exception as e:
            print(f"写入合并 CSV 文件时发生错误: {e}")
    else:
        print("--- 没有收集到任何数据可以保存。 ---")

    print("\n--- 统一抓取过程完成 --- ")

if __name__ == "__main__":
    print(f"请确保你已经安装了所有依赖 (seleniumbase, beautifulsoup4, requests)。")
    print(f"并配置了 Chrome 浏览器以使用 SeleniumBase (推荐使用 Chrome 浏览器)。")

    # --- 小程度测试示例 (默认抓取当前年份的最新两期) ---
    # 运行 `python combined_scraper.py` 即可。
    print("\n--- 运行默认小测试：抓取当前年份的最新两期 --- ")
    run_all_scrapers()

    # --- 其他测试示例 (你可以取消注释来测试) ---

    # # 示例 1: 抓取 2024 年的最新两期
    # print("\n--- 运行小测试：抓取 2024 年的最新两期 --- ")
    # run_all_scrapers(target_year=2024)

    # # 示例 2: 抓取 2023 年的所有 MISQ 和其他期刊的最新3期
    # # 注意：MISQ 不受 num_latest_issues 影响，总是抓取指定年份的所有期数。
    # print("\n--- 运行小测试：抓取 2023 年的所有 MISQ 和其他期刊的最新3期 --- ")
    # run_all_scrapers(target_year=2023, num_latest_issues=3)

    # # 示例 3: 抓取当前年份的所有 MISQ 和其他期刊的最新5期
    # print("\n--- 运行小测试：抓取当前年份的所有 MISQ 和其他期刊的最新5期 --- ")
    # run_all_scrapers(num_latest_issues=5)

    # 你可以根据需要修改 main 函数中的调用来测试不同的场景。
