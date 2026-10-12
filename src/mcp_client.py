"""麦当劳 MCP 客户端（Streamable HTTP + Bearer Token）。

仅实现本项目所需的最小 JSON-RPC 子集：
- initialize（握手）
- tools/list（列出工具）
- tools/call（调用工具并解析返回内容）

设计约束：
- 只封装传输，不缓存、不伪造任何业务数据；
- 所有网络失败都会抛出 MCPError，由上层决定降级；
- 限流（429）时按指数退避重试，请求之间串行，避免打满 600 次/分钟额度。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-03-26"
USER_AGENT = "mcd-annual-report/1.0"


class MCPError(Exception):
    """MCP 通信或协议错误。"""


class McDonaldsMCP:
    """麦当劳 MCP 最小客户端。"""

    def __init__(
        self,
        token: str,
        url: str = DEFAULT_URL,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        if not token or not token.strip():
            raise MCPError("MCP Token 不能为空")
        self._token = token.strip()
        self._url = url
        self._timeout = timeout
        self._max_retries = max_retries
        self._session_id: Optional[str] = None
        self._initialized = False
        self._rpc_id = 0

    # ------------------------------------------------------------------ #
    # 协议层
    # ------------------------------------------------------------------ #

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    def _post(self, payload: dict) -> dict:
        """发送一次 JSON-RPC 请求，返回解析后的响应对象。"""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self._token}",
            "User-Agent": USER_AGENT,
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        req = urllib.request.Request(self._url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self._session_id = sid
                raw = resp.read().decode("utf-8", errors="replace")
                content_type = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            if e.code == 401:
                raise MCPError("MCP Token 无效或已过期（401），请检查 MCD_MCP_TOKEN") from e
            if e.code == 429:
                raise MCPError("触发限流（429），请降低调用频率") from e
            raise MCPError(f"HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise MCPError(f"网络错误：{e.reason}") from e

        if "text/event-stream" in content_type:
            return self._parse_sse(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise MCPError(f"响应不是合法 JSON：{raw[:200]}") from e

    @staticmethod
    def _parse_sse(raw: str) -> dict:
        """从 SSE 流中取出最后一个带 id 的 data 事件。"""
        last: Optional[dict] = None
        for line in raw.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "id" in obj:
                last = obj
        if last is None:
            raise MCPError("SSE 响应中未找到 JSON-RPC 消息")
        return last

    def _rpc(self, method: str, params: Optional[dict] = None) -> Any:
        """发起一次请求并做限流退避重试，返回 result 字段。"""
        payload: dict = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            payload["params"] = params

        delay = 1.0
        for attempt in range(1, self._max_retries + 1):
            resp = self._post(payload)
            if "error" in resp:
                err = resp["error"]
                # 限流类错误退避重试
                code = err.get("code") if isinstance(err, dict) else None
                if code in (-32000, 429) or (isinstance(err, dict) and "rate" in str(err).lower()):
                    if attempt < self._max_retries:
                        time.sleep(delay)
                        delay *= 2
                        continue
                raise MCPError(f"MCP 错误 {code}: {err.get('message') if isinstance(err, dict) else err}")
            return resp.get("result")
        raise MCPError("请求重试次数用尽")

    # ------------------------------------------------------------------ #
    # MCP 语义层
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        if self._initialized:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcd-annual-report", "version": "1.0.0"},
            },
        )
        # 初始化完成通知（无 id，不关心响应）
        try:
            body = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode()
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": USER_AGENT,
            }
            if self._session_id:
                headers["mcp-session-id"] = self._session_id
            req = urllib.request.Request(self._url, data=body, headers=headers, method="POST")
            urllib.request.urlopen(req, timeout=self._timeout).read()
        except Exception:
            pass  # 通知失败不影响主流程
        self._initialized = True

    def list_tools(self) -> list[dict]:
        self.initialize()
        result = self._rpc("tools/list")
        tools = (result or {}).get("tools", [])
        return tools if isinstance(tools, list) else []

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        """调用工具，返回 content 中第一个 text 段落解析后的 JSON（解析失败则返回原文）。"""
        self.initialize()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if not isinstance(result, dict):
            return result
        if result.get("isError"):
            texts = [c.get("text", "") for c in result.get("content", []) if isinstance(c, dict)]
            raise MCPError(f"工具 {name} 返回错误：{' | '.join(texts)[:300]}")
        for block in result.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    return text
        return result

    def close(self) -> None:  # pragma: no cover - 无持久连接，预留接口
        self._initialized = False
        self._session_id = None
