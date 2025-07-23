import requests
from langchain_core.tools import tool
from dotenv import load_dotenv
import os

load_dotenv()
amap_key = os.getenv("AMAP_API_KEY")
amapjs_key = os.getenv("AMAPJS_API_KEY")
security_key = os.getenv("AMAPJS_SECURITY_KEY")
MODE_API_URL = {
    "driving": "https://restapi.amap.com/v5/direction/driving",
    "walking": "https://restapi.amap.com/v5/direction/walking",
    "bicycling": "https://restapi.amap.com/v5/direction/bicycling",
    "electrobike": "https://restapi.amap.com/v5/direction/electrobike",
    "transit": "https://restapi.amap.com/v5/direction/transit/integrated"
}


# @tool(description="Get the longitude and latitude coordinates of a given address (address) and optional city name (city), return a float list [longitude, latitude].")
def get_location_by_address(address, city=40):
    """
    Get longitude and latitude by address
    :param address: Detailed address string
    :param city: Optional, city name
    :return: [longitude, latitude] float list, or None
    """
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "address": address,
        "key": amap_key
    }
    if city:
        params["city"] = city
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    if data.get("status") == "1" and data.get("geocodes"):
        location = data["geocodes"][0]["location"]  # "longitude,latitude"
        lng, lat = location.split(",")
        return [float(lng), float(lat)]
    else:
        return None


@tool(
    description="Get route planning information for various transportation modes (driving, walking, cycling, etc.) based on the starting point coordinates (origin), destination address (address), city (city), mode of transportation (mode), and return a dictionary containing route, distance, estimated time, etc.")
def get_route(origin, address, city=40, mode="driving", isindoor=True, **kwargs):
    """
    Backend non-visual route planning: Get routes for various transportation modes based on starting point coordinates and destination address.

    Parameters:
        origin (str): Starting point coordinates, format "longitude,latitude", required for all modes.
        address (str): Destination detailed address, required for all modes, will be automatically geocoded to coordinates.
        city (str, optional): City name, used for geocoding.
        mode (str): Mode of transportation, "driving" (default), "walking", "bicycling", "electrobike", "transit".
        isindoor (bool, optional): Used in walking mode, whether indoor route planning is needed. 0: not needed, 1: needed, default True.
        **kwargs: Other common parameters supported by AMap API.

    Returns:
        dict: API response result, including route, distance, estimated time, etc.
    """
    url = MODE_API_URL.get(mode)
    # Use .invoke to call the tool
    destination_coords = get_location_by_address.invoke({"address": address, "city": city})
    if not url:
        raise ValueError(f"Unsupported mode of transportation: {mode}")
    # Format destination as 'lng,lat' string if needed
    if isinstance(destination_coords, list) and len(destination_coords) == 2:
        destination = f"{destination_coords[0]},{destination_coords[1]}"
    else:
        destination = destination_coords
    if mode == "bicycling":
        params = {
            "origin": origin,
            "destination": destination,
            "key": amap_key,
            "isindoor": isindoor
        }
    else:
        params = {
            "origin": origin,
            "destination": destination,
            "key": amap_key
        }
    params.update(kwargs)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def test_get_route():
    """
    Test get_route function, output result to result_output.json file.
    """
    # Example parameters, can be modified as needed
    origin = "116.481028,39.989643"  # Beijing
    address = "No. 111, Youyi South Road, Xiqing District, Tianjin, 3rd Floor, AEON Mall"
    city = "Tianjin"
    mode = "driving"
    try:
        result = get_route(origin, address, city=city, mode=mode)
        with open("result_output.json", "w", encoding="utf-8") as f:
            import json
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("Test completed, result written to result_output.json")
    except Exception as e:
        print(f"Test failed: {e}")


# @tool(description="Return navigation variables required for frontend visualization based on origin, destination address, city, mode of transportation, etc., including origin and destination coordinates, mode, API key, security key, etc. Suitable for frontend-backend separation scenarios.")
def get_route_info(address, city="天津", mode="Driving", origin=None, **kwargs):
    """
    Get navigation variable information required for frontend visualization, for frontend to dynamically load AMap JS API and perform route visualization.

    Parameters:
        origin (str or dict, optional): Origin address string或{keyword, city}结构。
        address (str): Destination detailed address.
        city (str, optional): City name, used to improve geocoding accuracy.
        mode (str, optional): Mode of transportation, "Driving" (default), "Walking", "Riding", "Transfer", "TruckDriving", etc.
        **kwargs: Other optional parameters, reserved for extension.

    Returns:
        dict: Contains all variables required for frontend visualization, including:
            - destination: { keyword: string, city: string }
            - origin: { keyword: string, city: string } (如有)
            - city, mode, amapjs_key, security_key
    """
    # 防御：如果address是dict，取其'address'字段
    if isinstance(address, dict):
        address = address.get("address", "")
    # 适配前端AmapRouteBox的destination结构
    destination = {"keyword": address, "city": city}
    # 适配origin结构
    if origin is None:
        origin_obj = None
    elif isinstance(origin, dict):
        origin_obj = origin
    else:
        origin_obj = {"keyword": origin, "city": city}
    return {
        "map_action": True,
        "destination": destination,
        "origin": origin_obj,
        "city": city,
        "mode": mode,
    }


if __name__ == "__main__":
    test_get_route()
