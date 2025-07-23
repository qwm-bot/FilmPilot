import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re
from langchain_core.tools import tool

# @tool(description="根据经纬度获取城市ID，只返回id字段。参数为lat（纬度）、lng（经度），返回城市id（int）。")
def get_city_by_latlng(lat, lng):
    """
    Get the current city information based on latitude and longitude using the Maoyan API.

    Args:
        lat (float): Geographic latitude.
        lng (float): Geographic longitude.

    Returns:
        dict: City information returned by the API, or error info.
    """
    url = "https://apis.netstart.cn/maoyan/city/latlng"
    params = {
        "lat": lat,
        "lng": lng
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()["id"]
    except Exception as e:
        return {"error": str(e)}

# Example usage:
# result = get_city_by_latlng(23.4, 113.3)
# print(result)

# @tool(description="Search Maoyan movies by keyword, only return the first related movie info. Optional parameters include city ID (ci), pagination (offset), return count (limit), etc. Return movie rating, type, id, poster, etc.")
def get_film_info(keyword, ci=1, offset=0, limit=1):
    """
    Search Maoyan movies by keyword, only return the first related movie info.
    Args:
        keyword (str): Search keyword, required.
        ci (int, optional): City ID, default 1.
        offset (int, optional): Pagination offset, default 0.
        limit (int, optional): Return count, default 1 (only the first movie).

    Returns:
        dict: Includes movie Douban rating, type, movie id, poster, etc.
    """
    url = "https://apis.netstart.cn/maoyan/search/movies/"
    params = {
        "keyword": keyword,
        "ci": ci,
        "offset": offset,
        "limit": limit
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://maoyan.com/",  # Optional depending on API
        "Origin": "https://maoyan.com"     # Optional depending on API
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    # Only return the first data
    return data[0]

# @tool(description="Get and display detailed information of the movie by movie ID, including poster url, description, trailer url, etc. Return detailed info dict.")
def get_film_detail(movie_id):
    """
    Get and display detailed information of the specified movie, including poster, description, trailer, etc.

    Args:
        movie_id (int or str): Unique movie ID.

    Returns:
        dict: Contains detailed movie info, such as:
            - poster
            - description/summary
            - trailer
    """
    url = "https://apis.netstart.cn/maoyan/movie/intro/"
    params = {
        "movieId": movie_id,
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://maoyan.com/",  # Optional depending on API
        "Origin": "https://maoyan.com"     # Optional depending on API
    }
    response = requests.get(url, params=params,headers=headers)
    response.raise_for_status()
    data = response.json()
    return data

# @tool(description="Crawl Maoyan web page to get the raw HTML content of the cinema schedule for the specified movie ID, save to local file. Mainly used for development debugging or as a backup when API is unavailable.")
def get_maoyan_cinemas_by_movie(movie_id, city_id=None,filename="cinemas_raw.html"):
    """
    Get the schedule info of the movie by crawling the web page, basically not used, can use get_cinema_time function instead.
    """
    url = f"https://maoyan.com/cinemas?movieId={movie_id}"
    if city_id:
        url += f"&ci={city_id}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://maoyan.com/",
        "Origin": "https://maoyan.com"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Saved to {filename}")

# @tool(description="Get the cinema schedule info for the specified movie (movieId) in the specified city (cityId) and date (showDate), return a list of brief info including cinema coordinates, hall, address, distance, recent showtimes, etc. Optional parameter limit controls the number of results returned.")
def get_cinema_time(movieId, cityId=40, showDate=None,limit=20,lnt=117.346194,lat=38.988726):
    """
    Get the cinema schedule info for the specified movie in the specified city and date.
    showDate defaults to today, can return all cinemas showing the movie, their coordinates, hall, address, distance, recent showtimes, etc.
    """
    if showDate is None:
        showDate = datetime.today().strftime("%Y-%m-%d")
    url = "https://apis.netstart.cn/maoyan/movie/select/cinemas"
    params = {
        "movieId": movieId,
        "cityId": cityId,
        "showDate": showDate,
        "lng":117.346194,
        "lat":38.988726,
        "limit":limit
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://maoyan.com/",
        "Origin": "https://maoyan.com"
    }
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data=response.json()
    cinemas=[]
    for cinema in data.get("data", {}).get("cinemas", []):
        cinema_id = cinema.get("id")
        poi_id = cinema.get("poiId") or cinema.get("poiID")  # Compatible with different field names
        # Filter label with color #579daf
        labels = [label for label in cinema.get("labels", []) if label.get("color") == "#579daf" and label.get("name") != "退" and label.get("name") != "改签"]
        # Build new dict
        filtered = {
            "addr": cinema.get("addr"),
            "distance": cinema.get("distance"),
            "id": cinema_id,
            "lat": cinema.get("lat"),
            "lng": cinema.get("lng"),
            "name": cinema.get("name"),
            "poiId": poi_id,
            "sellPrice": cinema.get("sellPrice") or cinema.get("sellprice"),
            "showTimes": cinema.get("showTimes") or cinema.get("showTime"),
            "ticket_url": f"https://www.maoyan.com/cinema/{cinema_id}?poi={poi_id}&movieId={movieId}",
            "labels": labels
        }
        cinemas.append(filtered)
    return cinemas

@tool(description="Search for a movie by keyword and return the cinema schedule info for that movie in the specified city and date. Combines get_film_info and get_cinema_time. Parameters: {'keyword': 'movie name', 'cityId': 'city ID (default 40)', 'showDate': 'YYYY-MM-DD (optional)', 'limit': 'number of results (optional)' }.")
def get_film_cinema_schedule(keyword, cityId=40, showDate=None, limit=5,lnt=117.346194,lat=38.988726):
    """
    Search for a movie by keyword, extract the movie id, and return the cinema schedule info for that movie in the specified city and date.
    This function combines get_film_info and get_cinema_time.
    Args:
        keyword (str): Movie name to search for.
        cityId (int, optional): City ID, default 40 (Tianjin).
        showDate (str, optional): Date in YYYY-MM-DD format. Defaults to today.
        limit (int, optional): Number of results to return. Default 20.
    Returns:
        list: List of cinema schedule info dicts for the found movie.
    """
    movie_info = get_film_info(keyword)
    movie_id = None
    if isinstance(movie_info, dict):
        movie_id = movie_info.get("id") or movie_info.get("movie_id")
    if not movie_id:
        return {"error": f"Movie id not found for keyword: {keyword}"}
    return get_cinema_time(movie_id, cityId, showDate, limit,lnt,lat)

if __name__ == "__main__":
    # Test case
    result = get_film_info("Malice")
    id=result["id"]
    result=get_cinema_time(id)
    with open("result_cinematime_briefinfo.json", "w", encoding="utf-8") as f:
        import json
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("Test completed, result written to result_cinematime_briefinfo.json")
    # get_maoyan_cinemas_by_movie(movie_id=1522834)