# 审查报告 — demo/before.html

- 审查对象：`demo/before.html`（合成演示样例，非真实项目代码）
- 技术栈（预检 P4）：原生 CSS transition/animation + requestAnimationFrame + scroll 事件，**无外部动画库**
- 适用规则：fixing-motion-performance SKILL.md 全部 9 类
- 审查模式：只读，未改动原文件
- 备份：`demo/before.bak.1103a856.html`

---

## 违规清单（按优先级）

### V1 ｜ R1 never patterns + R2 choose the mechanism（critical）
- **原行 12**：`    transition: width 0.3s ease;`
- **原行 15**：`  .panel.open { width: 600px; }`
- **原因**：在 300px 高面板上连续动画 `width`，每帧触发 layout（reflow），属于应避免的布局属性连续动画。
- **修复**：面板保持最终布局宽度，用 `transform: scaleX()` 做展开视觉；`transform-origin: left`。

### V2 ｜ R6 layers（medium）
- **原行 13**：`    will-change: width, left, top, opacity, transform;`
- **原因**：长期声明多个 `will-change`，且 `width/left/top` 无法走合成，会无谓提升大层、占用内存。
- **修复**：移除静态声明；仅在动画即将开始前临时加 `will-change: transform`，结束后移除。

### V3 ｜ R5 paint（medium-high）
- **原行 20–21**：
  ```
    transform: translateX(var(--tx));
    transition: --tx 0.4s ease;
  ```
- **原因**：动画用于驱动 `transform` 的 CSS 自定义属性，每帧需重新计算 transform，无法走合成快速路径。
- **修复**：移除 `--tx` 变量与 `transition`；该元素的 `transform` 由 JS rAF 连续驱动（见 V9），同一属性只保留一套动画系统。若改为纯 CSS 驱动，则直接 `transition: transform` 且不再由 JS 每帧写 `transform`。

### V4 ｜ R7 blur and filters（medium）
- **原行 29**：`    animation: pulseBlur 2s infinite ease-in-out;`
- **原行 33**：`    50%  { filter: blur(20px); }`
- **原因**：在 100%×600px 大元素上无限循环动画 blur，峰值 20px > 8px，每帧触发昂贵 paint。
- **修复**：删除连续 blur 动画；呼吸效果改用 `opacity`/`transform`；blur 仅保留 ≤8px 的一次性场景。

### V5 ｜ R6 layers（medium）
- **原行 39**：`    will-change: transform, opacity;`
- **原因**：列表每个 `.list-item` 长期提升合成层，多层叠加浪费内存。
- **修复**：移除静态 `will-change`；仅在该项进入视口即将做动画时临时添加。

### V6 ｜ R1 never patterns + R4 scroll（critical / high）
- **原行 65–67**：
  ```js
  window.addEventListener('scroll', () => {
    hero.style.opacity = 1 - (window.scrollY / 500);
  });
  ```
- **原因**：用 scroll 事件逐帧读 `scrollY` 并写样式，主线程滚动监听易掉帧，且未在离屏时暂停。
- **修复**：优先 CSS `animation-timeline: scroll()`；降级用 `IntersectionObserver` 控制 rAF 批量写入，不可见时暂停。

### V7 ｜ R1 never patterns（critical）
- **原行 70–74**：
  ```js
  function loop() {
    card.style.transform = 'translateX(' + (Math.sin(Date.now() / 500) * 50) + 'px)';
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  ```
- **原因**：rAF 循环无停止条件，元素离屏/隐藏后仍持续运行，空耗 CPU/GPU。
- **修复**：加 `running` 标志位，用 `IntersectionObserver` 在离屏时 `cancelAnimationFrame`，回屏时恢复。

### V8 ｜ R1 never patterns + R3 measurement（critical / high）
- **原行 77–82**：
  ```js
  items.forEach((el) => {
    const x = el.getBoundingClientRect().left;
    el.style.left = (x + 10) + 'px';
    const y = el.getBoundingClientRect().top;
    el.style.top = y + 'px';
  });
  ```
- **原因**：同一帧内交错读写布局，每次写后再读强制同步布局（layout thrashing），N 个元素触发 N 次 reflow。
- **修复**：先批量读取所有 `getBoundingClientRect`，再批量写入；位移用 `transform` 而非 `left/top`。

### V9 ｜ R1 never patterns + R9 tool boundaries（critical）
- **原行 85–86**：
  ```js
  card.style.setProperty('--tx', '100px');
  card.style.transform = 'translateX(200px)';
  ```
- **原因**：CSS 变量 transition 与 JS 直接写 `transform` 两套系统同时改同一属性，互相覆盖、行为不可预测。
- **修复**：统一为一种机制；本处用 JS 控制 `transform`，移除 CSS 变量 transition（不引入新库，符合 R9）。

---

## 人工确认点

- **Gate A（审查后→修复前）**：以上 9 项是否全部修复？本演示为验证流程，按用户「完成诊断并修复」的要求继续生成 `after.html`；真实场景此处应暂停等待确认。
- **Gate B（库/API 边界）**：本次修复不迁移/引入任何动画库，全部在原生 CSS + rAF 栈内完成，无需额外授权。`animation-timeline: scroll()` 为原生 CSS 特性，降级路径已备。
- **Gate C（修复后→交付前）**：见交付时的 before/after 差异摘要。

## 执行日志

- 预检 P1–P7 全部通过（无 git，已生成内容哈希备份）。
- 审查阶段未写入任何目标文件。
- 未访问网络、未安装依赖、未调用外部服务。
