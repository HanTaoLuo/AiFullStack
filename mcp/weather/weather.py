from typing import Any,Annotated
import httpx
from mcp.server.fastmcp import FastMCP
import os

from pydantic import Field

# 1.初始化 mcp 服务器
# 创建一个名为"weather" 的服务器实例，名字用于大模型识别工具
mcp =FastMCP("weather-search")

AMAP_API_KEY = os.getenv("LBS_AMAP_API_KEY")
#常量定义
# 美国国家气象局 API 基础 URL
NWS_API_BASE = "https://api.weather.gov"
# 高德地图天气 API 基础 URL
REST_API_AMAP_BASE  = "https://restapi.amap.com"
# 设置请求头的User-Agent,公共 api 要求提供此信息以识别客户端
USER_AGENT = "weather-app/1.0"

# 辅助函数
# (异步函数)  返回 dict[str,所有类型] 或者空
async def make_request(url:str) ->dict[str,Any] | None:
    """
    通用异步函数、用户请求 API 并处理常见错误
    :param
        url: 要请求的完整 URL。
    :return:
        dict[str, Any] | None: 成功时返回解析后的 JSON 字典，失败时返回 None。
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept" : "application/geo+json"  # NWS API 推荐的 Accept 头
    }
    # 使用 httpx.AsyncClient 执行异步 HTTP GET 请求
    async  with httpx.AsyncClient() as client:
        try:
            # 发起请求 设置 30s 超时
            response = await client.get(url,headers =headers,timeout=30)
            # 如果响应状态码是 4xx 或 5xx（表示客户端或服务器错误），则会引发一个异常
            response.raise_for_status()
            # 请求成功了 返回json格式响应体
            return response.json()
        except Exception:
            # 捕获所有可能的异常（如网络问题、超时、HTTP错误等），并返回 None
            return None





def format_alert(feature:dict)->str:
    """
        将单个天气预警的 json 数据化格式化为字符串
    """
    props = feature["properties"]
    # 使用 .get() 方法安全的访问字典键,如果键不存在则返回默认值，避免程序出错
    result = f"""
        事件: {props.get('event', '未知')}
        区域: {props.get('areaDesc', '未知')}
        严重性: {props.get('severity', '未知')}
        描述: {props.get('description', '无描述信息')}
        指令: {props.get('instruction', '无具体指令')}
        """
    return result


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

# MCP 工具定义
# 大模型通过 get_alert 方法获取天气
@mcp.tool()
async def get_alert(state:Annotated[str,Field(description="两个字的美国州代码(例如:CA,NY)")]) -> str:
    """
    获取美国某个州的当前生效的预警信息，
    函数被 @mcp.tool() 装饰器标记、意味着它可以被大模型作为工具调用
    """
    # 构造特定州天气预警的 URL
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data  = await make_request(url)
    # 健壮性检查 如果请求失败或者返回的数据格式不正确
    if not data or "features" not in data:
        return "无法获取预警信息或未找到相关数据"

    if not data["features"]:
        return "该州当前没有生效的天气预警。"

    # 使用列表推导和 format_alert 函数来格式化预警信息
    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude:Annotated[float,Field(description="地点的纬度")],
                       longitude:Annotated[float,Field(description="地点的经度")],
                       days:Annotated[int,Field(description="查询最近几个预报周期的天气,默认值为 5",default=5)])->str:
    """
    根据经纬度获取天气预报,也是一个可被调用的 mcp 工具
    :param days:(可选) 查询最近几个预报周期的天气,默认值为 5
    :param latitude: 地点的纬度
    :param longitude: 地点的经度
    """
    #NWS API 获取预报需要两部
    # 第一步：根据经纬度获取一个包含具体预报接口 URL 的网格点信息
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data =  await make_request(points_url)
    if not points_data:
        return "无法获取该地点的预报数据。"

    # 第二步:从上一步响应中提取实际的天气预报接口 URL
    forecast_url = points_data["properties"]["forecast"]
    # 第三步:请求详细的天气预报数据
    forecast_data = await make_request(forecast_url)
    if not forecast_data:
        return "无法获取详细的预报信息。"
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    # 遍历接下来 5 个预报周期(例如:今天下午、今晚、明天)
    for period in periods[:days]:
        forecast = f"""
            {period['name']}：
                温度:{period['temperature']}°{period['temperatureUnit']}
                风力: {period['windSpeed']} {period['windDirection']}
                预报: {period['detailedForecast']}
        """
        forecasts.append(forecast)

    # 将格式化后的预报信息连接成一个字符串并返回
    return "\n---\n".join(forecasts)


@mcp.tool()
async def get_cn_weather(adcode:Annotated[int,Field(description="根据输入的中国城市的 adcode 编码查询对应天气")])->str:
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

@mcp.tool()
async def get_cn_adcode(keywords:Annotated[str,Field(description="获取输入城市的 adcode 值 ")])->Any:
    url = f"{REST_API_AMAP_BASE}/v3/config/district?keywords={keywords}&subdistrict=0&key={AMAP_API_KEY}"
    ad_code_data = make_request(url)
    if not ad_code_data or "districts" not in ad_code_data:
        return f"未查询到:{keywords} 对应的 adcode值 "
    return ad_code_data["districts"][0]["adcode"]


# ---启动服务器---
# 这是一个标准的 python 入口点检查
# 确保只有当这个文件被直接运行时，以下代码才会被执行
if __name__ == '__main__':
    # 初始化并运行 mcp 服务器
    # transport = 'stdio' 表示服务器将通过标准输入/输出(stdin/stdout) 与客户端(deepseek大模型) 进行通信
    mcp.run(transport='stdio')