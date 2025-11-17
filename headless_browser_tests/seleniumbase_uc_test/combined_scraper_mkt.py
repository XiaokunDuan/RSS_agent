import os
import csv
from time import sleep
from seleniumbase import Driver
from bs4 import BeautifulSoup
import re
from datetime import datetime
from selenium.common.exceptions import WebDriverException, TimeoutException

# --- 全局配置 ---
JOURNALS_CONFIG = {
    "MKSC": {
        "base_url": "https://pubsonline.informs.org/journal/mksc",
        "scraper_type": "selenium"
    },
    "JMX": {
        "base_url": "https://journals.sagepub.com/loi/jmx",
        "scraper_type": "selenium"
    },
    "MRJ": {
        "base_url": "https://journals.sagepub.com/loi/MRJ",
        "scraper_type": "selenium"
    },
    "JCR": {
        "base_url": "https://academic.oup.com/jcr",
        "scraper_type": "selenium"
    },
}

# 默认抓取的期数 (设置为大数以抓取全年)
DEFAULT_NUM_LATEST_ISSUES = 99

# --- 辅助函数：初始化Selenium Driver ---
def get_selenium_driver():
    """初始化并返回一个Selenium Driver实例。"""
    return Driver(uc=True, headless=True)

# --- Marketing Science (MKSC) 抓取函数 ---
def scrape_mksc(target_year, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES):
    """
    抓取 MKSC 期刊指定年份最新的 N 期文章的标题和链接。
    """
    journal_name = "MKSC"
    print(f"[{journal_name}] 正在开始抓取, 目标年份: {target_year}, 最新期数: {num_latest_issues}。")
    base_url = JOURNALS_CONFIG[journal_name]["base_url"]
    all_articles_data = []
    driver = None

    try:
        driver = get_selenium_driver()
        print(f"[{journal_name}] 正在打开期刊主页: {base_url}")
        driver.get(base_url)
        sleep(10)

        issue_urls_to_visit = []
        try:
            print(f"[{journal_name}] 尝试点击 'ARCHIVES' 按钮...")
            driver.wait_for_element_visible('a.loi__archive', timeout=20).click()
            sleep(3)
            
            decade = str(target_year)[:3] + "0"
            decade_selector = f'a[data-url="d{decade}"]'
            print(f"[{journal_name}] 等待并点击十年标签 ('{decade}s')...")
            driver.wait_for_element_visible(decade_selector, timeout=20).click()
            sleep(3)

            year_selector = f'a[data-url="d{decade}.y{target_year}"]'
            print(f"[{journal_name}] 等待并点击年份标签 ('{target_year}')...")
            driver.wait_for_element_visible(year_selector, timeout=20).click()
            
            issues_list_selector = "ul.issue-items"
            print(f"[{journal_name}] 等待期数列表出现...")
            driver.wait_for_element_present(issues_list_selector, timeout=20)
            sleep(2)

            soup = BeautifulSoup(driver.get_page_source(), 'html.parser')
            active_year_pane = soup.select_one('div.tab__pane.nested-tab.active')
            if active_year_pane:
                issue_links = active_year_pane.select('a.issue-info__vol-issue')
                latest_links = issue_links[:num_latest_issues]
                print(f"[{journal_name}] 找到 {len(issue_links)} 期, 选择最新的 {len(latest_links)} 期。")
                for link in latest_links:
                    issue_urls_to_visit.append("https://pubsonline.informs.org" + link['href'])
            else:
                print(f"[{journal_name}] 未找到 {target_year} 年的期数列表容器。")

        except Exception as e:
            print(f"[{journal_name}] 导航至年份/期数列表时发生错误: {e}")

        for issue_url in issue_urls_to_visit:
            try:
                print(f"[{journal_name}] 导航到期数目录页: {issue_url}")
                driver.get(issue_url)
                sleep(10)
                issue_soup = BeautifulSoup(driver.get_page_source(), 'html.parser')

                article_entries = issue_soup.select('div.issue-item')
                print(f"[{journal_name}] 在当前期数中找到 {len(article_entries)} 篇文章。")

                for entry in article_entries:
                    title_tag = entry.select_one('h5.issue-item__title > a')
                    if not (title_tag and title_tag.has_attr('href')):
                        continue
                    
                    title = title_tag.get_text(strip=True)
                    link = "https://pubsonline.informs.org" + title_tag['href']
                    
                    all_articles_data.append({
                        'journal': journal_name, 'year': target_year,
                        'title': title, 'link': link
                    })
                    print(f"[{journal_name}] -> 找到文章: {title[:70]}...")

            except Exception as issue_error:
                print(f"[{journal_name}] -! ERROR 处理期数 URL {issue_url} 时发生错误: {issue_error}")
                continue

    finally:
        if driver:
            driver.quit()
            print(f"[{journal_name}] 浏览器已关闭。")
    return all_articles_data

# --- SAGE Journals (JMX, MRJ) 抓取函数 ---
def scrape_sage_journal(journal_name, target_year, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES):
    """
    为 SAGE 平台上的期刊 (JMX, MRJ) 抓取标题和链接。
    """
    print(f"[{journal_name}] 正在开始抓取, 目标年份: {target_year}, 最新期数: {num_latest_issues}。")
    journal_code = JOURNALS_CONFIG[journal_name]["base_url"].split('/')[-1]
    
    decade = str(target_year)[:3] + "0"
    year_url = f"https://journals.sagepub.com/loi/{journal_code}/group/d{decade}.y{target_year}"
    
    all_articles_data = []
    driver = None

    try:
        driver = get_selenium_driver()
        print(f"[{journal_name}] 直接导航到年份页面: {year_url}")
        driver.get(year_url)
        sleep(10)

        issue_urls_to_visit = []
        try:
            soup = BeautifulSoup(driver.get_page_source(), 'html.parser')
            issue_links = soup.select('a.loi__issue__link')
            latest_links = issue_links[:num_latest_issues]
            print(f"[{journal_name}] 找到 {len(issue_links)} 期, 选择最新的 {len(latest_links)} 期。")

            for link in latest_links:
                full_url = "https://journals.sagepub.com" + link['href']
                issue_urls_to_visit.append(full_url)

        except Exception as e:
            print(f"[{journal_name}] 在年份页面 {year_url} 解析时发生错误: {e}")

        for issue_url in issue_urls_to_visit:
            try:
                print(f"[{journal_name}] 导航到期数目录页: {issue_url}")
                driver.get(issue_url)
                sleep(10)
                issue_soup = BeautifulSoup(driver.get_page_source(), 'html.parser')

                article_title_tags = issue_soup.select('h5.issue-item__heading')
                print(f"[{journal_name}] 在当前期数中找到 {len(article_title_tags)} 篇文章。")

                for title_tag in article_title_tags:
                    title = title_tag.get_text(strip=True)
                    link_tag = title_tag.find_parent('a')
                    link = "https://journals.sagepub.com" + link_tag['href'] if link_tag else "Link not found"
                    
                    all_articles_data.append({
                        'journal': journal_name, 'year': target_year,
                        'title': title, 'link': link
                    })
                    print(f"[{journal_name}] -> 找到文章: {title[:70]}...")

            except Exception as issue_error:
                print(f"[{journal_name}] -! ERROR 处理期数 URL {issue_url} 时发生错误: {issue_error}")

    finally:
        if driver:
            driver.quit()
            print(f"[{journal_name}] 浏览器已关闭。")
    return all_articles_data

# --- Journal of Consumer Research (JCR) 抓取函数 ---
def scrape_jcr(target_year, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES):
    """
    抓取 JCR 期刊指定年份最新的 N 期文章的标题和链接。
    """
    journal_name = "JCR"
    print(f"[{journal_name}] 正在开始抓取, 目标年份: {target_year}, 最新期数: {num_latest_issues}。")
    base_url = JOURNALS_CONFIG[journal_name]["base_url"]
    issues_url = f"{base_url}/issue-archive"
    all_articles_data = []
    driver = None

    try:
        driver = get_selenium_driver()
        print(f"[{journal_name}] 正在打开期刊存档页面: {issues_url}")
        driver.get(issues_url)
        sleep(10)

        issue_urls_to_visit = []
        try:
            year_selector = f'a[href="/jcr/issue-archive/{target_year}"]'
            print(f"[{journal_name}] 尝试点击年份链接 '{target_year}'...")
            driver.wait_for_element_visible(year_selector, timeout=20).click()
            sleep(5)

            page_source = driver.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            issue_list_container = soup.find('div', class_='issue-covers-main-column')
            if issue_list_container:
                links = issue_list_container.select('div.customLink > a')
                latest_links = links[:num_latest_issues]
                print(f"[{journal_name}] 找到 {len(links)} 期, 选择最新的 {len(latest_links)} 期。")

                for link in latest_links:
                    issue_urls_to_visit.append("https://academic.oup.com" + link['href'])
            else:
                print(f"[{journal_name}] 未找到 {target_year} 年的期数列表。")

        except Exception as e:
            print(f"[{journal_name}] 处理年份 {target_year} 时发生错误: {e}")

        for issue_url in issue_urls_to_visit:
            try:
                print(f"[{journal_name}] 导航到期数目录页: {issue_url}")
                driver.get(issue_url)
                sleep(10)
                issue_soup = BeautifulSoup(driver.get_page_source(), 'html.parser')

                article_links = issue_soup.select('h5.item-title a')
                print(f"[{journal_name}] 在当前期数中找到 {len(article_links)} 篇文章。")

                for link_tag in article_links:
                    title = link_tag.get_text(strip=True)
                    link = link_tag['href']
                    
                    all_articles_data.append({
                        'journal': journal_name, 'year': target_year,
                        'title': title, 'link': link
                    })
                    print(f"[{journal_name}] -> 找到文章: {title[:70]}...")

            except Exception as issue_error:
                print(f"[{journal_name}] -! ERROR 处理期数 URL {issue_url} 时发生错误: {issue_error}")

    finally:
        if driver:
            driver.quit()
            print(f"[{journal_name}] 浏览器已关闭。")
    return all_articles_data

# --- 主协调函数 ---
def run_all_scrapers(target_year=None, num_latest_issues=DEFAULT_NUM_LATEST_ISSUES, output_filename=None):
    if target_year is None:
        target_year = datetime.now().year
        print(f"未指定目标年份, 默认为当前年份: {target_year}")

    if output_filename is None:
        output_filename = f"combined_marketing_articles_{target_year}.csv"

    output_dir = "scraped_articles_data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    output_path = os.path.join(output_dir, output_filename)
    all_combined_articles = []

    print(f"\n--- 正在开始统一抓取, 目标年份: {target_year} --- ")
    print(f"所有数据将保存到: {output_path}\n")

    mksc_data = scrape_mksc(target_year, num_latest_issues)
    all_combined_articles.extend(mksc_data)

    jmx_data = scrape_sage_journal("JMX", target_year, num_latest_issues)
    all_combined_articles.extend(jmx_data)

    mrj_data = scrape_sage_journal("MRJ", target_year, num_latest_issues)
    all_combined_articles.extend(mrj_data)
    
    jcr_data = scrape_jcr(target_year, num_latest_issues)
    all_combined_articles.extend(jcr_data)

    if all_combined_articles:
        print(f"\n--- 正在将所有 {len(all_combined_articles)} 篇文章写入到 {output_path} ---")
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['journal', 'year', 'title', 'link']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_combined_articles)
            print("--- 所有数据成功保存到 CSV 文件! --- ")
        except Exception as e:
            print(f"写入合并 CSV 文件时发生错误: {e}")
    else:
        print("--- 没有收集到任何数据可以保存。 ---")

    print("\n--- 统一抓取过程完成 --- ")

# --- 主程序入口 ---
if __name__ == "__main__":
    TARGET_YEAR_TO_SCRAPE = 2025
    
    # 【已根据您的要求修改】设置为大数以抓取全年所有期数
    ISSUES_TO_SCRAPE_PER_JOURNAL = 99

    print("--- 爬虫任务准备启动 ---")
    print(f"目标年份: {TARGET_YEAR_TO_SCRAPE}")
    print(f"每个期刊抓取的最新期数: {ISSUES_TO_SCRAPE_PER_JOURNAL}")
    print("请确保已安装所有依赖 (seleniumbase, beautifulsoup4, requests)。\n")

    run_all_scrapers(
        target_year=TARGET_YEAR_TO_SCRAPE,
        num_latest_issues=ISSUES_TO_SCRAPE_PER_JOURNAL
    )