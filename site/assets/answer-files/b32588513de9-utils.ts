/**
 * 轻量 className 合并工具。
 * 若项目中已存在同类工具（如 Skill 示例中的 @/lib/utils 的 cn），
 * 请直接替换为既有实现，无需保留本文件。
 */
export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");
}
