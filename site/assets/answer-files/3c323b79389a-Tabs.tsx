import {
  createContext,
  useCallback,
  useContext,
  useId,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "./utils";
import "./components.css";

/**
 * 复合组件 Tabs（遵循 references/component-patterns.md 的 Compound Components 模式）
 *
 * 用法：
 * <Tabs defaultValue="a" onValueChange={...}>
 *   <Tabs.List>
 *     <Tabs.Tab tabValue="a">A</Tabs.Tab>
 *     <Tabs.Tab tabValue="b" disabled>B</Tabs.Tab>
 *   </Tabs.List>
 *   <Tabs.Panel tabValue="a">...</Tabs.Panel>
 * </Tabs>
 *
 * 同时支持受控（value + onValueChange）与非受控（defaultValue），
 * 遵循 SKILL.md 最佳实践第 4 条「Controlled vs Uncontrolled」。
 */

interface TabsContextValue {
  activeTab: string;
  setActiveTab: (value: string) => void;
  idBase: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabs(componentName: string): TabsContextValue {
  const ctx = useContext(TabsContext);
  if (!ctx) {
    throw new Error(`<${componentName}> 必须在 <Tabs> 内使用`);
  }
  return ctx;
}

export interface TabsProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "defaultValue" | "onChange"> {
  /** 非受控默认值 */
  defaultValue?: string;
  /** 受控当前值 */
  value?: string;
  /** 值变化回调 */
  onValueChange?: (value: string) => void;
  children: ReactNode;
}

export function Tabs({
  defaultValue,
  value,
  onValueChange,
  children,
  className,
  ...props
}: TabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue ?? "");
  const isControlled = value !== undefined;
  const activeTab = isControlled ? (value as string) : internalValue;
  // useId 生成稳定且唯一的 id 前缀，避免多实例 aria 关联冲突
  const idBase = useId();

  const setActiveTab = useCallback(
    (next: string) => {
      if (!isControlled) setInternalValue(next);
      onValueChange?.(next);
    },
    [isControlled, onValueChange],
  );

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab, idBase }}>
      <div className={cn("tabs", className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export interface TabsListProps extends HTMLAttributes<HTMLDivElement> {}

Tabs.List = function TabList({
  className,
  children,
  ...props
}: TabsListProps) {
  return (
    <div
      role="tablist"
      className={cn("tabs__list", className)}
      {...props}
    >
      {children}
    </div>
  );
};

export interface TabsTabProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "value"> {
  /** 该标签对应的唯一值（命名避开原生 value 属性） */
  tabValue: string;
  children: ReactNode;
}

Tabs.Tab = function Tab({
  tabValue,
  disabled,
  className,
  children,
  ...props
}: TabsTabProps) {
  const { activeTab, setActiveTab, idBase } = useTabs("Tabs.Tab");
  const isActive = activeTab === tabValue;
  const tabId = `${idBase}-tab-${tabValue}`;
  const panelId = `${idBase}-panel-${tabValue}`;

  // 键盘导航：方向键 / Home / End 在可聚焦标签间循环。
  // 实现方式参照 references/accessibility-patterns.md 中 Dropdown 的方向键焦点移动。
  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    const list = event.currentTarget.parentElement;
    if (!list) return;
    const tabs = Array.from(
      list.querySelectorAll<HTMLButtonElement>(
        '[role="tab"]:not([disabled])',
      ),
    );
    const currentIndex = tabs.indexOf(event.currentTarget);
    if (currentIndex === -1) return;

    let nextIndex: number | null = null;
    switch (event.key) {
      case "ArrowRight":
      case "ArrowDown":
        event.preventDefault();
        nextIndex = (currentIndex + 1) % tabs.length;
        break;
      case "ArrowLeft":
      case "ArrowUp":
        event.preventDefault();
        nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
        break;
      case "Home":
        event.preventDefault();
        nextIndex = 0;
        break;
      case "End":
        event.preventDefault();
        nextIndex = tabs.length - 1;
        break;
      default:
        break;
    }

    if (nextIndex !== null) {
      const target = tabs[nextIndex];
      target.focus();
      target.click();
    }
  };

  return (
    <button
      type="button"
      role="tab"
      id={tabId}
      aria-selected={isActive}
      aria-controls={panelId}
      // roving tabindex：仅当前标签可被 Tab 聚焦，其余通过方向键到达
      tabIndex={isActive ? 0 : -1}
      disabled={disabled}
      onClick={() => {
        if (!disabled) setActiveTab(tabValue);
      }}
      onKeyDown={handleKeyDown}
      className={cn(
        "tabs__tab",
        isActive && "tabs__tab--active",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
};

export interface TabsPanelProps extends HTMLAttributes<HTMLDivElement> {
  tabValue: string;
  children: ReactNode;
}

Tabs.Panel = function TabPanel({
  tabValue,
  className,
  children,
  ...props
}: TabsPanelProps) {
  const { activeTab, idBase } = useTabs("Tabs.Panel");
  // 非激活面板直接不渲染，保持与 Skill 示例一致
  if (activeTab !== tabValue) return null;

  const tabId = `${idBase}-tab-${tabValue}`;
  const panelId = `${idBase}-panel-${tabValue}`;

  return (
    <div
      role="tabpanel"
      id={panelId}
      aria-labelledby={tabId}
      tabIndex={0}
      className={cn("tabs__panel", className)}
      {...props}
    >
      {children}
    </div>
  );
};
