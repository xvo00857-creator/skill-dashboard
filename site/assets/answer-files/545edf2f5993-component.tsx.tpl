"use dom";

// {{COMPONENT_NAME}}.tsx
// 由 use-dom Skill 脚手架生成，遵循 SKILL.md 规则：
//   1. 文件顶部必须有 "use dom" 指令
//   2. 单个默认导出
//   3. 独立文件（不与原生组件内联定义）
//   4. props 仅可序列化（string/number/boolean/array/plain object）
//   5. CSS 写在组件文件内（隔离上下文）

interface {{COMPONENT_NAME}}Props {
  /** 示例可序列化属性 */
  title?: string;
  /** 每个 DOM 组件都会收到 dom 属性，用于 webview 配置 */
  dom?: import("expo/dom").DOMProps;
}

const styles = {
  container: {
    padding: 20,
    backgroundColor: "#f5f5f5",
    borderRadius: 8,
  },
  title: {
    fontSize: 18,
    color: "#333",
    margin: 0,
  },
} as const;

export default function {{COMPONENT_NAME}}({
  title = "{{COMPONENT_NAME}}",
}: {{COMPONENT_NAME}}Props) {
  return (
    <div style={styles.container}>
      <h2 style={styles.title}>{title}</h2>
      <p>此组件运行在 DOM 环境中（Web 端直接渲染，原生端在 WebView 中渲染）。</p>
    </div>
  );
}
