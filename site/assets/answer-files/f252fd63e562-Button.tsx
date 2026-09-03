import React, { useCallback } from 'react';
import {
  Pressable,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  StyleProp,
  View,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { useTheme } from '../theme/theme';
import { Text } from './Text';

type Variant = 'filled' | 'outlined' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

export interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
}

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

const sizeConfig = {
  sm: { paddingVertical: 8, paddingHorizontal: 12, fontSize: 14 },
  md: { paddingVertical: 12, paddingHorizontal: 16, fontSize: 16 },
  lg: { paddingVertical: 16, paddingHorizontal: 24, fontSize: 18 },
} as const;

/**
 * 按钮
 * 参考 react-native-design Skill / references/styling-patterns.md 的 Button Styles
 * 与 SKILL.md Quick Start 的按压缩放模式：
 * - Reanimated worklet 在 UI 线程执行 withSpring，保证 60fps（Best Practice #3）
 * - 完整交互态：默认 / 按下缩放 / disabled / loading
 * - 不引入新依赖，仅使用 react-native + react-native-reanimated
 */
function ButtonComponent({
  title,
  onPress,
  variant = 'filled',
  size = 'md',
  disabled = false,
  loading = false,
  leftIcon,
  rightIcon,
  style,
  accessibilityLabel,
}: ButtonProps) {
  const theme = useTheme();
  const scale = useSharedValue(1);

  // useAnimatedStyle 返回的 worklet 运行在 UI 线程
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const handlePressIn = useCallback(() => {
    scale.value = withSpring(0.97);
  }, [scale]);

  const handlePressOut = useCallback(() => {
    scale.value = withSpring(1);
  }, [scale]);

  const isInactive = disabled || loading;
  const sz = sizeConfig[size];

  const variantStyle: ViewStyle =
    variant === 'filled'
      ? { backgroundColor: theme.colors.primary }
      : variant === 'outlined'
      ? {
          backgroundColor: 'transparent',
          borderWidth: 1,
          borderColor: theme.colors.primary,
        }
      : { backgroundColor: 'transparent' };

  const textColor =
    variant === 'filled' ? '#ffffff' : theme.colors.primary;

  return (
    <AnimatedPressable
      style={[
        styles.base,
        variantStyle,
        {
          paddingVertical: sz.paddingVertical,
          paddingHorizontal: sz.paddingHorizontal,
          opacity: isInactive ? 0.5 : 1,
        },
        animatedStyle,
        style,
      ]}
      onPress={onPress}
      onPressIn={isInactive ? undefined : handlePressIn}
      onPressOut={isInactive ? undefined : handlePressOut}
      disabled={isInactive}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: isInactive, busy: loading }}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <View style={styles.content}>
          {leftIcon}
          <Text
            variant="label"
            style={{
              color: textColor,
              fontSize: sz.fontSize,
              fontWeight: '600',
              marginHorizontal: leftIcon || rightIcon ? 8 : 0,
            }}
          >
            {title}
          </Text>
          {rightIcon}
        </View>
      )}
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});

export const Button = React.memo(ButtonComponent);
Button.displayName = 'Button';
