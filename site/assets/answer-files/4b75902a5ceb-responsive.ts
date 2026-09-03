import { useWindowDimensions } from 'react-native';

/**
 * 响应式工具
 * 参考 react-native-design Skill / references/styling-patterns.md 的 Responsive Design
 *
 * 关键约束：使用 useWindowDimensions 而非 Dimensions.get('window')，
 * 以保证屏幕旋转 / 分屏时尺寸能实时更新（Skill 明确指出 Dimensions.get 可能过期）。
 */

export type Breakpoint = 'sm' | 'md' | 'lg' | 'xl';

export const breakpoints: Record<Breakpoint, number> = {
  sm: 0,
  md: 768,
  lg: 1024,
  xl: 1280,
};

export function useBreakpoint(): Breakpoint {
  const { width } = useWindowDimensions();
  if (width >= breakpoints.xl) return 'xl';
  if (width >= breakpoints.lg) return 'lg';
  if (width >= breakpoints.md) return 'md';
  return 'sm';
}

/**
 * 按断点取值；当前断点未提供时向下回退到最近的已定义断点。
 */
export function useResponsiveValue<T>(
  values: Partial<Record<Breakpoint, T>>
): T | undefined {
  const breakpoint = useBreakpoint();
  const order: Breakpoint[] = ['xl', 'lg', 'md', 'sm'];
  const start = order.indexOf(breakpoint);
  for (let i = start; i < order.length; i++) {
    const v = values[order[i]];
    if (v !== undefined) return v;
  }
  return undefined;
}

/**
 * 基于设计稿基准宽度 375（iPhone 标准）的等比缩放。
 * 注意：仅用于需要严格等比的装饰性尺寸；间距/字号优先用主题 token。
 */
const guidelineBaseWidth = 375;
const guidelineBaseHeight = 812;

export const scale = (size: number, screenWidth: number) =>
  (screenWidth / guidelineBaseWidth) * size;

export const verticalScale = (size: number, screenHeight: number) =>
  (screenHeight / guidelineBaseHeight) * size;

export const moderateScale = (
  size: number,
  screenWidth: number,
  factor = 0.5
) => size + (scale(size, screenWidth) - size) * factor;
