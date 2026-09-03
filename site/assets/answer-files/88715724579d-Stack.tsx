import React from 'react';
import { View, ViewStyle, StyleProp } from 'react-native';

export interface StackProps {
  children: React.ReactNode;
  spacing?: number;
  style?: StyleProp<ViewStyle>;
}

/**
 * 垂直堆叠。使用 gap 实现间距（RN 0.71+ 支持），避免在子元素上插 margin。
 */
export const VStack = React.memo(function VStack({
  children,
  spacing = 8,
  style,
}: StackProps) {
  return <View style={[{ gap: spacing }, style]}>{children}</View>;
});

/**
 * 水平排列，默认垂直居中对齐。
 */
export const HStack = React.memo(function HStack({
  children,
  spacing = 8,
  style,
}: StackProps) {
  return (
    <View style={[{ flexDirection: 'row', alignItems: 'center', gap: spacing }, style]}>
      {children}
    </View>
  );
});

export interface SpacerProps {
  /** 固定尺寸（宽高相等） */
  size?: number;
  /** 弹性占位，与 flex:1 等价 */
  flex?: number;
}

export const Spacer = React.memo(function Spacer({ size, flex }: SpacerProps) {
  if (flex !== undefined) {
    return <View style={{ flex }} />;
  }
  return <View style={{ height: size, width: size }} />;
});
