// 集成验证清单
// 依据：merge-strategies.md「Integration Verification Checklist」与「Conflict Resolution」

## 合并后验证（lead 执行，全部通过方可交付）

- [ ] 1. 构建检查：代码可编译/打包，无错误
- [ ] 2. 类型检查：TypeScript 类型注解通过
- [ ] 3. Lint 检查：符合代码规范
- [ ] 4. 单元测试：所有单元测试通过
- [ ] 5. 集成测试：跨组件测试通过
- [ ] 6. 接口核验：所有接口契约与实现一致（AuthService 方法签名、AuthResponse 字段）

## 冲突判定优先级（merge-strategies.md Resolution Strategies）

1. 契约优先：代码与接口契约不一致时，以契约为准，改代码
2. lead 裁决：实现间冲突由 lead 决定保留哪一方
3. 测试决定：通过测试的实现视为正确
4. 手动合并：复杂冲突由 lead 手动合并

## 本演示的可核验项

在真实仓库中，第 1–6 项需在对应代码库执行；本次演示仅能静态核验第 6 项的前置条件：
文件归属矩阵满足「一个文件一个 owner」「契约文件归 lead」「barrel 文件唯一 owner」，
由 validate-ownership.js 自动完成。
