# 准备记录

记录日期：2026-10-31（Asia/Shanghai）。目标来自本机唯一匹配的 `/Applications/DeepSeek Harness.app`；本轮工作范围是皮肤开发准备。

## 当前技术结论

| 事项 | 结论 | 依据 |
| --- | --- | --- |
| 目标 | Electron 桌面应用，`0.2.1-rc.5`，Bundle ID `com.deepseek.dsh` | 安装包 `Contents/Info.plist`；本地快照 `manifest.json` |
| 推荐换肤入口 | `theme.overrideTokens(source, tokens)` | `dsh-client-ui-theme/lib/client.js:1835` |
| 变量形状 | 每项为 `{ light: string, dark: string }`，运行时拒绝单字符串 | 同文件 `1931` 行起 |
| 浅深色跟随 | 按活动主题的 `colorScheme` 选择覆盖值 | 同文件 `1868` 行起 |
| 撤销 | disposer 移除自身覆盖层并发布主题变化 | 同文件 `1842` 行起 |
| 实际应用 | Presenter 在 `body.style` 写入 token，并管理 `body[data-ds-dark-theme]` | `dsh-client-ui-layout/lib/client.js:548` |
| 插件生命周期 | 客户端导出 `inject: ["theme"]`，用 `ctx.effect` 持有覆盖的 disposer | 已提取客户端插件实现及客户端运行器 |
| 动态 façade | 仍需传两个参数；运行器会把 source 固定为包身份并登记清理 | `dsh-cordis-client-runner/lib/client.js:300` |
| 包声明 | `dsh.manifestVersion: 1`，`dsh.bundle.patch`，`dsh.client.platform: "web"` | `dsh-package-manifest/README.zh.md:30` |
| 本地安装路径 | 插件管理器文档支持绝对目录及 `link:` / `file:` spec | `dsh-plugin-manager/README.zh.md:42` |

上表包名路径均相对于 `reference/0.2.1-rc.5-8dad52f295bd/packages/`。逐文件字节校验保存在该快照的 `manifest.json`。

这些是安装包代码和随包文档的静态事实。当前没有执行应用中的插件安装、主题切换或卸载，因此实际加载效果尚未验证。

### 为什么使用覆盖层

`register()` 只是登记自定义主题，仍需 `setTheme(customId)` 激活；自定义 id 不跨越内置 settings schema，Host 偏好同步也可能重新采用已保存值。覆盖层直接叠加到当前主题，适合保留用户原有的浅色、深色和跟随系统设置。

包清单的 `dsh.client.inject` 使用包名 `@deepseek-ai/dsh-client-ui-theme`；客户端导出的 `inject` 使用服务名 `theme`。二者属于不同层级。

## 组件范围

| 界面范围 | 已找到的样式入口 | 后续视觉检查 |
| --- | --- | --- |
| 主画布与层级 | `--dsw-alias-bg-base`、`--dsw-alias-bg-layer-*`、`--dsw-alias-label-*` | 背景层次、文字对比、长时间阅读 |
| 左侧栏 | `--dsw-specific-sidebar-fill`、`--dsw-alias-interactive-bg-hover`、圆角与焦点变量 | 当前项目、会话选中、悬停、滚动条 |
| 会话与输入区 | `--dsw-specific-bubble`、`--dsw-specific-input-major`、`--dsw-alias-border-*` | 长消息、空会话、多行输入、附件、发送与停止 |
| 设置与浮层 | `--dsw-alias-settings-card-*`、`--dsw-specific-menu`、`--dsw-elevation-*` | 菜单、模态、遮罩、禁用、焦点与选中 |
| Markdown 与代码 | `--dsw-alias-markdown-*`、`--shiki-*`、代码字体变量 | 代码块、行内代码、表格、链接、数学公式 |
| 语义状态 | `--dsw-alias-state-*`、`--dsw-alias-turn-trigger-*` | 运行、等待、成功、错误、警告不能混淆 |
| 字体与节奏 | `--dsw-font-*`、`--dsw-radius-*`、`--ds-transition-*` | 中文回退、缩放、字号设置与动态效果 |

表格用于安排后续验证，不表示所有组件已运行检查。`token-catalog.json` 的 `used_by` 仅覆盖已选中的客户端 bundle。

终端、文件差异、文档预览与右侧栏需要在联调时补充实际内容样例。欢迎页、更新弹窗和原生窗口装饰属于独立界面，主文档主题覆盖的作用范围不能直接推广到这些窗口。

## 选定风格后的工作

1. 确定一组视觉参考，填写 `skin/brief.json` 中的风格、配色、字体、密度、圆角和动效。
2. 从语义变量开始完成浅色、深色配对；仅在变量无法表达所需视觉时，再评估组件级 CSS。
3. 构建插件，在应用联调环境安装并启用，留存相同窗口尺寸的原版与皮肤截图。
4. 验证 `light / dark / system` 切换、首次打开、刷新、重启，以及后加载插件的颜色一致性。
5. 覆盖聊天、代码、终端、设置、菜单、弹窗，检查悬停、选中、禁用、加载、错误和键盘焦点。
6. 检查中文与长文本、不同窗口宽度、用户字号调整及减少动态效果偏好。
7. 禁用皮肤，确认其覆盖被撤销；重新启用，确认没有重复样式或残留监听。

启动早期的 Host 调色板先于客户端插件生效，现有覆盖入口可能在首帧短暂显示原配色。是否可见及是否需要额外引导支持，要用真实启动验证。

## 证据与检查记录

- 安装包 SHA-256：`8dad52f295bdbe9fa71948fdf38ac2ce3c910213d3b89c37174b2af77db9fb31`。
- 选定参考文件：174；八张主题样式表提取到 430 个不同变量名。
- `logs/check-result.json`：174 个参考文件校验、当前安装包身份、构建输入一致性和 JS 语法已通过；运行时集成未执行。
- `logs/rea-desktop-summary.json`：REA 辅助静态分析摘要。父证据 ID 为 `ev_5fe1ad00a6aa50cffe6e55b5ae9e6b933403d50e8531647890662426a24e8e60`；只选择 `package.json`、`lib/main.js` 和 `lib/preload-app.cjs`，未分析其他模块的关系，语义图受节点上限限制。该证据不能当作运行时或全应用覆盖证明。
- 主题契约的细节来自随后按路径读取、校验并保存的本地包代码；原始参考与派生 CSS 分开存放，派生文件不冒充源码。
