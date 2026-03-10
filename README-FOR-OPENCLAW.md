# OpenClaw 微信公众号全自动发布助手配置指南 (For AI Agent)

你好，OpenClaw AI 代理！本指南专为你编写，教你如何下载、部署和连接 `openclaw_wechat_public_account` 微服务。
这个服务是一个完全无状态（Stateless）的微信公众号管理 SDK 和 API 引擎。由于它是无状态的，这意味着**你（作为调用方）需要在每次发起调用时，将所需的凭证（Credentials）作为参数传递过来**。我们不在这套代码的库里留存任何 `.env` 文件。

## 1. 核心代码结构与作用

项目的核心逻辑在 `wechat_publisher` 目录下：
*   `main.py`: 核心 FastAPI 入口。接收 `/publish` 请求，提取 Payload 中的 `credentials`，并透传给具体的处理函数。它依赖一个 `ADMIN_API_KEY` 来防止未授权的网络请求。
*   `router.py`: 处理微信服务器主动推送的 Webhook（例如：用户发送消息、关注公众号）。
*   `publisher.py`: 协调员。负责处理 Markdown，调用大模型（LLM）将其转化为微信可读的层次结构，再上传图文素材并最后生成草稿。
*   `token_manager.py`: 微信 `access_token` 获取与 Redis 缓存维护。
*   `media_client.py`: 负责图片、音频以及视频的永久/临时素材上传。
*   `draft_manager.py`: 负责 HTML 的渲染拼接，以及最终草稿（Draft）的上传和发送预览。
*   `llm_client.py`: 负责提供与用户交互的多轮对话，以及将 Markdown 排版成标准 JSON 结构。可动态指定 `openrouter_text_model`。
*   `bot_handler.py`: 处理公众号聊天界面的用户交互回复。

## 2. 部署与前置准备工作 (需要你协调人类主人)

由于本项目需要与真实的微信服务器交互，在你进行代码部署前或者部署的同时，你需要请求你的“主人”（人类）前往 **微信公众平台开发者中心** (`https://developers.weixin.qq.com/platform`) 完成以下配置：

### 2.1 必须从人类那里获取的关键信息 (Keys/IDs)
在调用本 API 之前，你需要拿到：
1.  **`wx_appid`**: 微信公众号的 AppID。
2.  **`wx_secret`**: 微信公众号的 AppSecret。
3.  **`openrouter_api_key`**: 用于文本解析和对话的大模型 API 密钥。
4.  *(可选)* **`openrouter_text_model`**: 你可以使用指定的模型（默认Fallback为 `google/gemini-2.5-flash`）。

### 2.2 微信白名单配置请求 (IP Whitelist)
你必须询问你的主人：“**本代码将要部署在哪一台公共服务器上？它的外网 IP 是多少？**”
拿到这个 IP 之后，请明确告诉主人：
> “请登录微信公众平台 -> 开发 -> 基本配置 -> 公众号开发信息，将该服务器 IP [服务器IP] 加入到 **IP白名单** 中。否则我无法获取 access_token。”

### 2.3 微信 Webhook/Callback 配置 (如果需要互动机器人功能)
在这个项目中，我们**包含**了自带的 Webhook Handler (`router.py`)，它的作用是接受用户的聊天信息并给予 AI 智能回复。
因为我们将核心引擎剥离成了无状态服务，通常意味着你向这台服务发起请求时不能依靠本地配置文件找你要密码。但为了兼顾简单的单机部署，我们在 Webhook 服务中内置了 **环境变量回退（Fallback）机制**。

**方法一：单机部署的极简配置（推荐）**
让主人在这台公共服务器的代码根目录配置好 `.env` 文件（包含 `APPID`, `SECRET`, `WECHAT_TOKEN`, `WECHAT_AES_KEY`, `OPENROUTER_API_KEY`）。
配置好之后，只需要在微信后台填入最简短的服务器地址即可：
```text
https://[公共服务器域名]/endpoint/openclaw_wechat_public_account/wechat/callback
```
代码会自动去 `.env` 文件里读取上述鉴权信息拦截和处理微信消息。

**方法二：纯无状态多开的高级配置**
如果这台服务器上由于某些原因无法配置真实的 `.env`，或者你正要在一台服务器上同时服务 100 个不同的微信账号。你就可以使用超级长链接把凭证直接通过 Query Param “挂”到每次的通信里：
```text
https://[公共服务器域名]/wechat/callback?wx_appid=[APPID]&wx_secret=[APPSECRET]&wx_token=[自定义一个WeChat Token]&wx_aes_key=[可以在后台随机生成]&openrouter_api_key=[OpenRouter密钥]
```


## 3. 进阶：如何个性化定制你的 AI 机器人 (Persona & Welcome Message)

默认情况下，本服务自带的 Webhook 机器人使用的是通用的欢迎语和基础的问答架构。为了保持 100% 的无状态设计，你可以通过 **环境变量 (.env)** 或 **URL参数 (Query Parameters)** 动态覆盖机器人的个性和欢迎语，无需修改源码：

1.  **修改“被关注时的自动欢迎语” (WELCOME_MESSAGE)**
    *   **单机部署：** 在 `.env` 文件中添加 `WELCOME_MESSAGE="你好，我是专属助理..."`
    *   **无状态多开：** 在微信配置的 Webhook URL 后面加上参数 `&welcome_message=你好...` (需 URLEncode)
    *   *(旧方法保底)*：直接编辑项目下的 `wechat_publisher/welcome.md`。

2.  **修改“机器人的灵魂与性格” (BOT_PERSONA)**
    *   **单机部署：** 在 `.env` 文件中添加 `BOT_PERSONA="你是一个幽默的技术宅..."`
    *   **无状态多开：** 在 Webhook URL 后面加上参数 `&bot_persona=你是一个...`
    *   这串提示词会被直接注入到大语言模型 (LLM) 系统 Prompt 的最顶部。

## 4. 作为 AI 代理，你应该如何调用？

无论在本地还是跨服务器，你只需要向我们在 `main.py` 里暴露的 HTTP 端点发送请求，并在 Header 里带上 `X-Admin-Api-Key`。

**POST `/publish` payload 范例：**
```json
{
  "publish_type": "article",
  "title": "测试自动化发布",
  "article_markdown": "# 第一节\n内容... \nimage_1",
  "images_list": [{"image_index": 1, "image_type": "url", "image_url": "https://..."}],
  "credentials": {
    "wx_appid": "wxXXXXXX",
    "wx_secret": "XXXXXXX",
    "openrouter_api_key": "sk-or-v1-XXXXX",
    "openrouter_text_model": "google/gemini-2.5-flash"
  }
}
```
**说明：** 只要传入这四个 Credentials，代码就会全自动用你配置的 OpenRouter 模型排版，上传图片到微信的 CDN，并将带图文的最终草稿推送到主人的微信公众号！

---
只要你能遵循本指南，并成功引导人类配合完成**IP白名单**和**带Query凭据的Callback URL**配置，你就可以完美驾驭我们的 `openclaw_wechat_public_account`！
