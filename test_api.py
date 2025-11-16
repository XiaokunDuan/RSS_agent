import google.generativeai as genai
import os

print("--> 正在运行最简API连通性测试...")

try:
    # 使用你提供的硬编码API密钥
    api_key = "AIzaSyDt9DpVj4sTR7GlYwleqU7-4pX51zA7e1M"
    
    genai.configure(api_key=api_key)

    print("--> 正在初始化模型...")
    model = genai.GenerativeModel('gemini-1.5-pro-latest')

    print("--> 正在发送一个简单的请求 ('Hello')...")
    # generate_content 是一个阻塞调用，如果网络不通，会卡在这里
    response = model.generate_content("Hello")

    print("\n✅✅✅ 成功! API通信正常! ✅✅✅")
    print("Gemini 的回复:")
    print(response.text)

except Exception as e:
    print(f"\n❌❌❌ 失败! 发生了错误! ❌❌❌")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误详情: {e}")