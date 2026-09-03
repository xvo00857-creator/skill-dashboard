import React, { createContext, useContext, useMemo } from 'react';
import { useColorScheme } from 'react-native';

/**
 * 主题定义
 * 参考 react-native-design Skill / references/styling-patterns.md 的 Theme System
 * 保持字段稳定，既有页面可直接通过 useTheme() 消费，不破坏既有接口。
 */
export interface Theme {
  colors: {
    primary: string;
    secondary: string;
    background: string;
    surface: string;
    text: string;
    textSecondary: string;
    border: string;
    error: string;
    success: string;
  };
  spacing: {
    xs: number;
    sm: number;
    md: number;
    lg: number;
    xl: number;
  };
  borderRadius: {
    sm: number;
    md: number;
    lg: number;
    full: number;
  };
  typography: {
    h1: { fontSize: number; fontWeight: '700'; lineHeight: number };
    h2: { fontSize: number; fontWeight: '600'; lineHeight: number };
    body: { fontSize: number; fontWeight: '400'; lineHeight: number };
    caption: { fontSize: number; fontWeight: '400'; lineHeight: number };
  };
}

const lightTheme: Theme = {
  colors: {
    primary: '#6366f1',
    secondary: '#8b5cf6',
    background: '#ffffff',
    surface: '#f9fafb',
    text: '#1f2937',
    textSecondary: '#6b7280',
    border: '#e5e7eb',
    error: '#ef4444',
    success: '#10b981',
  },
  spacing: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 },
  borderRadius: { sm: 4, md: 8, lg: 16, full: 9999 },
  typography: {
    h1: { fontSize: 32, fontWeight: '700', lineHeight: 40 },
    h2: { fontSize: 24, fontWeight: '600', lineHeight: 32 },
    body: { fontSize: 16, fontWeight: '400', lineHeight: 24 },
    caption: { fontSize: 12, fontWeight: '400', lineHeight: 16 },
  },
};

const darkTheme: Theme = {
  ...lightTheme,
  colors: {
    primary: '#818cf8',
    secondary: '#a78bfa',
    background: '#111827',
    surface: '#1f2937',
    text: '#f9fafb',
    textSecondary: '#9ca3af',
    border: '#374151',
    error: '#f87171',
    success: '#34d399',
  },
};

const ThemeContext = createContext<Theme>(lightTheme);

export interface ThemeProviderProps {
  children: React.ReactNode;
  /** 可选：强制指定主题，不传则跟随系统配色方案 */
  mode?: 'light' | 'dark' | 'system';
}

export function ThemeProvider({ children, mode = 'system' }: ThemeProviderProps) {
  const systemScheme = useColorScheme();
  const theme = useMemo<Theme>(() => {
    if (mode === 'system') {
      return systemScheme === 'dark' ? darkTheme : lightTheme;
    }
    return mode === 'dark' ? darkTheme : lightTheme;
  }, [mode, systemScheme]);

  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  return useContext(ThemeContext);
}
