# 微信公众号发布后端 SDK 核心逻辑流程说明书 (Process Logic)

本文档详细描述了 `wechat-public-account` 服务如何处理一个发布请求，从接收数据到最终生成微信草稿的全过程。

## 1. 总体架构

服务核心由 FastAPI 提供 HTTP 接口，内部调用 `wechat_publisher` SDK。SDK 主要协调三个核心模块：
- **MediaClient**: 负责与微信服务器交互，上传图片资源。
- **LLMClient**: 负责调用 OpenRouter (Google Gemini)，进行文本结构化处理。
- **DraftManager**: 负责 HTML 渲染和草稿箱接口调用。

---

## 2. 详细执行流程

当客户端向 `/publish` 接口发送 POST 请求时，系统依次执行以下步骤：

### 第一步：接收与校验 (Request Handling)
*   **输入**: API 接收 JSON 数据，包含 `title` (标题), `author` (作者), `article_markdown` (文章 Markdown 源码), `images_list` (图片列表), `cover_image_index` (封面图索引)。
*   **Auth 校验**: 系统首先检查 Header 中的 `X-Admin-Api-Key` 是否与服务器 `.env` 文件中的配置一致。
*   **参数校验**: 确认 `cover_image_index` 指向的图片确实存在于 `images_list` 中。

### 第二步：图片资源上传 (Image Processing)
在此阶段，系统遍历 `images_list`，将所有图片上传到微信服务器，获取微信专用的 URL 或 Media ID。

1.  **处理正文插图 (Body Images)**:
    *   遍历列表中的每一张图片。
    *   **下载/解码**: 如果是 URL，下载图片二进制数据；如果是 Base64，解码还原。
    *   **压缩**: 检查图片大小，如果超过限制 (2MB)，自动进行压缩处理。
    *   **MD5 去重**: 计算图片 Hash 值，查询 Redis 缓存。如果该图片之前传过，直接返回缓存的微信 URL，避免重复上传。
    *   **上传**: 调用微信 `media/uploadimg` 接口。
    *   **输出**: 获得一个 HTTP 格式的微信图片链接 (`http://mmbiz.qpic.cn/...`)。我们将这个链接保存在一个映射表 `image_url_map` 中 (Key: 图片 index, Value: 微信 URL)。

2.  **处理封面图 (Cover Image)**:
    *   找到 `cover_image_index` 对应的图片。
    *   **上传**: 尝试调用微信 `material/add_material` (永久素材) 接口。
    *   **Fallback 机制**: 如果永久素材上传失败 (例如 API 权限不足 `48001` 或素材库满了)，系统会自动降级，调用 `media/upload` (临时素材) 接口。
    *   **输出**: 获得一个 `media_id` (封面必须使用 Media ID，不能用 URL)。

### 第三步：LLM 结构化转换 (LLM Processing)
这是最关键的一步。原始 Markdown 很难直接通过正则完美转换为微信复杂的 HTML。我们使用大模型来做“排版理解”。

*   **输入**: 原始 `article_markdown` 文本。
*   **Prompt 设定**: 设定 System Prompt 为 "微信公众号排版专家"，要求将 Markdown 解析为特定的 JSON 结构。
*   **模型调用**: 通过 OpenRouter 调用 `google/gemini-2.5-flash` 模型。
*   **结构化输出**: 模型返回一个 JSON 数组，将文章拆解为：
    *   `{"type": "header", "level": 1, "content": "..."}`
    *   `{"type": "paragraph", "content": "..."}`
    *   `{"type": "image", "content": "image_1"}` (保留占位符)
    *   `{"type": "quote", "content": "..."}`
*   **优势**: 这种方式能智能识别引用块、列表，并且即使 Mardkown 语法不规范，AI 也能理解语义进行正确拆分。

## 4. Workflows

### 4.1 Email Approval Flow (Recommended)
This workflow ensures human review before public release.

1.  **Request**: User calls `/publish` with `preview_email="..."` and `auto_publish=False`.
2.  **Draft Creation**: 
    *   System uploads images.
    *   System structures Markdown via LLM.
    *   System generates HTML.
    *   System calls `draft/add` to create WeChat draft.
3.  **Link Retrieval**: System calls `draft/get` (or `batchget`) to find the permanent URL of the newly created draft.
4.  **Email Notification**:
    *   System constructs an HTML email.
    *   **"View Draft"**: Links to the valid WeChat draft URL.
    *   **"Publish Now"**: Links to `https://animagent.ai/api/weixin-publish/approve?media_id=...&key=...`.
    *   Email is sent via internal Gmail service.
5.  **Approval**:
    *   User clicks "Publish Now" in email.
    *   Server receives request at `/approve`.
    *   Server validates `key`.
    *   Server calls `freepublish/submit` with the `media_id`.
6.  **Result**: Article published.

### 4.2 Direct Publish Flow
1.  **Request**: User calls `/publish` with `auto_publish=True`.
2.  **Draft Creation**: (Same as above).
3.  **Immediate Publish**: System immediately calls `freepublish/submit`.
4.  **Result**: Article published (pending audit).

## 5. Token Management Strategy

### 5.1 Dual-Layer Caching
To ensure reliability and minimize API calls, the `TokenManager` uses a dual-layer strategy:
1.  **Local File (`access_token.json`)**: Persisted on disk for single-instance or CLI usage.
2.  **Redis Cache**: Shared across containers if Redis is available.

### 5.2 Expiration & Safety Buffer
WeChat Access Tokens are valid for **7200 seconds (2 hours)**.
To prevent edge-case failures (e.g., clock skew, network latency), we enforce a **strict 10-minute safety buffer**:
*   Effective Validity: **110 minutes** (6600 seconds).
*   Buffer: **600 seconds**.

If the current time is within this 10-minute buffer window of the expiration, the system proactively treats the token as expired and fetches a new one.

### 第四步：HTML 渲染 (HTML Rendering)
`DraftManager` 接收 JSON 结构数据，将其拼装成 HTML 字符串。

1.  **注入容器**: 给整篇文章包裹一个基础 `div`，设置微信标准的字体 (PingFang SC, Helvetica 等) 和字间距。
2.  **元素遍历**: 逐个处理 JSON 节点。
    *   **Header**: 渲染 `<h1/h2>`，并添加内联样式 (font-size, font-weight, margin)。
    *   **Paragraph**: 渲染 `<p>`，添加行高 (line-height: 1.6) 和对齐样式。
    *   **Image**: 
        *   当遇到 `content` 为 `image_{n}` 的节点时，解析出索引 `n`。
        *   从 **第二步** 生成的 `image_url_map` 中查找对应的微信 URL。
        *   生成 `<img src="微信URL" />` 标签，并加上样式 (width: 100%, border-radius 等)。
        *   **关键点**: 这里完成了将“本地/网络图片”替换为“微信合法图片”的过程。
3.  **结果**: 生成一段完整的、带内联样式的 HTML 字符串。

### 第五步：创建草稿 (Draft Creation)
*   **组装 Payload**: 将 标题、作者、摘要、**封面 Media ID** 以及 **渲染好的 HTML** 组合。
*   **编码修正**: 在序列化 JSON 时，强制使用 `ensure_ascii=False` 并手动 encode 为 UTF-8。这是为了防止中文被转义成 `\uXXXX` 格式，确保微信后台能正确显示汉字。
*   **调用 API**: 请求微信 `draft/add` 接口。
*   **结果**: 微信返回一个新的 `draft_media_id`。

### 第六步：发布 (Optional Publish)
*   如果请求参数 `auto_publish=True`，系统会继续利用 `draft_media_id` 调用 `freepublish/submit` 接口。
*   **注意**: 这里的发布通常是“发布声明”（如果不推送到粉丝手机），或者根据微信后台策略而定。默认建议设为 `False`，人工在后台检查草稿后再群发。

---

## 3. 异常处理
*   **网络重试**: 图片下载和 OpenRouter 调用均由于网络库支持自动重试。
*   **权限降级**: 封面图上传有自动降级机制。
*   **日志记录**: 全程记录 Info/Error 日志，方便 Docker logs 排查。
