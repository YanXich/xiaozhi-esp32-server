import requests

def send_get_request_with_device_id(url: str) -> None:
    """
    发送带 Device-Id 头的 GET 请求
    :param url: 目标请求地址（例如 "https://api.example.com/data"）
    """
    # 1. 定义请求头（包含指定的 Device-Id）
    headers = {
        "Device-Id": "E3:E1:C2:C8:81:07"
    }

    try:
        # 2. 发送 GET 请求
        response = requests.get(
            url=url,
            headers=headers,
            timeout=10  # 超时时间（秒），防止请求卡死
        )

        # 3. 验证响应状态（200 表示请求成功）
        response.raise_for_status()  # 若状态码 >=400，会抛出 HTTPError 异常

        # 4. 处理响应结果（根据实际需求调整，这里打印响应内容）
        print("请求成功！")
        print(f"响应状态码：{response.status_code}")
        print(f"响应内容：{response.text}")  # 文本格式（JSON/HTML 等）
        # 若响应是 JSON 格式，可直接解析：print(response.json())

    except requests.exceptions.Timeout:
        print("错误：请求超时（可能是网络问题或目标服务不可用）")
    except requests.exceptions.ConnectionError:
        print("错误：无法连接到目标服务器（检查 URL 或网络连接）")
    except requests.exceptions.HTTPError as e:
        print(f"错误：请求失败，状态码：{e.response.status_code}，详情：{e.response.text}")
    except Exception as e:
        print(f"未知错误：{str(e)}")

# ------------------------------
# 使用示例
# ------------------------------
if __name__ == "__main__":
    # 替换为你的实际请求 URL
    target_url = "http://47.109.177.102:8002/xiaozhi/ota/checkOTAVersion"
    send_get_request_with_device_id(target_url)
