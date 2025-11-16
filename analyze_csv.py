import pandas as pd
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

# --- 配置 ---
# 加载环境变量 (如果您的API密钥在 .env 文件中)
load_dotenv()

# 从环境变量或直接字符串获取API密钥
# 警告：直接在代码中写入API密钥存在安全风险。强烈建议使用环境变量。
# 请将 "YOUR_GOOGLE_API_KEY" 替换为您的真实密钥，如果不是在 .env 文件中的话
GOOGLE_API_KEY = "AIzaSyAf3KUDleD3_MizuUgk8K5sJa1qZsXUCNM"


# 初始化 Google Generative AI 模型
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY)


def analyze_single_paper(paper_data):
    """
    通过一次API调用，对单篇论文的数据进行完整的四步分析，并返回中文分析结果。
    （此函数无需更改）
    """
    # 将论文数据格式化为字符串，以便输入模型
    paper_context = f"Title: {paper_data['title']}\nAbstract: {paper_data['abstract']}"

    # --- 创建一个包含所有四个任务的结构化提示词 ---
    # 我们要求模型使用特殊的分隔符来分隔每个部分的答案，以便于解析。
    comprehensive_prompt = PromptTemplate.from_template(
        """
        你是一位专业的研究助理。请根据以下学术论文的标题和摘要，提供一份全面的四部分中文分析报告。

        请严格按照以下顺序和格式完成任务，并在每个部分结束后使用指定的分隔符。

        **论文信息:**
        {context}

        ---

        **第1部分：识别主要研究变量**
        首先，识别出正在研究的主要研究变量。请关注文本中可衡量的概念和属性，并清晰地列出它们。
        完成此部分后，插入分隔符：[---变量---]

        **第2部分：评估数据获取难度**
        基于你在第1部分中识别的变量，评估获取每个变量数据的潜在难度，并为每个评估提供简要解释。
        完成此部分后，插入分隔符：[---难度---]

        **第3部分：建议数据处理方法与成本**
        同样基于第1部分中的变量，建议可能的数据处理方法，并估算其相关成本（例如，计算资源、人力投入、专用软件）。
        完成此部分后，插入分隔符：[---处理---]

        **第4部分：识别相关理论**
        最后，根据研究问题和你识别的变量，指出哪些理论视角或现有理论（例如，来自信息系统、社会科学或管理学）可以解释该研究问题和潜在结果。
        完成此部分后，插入分隔符：[---理论---]

        **重要提示：** 整个回答必须全部使用中文。输出应为一个包含所有四个部分和分隔符的连续文本块。
        """
    )

    # 创建并调用单一的分析链
    analysis_chain = comprehensive_prompt | model | StrOutputParser()
    print(f"    [1/1] 正在进行综合分析...")
    combined_analysis = analysis_chain.invoke({"context": paper_context})

    # --- 解析模型的单一响应 ---
    try:
        # 使用分隔符将响应文本分割成四个部分
        parts = combined_analysis.split('[---变量---]')
        research_variables = parts[0].strip()
        
        parts = parts[1].split('[---难度---]')
        data_acquisition_difficulty = parts[0].strip()
        
        parts = parts[1].split('[---处理---]')
        data_processing = parts[0].strip()
        
        parts = parts[1].split('[---理论---]')
        relevant_theories = parts[0].strip()

        print(f"    分析完成，成功解析所有部分。")
        
    except IndexError:
        # 如果模型未能按预期格式返回，则提供一个备用方案
        print("    警告：模型输出格式不符合预期，无法完美解析。将返回整个文本块。")
        research_variables = "解析失败，以下是完整输出：\n" + combined_analysis
        data_acquisition_difficulty = "N/A"
        data_processing = "N/A"
        relevant_theories = "N/A"

    return research_variables, data_acquisition_difficulty, data_processing, relevant_theories


def generate_analysis_report(file_path, num_rows=5):
    """
    读取CSV文件，逐篇分析论文，并生成一份完整的中文分析报告。
    【新增逻辑】每处理3篇文章，就将结果追加写入MD文件，以防程序中断丢失数据。
    """
    try:
        df = pd.read_csv(file_path)
        if num_rows is not None:
            df_to_process = df.head(num_rows)
        else:
            df_to_process = df

        print(f"成功读取CSV文件: {file_path}")
        print(f"准备分析 {len(df_to_process)} 篇文章...\n")

        report_filename = "per_article_analysis_report_zh_optimized.md"
        
        # 【新增改动 1/4】: 在循环开始前，先用'w'模式清空或创建文件，并写入主标题。
        # 这样可以确保每次运行都是一个全新的报告。
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write("# 论文数据分析报告\n\n")

        # 【新增改动 2/4】: 初始化一个缓冲区和一个计数器。
        articles_buffer = ""  # 用于暂存每3篇文章的内容
        processed_count = 0   # 记录已处理的文章数量

        for index, row in df_to_process.iterrows():
            print(f"--- 正在分析第 {index + 1} 篇文章: {row['title']} ---")
            
            variables, acquisition, processing, theories = analyze_single_paper(row)
            
            # 将新分析的文章内容添加到缓冲区，而不是直接加到总报告中
            articles_buffer += f"## {index + 1}. {row['title']}\n\n"
            articles_buffer += "### 1. 主要研究变量\n"
            articles_buffer += f"{variables}\n\n"
            articles_buffer += "### 2. 数据获取难度\n"
            articles_buffer += f"{acquisition}\n\n"
            articles_buffer += "### 3. 数据处理方法与成本\n"
            articles_buffer += f"{processing}\n\n"
            articles_buffer += "### 4. 相关理论\n"
            articles_buffer += f"{theories}\n\n"
            articles_buffer += "---\n\n"
            print(f"--- 第 {index + 1} 篇文章分析完成 ---\n")

            processed_count += 1

            # 【新增改动 3/4】: 每处理3篇文章，就执行一次写入操作。
            if processed_count % 3 == 0:
                print(f"--- 已处理 {processed_count} 篇文章，正在保存进度到 {report_filename} ---")
                # 使用 'a' (append) 模式将缓冲区内容追加到文件中
                with open(report_filename, "a", encoding="utf-8") as f:
                    f.write(articles_buffer)
                
                # 写入后清空缓冲区，为下一批文章做准备
                articles_buffer = ""
                print(f"--- 进度保存完毕 ---\n")

        # 【新增改动 4/4】: 循环结束后，检查缓冲区中是否还有剩余的文章（总数不是3的倍数时）。
        if articles_buffer:
            print(f"--- 正在保存最后剩余的文章到 {report_filename} ---")
            with open(report_filename, "a", encoding="utf-8") as f:
                f.write(articles_buffer)
            print(f"--- 最后保存完成 ---\n")

        print(f"报告生成完毕！已保存至: {report_filename}")

    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 未找到。")
    except pd.errors.EmptyDataError:
        print(f"错误: 文件 '{file_path}' 为空。")
    except Exception as e:
        print(f"发生未知错误: {e}")


if __name__ == "__main__":
    # --- 请在这里设置您的CSV文件路径 ---
    csv_file_path = "/Users/dxk/Repos/learning/rss_agent/headless_browser_tests/seleniumbase_uc_test/scraped_articles_data/combined_articles_2025.csv"
    
    # --- 设置您想分析的论文数量 (设置为 None 可分析所有论文) ---
    # 例如，设置为10，它会在处理第3、6、9篇后各保存一次，最后再保存第10篇。
    articles_to_analyze = 62

    generate_analysis_report(csv_file_path, num_rows=articles_to_analyze)