import React from 'react';
import {
  Text as RNText,
  TextStyle,
  StyleProp,
  TextProps as RNTextProps,
  StyleSheet,
} from 'react-native';
import { useTheme } from '../theme/theme';

type Variant = 'h1' | 'h2' | 'h3' | 'body' | 'bodySmall' | 'caption' | 'label';
type ColorName =
  | 'primary'
  | 'secondary'
  | 'text'
  | 'textSecondary'
  | 'error'
  | 'success';
type Weight = 'normal' | 'medium' | 'semibold' | 'bold';
type Align = 'left' | 'center' | 'right';

export interface TextProps extends RNTextProps {
  variant?: Variant;
  color?: ColorName;
  weight?: Weight;
  align?: Align;
}

const variantStyles: Record<Variant, TextStyle> = {
  h1: { fontSize: 32, lineHeight: 40, fontWeight: '700' },
  h2: { fontSize: 24, lineHeight: 32, fontWeight: '600' },
  h3: { fontSize: 20, lineHeight: 28, fontWeight: '600' },
  body: { fontSize: 16, lineHeight: 24, fontWeight: '400' },
  bodySmall: { fontSize: 14, lineHeight: 20, fontWeight: '400' },
  caption: { fontSize: 12, lineHeight: 16, fontWeight: '400' },
  label: { fontSize: 14, lineHeight: 20, fontWeight: '500' },
};

const weightStyles: Record<Weight, TextStyle> = {
  normal: { fontWeight: '400' },
  medium: { fontWeight: '500' },
  semibold: { fontWeight: '600' },
  bold: { fontWeight: '700' },
};

function TextComponent({
  variant = 'body',
  color = 'text',
  weight,
  align,
  style,
  ...props
}: TextProps) {
  const theme = useTheme();
  return (
    <RNText
      style={StyleSheet.flatten([
        variantStyles[variant],
        { color: theme.colors[color] },
        weight ? weightStyles[weight] : null,
        align ? { textAlign: align } : null,
        style,
      ])}
      {...props}
    />
  );
}

/**
 * 文本组件
 * 参考 react-native-design Skill / references/styling-patterns.md 的 Typography System
 * 使用 React.memo 避免不必要的重渲染（Skill Best Practice #2）。
 */
export const Text = React.memo(TextComponent);
Text.displayName = 'Text';
