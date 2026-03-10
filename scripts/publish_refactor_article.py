import os
import requests
import json
from dotenv import load_dotenv

# Load local .env to safely get credentials
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def publish_article():
    # We will use the remote API through the newly configured Apache endpoint
    url = "https://oc.macroalpha.io/endpoint/openclaw_wechat_public_account/publish"
    admin_key = os.getenv("ADMIN_API_KEY")
    
    headers = {
        "X-Admin-Api-Key": admin_key
    }
    
    article_markdown = """# OpenClaw 微信服务：从私有状态到无状态的开源架构重构

在构建 AI Agent 生态系统的过程中，我们将原有的 `wechat-public-account` 服务成功重构为开源的、完全无状态的 `openclaw_wechat_public_account` 微服务组件。

本次重构的核心目标是**解除对本地配置文件（如 `.env`）的强依赖**，使服务具备极高的可移植性和多租户兼容性。

## 1. 为什么要做无状态重构？

早期的代码中，WeChat 的 `APPID`、`APPSECRET` 以及大模型的 `API_KEY` 是通过全局的环境变量读取的。这种设计在私有化部署时导致：
- 无法在同一个服务实例中支持多个微信公众号（多租户限制）。
- 部署到不可信环境时，存在敏感配置被打包或覆盖的风险。
- 难以动态更换渠道或语言模型。

## 2. 改造方案与实现细节

我们将系统完全变成了“由调用方驱动”的 SDK 模式：

### 核心凭据的动态注入 (Dynamic Credentials)
所有的内部 Client（如 `MediaClient`, `LLMClient`, `DraftManager`）被重构，不再读取默认全局变量。所有的底层请求都需要传入带有确切凭证的参数。
在最外层（FastAPI `/publish` 端点），我们要求客户端必须在请求的 JSON Payload 里主动出示所有的 Key 才能完成发布。

### Webhook 异步回调改造
微信公众号后台原本配置的回调地址是固定的。在无状态模式下，我们将所有的解密与鉴权标识放到了 URL Query Parameters 中：
`.../wechat/callback?wx_token=XXX&wx_aes_key=YYY&wx_appid=ZZZ`
这样，无论是处理哪个租户的自动回复，Webhook 都能动态从 URL 提取密码本来解密微信服务器发来的信息。

### 避免配置文件污染
在 `deploy.sh` 脚本中，我们严格限制不再同步包含一切核心资产的 `.env` 文件，只允许用于网关防护防刷的 `ADMIN_API_KEY` 进入生产服务器。

## 3. 经验总结

- **IP 白名单机制**：在本地改造和测试时，一旦走通动态注入数据链路，就会遇到微信 API 的 `invalid ip` 拦截。这一特性反而帮助我们确信：基于调用方环境传参的设计，必须在正式部署（处于白名单的云服务器）上走请求，保证了发布网关的控制权。
- **向下兼容 (Backward Compatibility)**：即使内部架构改头换面，我们通过在文档中补充说明，旧有的业务系统（如 Animagent 自动生成）只需要按照新格式包裹一层 `credentials` 对象，即可无缝对接新的接口。

目前，OpenClaw 微信发布模块已经拥有了作为独立基础设施组件的能力，为将来的开源打下了坚实基础。
"""

    payload = {
        "publish_type": "article",
        "title": "OpenClaw 微信服务：从私有状态到无状态的开源架构重构",
        "author": "OpenClaw AI",
        "digest": "我们如何重构微信公众号发布工具，将其改造为 100% 无状态、由调用方注资密钥的开源 API。",
        "cover_image_index": 1,
        "use_llm_parser": True, # Optimize the layout for WeChat
        "images_list": [
            {
                "image_index": 1,
                "image_type": "url",
                "image_url": "https://picsum.photos/900/500?random=1"
            }
        ],
        "article_markdown": article_markdown,
        "credentials": {
            "wx_appid": os.getenv("APPID"),
            "wx_secret": os.getenv("SECRET"),
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
            "openrouter_text_model": "google/gemini-2.5-flash"
        }
    }

    print("Sending publish request to remote server (via tunneled local port)...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    publish_article()
