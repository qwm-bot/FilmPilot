from backend.Tool.core import MovieRecommender
import time
import os
import json

def test_daily_recommendation():
    """测试每日推荐功能"""
    print("开始测试每日推荐功能...")
    
    # 设置API密钥 - 从环境变量获取或使用默认值
    qwen_api_key = "sk-41ec31f7dbc74f4b81a63f892bd528e4"
    
    # 使用API密钥初始化推荐器
    recommender = MovieRecommender(qwen_api_key=qwen_api_key)
    
    # 存储所有结果
    all_results = {}
    
    # 测试不同数量的推荐
    for count in [3, 5]:
        print(f"\n测试获取 {count} 部每日推荐电影:")
        start_time = time.time()
        
        try:
            daily_movies = recommender.get_daily_recommendations(count=count)
            elapsed = time.time() - start_time
            
            if not daily_movies:
                print("测试失败: 未获取到任何电影")
                all_results[f"{count}movies"] = {"status": "failed", "error": "未获取到任何电影"}
                continue
                
            print(f"测试成功! 获取到 {len(daily_movies)} 部电影 (耗时: {elapsed:.2f}秒)")
            
            # 将电影信息转换为JSON格式
            movies_json = []
            for i, movie in enumerate(daily_movies, 1):
                movie_info = {
                    "rank": i,
                    "title": movie.get('title', '未知'),
                    "vote_average": movie.get('vote_average', 0),
                    "tagline": movie.get('tagline', '无'),
                    "overview": movie.get('overview', '暂无简介'),
                    "poster_url": movie.get('poster_url', '无'),
                    "genres": movie.get('genres', []),
                    "runtime": movie.get('runtime', 0)
                }
                movies_json.append(movie_info)
            
            all_results[f"{count}movies"] = {
                "status": "success",
                "count": len(daily_movies),
                "execution_time": round(elapsed, 2),
                "movies": movies_json
            }
                
        except Exception as e:
            print(f"测试失败: {str(e)}")
            all_results[f"{count}movies"] = {"status": "failed", "error": str(e)}
            continue
    
    print("\n测试完成!")
    return all_results

if __name__ == "__main__":
    result = test_daily_recommendation()
    print("\n返回的JSON结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))