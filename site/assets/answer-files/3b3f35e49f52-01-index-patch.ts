/**
 * index.ts 补丁：新增 summarize-weather tool
 *
 * 遵循的 Skill 规则：
 * - server-and-widgets.md: server.tool() 定义模式，zod schema，annotations
 * - architecture.md: 动词开头命名，tool-only（无 widget），不重复数据
 * - csp-and-metadata.md: 外部 API 需在 CSP connectDomains 中声明
 * - setup.md: 使用 process.env 读取配置
 *
 * 注意：此文件展示新增部分。现有 get-weather tool 保持不变（向后兼容）。
 */

import { MCPServer, text, object } from "mcp-use/server";
import { z } from "zod";

const server = new MCPServer({
  name: "weather-app",
  version: "1.1.0",
  baseUrl: process.env.MCP_URL || "http://localhost:3000",
});

// 现有 tool（不修改，保持向后兼容）
server.tool(
  {
    name: "get-weather",
    description: "Get current weather for a city",
    schema: z.object({
      city: z.string().describe("City name"),
    }),
    annotations: { readOnlyHint: true },
  },
  async ({ city }) => {
    return object({ city, temperature: 22, condition: "sunny" });
  },
);

// 新增 tool: summarize-weather
// 架构决策（architecture.md Step 2）：纯文本输出 -> tool-only，不需要 widget
// 命名（architecture.md）：动词开头 "summarize-weather"
// 不重复（architecture.md）：get-weather 返回原始数据，此 tool 生成摘要

const SUMMARY_PROVIDER = {
  baseUrl: process.env.SUMMARY_API_BASE_URL || "",
  apiKey: process.env.SUMMARY_API_KEY || "",
  model: process.env.SUMMARY_MODEL || "default",
  timeoutMs: Number(process.env.SUMMARY_TIMEOUT_MS) || 10000,
};

server.tool(
  {
    name: "summarize-weather",
    description: "Generate a natural-language weather summary using an LLM provider",
    schema: z.object({
      city: z.string().describe("City name to summarize weather for"),
      model: z.string().optional().describe("Optional model override"),
      language: z.string().default("en").describe("Summary language code"),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
    },
  },
  async ({ city, model, language }) => {
    // 错误可诊断：缺失配置给出明确错误和修复指引
    if (!SUMMARY_PROVIDER.baseUrl) {
      return text(
        "summarize-weather is not configured: SUMMARY_API_BASE_URL is not set. " +
        "Set it in your environment or .env file.",
      );
    }
    if (!SUMMARY_PROVIDER.apiKey) {
      return text(
        "summarize-weather is not configured: SUMMARY_API_KEY is not set. " +
        "Set it in your environment or .env file.",
      );
    }

    const selectedModel = model || SUMMARY_PROVIDER.model;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), SUMMARY_PROVIDER.timeoutMs);

    try {
      // [占位符] URL 和请求格式需替换为实际提供方的 API 规范
      const response = await fetch(`${SUMMARY_PROVIDER.baseUrl}/v1/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${SUMMARY_PROVIDER.apiKey}`,
        },
        body: JSON.stringify({
          model: selectedModel,
          messages: [
            { role: "system", content: `You are a weather reporter. Respond in ${language}. Be concise.` },
            { role: "user", content: `Summarize the current weather in ${city}.` },
          ],
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorBody = await response.text().catch(() => "unknown error");
        return text(`Weather summary provider error (HTTP ${response.status}): ${errorBody.slice(0, 200)}`);
      }

      const data = await response.json();
      const summary = data?.choices?.[0]?.message?.content || "No summary available.";
      return text(summary);
    } catch (err: unknown) {
      clearTimeout(timeout);
      if (err instanceof Error && err.name === "AbortError") {
        return text(`Weather summary request timed out after ${SUMMARY_PROVIDER.timeoutMs}ms.`);
      }
      const message = err instanceof Error ? err.message : String(err);
      return text(`Weather summary failed: ${message}`);
    } finally {
      clearTimeout(timeout);
    }
  },
);

// CSP 说明（csp-and-metadata.md）：
// 如果 widget 需要直接调用外部 API，须在 widgetMetadata.metadata.csp.connectDomains 中声明。
// 本方案外部调用在 server 端完成，widget 无需直接访问外部 API。

export default server;
