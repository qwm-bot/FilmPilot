from langchain.tools import BaseTool
from pydantic import BaseModel, Field, TypeAdapter, PrivateAttr
import re
from typing import Type, Optional
from Tool.core import MovieRecommender

class RecommendationInput(BaseModel):
    query: str = Field(description="用户对电影需求的描述")

class DetailInput(BaseModel):
    movie_title: str = Field(description="具体电影名称，格式如《盗梦空间》")

class MovieRecommendationTool(BaseTool):
    """电影推荐工具（处理多种推荐场景）"""
    name: str = "movie_recommendation_tool"
    description: str = (
        "当用户要求电影推荐时使用此工具，支持：\n"
        "1. 常规推荐（如'推荐浪漫喜剧'）\n"
        "2. 基于特定电影的推荐（如'看了《盗梦空间》，有类似电影吗？'）\n"
        "3. 导演/演员特定推荐（如'推荐诺兰导演的电影'）"
    )
    args_schema: Optional[Type[BaseModel]] = RecommendationInput
    _recommender: MovieRecommender = PrivateAttr()

    def __init__(self, recommender: MovieRecommender, **kwargs):
        super().__init__(**kwargs)
        self._recommender = recommender
        
    def _run(self, query: str) -> str:
        if self.is_specific_movie_query(query):
            return self.handle_movie_based_query(query)
        elif self.is_director_actor_query(query):
            return self.handle_creator_query(query)
        else:
            return self.handle_general_query(query)
    
    def is_specific_movie_query(self, query: str) -> bool:
        return "《" in query and "》" in query
    
    def is_director_actor_query(self, query: str) -> bool:
        return "导演" in query or "主演" in query or "演员" in query
    
    def handle_general_query(self, query: str) -> str:
        tags = self._recommender.parse_user_intent(query)
        combined_tags = self._recommender.merge_profile_with_tags(
            self._recommender.user_profile, tags
        )
        movies = self._recommender.search_tmdb_movies(combined_tags)
        top_movies = self._recommender.rerank_movies_with_deepseek(
            movies, query, self._recommender.user_profile
        )
        return self._recommender.format_movie_results(top_movies)
    
    def handle_movie_based_query(self, query: str) -> str:
        """修改：基于特定电影的相似推荐"""
        movie_title = re.findall(r"《(.+?)》", query)[0]
        movie_details = self._recommender.get_movie_details(movie_title)
        
        if not movie_details:
            return f"未找到电影《{movie_title}》的相关信息"
        
        # 直接从电影详情中提取信息构建搜索条件
        tags = {}
        
        # 1. 添加导演ID
        if movie_details["directors"]:
            tags["directors"] = [director["id"] for director in movie_details["directors"]]
        
        # 2. 添加演员ID
        if movie_details["actors"]:
            tags["actors"] = [actor["id"] for actor in movie_details["actors"]]
        
        # 3. 添加关键词ID
        if movie_details.get("keyword_ids"):
            tags["keywords"] = movie_details["keyword_ids"]
        
        # 4. 添加电影类型
        tags["genres"] = movie_details["genres"]
        
        # 合并用户画像
        combined_tags = self._recommender.merge_profile_with_tags(
            self._recommender.user_profile, tags
        )
        
        # 使用电影详情中的信息进行搜索
        movies = self._recommender.search_tmdb_movies(combined_tags)
        top_movies = self._recommender.rerank_movies_with_deepseek(
            movies, query, self._recommender.user_profile
        )
        recommendations = self._recommender.format_movie_results(top_movies)
        
        movie_info = (
            f"🎬 **{movie_details['title']}** ({movie_details['release_date'][:4]})\n"
            f"📌 类型: {', '.join(movie_details['genres'])}\n"
            f"🎥 导演: {', '.join([d['name'] for d in movie_details['directors']] or ['未知'])}\n"
            f"🌟 主演: {', '.join([a['name'] for a in movie_details['actors']] or ['未知'])}\n"
            f"💫 评分: ⭐{movie_details['vote_average']:.1f}\n"
            f"📝 简介: {movie_details['overview']}"
        )
        
        return f"{movie_info}\n\n🔍 基于此电影的推荐:\n{recommendations}"
    
    def handle_creator_query(self, query: str) -> str:
        tags = self._recommender.parse_user_intent(query)
        if "导演" in query:
            match = re.search(r"导演[：:]\s*([\u4e00-\u9fa5a-zA-Z\s·]+)", query)
            if match:
                tags["directors"] = [d.strip() for d in re.split(r'[,，]', match.group(1))]
        if "主演" in query or "演员" in query:
            match = re.search(r"(主演|演员)[：:]\s*([\u4e00-\u9fa5a-zA-Z\s·]+)", query)
            if match:
                tags["actors"] = [a.strip() for a in re.split(r'[,，]', match.group(2))]
        combined_tags = self._recommender.merge_profile_with_tags(
            self._recommender.user_profile, tags
        )
        movies = self._recommender.search_tmdb_movies(combined_tags)
        top_movies = self._recommender.rerank_movies_with_deepseek(
            movies, query, self._recommender.user_profile
        )
        return self._recommender.format_movie_results(top_movies)

class MovieDetailTool(BaseTool):
    """电影详情查询工具"""
    name: str = "movie_detail_tool"
    description: str = "当用户询问具体电影信息时使用此工具"
    args_schema: Optional[Type[BaseModel]] = DetailInput
    _recommender: MovieRecommender = PrivateAttr()

    def __init__(self, recommender: MovieRecommender, **kwargs):
        super().__init__(**kwargs)
        self._recommender = recommender
        
    def _run(self, movie_title: str) -> str:
        movie_details = self._recommender.get_movie_details(movie_title)
        if not movie_details:
            return f"未找到电影《{movie_title}》的相关信息"
        return (
            f"🎬 **{movie_details['title']}** ({movie_details['release_date'][:4]})\n"
            f"📌 类型: {', '.join(movie_details['genres'])}\n"
            f"🎥 导演: {', '.join([d['name'] for d in movie_details['directors']] or ['未知'])}\n"
            f"🌟 主演: {', '.join([a['name'] for a in movie_details['actors']] or ['未知'])}\n"
            f"💫 评分: ⭐{movie_details['vote_average']:.1f}\n"
            f"📝 简介: {movie_details['overview']}\n"
            f"🔗 类似电影: {', '.join(movie_details['similar_movies'][:3])}"
        )