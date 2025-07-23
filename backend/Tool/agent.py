from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from Tool.tools import MovieRecommendationTool, MovieDetailTool
from Tool.core import MovieRecommender
from typing import Dict, Any
from langchain_core.tools import tool

def create_movie_agent(user_profile: Dict[str, Any] = None, openai_api_key: str = None,user_id: str = "default") -> Any:
    """
    创建电影推荐Agent
    
    参数:
    user_profile: 用户画像字典
    openai_api_key: 用于LangChain的OpenAI API密钥
    
    返回:
    配置好的LangChain Agent
    """
    recommender = MovieRecommender(user_profile=user_profile, qwen_api_key=openai_api_key,user_id=user_id)
    tools = [
        MovieRecommendationTool(recommender=recommender),
        MovieDetailTool(recommender=recommender)
    ]
    agent = initialize_agent(
        tools=tools,
        llm = ChatOpenAI(
            model="qwen-plus",  # 或 "qwen-turbo"
            api_key=openai_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # Qwen OpenAI兼容API地址
            temperature=0.7
        ),
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3
    )
    return agent

def run_movie_agent(agent, query: str) -> str:
    """
    使用Agent处理查询
    
    参数:
    agent: 创建的电影推荐Agent
    query: 用户查询文本
    
    返回:
    Agent的响应结果
    """
    try:
        response = agent.invoke(query)
        return response
    except Exception as e:
        return f"处理查询时出错: {str(e)}"

@tool(description="根据用户画像和查询，调用大模型Agent进行电影推荐或详情问答。参数包括用户画像、OpenAI API密钥和用户查询，返回推荐或问答结果。")
def movie_agent_tool(user_profile: dict = None, openai_api_key: str = None, query: str = None) -> str:
    """
    电影推荐与问答工具（Agent版）

    根据用户画像和查询，自动调用大模型Agent进行电影推荐或电影详情问答。

    Args:
        user_profile (dict, optional): 用户画像字典，如{"gender": "男", "age_group": "25-35", "fav_genres": ["科幻", "动作"]}。
        openai_api_key (str, optional): OpenAI API密钥，用于LangChain大模型。
        query (str): 用户的自然语言查询，如“推荐一些适合情侣看的浪漫喜剧”或“《流浪地球2》的导演和主演是谁？”

    Returns:
        str: Agent的响应结果，可能是推荐电影列表、电影详情或错误信息。
    """
    agent = create_movie_agent(user_profile=user_profile, openai_api_key=openai_api_key)
    return run_movie_agent(agent, query)

if __name__ == "__main__":
    # 示例用法
    user_profile = {
        "gender": "男",
        "age_group": "25-35",
        "fav_genres": ["科幻", "动作"]
    }
    import os
    os.environ.pop("OPENAI_API_KEY", None)
    # 替换为你的OpenAI API密钥
    OPENAI_API_KEY = "sk-41ec31f7dbc74f4b81a63f892bd528e4"

    # 测试不同场景
    test_queries = [
        "推荐一些适合情侣看的浪漫喜剧",
        "看了《盗梦空间》，有没有类似烧脑电影？",
        "《流浪地球2》的导演和主演是谁？",
        "推荐克里斯托弗·诺兰导演的电影"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"用户查询: {query}")
        response = movie_agent_tool(
            user_profile=user_profile,
            openai_api_key=OPENAI_API_KEY,
            query=query
        )
        print(f"\n响应结果:\n{response}")
        print(f"{'='*50}\n")