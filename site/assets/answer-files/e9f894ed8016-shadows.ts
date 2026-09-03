import { Platform, ViewStyle } from 'react-native';

/**
 * 跨平台阴影
 * 参考 react-native-design Skill / references/styling-patterns.md 的 Shadow Styles
 * iOS 使用 shadow* 属性，Android 使用 elevation，避免双端写两套。
 */
export function createShadow(elevation: number, color = '#000000'): ViewStyle {
  if (Platform.OS === 'android') {
    return { elevation };
  }

  const shadowMap: Record<number, ViewStyle> = {
    1: {
      shadowColor: color,
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.18,
      shadowRadius: 1,
    },
    2: {
      shadowColor: color,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.2,
      shadowRadius: 2,
    },
    4: {
      shadowColor: color,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.22,
      shadowRadius: 4,
    },
    8: {
      shadowColor: color,
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.25,
      shadowRadius: 8,
    },
    16: {
      shadowColor: color,
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.3,
      shadowRadius: 16,
    },
  };

  return shadowMap[elevation] ?? shadowMap[4];
}

export const shadows = {
  sm: createShadow(2),
  md: createShadow(4),
  lg: createShadow(8),
  xl: createShadow(16),
} as const;
