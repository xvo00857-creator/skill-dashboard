import React from 'react';
import { View, ViewStyle, StyleProp, StyleSheet } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../theme/theme';

export interface ContainerProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  /** 需要应用安全区内边距的边，默认上下 */
  edges?: Array<'top' | 'bottom' | 'left' | 'right'>;
}

/**
 * 安全区容器
 * 参考 react-native-design Skill Best Practice #5：使用 useSafeAreaInsets 处理刘海/挖孔屏。
 * 背景色取自主题，保证深色模式下不留白边。
 */
function ContainerComponent({
  children,
  style,
  edges = ['top', 'bottom'],
}: ContainerProps) {
  const insets = useSafeAreaInsets();
  const theme = useTheme();

  return (
    <View
      style={StyleSheet.flatten([
        {
          flex: 1,
          backgroundColor: theme.colors.background,
          paddingTop: edges.includes('top') ? insets.top : 0,
          paddingBottom: edges.includes('bottom') ? insets.bottom : 0,
          paddingLeft: edges.includes('left') ? insets.left : 0,
          paddingRight: edges.includes('right') ? insets.right : 0,
        },
        style,
      ])}
    >
      {children}
    </View>
  );
}

export const Container = React.memo(ContainerComponent);
Container.displayName = 'Container';
