import os
import csv
from time import sleep
from seleniumbase import Driver
from bs4 import BeautifulSoup

def scrape_latest_issues(base_url, output_csv_file, target_year, num_latest_issues):
    """
    抓取指定年份最新的 N 期，并提取其中所有文章的标题、链接和摘要。
    
    :param base_url: 期刊的所有卷期列表页 URL
    :param output_csv_file: 保存结果的 CSV 文件路径
    :param target_year: 目标年份 (整数), e.g., 2025
    :param num_latest_issues: 要从该年份抓取的最新期的数量 (整数), e.g., 2
    """
    print("Initializing scraping process...")
    all_articles_data = []
    driver = None

    try:
        # --- 步骤 1: 初始化 Driver 并打开主列表页面 ---
        driver = Driver(uc=True, headless=True) # 调试时改为 headless=False
        print(f"Opening main issues list: {base_url}")
        driver.uc_open_with_reconnect(base_url, reconnect_time=10)
        
        print("Waiting 15 seconds for the initial page to load and bypass security...")
        sleep(15)

        # --- 步骤 2: 收集指定年份下最新的 N 个 Issue 的链接 ---
        issue_urls_to_visit = []
        print(f"\n--- Processing Year: {target_year} ---")
        try:
            # 定位并点击年份按钮以展开内容
            year_button_selector = f'//button[contains(text(), "{target_year}")]'
            print(f"Attempting to click button for year {target_year} to expand issues...")
            driver.click(year_button_selector)
            sleep(5) # 等待 issues 列表加载
            
            # 获取展开后的页面 HTML，并用 BeautifulSoup 解析
            page_source = driver.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 找到被点击的按钮，然后定位其后的 <ul> 列表
            volume_button = soup.find('button', string=lambda t: t and str(target_year) in t)
            if volume_button:
                issue_list_ul = volume_button.find_next_sibling('ul')
                if issue_list_ul:
                    links = issue_list_ul.find_all('a', href=True)
                    
                    # --- 核心改动：只选择最新的 N 个链接 ---
                    # 网站默认按降序排列 (Issue 5, 4, 3...), 所以前 N 个就是最新的
                    latest_links = links[:num_latest_issues]
                    
                    print(f"Found {len(links)} issues for {target_year}. Selecting the latest {len(latest_links)}.")
                    
                    for link in latest_links:
                        full_url = "https://www.tandfonline.com" + link['href']
                        issue_urls_to_visit.append(full_url)
                else:
                    print(f"Could not find the list of issues for {target_year} after clicking.")
            else:
                print(f"Could not find the button for year {target_year} on the page.")

        except Exception as e:
            print(f"Could not process year {target_year}. Maybe the button was not found or an error occurred: {e}")

        if not issue_urls_to_visit:
            print("No issue URLs were collected. Exiting.")
            return

        print(f"\nSelected latest issues to scrape: {issue_urls_to_visit}")

        # --- 步骤 3 & 4: 遍历选定的 Issue 链接并抓取文章 ---
        for issue_url in issue_urls_to_visit:
            try:
                print(f"\nNavigating to issue TOC page: {issue_url}")
                driver.get(issue_url)
                sleep(10) # 等待文章列表页面加载
                
                issue_html = driver.get_page_source()
                issue_soup = BeautifulSoup(issue_html, 'html.parser')
                
                article_entries = issue_soup.find_all('div', class_='tocArticleEntry')
                print(f"Found {len(article_entries)} articles in this issue.")

                for entry in article_entries:
                    title_tag = entry.find('a', class_='ref')
                    if title_tag and title_tag.has_attr('href'):
                        title = title_tag.get_text(strip=True)
                        link = "https://www.tandfonline.com" + title_tag['href']
                        
                        print(f"  -> Scraping article: {title[:70]}...")
                        
                        try:
                            driver.get(link)
                            sleep(5) # 等待文章页面加载
                            
                            article_html = driver.get_page_source()
                            article_soup = BeautifulSoup(article_html, 'html.parser')
                            
                            abstract_div = article_soup.find('div', class_='hlFld-Abstract')
                            # 有些文章摘要里是多个<p>标签，需要合并
                            if abstract_div:
                                paragraphs = abstract_div.find_all('p')
                                abstract = ' '.join(p.get_text(strip=True) for p in paragraphs)
                            else:
                                abstract = "Abstract not found"

                            all_articles_data.append({
                                'year': target_year,
                                'title': title,
                                'link': link,
                                'abstract': abstract
                            })
                        except Exception as article_error:
                            print(f"    -! ERROR scraping article '{title[:50]}...': {article_error}")
                            if "tab crashed" in str(article_error):
                                print("    -> Tab crashed. Attempting to recover by restarting driver...")
                                driver.quit()
                                driver = Driver(uc=True, headless=True)
                                print("    -> Driver restarted. Continuing to the next issue.")
                                break # 跳出当前 issue 的文章循环
                            continue

            except Exception as issue_error:
                print(f"  -! ERROR processing issue URL {issue_url}: {issue_error}")
                continue

    finally:
        # --- 步骤 5: 确保浏览器被关闭 ---
        if driver:
            driver.quit()
            print("\nBrowser closed.")

    # --- 步骤 6: 将所有数据写入 CSV 文件 ---
    if all_articles_data:
        print(f"\nWriting {len(all_articles_data)} articles to {output_csv_file}...")
        try:
            with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['year', 'title', 'link', 'abstract']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_articles_data)
            print("Scraping process completed successfully!")
        except Exception as e:
            print(f"Error writing to CSV file: {e}")
    else:
        print("No data was collected to save.")


if __name__ == "__main__":
    # 目标期刊的所有卷期列表页
    journal_loi_url = "https://www.tandfonline.com/loi/tjis20"
    
    # ================== 在这里配置您想抓取的范围 ==================
    target_year = 2025  # 指定您想抓取的年份
    num_latest_issues_to_scrape = 2  # 指定从该年份中抓取最新的几期
    # ==========================================================

    # 输出的 CSV 文件名会根据您的配置自动生成
    output_filename = f"articles_{target_year}_latest_{num_latest_issues_to_scrape}_issues.csv"
    
    current_dir = os.path.dirname(__file__)
    output_path = os.path.join(current_dir, output_filename)
    
    scrape_latest_issues(journal_loi_url, output_path, target_year, num_latest_issues_to_scrape)