// src/types/auth-contract.ts
// 所有者：lead（团队负责人）
// 规则：implementer 只导入、不修改本文件；任何签名变更须由 lead 广播后生效。
// 依据：parallel-feature-development SKILL.md「Interface Contracts」与 Troubleshooting。

export interface UserProfile {
  id: string;
  email: string;
  displayName: string;
}

export interface AuthResponse {
  token: string;
  user: UserProfile;
  expiresAt: number;
}

export interface RegisterData {
  email: string;
  password: string;
  displayName: string;
}

export interface AuthService {
  login(email: string, password: string): Promise<AuthResponse>;
  register(data: RegisterData): Promise<AuthResponse>;
  logout(): Promise<void>;
}

// 下游未就绪时，实现方使用此 stub 继续开发；集成时替换为真实实现。
// 依据：SKILL.md Troubleshooting「An implementer finishes early but the integration step is blocked.」
export const AUTH_SERVICE_STUB: AuthService = {
  async login() {
    throw new Error("[stub] AuthService.login 尚未接入真实实现");
  },
  async register() {
    throw new Error("[stub] AuthService.register 尚未接入真实实现");
  },
  async logout() {
    throw new Error("[stub] AuthService.logout 尚未接入真实实现");
  },
};
