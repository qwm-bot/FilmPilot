from langchain_core.tools import tool
from Tool.user_interest_extract import extract_user_profile_from_input
from Tool.agent import movie_agent_tool
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()
openai_api_key = os.getenv("DASHSCOPE_API_KEY")

# 实际工具函数（不加装饰器，方便本地测试）
def _extract_and_recommend_movie(user_input: str = "", selected_tags: dict = None, frontend_data: dict = None) -> str:
    user_profile = extract_user_profile_from_input(
        user_input=user_input,
        selected_tags=selected_tags,
        frontend_data=frontend_data
    )

    # LangChain BaseTool.invoke() 要求将所有参数打包成一个 dict 作为 input
    input_payload = {
        "user_profile": user_profile,
        "openai_api_key": openai_api_key,
        "query": user_input
    }

    return movie_agent_tool.invoke(input_payload)

# 包装为 LangChain Tool 工具对象
@tool(description="根据用户输入、标签和前端数据自动提取用户画像，并调用大模型Agent进行电影推荐或详情问答。")
def extract_and_recommend_movie(user_input: str = "", selected_tags: dict = None, frontend_data: dict = None) -> str:
    return _extract_and_recommend_movie(user_input, selected_tags, frontend_data)

# 本地测试函数
def test_extract_and_recommend_movie():
    user_input = "我想看一些喜剧片，最好是轻松愉快的那种。"
    selected_tags = {
        "genre": "Comedy",
        "mood": "Lighthearted"
    }
    frontend_data = {
        "ageRange": "18-25",
        "gender": "Male",
        "lat": 38.988726,
        "lng": 117.346194,
        "moviePreferences": ["Action", "Adventure"]
    }

    result = _extract_and_recommend_movie(
        user_input=user_input,
        selected_tags=selected_tags,
        frontend_data=frontend_data
    )
    print("测试结果:", result)

# 执行测试
if __name__ == "__main__":
    test_extract_and_recommend_movie()
