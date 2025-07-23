from langchain_core.tools import tool
from Tool.user_interest_extract import extract_user_profile_from_input
from Tool.agent import movie_agent_tool
from dotenv import load_dotenv
import os
load_dotenv()
openai_api_key = os.getenv("DASHSCOPE_API_KEY")

@tool(description="根据用户输入、标签和前端数据自动提取用户画像，并调用大模型Agent进行电影推荐或详情问答。user_input既用于画像提取也作为推荐/问答的查询内容。参数包括用户自然语言输入、标签、前端结构化数据、API密钥，返回推荐或问答结果。")
def extract_and_recommend_movie(user_input: str = "", selected_tags: dict = None, frontend_data: dict = None, user_id: str = "tool_temp_user") -> str:
    """
    用户画像提取与电影推荐一体化工具。

    该工具首先根据用户自然语言输入、标签和前端结构化数据，自动提取用户画像信息；
    然后将画像作为参数，user_input作为查询内容，调用大模型Agent进行电影推荐或电影详情问答。

    Args:
        user_input (str): 用户自然语言输入，既用于画像提取，也作为推荐/问答的查询内容。
        selected_tags (dict, optional): 用户选择的标签（如类型、演员等）。
        frontend_data (dict, optional): 前端传递的结构化数据（如性别、年龄段、偏好等）。
        user_id (str, optional): 用户ID。
        openai_api_key (str, optional): OpenAI API密钥。

    Returns:
        str: 推荐电影列表、电影详情或错误信息。
    """
    user_profile = extract_user_profile_from_input(user_input=user_input, selected_tags=selected_tags, frontend_data=frontend_data, user_id=user_id)
    return movie_agent_tool.invoke({
        "user_profile": user_profile,
        "openai_api_key": openai_api_key,
        "query": user_input
    }) 