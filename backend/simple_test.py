import os
import json
import logging
from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from Tool.amap_api import get_route, get_location_by_address, get_route_info
from Tool.maoyan_api import (
    get_film_info,
    get_film_detail,
    get_maoyan_cinemas_by_movie,
    get_cinema_time
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
if not dashscope_api_key:
    raise ValueError("Please set the environment variable DASHSCOPE_API_KEY")

# Initialize Tongyi LLM
llm = ChatTongyi(model="qwen-turbo", dashscope_api_key=dashscope_api_key, temperature=0)

# Tool mapping
tools = {
    "get_route": get_route,
    "get_location_by_address": get_location_by_address,
    "get_route_info": get_route_info,
    "get_film_info": get_film_info,
    "get_film_detail": get_film_detail,
    "get_maoyan_cinemas_by_movie": get_maoyan_cinemas_by_movie,
    "get_cinema_time": get_cinema_time
}

# Tool descriptions for LLM prompt
tools_description = """
Available tools:
- get_location_by_address: Get longitude and latitude for a given address. Parameters: {"address": "address string", "city": "city name (optional)"}
- get_route: Plan a route between two locations using various transportation modes. Parameters: {"origin": "longitude,latitude", "address": "destination address", "city": "city name (optional)", "mode": "driving|walking|bicycling|electrobike|transit (optional)", ...other AMap API params}
- get_route_info: Get navigation variables for frontend visualization, including coordinates, mode, API keys, etc. Parameters: {"origin": [longitude, latitude] or "longitude,latitude", "address": "destination address", "city": "city name (optional)", "mode": "Driving|Walking|Riding|Transfer|TruckDriving (optional)", ...other params}
- get_film_info: Search for a movie by keyword. Parameters: {"keyword": "movie name", "ci": "city ID (optional)", "offset": "pagination offset (optional)", "limit": "number of results (optional)"}
- get_film_detail: Get detailed information for a movie by its ID. Parameters: {"movie_id": "movie ID"}
- get_maoyan_cinemas_by_movie: Crawl Maoyan web page to get raw HTML of cinema schedule for a movie. Parameters: {"movie_id": "movie ID", "city_id": "city ID (optional)", "filename": "output file name (optional)"}
- get_cinema_time: Get cinema schedule info for a movie in a city and date. Parameters: {"movieId": "movie ID", "cityId": "city ID (default 40)", "showDate": "YYYY-MM-DD (optional)", "limit": "number of results (optional)"}
"""

# System prompt for LLM
system_prompt = f"""
You are an AI assistant who can help answer movie and navigation questions by calling tools.
You must respond ONLY in the following JSON format to specify which tool to call and with which parameters:

{{
  "tool": "tool_name",
  "parameters": {{
    // parameters object here
  }}
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

def call_llm_for_tool(user_question, system_prompt=system_prompt):
    """Let LLM decide which tool to call and with what parameters."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_question}
    ]
    response = llm.invoke(messages)
    return response.content

def parse_tool_response(model_response):
    try:
        obj = json.loads(model_response)
        return obj
    except Exception as e:
        logger.error(f"Failed to parse model response JSON: {e}\nContent was:\n{model_response}")
        return None

def run_tool(tool_name, parameters):
    if tool_name not in tools:
        logger.error(f"Tool {tool_name} is not registered")
        return f"Error: unknown tool {tool_name}"
    try:
        result = tools[tool_name].invoke(parameters)
        return result
    except Exception as e:
        logger.error(f"Exception when calling tool {tool_name}: {e}")
        return f"Error calling tool {tool_name}: {e}"

def summarize_with_llm(user_question, tool_results):
    """Let LLM summarize the final answer for the user."""
    summary_prompt = f"""
User question: {user_question}

Tool results:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

Please give a concise and friendly answer to the user based on the above info.
"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant who summarizes tool results for the user."},
        {"role": "user", "content": summary_prompt}
    ]
    response = llm.invoke(messages)
    return response.content

def multi_step_workflow(user_question):
    """
    Example: For a query like 'Find cinemas showing Malice in Beijing tomorrow and plan a route',
    1. Use LLM to get movie info (get_film_info)
    2. Use movie id to get cinema info (get_cinema_time)
    3. Use cinema address to get coordinates (get_location_by_address)
    4. Use user location and cinema location to plan route (get_route)
    5. Summarize all results
    """
    tool_results = {}

    # Step 1: Get movie info
    model_response = call_llm_for_tool(user_question)
    logger.info(f"Model response:\n{model_response}")
    tool_call = parse_tool_response(model_response)
    if not tool_call or tool_call["tool"] == "none":
        return tool_call.get("answer", "Sorry, no answer was provided.") if tool_call else "Sorry, I could not understand your request."
    movie_info = run_tool(tool_call["tool"], tool_call.get("parameters", {}))
    tool_results["movie_info"] = movie_info

    # Step 2: Get cinema info (if movie id available)
    movie_id = None
    if isinstance(movie_info, dict):
        movie_id = movie_info.get("id") or movie_info.get("movie_id")
    if movie_id:
        cinema_question = f"Find cinemas for movie id {movie_id} in Beijing tomorrow."
        cinema_response = call_llm_for_tool(cinema_question)
        cinema_tool_call = parse_tool_response(cinema_response)
        cinema_info = run_tool(cinema_tool_call["tool"], cinema_tool_call.get("parameters", {}))
        tool_results["cinema_info"] = cinema_info

        # Step 3: (Optional) Get route for the first cinema
        if isinstance(cinema_info, list) and len(cinema_info) > 0:
            cinema = cinema_info[0]
            cinema_address = cinema.get("addr") or cinema.get("name")
            if cinema_address:
                # Assume user location is fixed for demo
                user_location = "116.397128,39.916527"  # Tiananmen Square, Beijing
                route_question = f"Plan a route from {user_location} to {cinema_address} in Beijing."
                route_response = call_llm_for_tool(route_question)
                route_tool_call = parse_tool_response(route_response)
                route_info = run_tool(route_tool_call["tool"], route_tool_call.get("parameters", {}))
                tool_results["route_info"] = route_info

    # Step 4: Summarize all results
    summary = summarize_with_llm(user_question, tool_results)
    return summary

if __name__ == "__main__":
    query = "Find cinemas showing Malice in Beijing tomorrow and plan a route."
    answer = multi_step_workflow(query)
    print("Final answer:")
    print(answer)
