import os
import csv
from time import sleep
from seleniumbase import Driver
from bs4 import BeautifulSoup

def scrape_latest_issues_informs(base_url, output_csv_file, target_year, num_latest_issues):
    """
    针对 pubsonline.informs.org 网站，抓取指定年份最新的 N 期文章数据。
    此版本修正了文章列表和摘要的解析逻辑。
    """
    print("Initializing scraping process for PubsOnLine...")
    all_articles_data = []
    driver = None

    try:
        # --- 步骤 1: 初始化 Driver 并打开期刊主页 ---
        driver = Driver(uc=True, headless=True)  # 调试时改为 headless=False
        print(f"Opening main journal page: {base_url}")
        driver.get(base_url)
        
        print("Waiting 20 seconds for the initial page to fully load...")
        sleep(20)

        # --- 步骤 2: 导航到年份并收集 Issue 链接 ---
        issue_urls_to_visit = []
        print(f"\n--- Processing Year: {target_year} ---")
        try:
            archives_button_selector = 'a.loi__archive'
            print("Clicking on 'ARCHIVES' button to open the decades menu...")
            driver.click(archives_button_selector)
            
            decade = str(target_year)[:3] + "0"
            decade_selector = f'a[data-url="d{decade}"]'
            print(f"Waiting for decade tab ('{decade_selector}') to become visible...")
            driver.wait_for_element_visible(decade_selector, timeout=10)
            
            print(f"Clicking on decade tab: '{decade}s'...")
            driver.click(decade_selector)
            sleep(3)

            year_selector = f'a[data-url="d{decade}.y{target_year}"]'
            print(f"Waiting for year tab ('{year_selector}') to become visible...")
            driver.wait_for_element_visible(year_selector, timeout=10)

            print(f"Clicking on year tab: '{target_year}'...")
            driver.click(year_selector)
            
            issues_list_selector = "ul.issue-items"
            print(f"Waiting for the issues list ('{issues_list_selector}') to appear...")
            driver.wait_for_element_visible(issues_list_selector, timeout=15)
            print("Issues list has appeared.")
            sleep(2)

            page_source = driver.get_page_source()
            soup = BeautifulSoup(page_source, 'html.parser')
            
            issue_list_container = soup.find('ul', class_='issue-items')
            if issue_list_container:
                issue_links = issue_list_container.find_all('a', class_='issue-info__vol-issue')
                latest_links = issue_links[:num_latest_issues]
                
                print(f"Found {len(issue_links)} issues for {target_year}. Selecting the latest {len(latest_links)}.")
                
                for link in latest_links:
                    full_url = "https://pubsonline.informs.org" + link['href']
                    issue_urls_to_visit.append(full_url)
            else:
                print(f"Could not find the issue list container even after waiting.")

        except Exception as e:
            print(f"Could not process year {target_year}. Maybe selectors failed. Error: {e}")

        if not issue_urls_to_visit:
            print("No issue URLs were collected. Exiting.")
            return

        print(f"\nSelected latest issues to scrape: {issue_urls_to_visit}")

        # --- 步骤 3 & 4: 遍历并抓取文章 ---
        for issue_url in issue_urls_to_visit:
            try:
                print(f"\nNavigating to issue TOC page: {issue_url}")
                driver.get(issue_url)
                sleep(10)
                
                issue_html = driver.get_page_source()
                issue_soup = BeautifulSoup(issue_html, 'html.parser')
                
                # --- 核心修正：使用新的、更精确的选择器 ---
                article_entries = issue_soup.select('div.issue-item')
                print(f"Found {len(article_entries)} articles in this issue.")

                for entry in article_entries:
                    # 文章标题和链接在 h5.issue-item__title > a
                    title_tag = entry.select_one('h5.issue-item__title > a')
                    if title_tag and title_tag.has_attr('href'):
                        title = title_tag.get_text(strip=True)
                        link = "https://pubsonline.informs.org" + title_tag['href']
                        
                        print(f"  -> Scraping article: {title[:70]}...")
                        
                        try:
                            # 直接访问文章的摘要页 (abs) 通常更快更稳定
                            abs_link = link.replace('/full/', '/abs/')
                            driver.get(abs_link)
                            sleep(5)
                            
                            article_html = driver.get_page_source()
                            article_soup = BeautifulSoup(article_html, 'html.parser')
                            
                            # 摘要在 div.abstractSection p 标签中
                            abstract_div = article_soup.find('div', class_='abstractSection')
                            abstract = abstract_div.find('p').get_text(strip=True) if abstract_div and abstract_div.find('p') else "Abstract not found"
                            
                            all_articles_data.append({
                                'year': target_year,
                                'title': title,
                                'link': link,
                                'abstract': abstract
                            })
                        except Exception as article_error:
                            print(f"    -! ERROR scraping article '{title[:50]}...': {article_error}")
                            continue
            except Exception as issue_error:
                print(f"  -! ERROR processing issue URL {issue_url}: {issue_error}")
                continue

    finally:
        if driver:
            driver.quit()
            print("\nBrowser closed.")

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
    # ================== 在这里配置您想抓取的期刊和范围 ==================
    journal_url = "https://pubsonline.informs.org/journal/isre"
    target_year = 2025  
    num_latest_issues_to_scrape = 2
    # =================================================================

    output_filename = f"ISRE_articles_{target_year}_latest_{num_latest_issues_to_scrape}_issues.csv"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, output_filename)
    
    scrape_latest_issues_informs(journal_url, output_path, target_year, num_latest_issues_to_scrape)