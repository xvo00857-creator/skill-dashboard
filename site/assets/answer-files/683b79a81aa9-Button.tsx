import {
  forwardRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "./utils";
import "./components.css";

// 变体与尺寸枚举对齐 SKILL.md「Component API Design」示例：
// variant: primary | secondary | ghost；size: sm | md | lg
type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** 视觉变体 */
  variant?: ButtonVariant;
  /** 尺寸 */
  size?: ButtonSize;
  /** 加载态：显示旋转图标、禁用点击、aria-busy */
  isLoading?: boolean;
  /** 左侧图标 */
  leftIcon?: ReactNode;
  /** 右侧图标 */
  rightIcon?: ReactNode;
}

/**
 * 按钮组件
 * - 语义化属性名 isLoading（遵循 SKILL.md 最佳实践）
 * - forwardRef 转发 DOM（遵循 SKILL.md 最佳实践第 5 条）
 * - 支持 className/style 覆盖（遵循 SKILL.md 组件 API 原则）
 * - 不引入 class-variance-authority / clsx / tailwind-merge 等新依赖，
 *   变体通过 CSS 类名拼接实现，避免未经批准的依赖变更。
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      leftIcon,
      rightIcon,
      children,
      disabled,
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        className={cn(
          "btn",
          `btn--${variant}`,
          `btn--${size}`,
          isLoading && "btn--loading",
          className,
        )}
        disabled={isLoading || disabled}
        aria-busy={isLoading || undefined}
        {...props}
      >
        {isLoading && (
          <span className="btn__spinner" aria-hidden="true" />
        )}
        {!isLoading && leftIcon && (
          <span className="btn__icon btn__icon--left">{leftIcon}</span>
        )}
        <span className="btn__label">{children}</span>
        {!isLoading && rightIcon && (
          <span className="btn__icon btn__icon--right">{rightIcon}</span>
        )}
      </button>
    );
  },
);
