import React, { useCallback } from 'react';
import {
  View,
  Image,
  StyleSheet,
  Pressable,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { useTheme } from '../theme/theme';
import { createShadow } from '../theme/shadows';
import { Text } from './Text';

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

export interface ItemCardProps {
  title: string;
  subtitle: string;
  imageUrl: string;
  onPress: () => void;
  /** 图片高度，默认 160；响应式场景下可由父组件按断点传入 */
  imageHeight?: number;
  accessibilityLabel?: string;
}

/**
 * 图文卡片
 * 直接采用 SKILL.md「Quick Start Component」的按压缩放模式，
 * 并补充：React.memo / useCallback（Best Practice #2）、
 * createShadow 双端阴影（iOS shadow / Android elevation，Best Practice #8）、无障碍属性。
 */
function ItemCardComponent({
  title,
  subtitle,
  imageUrl,
  onPress,
  imageHeight = 160,
  accessibilityLabel,
}: ItemCardProps) {
  const theme = useTheme();
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const handlePressIn = useCallback(() => {
    scale.value = withSpring(0.97);
  }, [scale]);

  const handlePressOut = useCallback(() => {
    scale.value = withSpring(1);
  }, [scale]);

  return (
    <AnimatedPressable
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.background,
          borderRadius: theme.borderRadius.lg,
        },
        createShadow(4),
        animatedStyle,
      ]}
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? `${title}，${subtitle}`}
    >
      <Image
        source={{ uri: imageUrl }}
        style={[styles.image, { height: imageHeight, backgroundColor: theme.colors.surface }]}
      />
      <View style={[styles.content, { gap: theme.spacing.xs }]}>
        <Text variant="h3" color="text" numberOfLines={1}>
          {title}
        </Text>
        <Text variant="bodySmall" color="textSecondary" numberOfLines={2}>
          {subtitle}
        </Text>
      </View>
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  card: {
    overflow: 'hidden',
  },
  image: {
    width: '100%',
  },
  content: {
    padding: 16,
  },
});

export const ItemCard = React.memo(ItemCardComponent);
ItemCard.displayName = 'ItemCard';
