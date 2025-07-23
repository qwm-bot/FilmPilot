
import json
import re
import requests
import logging
from datetime import datetime
from openai import OpenAI
import random
from Tool.user_interest_extract import UserProfileSystem

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MovieRecommender:
    """电影推荐系统核心功能"""
    
    # API密钥配置
    # QWEN_API_KEY = "sk-41ec31f7dbc74f4b81a63f892bd528e4"
    TMDB_API_KEY = "530ae9f18a5985f155a45682ad27311e"

    # 新增关键词优先级映射（1为最高优先级）
    KEYWORD_PRIORITY_MAP = {
        # 导演/演员优先级最高
        "directors": 1,
        "actors": 1,
        # 核心类型/情感次之
        "genres": 2,
        "emotion": 2,
        # 排除项和主题关键词优先级较低
        "exclude": 3,
        "keywords": 3,
        # 时间范围优先级最低
        "time_range": 4
    }

    # 类型名称到ID映射
    GENRE_MAP = {
        # 主要类型
        "动作": 28, "冒险": 12, "动画": 16, "喜剧": 35, "犯罪": 80,
        "剧情": 18, "家庭": 10751, "奇幻": 14, "恐怖": 27, "爱情": 10749,
        "科幻": 878, "惊悚": 53, "战争": 10752, "西方": 37,
        
        # 扩展类型
        "悬疑": 9648, "音乐": 10402, "歌舞": 10402, "历史": 36,
        "纪录片": 99, "传记": 99, "运动": 10770, "奇幻冒险": 14,
        "灾难": 10752, "武侠": 28, "黑色电影": 10752,
        
        # 细分类型（映射到主要类型）
        "恐怖喜剧": 27, "科幻恐怖": 878, "浪漫喜剧": 10749,
        "动作喜剧": 28, "犯罪惊悚": 80, "政治惊悚": 53,
        "奇幻爱情": 14, "科幻动作": 878, "青春成长": 18,
        
        # 中国特色类型
        "武侠": 28, "古装": 36, "宫廷": 36, "谍战": 53,
        "警匪": 80, "革命": 10752, "都市": 18
    }

    # 情感关键词映射
    EMOTION_MAP = {
        # 积极情感
        "浪漫": "romance", "温馨": "heartwarming", "治愈": "feel-good", 
        "轻松": "lighthearted", "搞笑": "funny", "欢乐": "joyful",
        "甜蜜": "sweet", "温暖": "warm", "励志": "inspirational",
        "感动": "touching", "愉悦": "uplifting", "梦幻": "dreamy",
        
        # 中性/复杂情感
        "烧脑": "mind-bending", "悬疑": "suspenseful", "惊险": "thrilling",
        "震撼": "mind-blowing", "史诗": "epic", "深沉": "profound",
        "艺术": "artistic", "深刻": "thought-provoking", "怀旧": "nostalgic",
        
        # 消极情感
        "悲伤": "sad", "恐怖": "horror", "惊悚": "thriller",
        "黑暗": "dark", "压抑": "oppressive", "暴力": "violent",
        "惊悚": "thrilling", "刺激": "intense", "悬疑": "mysterious",
        
        # 特定氛围
        "奇幻": "fantasy", "科幻": "sci-fi", "动作": "action-packed",
        "冒险": "adventure", "音乐": "musical", "歌舞": "musical",
        "家庭": "family", "成长": "coming-of-age", "历史": "historical",
        
        # 关系类型
        "爱情": "romantic", "友情": "friendship", "亲情": "family",
        "兄弟情": "bromance", "闺蜜情": "sisterhood"
    }

    KEYWORD_CATEGORY_MAP = {
        # 主题映射
        "人工智能": "artificial intelligence",
        "时间旅行": "time travel",
        "平行宇宙": "parallel universe",
        "反乌托邦": "dystopia",
        "末日": "apocalypse",
        "超级英雄": "superhero",
        "吸血鬼": "vampire",
        "僵尸": "zombie",
        "外星人": "alien",
        "机器人": "robot",
        "魔法": "magic",
        "神话": "mythology",
        
        # 情节类型
        "复仇": "revenge",
        "救赎": "redemption",
        "背叛": "betrayal",
        "阴谋": "conspiracy",
        "生存": "survival",
        "寻宝": "treasure hunt",
        "侦探": "detective",
        "卧底": "undercover",
        
        # 人物关系
        "父子": "father-son relationship",
        "母女": "mother-daughter relationship",
        "师生": "teacher-student relationship",
        "竞争对手": "rivalry",
        "三角恋": "love triangle",
        
        # 场景/氛围
        "太空": "space",
        "海洋": "ocean",
        "森林": "forest",
        "城市": "city",
        "乡村": "countryside",
        "校园": "school",
        "办公室": "office",
        "未来世界": "futuristic world",
        "历史时期": "historical period"
    }

    # 默认用户画像
    DEFAULT_USER_PROFILE = {
        "gender": "未知",
        "age_group": "未知",
        "fav_genres": []
    }

    def __init__(self, user_id,user_profile=None, qwen_api_key=None,mysql_url: str = "mysql+pymysql://root:123456@localhost:3306/movie_recommendation"):
        """初始化推荐系统"""
        user_profile = UserProfileSystem(user_id=user_id, mysql_url=mysql_url).get_full_profile()
        self.user_profile = user_profile or self.DEFAULT_USER_PROFILE.copy()
        self.openai_client = OpenAI(
            api_key= qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1" # Qwen OpenAI兼容API地址
        )
    
    def parse_user_intent(self, user_input):
        """解析用户意图（支持时间/导演/演员/情感/类型/主题筛选）"""
        try:
            prompt = f"""
    ## 用户需求
    {user_input}

    ## 任务
    请将用户需求解析为以下JSON格式：
    {{
    "emotion": ["情感关键词1", "情感关键词2"],  # 如: 浪漫, 烧脑, 温馨
    "genres": ["类型1", "类型2"],             # 如: 科幻, 爱情, 悬疑
    "keywords": ["主题关键词1", "主题关键词2"], # 如: 人工智能, 时间旅行
    "exclude": ["排除元素1", "排除元素2"],     # 如: 恐怖, 暴力
    "time_range": "时间范围",                 # 格式: 起始日期,结束日期 或 2010-2020
    "directors": ["导演名1", "导演名2"],
    "actors": ["演员名1", "演员名2"]
    }}

    ## 说明
    1. 情感关键词参考: {", ".join(self.EMOTION_MAP.keys())}
    2. 电影类型参考: {", ".join(self.GENRE_MAP.keys())}
    3. 主题关键词参考: {", ".join(self.KEYWORD_CATEGORY_MAP.keys())}
    4. 时间范围格式: 
    - "2010年至今" → "2010-01-01,{datetime.today().strftime('%Y-%m-%d')}"
    - "2000-2010年" → "2000-01-01,2010-12-31"
    - "90年代" → "1990-01-01,1999-12-31"
    5. 只输出纯JSON格式，不要添加任何解释
    """
            
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "作为电影需求解析专家，请精确提取用户需求"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content.strip()
            logging.info(f"原始解析输出: {raw_content}")
            
            # 清理输出
            clean_content = re.sub(r'```json|\```', '', raw_content).strip()
            clean_content = clean_content.replace("'", '"')
            
            try:
                tags = json.loads(clean_content)
            except json.JSONDecodeError:
                logging.warning("JSON解析失败，使用回退策略")
                tags = {"emotion": [], "genres": [], "keywords": [], "exclude": []}
            
            # ==== 手动提取补充信息 ====
            # 1. 时间范围检测
            if "time_range" not in tags or not tags["time_range"]:
                if "年" in user_input:
                    # 格式1: XXXX年至今
                    if "至今" in user_input:
                        match = re.search(r"(\d{4})年至今", user_input)
                        if match:
                            tags["time_range"] = f"{match.group(1)}-01-01,{datetime.today().strftime('%Y-%m-%d')}"
                    # 格式2: XXXX年-YYYY年
                    elif re.search(r"\d{4}年[\-到至]\d{4}年", user_input):
                        match = re.search(r"(\d{4})年[\-到至](\d{4})年", user_input)
                        if match:
                            start_year, end_year = match.groups()
                            tags["time_range"] = f"{start_year}-01-01,{end_year}-12-31"
                    # 格式3: XXXX年代
                    elif re.search(r"\d{4}年代", user_input):
                        match = re.search(r"(\d{3})0年代", user_input)
                        if match:
                            decade = match.group(1)
                            tags["time_range"] = f"{decade}0-01-01,{decade}9-12-31"
            
            # 2. 导演检测
            if ("directors" not in tags or not tags["directors"]) and re.search(r"导演[：:]\s*([\u4e00-\u9fa5a-zA-Z\s·]+)", user_input):
                director_match = re.search(r"导演[：:]\s*([\u4e00-\u9fa5a-zA-Z\s·]+)", user_input)
                directors = [d.strip() for d in re.split(r'[,，]', director_match.group(1))]
                # 翻译中文名导演
                translated_directors = []
                for name in directors:
                    if any('\u4e00' <= char <= '\u9fff' for char in name):
                        translated = self.translate_text(name, "en")
                        translated_directors.append(translated)
                        logging.info(f"导演翻译: {name} → {translated}")
                    else:
                        translated_directors.append(name)
                tags["directors"] = translated_directors
            
            # 3. 演员检测
            if ("actors" not in tags or not tags["actors"]) and re.search(r"(主演|演员)[：:]\s*([\u4e00-\u9fa5a-zA-Z\s·]+)", user_input):
                actor_match = re.search(r"(主演|演员)[：:]\s*([\u4e00-\u9fa5a-zA-Z\s·]+)", user_input)
                actors = [a.strip() for a in re.split(r'[,，]', actor_match.group(2))]
                # 翻译中文名演员
                translated_actors = []
                for name in actors:
                    if any('\u4e00' <= char <= '\u9fff' for char in name):
                        translated = self.translate_text(name, "en")
                        translated_actors.append(translated)
                        logging.info(f"演员翻译: {name} → {translated}")
                    else:
                        translated_actors.append(name)
                tags["actors"] = translated_actors
            
            # ==== 关键词提取增强 ====
            # 1. 情感关键词提取
            emotion_keywords = []
            for emotion in self.EMOTION_MAP:
                if emotion in user_input and emotion not in emotion_keywords:
                    emotion_keywords.append(emotion)
            
            # 合并模型输出和手动提取的情感关键词
            if emotion_keywords:
                tags["emotion"] = list(set(tags.get("emotion", []) + emotion_keywords))
            
            # 2. 电影类型提取
            genre_keywords = []
            for genre in self.GENRE_MAP:
                if genre in user_input and genre not in genre_keywords:
                    genre_keywords.append(genre)
            
            # 合并模型输出和手动提取的类型关键词
            if genre_keywords:
                tags["genres"] = list(set(tags.get("genres", []) + genre_keywords))
            
            # 3. 主题关键词提取
            keyword_keywords = []
            for keyword in self.KEYWORD_CATEGORY_MAP:
                if keyword in user_input and keyword not in keyword_keywords:
                    keyword_keywords.append(keyword)
            
            # 合并模型输出和手动提取的主题关键词
            if keyword_keywords:
                tags["keywords"] = list(set(tags.get("keywords", []) + keyword_keywords))
            
            # 4. 排除元素检测
            exclude_keywords = []
            for exclude in ["恐怖", "暴力", "血腥", "惊悚", "悲伤", "压抑"]:
                if exclude in user_input and exclude not in exclude_keywords:
                    exclude_keywords.append(exclude)
            
            if exclude_keywords:
                tags["exclude"] = list(set(tags.get("exclude", []) + exclude_keywords))
            
            tags = self.sort_keywords_by_priority(tags)
            logging.info(f"排序后的推荐标签: {tags}")
            
            return tags
                    
        except Exception as e:
            logging.error(f"需求解析失败: {str(e)}")
            # 最简回退策略
            return {
                "emotion": ["浪漫", "温馨"] if "浪漫" in user_input or "温馨" in user_input else [],
                "genres": ["爱情", "喜剧"] if "爱情" in user_input or "喜剧" in user_input else ["剧情"],
                "keywords": [],
                "exclude": ["恐怖", "暴力"]
            }

    def sort_keywords_by_priority(self, tags):
        """按优先级对关键词进行排序"""
        sorted_tags = {}
        
        # 按优先级从高到低排序
        for key in sorted(tags.keys(), key=lambda k: self.KEYWORD_PRIORITY_MAP.get(k, 5)):
            if isinstance(tags[key], list):
                # 对列表类关键词进行重要性排序
                sorted_tags[key] = self.sort_keyword_list(key, tags[key])
            else:
                sorted_tags[key] = tags[key]
        
        return sorted_tags
    
    def sort_keyword_list(self, key_type, keyword_list):
        """根据关键词类型进行具体排序"""
        # 导演/演员按出现顺序保持原样
        if key_type in ["directors", "actors"]:
            return keyword_list
        
        # 情感关键词不再排序 - 保持原样
        if key_type == "emotion":
            return keyword_list  # 不再对情感关键词排序
        
        # 类型关键词排序（主要类型>扩展类型>细分类型）
        if key_type == "genres":
            genre_order = ["动作", "冒险", "动画", "喜剧", "犯罪", "剧情", "家庭", 
                         "奇幻", "恐怖", "爱情", "科幻", "惊悚", "战争", "西方",
                         "悬疑", "音乐", "历史", "纪录片", "传记", "运动",
                         "恐怖喜剧", "科幻恐怖", "浪漫喜剧", "动作喜剧", "犯罪惊悚"]
            return sorted(keyword_list, key=lambda x: genre_order.index(x) if x in genre_order else len(genre_order))
        
        # 其他关键词保持原样
        return keyword_list

    def map_to_tmdb_params(self, tags, attempt=3):
        """带智能回退的TMDB参数映射（根据优先级舍弃关键词）"""
        # 创建可修改的标签副本
        current_tags = tags.copy()
        
        
        # 回退策略：根据尝试次数舍弃低优先级关键词
        if attempt == 2:  # 第一次回退
            # 移除优先级最低的2个元素（时间范围+1个低优先级关键词）
            self.remove_low_priority_items(current_tags, count=2)
            logging.info(f"回退策略1: 移除最低优先级元素, 当前标签: {current_tags}")
        
        elif attempt == 3:  # 第二次回退
            # 移除优先级最低的3个元素
            self.remove_low_priority_items(current_tags, count=3)
            logging.info(f"回退策略2: 移除低优先级元素, 当前标签: {current_tags}")
            
            # 确保至少保留一个核心类型
            if not current_tags.get("genres"):
                current_tags["genres"] = ["剧情"]  # 默认核心类型
        
        # 使用更新后的标签生成参数
        return self.generate_tmdb_params_from_tags(current_tags)

    def remove_low_priority_items(self, tags, count=1):
        """移除指定数量的最低优先级元素"""
        # 获取所有标签项并按优先级排序
        all_items = []
        for key, value in tags.items():
            if isinstance(value, list) and value:
                priority = self.KEYWORD_PRIORITY_MAP.get(key, 5)
                all_items.append((key, value, priority))
            elif value:  # 处理非列表类型的值（如time_range）
                priority = self.KEYWORD_PRIORITY_MAP.get(key, 5)
                all_items.append((key, value, priority))
        
        # 按优先级从低到高排序（优先级数值越大，优先级越低）
        sorted_items = sorted(all_items, key=lambda x: (-x[2], x[0]))
        
        # 移除最低优先级的count个元素
        removed_count = 0
        for key, value, _ in sorted_items:
            if removed_count >= count:
                break
                
            # 移除整个键值对
            if key in tags:
                del tags[key]
                removed_count += 1
    
    def generate_tmdb_params_from_tags(self, tags):
        """从标签生成TMDB参数（核心参数映射）"""
        params = {
            "api_key": self.TMDB_API_KEY,
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "language": "zh-CN"  # 添加中文支持
        }
        
        # ===== 处理影片类型 =====
        if "genres" in tags and isinstance(tags["genres"], list):
            valid_genres = [str(self.GENRE_MAP[g]) for g in tags["genres"] if g in self.GENRE_MAP]
            if valid_genres:
                params["with_genres"] = "|".join(valid_genres)
                logging.info(f"添加类型筛选: {tags['genres']} → IDs: {valid_genres}")
        
        # ===== 处理情感关键词 =====
        if "emotion" in tags and isinstance(tags["emotion"], list):
            valid_emotions = [self.EMOTION_MAP[e] for e in tags["emotion"] if e in self.EMOTION_MAP]
            if valid_emotions:
                # 构建关键词查询字符串
                keyword_str = ",".join(valid_emotions)
                # 添加到参数中
                params["with_keywords"] = keyword_str
                logging.info(f"添加情感关键词筛选: {tags['emotion']} → {keyword_str}")
        
        # ===== 处理主题关键词 =====
        if "keywords" in tags and isinstance(tags["keywords"], list):
            valid_keywords = [self.KEYWORD_CATEGORY_MAP[k] for k in tags["keywords"] if k in self.KEYWORD_CATEGORY_MAP]
            if valid_keywords:
                # 添加到参数中
                params["with_keywords"] = params.get("with_keywords", "") + "," + ",".join(valid_keywords)
                logging.info(f"添加主题关键词筛选: {tags['keywords']} → {valid_keywords}")
        
        # ===== 处理排除要求 =====
        if "exclude" in tags and isinstance(tags["exclude"], list):
            # 排除恐怖元素
            if "恐怖" in tags["exclude"]:
                params["without_keywords"] = "horror,terror"
                logging.info("排除恐怖元素")
            
            # 排除暴力元素
            if "暴力" in tags["exclude"]:
                params["certification_country"] = "US"
                params["certification.lte"] = "PG-13"
                logging.info("排除暴力元素（限制为PG-13级）")
        
        # ===== 时间范围映射 =====
        if "time_range" in tags:
            try:
                start_date, end_date = tags["time_range"].split(",")
                params["primary_release_date.gte"] = start_date
                params["primary_release_date.lte"] = end_date
                logging.info(f"添加时间筛选: {start_date} 至 {end_date}")
            except:
                logging.warning(f"无效的时间范围格式: {tags.get('time_range', '')}")
        
        # ===== 导演筛选映射 =====
        if "directors" in tags:
            director_ids = []
            for director_name in tags["directors"]:
                try:
                    search_url = f"https://api.themoviedb.org/3/search/person?api_key={self.TMDB_API_KEY}&query={director_name}&language=zh-CN"
                    search_res = requests.get(search_url, timeout=8)
                    if search_res.status_code == 200 and search_res.json()["results"]:
                        director_id = search_res.json()["results"][0]["id"]
                        director_ids.append(str(director_id))
                        logging.debug(f"找到导演: {director_name} → ID: {director_id}")
                    else:
                        logging.warning(f"未找到导演: {director_name}")
                except Exception as e:
                    logging.error(f"查询导演失败: {director_name} - {str(e)}")
            
            if director_ids:
                params["with_crew"] = ",".join(director_ids)
                logging.info(f"添加导演筛选: {tags['directors']} → IDs: {director_ids}")
            else:
                logging.warning("无有效导演ID")
        
        # ===== 演员筛选映射 =====
        if "actors" in tags:
            actor_ids = []
            for actor_name in tags["actors"]:
                try:
                    # 检查是否已经是ID
                    if isinstance(actor_name, int):
                        actor_ids.append(str(actor_name))
                        logging.debug(f"使用演员ID: {actor_name}")
                        continue
                    
                    search_url = f"https://api.themoviedb.org/3/search/person?api_key={self.TMDB_API_KEY}&query={actor_name}&language=zh-CN"
                    search_res = requests.get(search_url, timeout=8)
                    if search_res.status_code == 200 and search_res.json()["results"]:
                        actor_id = search_res.json()["results"][0]["id"]
                        actor_ids.append(str(actor_id))
                        logging.debug(f"找到演员: {actor_name} → ID: {actor_id}")
                    else:
                        logging.warning(f"未找到演员: {actor_name}")
                except Exception as e:
                    logging.error(f"查询演员失败: {actor_name} - {str(e)}")
            
            if actor_ids:
                params["with_cast"] = ",".join(actor_ids)
                logging.info(f"添加演员筛选: {tags['actors']} → IDs: {actor_ids}")
            else:
                logging.warning("无有效演员ID")
        
        # ===== 确保基本筛选条件 =====
        # 如果没有设置任何筛选条件，添加默认条件避免过多结果
        if not any(key in params for key in ["with_genres", "with_keywords", "with_crew", "with_cast"]):
            logging.info("无有效筛选条件，添加默认类型筛选")
            params["with_genres"] = "18"  # 默认剧情片
        
        # 添加最小投票数限制，避免冷门电影
        params["vote_count.gte"] = 100
        
        logging.info(f"最终TMDB参数: {params}")
        return params

    def search_tmdb_movies(self, params, max_attempts=3):
        """带多级回退的TMDB搜索"""
        movies = []
        
        for attempt in range(1, max_attempts + 1):
            try:
                # 为当前尝试生成参数
                current_params = self.map_to_tmdb_params({}, attempt) if not params else self.map_to_tmdb_params(params, attempt)
                logging.info(f"搜索尝试 #{attempt} 参数: {current_params}")
                
                response = requests.get(
                    "https://api.themoviedb.org/3/discover/movie",
                    params=current_params,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                total_results = data.get("total_results", 0)
                logging.info(f"找到 {total_results} 条结果 (尝试 #{attempt})")
                
                if results:
                    # 确保有足够的电影用于精排
                    min_results = max(20, min(30, total_results))
                    return results[:min_results]
                
            except requests.exceptions.RequestException as e:
                logging.error(f"TMDB API错误 (尝试 #{attempt}): {str(e)}")
        
        # 所有尝试都失败时返回热门外语片
        logging.warning("所有尝试失败，返回热门电影作为后备")
        backup_params = {
            "api_key": self.TMDB_API_KEY,
            "sort_by": "popularity.desc",
            "with_original_language": "en",
            "vote_count.gte": 1000,
            "primary_release_date.gte": "2015-01-01"
        }
        backup_response = requests.get(
            "https://api.themoviedb.org/3/discover/movie",
            params=backup_params
        ).json()
        return backup_response.get("results", [])[:20]

    def rerank_movies_with_deepseek(self, movies, user_input, user_profile):
        """使用DeepSeek对召回结果进行精排（为每部电影生成个性化理由）"""
        if not movies:
            return movies  # 无结果时直接返回
        
        try:
            # 准备电影摘要信息
            movie_summaries = []
            for i, movie in enumerate(movies, 1):
                title = movie.get("title", "未知电影")
                year = movie.get("release_date", "年份未知")[:4] if movie.get("release_date") else "年份未知"
                genres = ", ".join([name for genre_id in movie.get("genre_ids", []) 
                                  for name, id_val in self.GENRE_MAP.items() if id_val == genre_id][:2])
                overview = movie.get("overview", "暂无简介")
                movie_summaries.append(f"{i}. {title} ({year}) - {genres} | {overview[:70]}{'...' if len(overview) > 70 else ''}")
            
            # 准备用户画像信息
            profile_info = []
            if user_profile["gender"] != "未知":
                profile_info.append(f"性别: {user_profile['gender']}")
            if user_profile["age_group"] != "未知":
                profile_info.append(f"年龄段: {user_profile['age_group']}")
            if user_profile["fav_genres"]:
                profile_info.append(f"喜欢的类型: {', '.join(user_profile['fav_genres'])}")
            
            profile_str = " | ".join(profile_info) if profile_info else "无额外信息"
            
            # 构建精排提示词 - 要求为每部电影生成个性化理由
            prompt = f"""
    ## 用户需求
    {user_input}

    ## 用户画像
    {profile_str}

    ## 召回电影列表（共{len(movies)}部）
    以下是需要精排的电影（已编号）：
    """
            prompt += "\n".join(movie_summaries)

            prompt += f"""

    ## 任务
    请基于用户需求和用户画像，完成以下两项工作：
    1. 选出最符合用户需求的Top5电影
    2. 为每部入选电影撰写独特的个性化推荐理由（10-15字）

    推荐理由应该：
    - 突出电影与用户需求/画像的匹配点
    - 体现电影的核心吸引力
    - 使用口语化表达

    ## 输出格式（纯JSON）
    {{
      "overall_reason": "整体选择思路简述（30字内）",
      "top5": [排名1的电影编号, 排名2的电影编号, ...],
      "reasons": {{
        "1": "排名第1的专属推荐理由",
        "2": "排名第2的专属推荐理由",
        // ...其他电影...
      }}
    }}
    请确保输出完整JSON结构，包含所有电影编号的推荐理由。
    """
            
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "作为电影推荐专家，你需要为每部电影生成独特的个性化推荐理由"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,  # 增加token限额
                response_format={"type": "json_object"}
            )
            
            ranking_data = json.loads(response.choices[0].message.content)
            logging.info(f"精排结果: {ranking_data}")
            
            # 处理精排结果
            top_ids = [int(i)-1 for i in ranking_data["top5"][:5]]
            ranked_movies = []
            
            # 为每部电影添加个性化理由
            for idx, movie_id in enumerate(top_ids):
                if movie_id < len(movies):
                    movie = movies[movie_id]
                    # 从reasons对象中获取该电影编号的专属理由
                    reason_key = str(len(ranked_movies)+1)
                    reason_text = ranking_data.get("reasons", {}).get(reason_key, "深度匹配您的观影偏好")
                    movie["recommendation_reason"] = reason_text
                    movie["ranking_position"] = idx+1
                    ranked_movies.append(movie)
            
            # 添加整体推荐思路
            if ranked_movies:
                ranked_movies[0]["overall_reason"] = ranking_data.get("overall_reason", "")
            
            return ranked_movies
        
        except Exception as e:
            logging.error(f"精排过程失败: {str(e)}")
            # 失败时返回原列表的前5部
            return movies[:5]

    def merge_profile_with_tags(self, profile, tags):
        """
        将用户画像与动态需求标签合并
        
        参数:
        profile: 用户画像字典
        tags: 从用户查询中解析出的动态标签
        
        返回:
        合并后的完整标签字典
        """
        # 初始化标签字典（确保所有键都存在）
        merged_tags = {
            "emotion": [],
            "genres": [],
            "keywords": [],
            "exclude": [],
            "time_range": "",
            "directors": [],
            "actors": []
        }
        
        # 合并基本标签（保留查询中的原始标签）
        for key in merged_tags:
            if key in tags:
                merged_tags[key] = tags[key] if isinstance(tags[key], list) else [tags[key]]
        
        # ===== 合并用户喜欢的类型 =====
        if "fav_genres" in profile and profile["fav_genres"]:
            # 去重添加，最多保留3种
            for genre in profile["fav_genres"][:3]:
                if genre not in merged_tags["genres"]:
                    merged_tags["genres"].append(genre)
        
        # ===== 基于年龄组的处理 =====
        age_group = profile.get("age_group", "未知")
        gender = profile.get("gender", "未知")
        
        if age_group == "儿童":
            # 儿童推荐偏好
            merged_tags["genres"].extend(["动画", "家庭"])
            merged_tags["keywords"].extend(["成长", "友谊", "教育"])
            merged_tags["emotion"].extend(["欢乐", "轻松", "温馨"])
            merged_tags["exclude"].extend(["恐怖", "暴力", "惊悚"])
            
        elif age_group in ["青少年", "青年"]:
            # 青少年/青年推荐偏好
            merged_tags["keywords"].extend(["成长", "校园", "爱情", "自我发现"])
            if "科幻" not in merged_tags["genres"]:
                merged_tags["genres"].append("科幻")
            
        elif age_group in ["25-35", "35-45"]:
            # 成年人推荐偏好
            merged_tags["keywords"].extend(["事业", "家庭", "责任", "人生选择"])
            if "剧情" not in merged_tags["genres"]:
                merged_tags["genres"].append("剧情")
            
        elif age_group in ["45-60", "60+"]:
            # 中老年推荐偏好
            merged_tags["keywords"].extend(["回忆", "人生", "家庭", "历史"])
            merged_tags["emotion"].extend(["深刻", "怀旧"])
            if "历史" not in merged_tags["genres"]:
                merged_tags["genres"].append("历史")
        
        # ===== 基于性别的处理 =====
        if gender == "女":
            # 女性用户偏好
            if "爱情" not in merged_tags["genres"]:
                merged_tags["genres"].append("爱情")
            merged_tags["keywords"].extend(["情感", "关系", "成长"])
            merged_tags["emotion"].extend(["温馨", "治愈"])
            
        elif gender == "男":
            # 男性用户偏好
            if "动作" not in merged_tags["genres"]:
                merged_tags["genres"].append("动作")
            merged_tags["keywords"].extend(["冒险", "英雄", "技术"])
            merged_tags["emotion"].extend(["惊险", "震撼"])
        
        # ===== 智能冲突解决 =====
        # 1. 解决情感冲突（如同时要求"悲伤"和"欢乐"）
        if "悲伤" in merged_tags["emotion"] and "欢乐" in merged_tags["emotion"]:
            # 优先保留更强烈的情感
            if "悲伤" in profile.get("fav_emotions", []):
                merged_tags["emotion"].remove("欢乐")
            else:
                merged_tags["emotion"].remove("悲伤")
        
        # 2. 解决类型冲突（如同时要求"恐怖"和"家庭"）
        if "恐怖" in merged_tags["genres"] and "家庭" in merged_tags["genres"]:
            # 根据年龄组决定保留哪个
            if age_group == "儿童":
                merged_tags["genres"].remove("恐怖")
                merged_tags["exclude"].append("恐怖")
            else:
                # 为成人用户保留两者但添加提示
                merged_tags["keywords"].append("家庭恐怖")  # 特殊类型
        
        # 3. 排除项处理 - 确保排除项与内容不冲突
        for exclude_item in merged_tags["exclude"]:
            if exclude_item in merged_tags["genres"]:
                merged_tags["genres"].remove(exclude_item)
            if exclude_item in merged_tags["keywords"]:
                merged_tags["keywords"].remove(exclude_item)
            if exclude_item in merged_tags["emotion"]:
                merged_tags["emotion"].remove(exclude_item)
        
        # ===== 限制标签数量 =====
        # 类型最多5种
        merged_tags["genres"] = list(set(merged_tags["genres"]))[:5]
        # 情感最多3种
        merged_tags["emotion"] = list(set(merged_tags["emotion"]))[:3]
        # 关键词最多5个
        merged_tags["keywords"] = list(set(merged_tags["keywords"]))[:5]
        # 排除项最多3个
        merged_tags["exclude"] = list(set(merged_tags["exclude"]))[:3]
        
        # 日志记录合并结果
        logging.info(f"合并后的推荐标签: {merged_tags}")
        
        return merged_tags

    def get_movie_details(self, movie_title):
        """通过TMDB API获取电影详细信息"""
        try:
            # 先搜索电影ID
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={self.TMDB_API_KEY}&query={movie_title}&language=zh-CN"
            search_res = requests.get(search_url, timeout=10)
            if search_res.status_code != 200 or not search_res.json().get("results"):
                return None
            
            # 取第一个匹配结果
            movie_id = search_res.json()["results"][0]["id"]
            
            # 获取详细信息
            detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={self.TMDB_API_KEY}&language=zh-CN&append_to_response=credits,recommendations"
            detail_res = requests.get(detail_url, timeout=10)
            if detail_res.status_code != 200:
                return None
            
            movie_data = detail_res.json()
            
            # 提取导演（含ID）
            directors = []
            for crew in movie_data.get("credits", {}).get("crew", []):
                if crew.get("job") == "Director":
                    directors.append({
                        "id": crew["id"],
                        "name": crew["name"]
                    })
                    if len(directors) >= 2:  # 最多两位导演
                        break
            
            # 提取主演（含ID）
            actors = []
            for cast in movie_data.get("credits", {}).get("cast", []):
                actors.append({
                    "id": cast["id"],
                    "name": cast["name"]
                })
                if len(actors) >= 3:  # 最多三位主演
                    break
            
            # 提取关键词ID
            keyword_ids = [kw["id"] for kw in movie_data.get("keywords", {}).get("keywords", [])]
            
            # 提取类似电影
            similar_movies = [movie["title"] for movie in movie_data.get("recommendations", {}).get("results", [])[:5]]
            
            return {
                "title": movie_data.get("title", "未知电影"),
                "original_title": movie_data.get("original_title", ""),
                "genres": [genre["name"] for genre in movie_data.get("genres", [])][:3],
                "directors": directors,
                "actors": actors,
                "keyword_ids": keyword_ids,  # 新增关键词ID
                "overview": movie_data.get("overview", "暂无简介"),
                "release_date": movie_data.get("release_date", ""),
                "vote_average": movie_data.get("vote_average", 0),
                "similar_movies": similar_movies
            }
        except Exception as e:
            logging.error(f"获取电影详情失败: {str(e)}")
            return None

    def generate_association_keywords(self, movie_details, user_profile):
        """生成联想关键词（DeepSeek）"""
        try:
            # 构建提示词
            prompt = f"""
    ## 用户画像
    性别: {user_profile['gender']} | 年龄段: {user_profile['age_group']} | 喜好类型: {', '.join(user_profile['fav_genres'] or ['无'])}"

    ## 目标电影详情
    标题: {movie_details['title']}
    类型: {', '.join(movie_details['genres'])}
    导演: {', '.join(movie_details['directors'] or ['未知'])}
    主演: {', '.join(movie_details['actors'] or ['未知'])}
    简介: {movie_details['overview'][:150]}...

    ## 任务
    基于用户画像和电影特点，生成3-5个推荐联想关键词（如导演名、演员名、主题关键词等）。
    关键词可以是：
    1. 同导演作品（示例："克里斯托弗·诺兰"）
    2. 同主演作品（示例："莱昂纳多·迪卡普里奥"）
    3. 同类型作品（示例："科幻悬疑"）
    4. 相似主题（示例："时间旅行"）
    5. 类似电影（示例："盗梦空间"）

    输出格式（纯JSON）：
    {{ "keywords": ["关键词1", "关键词2", ...] }}
    """
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "作为电影推荐专家，你需要生成精准的联想关键词"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)["keywords"]
        except Exception as e:
            logging.error(f"生成联想关键词失败: {str(e)}")
            return movie_details['genres']  # 回退到电影类型

    def format_movie_results(self, movies):
        """格式化搜索结果（带个性化推荐理由）"""
        if not movies:
            return "暂时没有找到完全匹配的电影，但为您推荐以下热门影片：\n* 请尝试更具体的描述（如'浪漫喜剧'或'温馨剧情片'）"
        
        formatted = "为您精选的Top5推荐："
        
        # 添加整体推荐思路（只在第一名显示）
        if movies and "overall_reason" in movies[0]:
            formatted += f"\n\n💡💡 推荐思路: {movies[0]['overall_reason']}\n"
        
        for i, movie in enumerate(movies, 1):
            title = movie.get("title", "未知电影")
            year = movie.get("release_date", "年份未知")[:4] if movie.get("release_date") else "年份未知"
            rating = movie.get("vote_average", 0)
            overview = movie.get("overview", "暂无简介")
            reason = movie.get("recommendation_reason", "深度匹配您的观影偏好")
            
            # 处理类型
            genre_names = []
            if "genre_ids" in movie:
                for genre_id in movie["genre_ids"]:
                    for name, id_val in self.GENRE_MAP.items():
                        if id_val == genre_id:
                            genre_names.append(name)
                            break
                    # 最多显示2个类型
                    if len(genre_names) >= 2:
                        break
            
            formatted += f"\n\n🏆🏆 {i}. **{title}** ({year}) ⭐⭐{rating:.1f}"
            if genre_names:
                formatted += f" | {', '.join(genre_names)}"
            formatted += f"\n🎯🎯 推荐理由: {reason}"
            formatted += f"\n📝📝 简介: {overview[:80]}{'...' if len(overview) > 80 else ''}"
        
        return formatted
    
    def get_daily_recommendations(self, count=5):
        """获取每日推荐电影（随机热映电影）
        
        参数:
            count: 推荐电影数量(3-5部)
        
        返回:
            list: 包含电影详情的字典列表
        """
        try:
            # 获取当前热映电影
            url = f"https://api.themoviedb.org/3/movie/now_playing"
            params = {
                "api_key": self.TMDB_API_KEY,
                "language": "zh-CN",
                "region": "CN",  # 中国地区
                "page": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            movies = data.get("results", [])
            
            if not movies:
                logging.warning("未找到热映电影，使用热门电影替代")
                backup_params = {
                    "api_key": self.TMDB_API_KEY,
                    "sort_by": "popularity.desc",
                    "language": "zh-CN",
                    "vote_count.gte": 1000,
                    "primary_release_date.gte": "2023-01-01"
                }
                backup_response = requests.get(
                    "https://api.themoviedb.org/3/discover/movie",
                    params=backup_params
                ).json()
                movies = backup_response.get("results", [])
            
            # 随机选择指定数量的电影
            count = min(max(3, count), 5)  # 确保在3-5之间
            selected_movies = random.sample(movies, min(count, len(movies)))
            
            # 获取每部电影的详细信息
            detailed_movies = []
            for movie in selected_movies:
                movie_id = movie["id"]
                detailed_movie = self.get_movie_details_by_id(movie_id)
                if detailed_movie:
                    detailed_movies.append(detailed_movie)
            
            return detailed_movies
        
        except Exception as e:
            logging.error(f"每日推荐失败: {str(e)}")
            return []

    def get_movie_details_by_id(self, movie_id):
        """根据电影ID获取完整详情"""
        try:
            # 获取基本信息
            detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
            params = {
                "api_key": self.TMDB_API_KEY,
                "language": "zh-CN",
                "append_to_response": "credits,keywords,images"
            }
            
            response = requests.get(detail_url, params=params, timeout=10)
            response.raise_for_status()
            movie_data = response.json()
            
            # 提取导演信息
            directors = []
            for crew in movie_data.get("credits", {}).get("crew", []):
                if crew.get("job") == "Director":
                    directors.append(crew["name"])
                    if len(directors) >= 2:  # 最多两位导演
                        break
            
            # 提取主演信息
            actors = []
            for cast in movie_data.get("credits", {}).get("cast", []):
                actors.append(cast["name"])
                if len(actors) >= 3:  # 最多三位主演
                    break
            
            # 获取经典台词
            tagline = movie_data.get("tagline", "")
            if not tagline:
                # 使用大模型生成台词
                tagline = self.generate_movie_tagline(movie_data["title"], movie_data["overview"])
            
            # 获取海报路径
            poster_path = movie_data.get("poster_path", "")
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
            
            # 获取背景图
            backdrop_path = movie_data.get("backdrop_path", "")
            backdrop_url = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else ""
            
            return {
                "id": movie_id,
                "title": movie_data.get("title", "未知电影"),
                "original_title": movie_data.get("original_title", ""),
                "overview": movie_data.get("overview", "暂无简介"),
                "tagline": tagline,  # 经典台词
                "release_date": movie_data.get("release_date", "未知"),
                "vote_average": movie_data.get("vote_average", 0),
                "runtime": movie_data.get("runtime", 0),  # 片长(分钟)
                "directors": directors,
                "actors": actors,
                "poster_url": poster_url,  # 海报URL
                "backdrop_url": backdrop_url,  # 背景图URL
                "genres": [genre["name"] for genre in movie_data.get("genres", [])]
            }
        
        except Exception as e:
            logging.error(f"获取电影详情失败(ID:{movie_id}): {str(e)}")
            return None

    def generate_movie_tagline(self, title, overview):
        """使用大模型生成电影经典台词"""
        try:
            prompt = f"电影《{title}》的简介是：{overview[:100]}... 请为这部电影生成一句10-15字的中文经典台词（类似电影海报上的标语），直接输出台词内容不要添加其他文字"
            
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "你是一个电影宣传语专家，请创作简短有力的电影标语"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=30
            )
            
            tagline = response.choices[0].message.content.strip()
            # 清理多余引号
            tagline = re.sub(r'^["\']|["\']$', '', tagline)
            return tagline
        
        except Exception as e:
            logging.error(f"生成电影台词失败: {str(e)}")
            return "一部值得铭记的佳作"  # 默认台词
        
    