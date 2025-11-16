
# ==============================================================================
# 📚 信息系统(IS)顶刊论文摘要自动汇总程序 (MISQ & ISJ) - 修复版
# 作者: ChatGPT (GPT-5) & AI Assistant
# 版本: 2.0
# 更新日志:
# - 使用 feedparser 替代 RSSFeedLoader 以解决 ISJ 的 403 Forbidden 错误。
#   (This bypasses the loader's attempt to scrape the main article URL, which is blocked.)
# - 在摘要生成前增加内容检查，避免为空的条目（如'Issue Information'）浪费API调用。
# - 增加了 MISQ 的 RSS 源。
# ==============================================================================

print("\n--> 正在加载主程序...")

try:
    import os, csv, time, warnings
    from datetime import datetime, timedelta
    from collections import defaultdict
    warnings.filterwarnings("ignore", category=UserWarning)

    # NEW: Import feedparser and Document
    import feedparser
    from langchain_core.documents import Document

    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_classic.chains.summarize import load_summarize_chain
    from langchain_core.prompts import PromptTemplate
    import markdown

    # ==============================================================================
    # 🔧 配置 (Configuration)
    # ==============================================================================
    # ⚠️ 请从环境变量中加载您的 Google API Key
    # 例如: export GOOGLE_API_KEY='YourActualApiKeyHere'
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    DRIVE_MEMORY_PATH = "." # Changed to local directory
    MEMORY_FILE = os.path.join(DRIVE_MEMORY_PATH, "processed_is_links2.csv")
    RETENTION_DAYS = 7 # 记忆文件保留天数

    LLM_MODEL = "gemini-2.5-pro" # 使用最新的模型
    LLM_TEMPERATURE = 0.2
    PROMPT_TEMPLATE = """Please analyze the following academic abstract in Chinese. From the text, extract the core research question, the methodology used, and the key findings. Present the output in a structured list format.

Original Abstract: "{text}"

---
- **研究问题 (Research Question):**
- **研究方法 (Methodology):**
- **主要发现 (Key Findings):**
"""

    # ==============================================================================
    # 🧩 RSS 源 (RSS Feeds)
    # ==============================================================================
    MEDIA_SOURCES = {
        "MIS Quarterly (MISQ)": "https://aisel.aisnet.org/misq/recent.rss",
        "Information Systems Journal (ISJ)": "https://onlinelibrary.wiley.com/feed/13652575/most-recent",
        "European Journal of Information Systems (EJIS)": "https://www.tandfonline.com/feed/rss/tjis20"
    }

    # ==============================================================================
    # ⚙️ 功能函数 (Core Functions) - v3.0 批量处理版
    # ==============================================================================
    def load_processed_links(memory_file):
        processed = set()
        if not os.path.exists(memory_file):
            return processed
        try:
            with open(memory_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        processed.add(row[0])
            print(f"\n--> 从 {memory_file} 加载了 {len(processed)} 条已处理链接。")
        except Exception as e:
            print(f"--> ⚠️ 读取记忆文件失败: {e}")
        return processed

    def fetch_articles(sources: dict, processed_links: set):
        print("\n--> 正在加载各期刊 RSS 源...")
        all_docs = []
        newly_processed_links = []

        for name, url in sources.items():
            print(f"    - 正在处理【{name}】...")
            try:
                feed = feedparser.parse(url)
                if feed.bozo:
                    print(f"      ⚠️ 【{name}】的RSS源可能格式不正确: {feed.bozo_exception}")

                docs_count = 0
                for entry in feed.entries:
                    link = entry.get("link", "N/A")
                    if link in processed_links or link == "N/A":
                        continue

                    content = entry.get("summary") or entry.get("dc_description") or entry.get("description", "")
                    # 改进内容检查：跳过空内容或过短的内容（可能不是摘要）
                    MIN_CONTENT_LENGTH = 100
                    if not content or len(content) < MIN_CONTENT_LENGTH:
                        continue

                    doc = Document(
                        page_content=content,
                        metadata={
                            "link": link,
                            "title": entry.get("title", "N/A"),
                            "source_name": name
                        }
                    )
                    all_docs.append(doc)
                    newly_processed_links.append(link)
                    docs_count += 1

                if docs_count > 0:
                    print(f"      ✅ 找到 {docs_count} 篇新文章。")
                else:
                    print("      - 没有找到新文章。")

            except Exception as e:
                print(f"      ❌ 加载或解析失败: {url}\n         错误: {str(e)[:120]}")

        print(f"\n--> 共找到 {len(all_docs)} 篇需处理的新论文。")
        return all_docs, newly_processed_links

    def analyze_articles_individually(docs, api_key, model, temp, prompt_str):
        print("\n--> 正在调用 Gemini 模型逐篇分析论文...")
        llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=temp)
        prompt = PromptTemplate(template=prompt_str, input_variables=["text"])

        final_md = ""
        final_md += f"# 学术论文分析报告 ({datetime.now().strftime('%Y-%m-%d')})\n\n"

        for i, doc in enumerate(docs):
            title = doc.metadata.get("title", "N/A")
            link = doc.metadata.get("link", "N/A")
            source_name = doc.metadata.get("source_name", "N/A")

            print(f"    - 正在分析 [{i+1}/{len(docs)}]【{source_name}】: {title[:50]}...")
            try:
                full_prompt = prompt.format(text=doc.page_content)
                result = llm.invoke(full_prompt)
                analysis = result.content if hasattr(result, 'content') else str(result)

                final_md += f"## {i+1}. {title}\n\n"
                final_md += f"**来源 (Source):** {source_name}\n"
                final_md += f"**链接 (Link):** <{link}>\n\n"
                final_md += f"**摘要分析:**\n{analysis}\n\n---\n\n"
                time.sleep(2)
            except Exception as e:
                print(f"      ❌ 分析文章《{title[:50]}...》时出错: {e}")
                final_md += f"## {i+1}. {title}\n\n"
                final_md += f"**链接 (Link):** <{link}>\n\n"
                final_md += "**摘要分析:**\n分析失败。\n\n---\n\n"
        return final_md



    def save_processed_links(memory_file, new_links):
        try:
            with open(memory_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for link in new_links:
                    writer.writerow([link])
            print(f"\n--> {len(new_links)} 个新链接已保存到: {memory_file}")
        except Exception as e:
            print(f"\n--> ❌ 保存处理过的链接失败: {e}")


    def save_report(report_md):
        report_file_path = "report.md"
        try:
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            print(f"\n--> ✅ 报告已成功保存到: {report_file_path}")
        except Exception as e:
            print(f"\n--> ❌ 保存报告失败: {e}")

    # ==============================================================================
    # 🚀 主流程 (Main Workflow)
    # ==============================================================================
    def main():
        if not GOOGLE_API_KEY:
            print("❌ 错误: GOOGLE_API_KEY 环境变量未设置。")
            print("请在运行脚本前设置该环境变量, 例如: export GOOGLE_API_KEY='YourActualApiKeyHere'")
            return

        processed_links = load_processed_links(MEMORY_FILE)
        all_docs, new_links = fetch_articles(MEDIA_SOURCES, processed_links)

        if all_docs:
            report = analyze_articles_individually(all_docs, GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE, PROMPT_TEMPLATE)
            print("\n" + "="*50 + "\n ✨ 生成的报告内容 ✨\n" + "="*50)
            print(report)
            save_report(report)
            if new_links:
                save_processed_links(MEMORY_FILE, new_links)
        else:
            print("\n✅ 未从任何 RSS 源中找到可处理的新文章，程序执行完毕。")

    main()

except Exception as e:
    import traceback
    print(f"\n❌ 程序执行期间发生严重错误: {e}")
    traceback.print_exc()
