#!/usr/bin/env python3
"""
测试iTick API连接状态
"""

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 忽略SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_itick_api():
    """测试iTick API连接"""
    
    # API配置
    api_key = "70b52ae52b23474a8da516ea4215b47e063419e5ed694a6b9ea6ab6cff85b7d2"
    base_urls = [
        "https://api.itick.com",
        "https://api.iextrading.com",  # 备用API
        "https://api.polygon.io"       # 另一个备用API
    ]
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    session.verify = False  # 忽略SSL验证
    
    for base_url in base_urls:
        print(f"\n测试API: {base_url}")
        
        # 测试市场状态端点
        endpoints = [
            "/v1/market/status",
            "/v1/quote/AAPL",
            "/api/v1/quote/AAPL",  # 备用路径
            "/quote/AAPL"          # 简化路径
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{base_url}{endpoint}"
                print(f"  测试: {url}")
                
                response = session.get(url, headers=headers, timeout=10)
                
                print(f"    状态码: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"    响应: {data}")
                        print(f"    ✅ API连接成功！")
                        return True
                    except:
                        print(f"    响应内容: {response.text[:200]}")
                elif response.status_code == 401:
                    print(f"    ❌ API Key无效或过期")
                elif response.status_code == 403:
                    print(f"    ❌ 权限不足")
                elif response.status_code == 404:
                    print(f"    ❌ 端点不存在")
                else:
                    print(f"    ❌ 请求失败: {response.text[:100]}")
                    
            except requests.exceptions.SSLError as e:
                print(f"    ❌ SSL错误: {e}")
            except requests.exceptions.ConnectionError as e:
                print(f"    ❌ 连接错误: {e}")
            except requests.exceptions.Timeout as e:
                print(f"    ❌ 超时错误: {e}")
            except Exception as e:
                print(f"    ❌ 其他错误: {e}")
    
    print(f"\n❌ 所有API测试失败")
    return False

def test_alternative_data():
    """测试备用数据源"""
    print("\n=== 测试备用数据源 ===")
    
    # 测试Alpha Vantage（免费）
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': 'AAPL',
            'apikey': 'demo'  # 使用演示密钥
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"Alpha Vantage响应: {data}")
            if 'Global Quote' in data:
                print("✅ Alpha Vantage API可用")
                return True
        
    except Exception as e:
        print(f"❌ Alpha Vantage测试失败: {e}")
    
    # 测试Yahoo Finance（通过yfinance）
    try:
        import yfinance as yf
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price:
            print(f"✅ Yahoo Finance可用，AAPL价格: ${price}")
            return True
    except ImportError:
        print("❌ yfinance未安装")
    except Exception as e:
        print(f"❌ Yahoo Finance测试失败: {e}")
    
    return False

if __name__ == "__main__":
    print("=== iTick API连接测试 ===")
    
    if not test_itick_api():
        print("\n=== iTick API不可用，测试备用数据源 ===")
        if test_alternative_data():
            print("\n✅ 找到可用的备用数据源")
        else:
            print("\n❌ 没有找到可用的数据源")
            print("\n建议：")
            print("1. 检查网络连接")
            print("2. 验证iTick API Key是否有效")
            print("3. 考虑使用Yahoo Finance等免费数据源")
            print("4. 联系iTick支持检查API状态")
    else:
        print("\n✅ iTick API连接正常")