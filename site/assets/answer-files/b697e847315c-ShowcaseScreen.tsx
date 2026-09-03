import React, { useState, useCallback } from 'react';
import { View, StyleSheet, FlatList, ListRenderItem } from 'react-native';
import { Container } from '../components/Container';
import { VStack, HStack, Spacer } from '../components/Stack';
import { Text } from '../components/Text';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { ItemCard } from '../components/ItemCard';
import { useResponsiveValue } from '../theme/responsive';
import { useTheme } from '../theme/theme';

/**
 * 以下为组件演示用的示例数据，非真实业务数据。
 * 图片使用 placehold.co 占位图，真机运行需联网；离线时图片区域显示主题底色。
 */
interface DemoItem {
  id: string;
  title: string;
  subtitle: string;
  imageUrl: string;
}

const DEMO_ITEMS: DemoItem[] = [
  { id: '1', title: '示例卡片一', subtitle: '这是一段用于演示两行截断的副标题文案。', imageUrl: 'https://placehold.co/600x400/6366f1/ffffff?text=1' },
  { id: '2', title: '示例卡片二', subtitle: '按下时卡片会有弹簧缩放反馈。', imageUrl: 'https://placehold.co/600x400/8b5cf6/ffffff?text=2' },
  { id: '3', title: '示例卡片三', subtitle: '网格列数随屏幕宽度自适应。', imageUrl: 'https://placehold.co/600x400/ec4899/ffffff?text=3' },
  { id: '4', title: '示例卡片四', subtitle: '平板上自动变为两列，大屏三列。', imageUrl: 'https://placehold.co/600x400/10b981/ffffff?text=4' },
  { id: '5', title: '示例卡片五', subtitle: '深色模式下颜色自动切换。', imageUrl: 'https://placehold.co/600x400/f59e0b/ffffff?text=5' },
  { id: '6', title: '示例卡片六', subtitle: '所有样式来自主题 token。', imageUrl: 'https://placehold.co/600x400/3b82f6/ffffff?text=6' },
];

export interface ShowcaseScreenProps {
  /** 由外层 ThemeProvider 控制；这里仅用于演示切换按钮 */
  isDark: boolean;
  onToggleTheme: () => void;
}

/**
 * 组件演示页
 * - 响应式：列数与卡片图高随断点变化（useResponsiveValue）
 * - 列表：使用 FlatList（Skill Best Practice #7），numColumns 实现网格
 * - 交互态：按钮按压缩放 / 输入框聚焦与错误 / 卡片按压反馈
 */
export function ShowcaseScreen({ isDark, onToggleTheme }: ShowcaseScreenProps) {
  const theme = useTheme();
  const [email, setEmail] = useState('');
  const [showError, setShowError] = useState(false);
  const [loading, setLoading] = useState(false);

  // 响应式列数：手机 1 列 / 平板 2 列 / 大屏 3 列
  const numColumns = useResponsiveValue<number>({ sm: 1, md: 2, lg: 3, xl: 4 }) ?? 1;
  // 响应式图片高度
  const imageHeight = useResponsiveValue<number>({ sm: 160, md: 140, lg: 160 }) ?? 160;
  // 响应式卡片间距
  const gap = useResponsiveValue<number>({ sm: 12, md: 16 }) ?? 12;

  const handleSubmit = useCallback(() => {
    if (!email.includes('@')) {
      setShowError(true);
      return;
    }
    setShowError(false);
    setLoading(true);
    setTimeout(() => setLoading(false), 1500);
  }, [email]);

  const renderItem = useCallback<ListRenderItem<DemoItem>>(
    ({ item }) => (
      <View style={{ flex: 1, margin: gap / 2 }}>
        <ItemCard
          title={item.title}
          subtitle={item.subtitle}
          imageUrl={item.imageUrl}
          imageHeight={imageHeight}
          onPress={() => {
            // 演示用：实际项目中接入 navigation.navigate('Detail', { id: item.id })
          }}
        />
      </View>
    ),
    [gap, imageHeight]
  );

  const keyExtractor = useCallback((item: DemoItem) => item.id, []);

  return (
    <Container edges={['top', 'left', 'right']}>
      <FlatList
        data={DEMO_ITEMS}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        key={`cols-${numColumns}`}
        numColumns={numColumns}
        contentContainerStyle={{
          padding: theme.spacing.md,
          paddingBottom: theme.spacing.xl,
        }}
        ListHeaderComponent={
          <VStack spacing={theme.spacing.md} style={{ marginBottom: theme.spacing.md }}>
            <HStack>
              <Text variant="h1" color="text">组件演示</Text>
              <Spacer flex={1} />
              <Button
                title={isDark ? '浅色' : '深色'}
                variant="ghost"
                size="sm"
                onPress={onToggleTheme}
                accessibilityLabel="切换深浅色模式"
              />
            </HStack>

            <Input
              label="邮箱"
              placeholder="请输入邮箱地址"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              error={showError ? '邮箱格式不正确' : undefined}
            />

            <HStack spacing={8} style={{ flexWrap: 'wrap' }}>
              <Button title="主要按钮" onPress={handleSubmit} loading={loading} />
              <Button title="次要" variant="outlined" onPress={() => {}} />
              <Button title="禁用" variant="filled" disabled onPress={() => {}} />
            </HStack>
          </VStack>
        }
      />
    </Container>
  );
}
