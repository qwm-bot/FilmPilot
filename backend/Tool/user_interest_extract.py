import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, List
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from openai import OpenAI
from pydantic import BaseModel
import copy
from pprint import pprint
# 新增SQLAlchemy相关
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# 用户画像表模型
class UserProfileDB(Base):
    __tablename__ = 'user_profiles'
    user_id = Column(String(64), primary_key=True)
    profile_json = Column(Text)
    last_updated = Column(DateTime)
    password = Column(String(128), default="")  # 新增密码字段

class UserProfileSystem:
    """
    用户画像系统
    """

    def __init__(self, user_id: str = "default", mysql_url: str = "mysql+pymysql://root:123456@localhost:3306/movie_recommendation"):
        self.user_id = user_id
        self.mysql_url = mysql_url
        # 初始化MySQL连接
        self.engine = create_engine(mysql_url, echo=False, pool_recycle=3600, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        # 打印数据库和表信息
        db_name = self.engine.url.database
        print(f"[UserProfileSystem] 当前用户画像将保存到数据库: {db_name}，表: user_profiles")

        # 初始化记忆系统
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )

        # 初始化客户端
        self.client = OpenAI(
            api_key="sk-ca8af0975c314d67854bc95adf258d7c",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # 强化后的提取模板
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """
你是一个用户画像信息提取助手。请根据以下严格规则，从用户对话中提取画像信息：

1. 用户明确表达“喜欢、想看”的内容，才可加入到正面字段。
2. 用户只有在明确表达“不要、不喜欢、不想看”的内容时，才可加入到 negative_* 字段，并从正面字段中移除（如果有）。
   - 不要根据上下文做任何推测或泛化。
   - 举例：如果用户说“不要开心麻花的电影”，你只能标记“开心麻花”或其导演，而不能将相关演员如“沈腾”加入 negative。
3. 最新表达优先于历史记录，但只以明确表达为准。
4. 输出格式为 JSON，包含以下字段（缺失内容请填空数组或空字符串）：
   - watching_time（今天/明天/周末/下周）
   - gender（男/女）
   - age_group（18岁以下/18-25/26-35/36-45/45岁以上）
   - group_type（单人/情侣/家庭/亲子/朋友）
   - movie_genre（如["喜剧","科幻"]）
   - favorite_actors（数组）
   - favorite_directors（数组）
   - location（具体到市与区，如"北京市朝阳区"）
   - emotion（happy/sad/neutral/angry/excited）
   - negative_genres（不喜欢的类型）
   - negative_actors（不喜欢的演员）
   - negative_directors（不喜欢的导演）
"""),

            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "用户选择标签：{selected_tags}\n最新输入：{user_input}")
        ])

        # 构建处理链
        self.chain = (
            RunnablePassthrough.assign(
                chat_history=lambda x: self.memory.load_memory_variables(x)["chat_history"],
                selected_tags=lambda x: json.dumps(x.get("selected_tags", {}), ensure_ascii=False)
            )
            | self.extraction_prompt
            | self._call_llm
            | StrOutputParser()
        )

        # 初始化基础画像
        self.base_profile = self._init_base_profile()
        self._load_profile()

    def _init_base_profile(self) -> Dict[str, Any]:
        """初始化干净的基础画像模板"""
        return {
            "watching_time": "",
            "gender": "",
            "age_group": "",
            "group_type": "",
            "fav_genres": [],
            "favorite_actors": [],
            "favorite_directors": [],
            "location": "",
            "emotion": "",
            "negative_genres": [],
            "negative_actors": [],
            "negative_directors": [],
            "last_updated": datetime.now().isoformat()
            #"version": "1.0"  # 新增版本控制
        }



    def _load_profile(self):
        """从MySQL加载用户画像"""
        session = self.Session()
        try:
            db_name = self.engine.url.database
            print(f"[UserProfileSystem] 正在从数据库: {db_name}，表: user_profiles 加载用户画像...")
            record = session.query(UserProfileDB).filter_by(user_id=self.user_id).first()
            if record and record.profile_json:
                saved_data = json.loads(record.profile_json)
                if isinstance(saved_data, dict):
                    self.base_profile.update(saved_data)
        except Exception as e:
            print(f"加载用户画像失败: {str(e)}")
            self.base_profile = self._init_base_profile()
        finally:
            session.close()
        # 确保没有冲突数据
        self._clean_profile()

    def _clean_profile(self):
        """确保画像数据没有冲突"""
        # 从喜欢列表中移除不喜欢的内容
        for genre in self.base_profile["negative_genres"]:
            if genre in self.base_profile["movie_genre"]:
                self.base_profile["movie_genre"].remove(genre)
        
        for actor in self.base_profile["negative_actors"]:
            if actor in self.base_profile["favorite_actors"]:
                self.base_profile["favorite_actors"].remove(actor)
        
        for director in self.base_profile["negative_directors"]:
            if director in self.base_profile["favorite_directors"]:
                self.base_profile["favorite_directors"].remove(director)

    def save_profile(self):
        """保存用户画像到MySQL"""
        try:
            db_name = self.engine.url.database
            print(f"[UserProfileSystem] 正在保存用户画像到数据库: {db_name}，表: user_profiles ...")
            self._clean_profile()
            save_data = copy.deepcopy(self.base_profile)
            save_data["last_updated"] = datetime.now().isoformat()
            session = self.Session()
            record = session.query(UserProfileDB).filter_by(user_id=self.user_id).first()
            if record:
                record.profile_json = json.dumps(save_data, ensure_ascii=False)
                record.last_updated = datetime.now()
            else:
                record = UserProfileDB(
                    user_id=self.user_id,
                    profile_json=json.dumps(save_data, ensure_ascii=False),
                    last_updated=datetime.now()
                )
                session.add(record)
            session.commit()
        except Exception as e:
            print(f"保存用户画像失败: {str(e)}")
        finally:
            session.close()

    def _call_llm(self, prompt_messages: Any) -> str:
        """调用大模型API并严格验证响应"""
        try:
            message_dicts = []
            for m in prompt_messages.to_messages():
                role = {
                    "system": "system",
                    "human": "user",
                    "ai": "assistant"
                }.get(m.type, "user")
                message_dicts.append({
                    "role": role,
                    "content": m.content
                })

            response = self.client.chat.completions.create(
                model="qwen-plus",
                messages=message_dicts,
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}  # 强制JSON输出
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API调用失败: {str(e)}")
            return "{}"

    def clean_json_response(self, text: str) -> Dict[str, Any]:
        """严格解析API返回的JSON"""
        try:
            # 尝试直接解析
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except:
            pass
        
        # 尝试提取JSON部分
        cleaned = re.sub(r'^.*?(\{.*\}).*?$', r'\1', text, flags=re.DOTALL)
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(cleaned)
        except:
            return {}

    def process_input(self, user_input: str = "", selected_tags: Optional[Dict] = None,
                 frontend_data: Optional[Dict] = None) -> Dict[str, Any]:
        """处理用户输入并严格更新画像"""
        if frontend_data:
            # 从按钮标签获取确定数据
            extracted_data = {
                "age_group": frontend_data.get("ageRange", ""),
                "gender": frontend_data.get("gender", ""),
                "fav_genres": frontend_data.get("moviePreferences", []),
                "user_input": frontend_data.get("currentInput", "")  # 保留原始输入用于自然语言处理
            }
            
            # 从自然语言输入中提取其他信息
            if extracted_data["user_input"]:
                result = self.chain.invoke({
                    "user_input": extracted_data["user_input"],
                    "selected_tags": selected_tags or {}
                })
                nl_extracted = self.clean_json_response(result)
                
                # 合并自然语言提取的数据（但保留标签数据的优先级）
                for key in nl_extracted:
                    if key not in extracted_data or not extracted_data[key]:
                        extracted_data[key] = nl_extracted[key]
        else:
            # 纯自然语言处理模式
            result = self.chain.invoke({
                "user_input": user_input,
                "selected_tags": selected_tags or {}
            })
            extracted_data = self.clean_json_response(result)
        
        if extracted_data:
            input_content = user_input if not frontend_data else str(frontend_data)
            self.memory.save_context(
                {"input": input_content},
                {"output": json.dumps(extracted_data, ensure_ascii=False)}
            )
            
            self._strict_merge(extracted_data)
            self.save_profile()

        return extracted_data

    def _strict_merge(self, update: Dict[str, Any]):
        """
        严格合并更新，确保：
        1. 新喜欢的内容从negative_列表中移除
        2. 新不喜欢的内容从正面列表中移除
        """
                # 正向字段到负向字段的映射
        pos_to_neg_map = {
            "fav_genres": "negative_genres",
            "favorite_actors": "negative_actors",
            "favorite_directors": "negative_directors"
        }

        # 处理新喜欢的项目
        for pos_key, neg_key in pos_to_neg_map.items():
            if pos_key in update:
                for item in update[pos_key]:
                    if item in self.base_profile[neg_key]:
                        self.base_profile[neg_key].remove(item)

        # 处理新不喜欢的项目
        neg_to_pos_map = {v: k for k, v in pos_to_neg_map.items()}
        for neg_key, pos_key in neg_to_pos_map.items():
            if neg_key in update:
                for item in update[neg_key]:
                    if item in self.base_profile[pos_key]:
                        self.base_profile[pos_key].remove(item)

        
        # 合并所有更新
        for key, value in update.items():
            if key not in self.base_profile:
                continue
                
            if isinstance(self.base_profile[key], list):
                if isinstance(value, list):
                    # 合并并去重
                    self.base_profile[key] = list(set(self.base_profile[key] + value))
                elif value and value not in self.base_profile[key]:
                    self.base_profile[key].append(value)
            elif value:
                self.base_profile[key] = value
        
        # 更新最后修改时间
        self.base_profile["last_updated"] = datetime.now().isoformat()

    def get_full_profile(self) -> Dict[str, Any]:
        """获取当前完整且无冲突的用户画像"""
        # 深拷贝基础画像
        full_profile = copy.deepcopy(self.base_profile)
        
        # 合并当前会话的更新
        for msg in self.memory.chat_memory.messages:
            if msg.type == "ai":
                try:
                    update = json.loads(msg.content)
                    self._strict_merge(update)
                except:
                    continue
        
        # 最终清理
        self._clean_profile()
        return full_profile

    def reset_session(self):
        """重置当前会话"""
        self.memory.clear()

def extract_user_profile_from_input(user_input: str = "", selected_tags: Optional[Dict] = None, frontend_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    从用户输入、标签和前端数据中提取用户画像信息。

    Args:
        user_input (str): 用户自然语言输入。
        selected_tags (dict, optional): 用户选择的标签。
        frontend_data (dict, optional): 前端传递的结构化数据。

    Returns:
        dict: 提取出的用户画像信息。
    """
    system = UserProfileSystem("tool_temp_user")
    return system.process_input(user_input=user_input, selected_tags=selected_tags, frontend_data=frontend_data)

# 测试用例
if __name__ == "__main__":
    system = UserProfileSystem("小a")
    
    # 测试前端数据输入
    frontend_data = {
        "currentInput": "我明天想和朋友去看电影",
        "ageRange": "18-25",
        "gender": "女",
        "moviePreferences": ["爱情"]
    }
    updates = system.process_input(frontend_data=frontend_data)
    
    print("\n完整画像:")
    full_profile = system.get_full_profile()
    cleaned = {k: v for k, v in full_profile.items() if v not in ["", [], None]}
    pprint(cleaned, width=120, indent=2)
    
    system.save_profile()