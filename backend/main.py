from Tool.agent import create_movie_agent, run_movie_agent

# 配置用户画像
user_profile = {
    "gender": "女",
    "age_group": "28-35",
    "fav_genres": ["爱情", "喜剧"]
}

# 创建Agent
agent = create_movie_agent(
    user_profile=user_profile,
    openai_api_key="sk-41ec31f7dbc74f4b81a63f892bd528e4"  # 替换为你的OpenAI API密钥
)

# 处理查询
queries = [
    "推荐一部温馨的爱情电影",
    "我想看安妮·海瑟薇主演的电影",
    "《泰坦尼克号》的导演是谁？",
    "看了《爱乐之城》，有类似的音乐主题电影推荐吗？"
]

for query in queries:
    print(f"\n📌 用户查询: {query}")
    response = run_movie_agent(agent, query)
    print(f"\n💬 系统响应:\n{response}")
    print("\n" + "="*80)