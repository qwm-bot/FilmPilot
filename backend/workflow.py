import os
import json
import logging
import time
from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain.memory import ConversationBufferMemory, FileChatMessageHistory
from langchain.chains import ConversationChain
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from Tool.amap_api import get_route_info
from Tool.maoyan_api import get_film_cinema_schedule
from Tool.profile_agent_tool import extract_and_recommend_movie
from Tool.core import MovieRecommender
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from logging.handlers import RotatingFileHandler
import datetime

load_dotenv()

# 配置日志系统
def setup_logging():
    """配置日志系统 - UTF-8编码版本"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d")
    log_filename = os.path.join(log_dir, f"movie_assistant_{timestamp}.log")
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    file_handler = RotatingFileHandler(
        log_filename, 
        maxBytes=5 * 1024 * 1024,
        backupCount=7,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger

logger = setup_logging()

dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope_api_key:
    raise ValueError("Please set the environment variable DASHSCOPE_API_KEY")

llm = ChatTongyi(model="qwen-turbo", dashscope_api_key=dashscope_api_key, temperature=0)

tools = {
    "get_route_info": get_route_info,
    "get_film_cinema_schedule": get_film_cinema_schedule,
    "extract_and_recommend_movie": extract_and_recommend_movie
}

tools_description = """
Available tools:
- get_route_info: Get navigation variables for frontend visualization, including coordinates, mode, API keys, etc. Parameters: {"origin": "origin address", "address": "destination address", "city": "city name (optional)", "mode": "Driving|Walking|Riding|Transfer|TruckDriving (optional)", ...other params}
- get_film_cinema_schedule: Search for a movie by keyword and return the cinema schedule info for that movie in the specified city and date. Parameters: {"keyword": "movie name", "cityId": "city ID (default 40)", "showDate": "YYYY-MM-DD (optional)", "limit": "number of results (optional)","lng":"longitude of the origin address(optional)","lat":"latitude of the origin address"}
- extract_and_recommend_movie: Extract user profile from user_input, selected_tags, frontend_data, then recommend or answer about movies. Parameters: {"user_input": "user's natural language input", "selected_tags": "user selected tags (optional)", "frontend_data": "frontend structured data (optional)"}
"""

system_prompt = f"""
You are an AI assistant who can help answer movie and navigation questions by calling tools.

# IMPORTANT: Always respond with a valid, compact JSON object ONLY. Do NOT include any explanations, comments, markdown, or extra text. The response must be pure JSON, e.g.:
# {{"tool": "tool_name", "parameters": {{"param1": "value1"}}}}
# or
# {{"tool": "none", "parameters": {{}}, "answer": "your final answer here"}}

Respond ONLY in the following JSON format:
{{
  "tool": "tool_name",
  "parameters": {{ ... }}
}}
If no tool is needed, respond with:
{{
  "tool": "none",
  "parameters": {{}},
  "answer": "your final answer here"
}}

Tools description:
{tools_description}

User question will be provided next.
"""

def get_conversation_memory(conversation_id):
    """获取基于文件的对话记忆（兼容新版LangChain）"""
    os.makedirs("chat_histories", exist_ok=True)
    file_path = f"chat_histories/chat_{conversation_id}.json"
    message_history = FileChatMessageHistory(file_path)
    
    return ConversationBufferMemory(
        memory_key="history",
        return_messages=True,
        chat_memory=message_history
    )

def call_llm_with_memory(user_input, conversation_id):
    """统一使用消息对象格式（解决格式冲突）"""
    memory = get_conversation_memory(conversation_id)
    history = memory.load_memory_variables({}).get("history", [])
    
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(history)
    messages.append(HumanMessage(content=user_input))
    
    response = llm.invoke(messages)
    return response.content

""" def run_tool(tool_name, parameters, llm_fallback=None):
    if tool_name not in tools:
        if llm_fallback is not None:
            return llm_fallback
        return f"Error: unknown tool {tool_name}"
    try:
        return tools[tool_name](parameters)
    except Exception as e:
        return f"Error calling tool {tool_name}: {e}" """
def run_tool(tool_name, parameters, llm_fallback=None):
    if tool_name not in tools:
        return llm_fallback or f"Error: unknown tool {tool_name}"
    try:
        tool = tools[tool_name]

        # 如果是 LangChain 的 BaseTool 类型
        if hasattr(tool, "invoke"):
            return tool.invoke(parameters)

        # 如果是 extract_and_recommend_movie（可能是函数也可能是 tool）
        if tool_name == "extract_and_recommend_movie":
            user_input = parameters.get("user_input", "")
            selected_tags = parameters.get("selected_tags", None)
            frontend_data = parameters.get("frontend_data", None)
            return tool(user_input=user_input, selected_tags=selected_tags, frontend_data=frontend_data)

        # 其余普通函数
        return tool(**parameters)
    except Exception as e:
        return f"Error calling tool {tool_name}: {e}"

def summarize_with_llm(user_input, tool_result, tool_name=None):
    if tool_name == "get_route_info":
        if isinstance(tool_result, str):
            print(tool_result)
            return tool_result
        return json.dumps(tool_result, ensure_ascii=False)
    summary_prompt = f"""
你是一个智能助手，请根据用户的原始问题和工具返回的结构化结果，生成详细、准确的中文回复，尽量保留原始返回的信息，建议加点合适的emoji。

用户问题：{user_input}
工具返回结果：{json.dumps(tool_result, ensure_ascii=False)}

请根据工具结果和用户需求，用自然语言回复,尽量保留原有的信息。
"""
    messages = [
        {"role": "system", "content": "你是一个专业的电影和出行助手。"},
        {"role": "user", "content": summary_prompt}
    ]
    response = llm.invoke(messages)
    return response.content.strip()

def workflow(user_input, conversation_id=None):
    if isinstance(user_input, dict):
        user_input_str = json.dumps(user_input, ensure_ascii=False)
    else:
        user_input_str = user_input
    logger.info(f"📩 用户输入: {user_input_str}")

    if isinstance(user_input, dict):
        user_input_str = user_input.get("currentInput", "")
        if not conversation_id:
            conversation_id = str(int(time.time()))
    else:
        user_input_str = user_input
        if not conversation_id:
            conversation_id = str(int(time.time()))
    
    # 获取记忆对象
    memory = get_conversation_memory(conversation_id)
    
    # 调用模型获取初始响应
    model_response = call_llm_with_memory(user_input_str, conversation_id)
    logger.info(f"Model response:\n{model_response}")

    try:
        tool_call = json.loads(model_response)
    except Exception as e:
        logger.error(f"❌ JSON解析失败: {e}\n原始内容: {model_response}")
        return f"Failed to parse model response: {e}\n原始内容: {model_response}"

    if tool_call["tool"] == "none":
        # 直接获取最终回答
        final_answer = tool_call.get("answer", "Sorry, no answer was provided.")
        logger.info(f"📤 系统响应: {final_answer}")
    else:
        try:
            # 调用工具并获取结果
            tool_result = run_tool(
                tool_call["tool"],
                tool_call.get("parameters", {}),
                llm_fallback=tool_call.get("answer", f"Tool {tool_call['tool']} not found. LLM output: {tool_call}")
            )
            # 生成自然语言摘要
            final_answer = summarize_with_llm(user_input_str, tool_result, tool_name=tool_call["tool"])
            logger.info(f"📤 系统响应: {final_answer}")
        except Exception as e:
            logger.error(f"❌ 工具执行失败: {e}")
            return f"Tool execution error: {e}"
    
    # 关键修改：只将最终的自然语言回答保存到记忆
    memory.save_context({"input": user_input_str}, {"output": final_answer})
    
    return final_answer

# FastAPI应用
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/workflow")
async def workflow_endpoint(request: Request):
    try:
        data = await request.json()
        conversation_id = data.get("conversation_id") or str(int(time.time()))
        result = workflow(data, conversation_id=conversation_id)
        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/daily_recommendations")
async def daily_recommendations(count: int = 6):
    recommender = MovieRecommender(qwen_api_key="sk-41ec31f7dbc74f4b81a63f892bd528e4")
    movies = recommender.get_daily_recommendations(count=count)
    result = []
    for i, m in enumerate(movies):
        result.append({
            "id": i+1,
            "title": m.get("title", ""),
            "year": m.get("release_date", "")[:4],
            "rating": m.get("vote_average", 0),
            "director": m.get("director", ""),
            "country": m.get("country", ""),
            "description": m.get("overview", ""),
            "poster_url":m.get('poster_url'),
            "tagline": m.get("tagline", "")
        })

    return result
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)