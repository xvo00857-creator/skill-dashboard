import React, { useState } from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, ShowcaseScreen } from './src';

/**
 * 接入示例（非既有项目文件，仅说明如何挂载）。
 * 既有项目接入时：
 * 1. 确认已安装 react-native-reanimated、react-native-safe-area-context（Reanimated 3 需 babel 插件配置）
 * 2. 在应用根部包一层 SafeAreaProvider（若已有则不要重复包裹）
 * 3. 用 ThemeProvider 包裹页面，mode 默认跟随系统
 */
export default function App() {
  const [isDark, setIsDark] = useState(false);

  return (
    <SafeAreaProvider>
      <ThemeProvider mode={isDark ? 'dark' : 'light'}>
        <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
        <ShowcaseScreen
          isDark={isDark}
          onToggleTheme={() => setIsDark((v) => !v)}
        />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
