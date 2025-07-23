from Tool.core import MovieRecommender
import time
import os


def test_daily_recommendation():
    """测试每日推荐功能"""
    print("开始测试每日推荐功能...")

    # 设置API密钥 - 从环境变量获取或使用默认值
    qwen_api_key = "sk-41ec31f7dbc74f4b81a63f892bd528e4"

    # 使用API密钥初始化推荐器
    recommender = MovieRecommender(qwen_api_key=qwen_api_key)

    # 测试不同数量的推荐
    for count in [3, 5]:
        print(f"\n📅📅 测试获取 {count} 部每日推荐电影:")
        start_time = time.time()

        try:
            daily_movies = recommender.get_daily_recommendations(count=count)
            elapsed = time.time() - start_time

            if not daily_movies:
                print("❌❌ 测试失败: 未获取到任何电影")
                continue

            print(f"✅✅ 测试成功! 获取到 {len(daily_movies)} 部电影 (耗时: {elapsed:.2f}秒)")

            # 打印电影详情
            for i, movie in enumerate(daily_movies, 1):
                print(f"\n🏆🏆 推荐电影 #{i}:")
                print(f"🎬 标题: {movie.get('title', '未知')}")
                print(f"⭐ 评分: {movie.get('vote_average', 0)}")
                print(f"💬 经典台词: 「{movie.get('tagline', '无')}」")
                print(f"📖 简介: {movie.get('overview', '暂无简介')[:80]}...")
                print(f"🖼️ 海报: {movie.get('poster_url', '无')}")
                print(f"🎭 类型: {', '.join(movie.get('genres', []))}")
                print(f"⏱️ 时长: {movie.get('runtime', 0)}分钟")

        except Exception as e:
            print(f"❌❌ 测试失败: {str(e)}")
            continue

    print("\n测试完成!")


if __name__ == "__main__":
    test_daily_recommendation()