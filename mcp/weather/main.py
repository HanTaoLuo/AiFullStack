from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import os
from typing import Any, Optional, Dict, Union
import requests
from requests.exceptions import RequestException

print(os.environ)

AMAP_API_KEY = os.getenv("LBS_AMAP_API_KEY")
#常量定义
# 美国国家气象局 API 基础 URL
NWS_API_BASE = "https://api.weather.gov"
# 高德地图天气 API 基础 URL
REST_API_AMAP_BASE  = "https://restapi.amap.com"
# 设置请求头的User-Agent,公共 api 要求提供此信息以识别客户端
USER_AGENT = "weather-app/1.0"

def get_cn_adcode(keywords:str)->Any:

    url = f"{REST_API_AMAP_BASE}/v3/config/district?keywords={keywords}&subdistrict=0&key={AMAP_API_KEY}"
    ad_code_data = make_request(url)
    if not ad_code_data or "districts" not in ad_code_data:
        return f"未查询到:{keywords} 对应的 adcode值 "
    return ad_code_data["districts"][0]["adcode"]
# 辅助函数
# (异步函数)  返回 dict[str,所有类型] 或者空

def get_cn_weather(adcode:int)->str:
    """
        根据输入的中国城市的 adcode 编码查询对应天气
    :param adcode: 城市的 adcode 编码
    :return:
    """
    amap_url =f"{REST_API_AMAP_BASE}/v3/weather/weatherInfo?city={adcode}&key={AMAP_API_KEY}&extensions=all"
    points_data = make_request(amap_url)
    if points_data['info']=='OK':
        return get_format_cn_weather(points_data)
    return "无法获取最新天气数据"


def get_format_cn_weather(data:dict)->str:
    if data.get('status') != '1':
        return "无法获取最新天气数据"

    forecast = data['forecasts'][0]
    report = [
        f"{forecast['province']}{forecast['city']}天气预报（{forecast['reporttime']}）",
        f"行政区划代码：{forecast['adcode']}",
        "未来几天天气预报："
    ]

    for cast in forecast['casts']:
        report.append(
            f"{cast['date']} 星期{cast['week']}: "
            f"白天{cast['dayweather']}，最高气温{cast['daytemp']}℃，{cast['daywind']}风{cast['daypower']}级；"
            f"夜间{cast['nightweather']}，最低气温{cast['nighttemp']}℃，{cast['nightwind']}风{cast['nightpower']}级"
        )

    return "\n-----\n".join(report)


def make_request(
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,  # 表单数据
        timeout: float = 30.0,
        raise_for_status: bool = True,
        **kwargs
) -> Union[Dict[str, Any], str, bytes, None]:
    """
    通用的同步 HTTP 请求方法

    Args:
        url: 请求的完整 URL
        method: HTTP 方法 (GET/POST/PUT/DELETE等)
        headers: 自定义请求头
        params: URL查询参数
        json_data: JSON请求体
        data: 表单数据
        timeout: 超时时间(秒)
        raise_for_status: 是否自动抛出HTTP错误
        **kwargs: 其他requests支持的参数

    Returns:
        - 成功时根据响应内容返回:
            * 如果是JSON响应: 返回解析后的字典
            * 如果是文本响应: 返回字符串
            * 如果是二进制响应: 返回bytes
        - 失败时返回None
    """
    # 设置默认请求头
    default_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MyApp/1.0)",
        "Accept": "application/json",
    }
    final_headers = {**default_headers, **(headers or {})}

    try:
        # 根据方法类型发送请求
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=final_headers,
            params=params,
            json=json_data,
            data=data,
            timeout=timeout,
            **kwargs
        )

        if raise_for_status:
            response.raise_for_status()

        # 根据响应内容类型返回不同格式的数据
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            return response.json()
        elif "text/" in content_type:
            return response.text
        else:
            return response.content

    except RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

if __name__ == "__main__":
    ad_code = get_cn_adcode("昆山市")
    print(get_cn_weather(adcode=ad_code))
