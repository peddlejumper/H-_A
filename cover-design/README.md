# H# 编程教程几何封面使用指南

## 简介

这是一个为 H# 编程教程设计的现代化几何封面，采用 HTML5 Canvas 和 CSS3 技术，支持动态动画效果和交互功能。

## 文件结构

```
cover-design/
├── index.html              # 主页面
├── css/
│   └── styles.css          # 样式表
├── js/
│   ├── main.js             # 主入口
│   ├── geometric-shapes.js # 几何图形绘制
│   ├── animation.js        # 动画控制
│   ├── code-flow.js        # 代码流效果
│   └── gradients.js        # 渐变管理
└── README.md               # 本文档
```

## 快速开始

### 1. 本地预览

使用 Python 简易服务器：

```bash
cd /Users/peddlejumper/H#/v0.4/cover-design
python3 -m http.server 8000
```

然后在浏览器中打开：`http://localhost:8000`

或者使用 VS Code 的 Live Server 插件。

### 2. 直接打开

双击 `index.html` 文件即可在浏览器中查看。

## 功能特性

### 🎨 视觉效果

- **动态六边形网格**：带有旋转和透明度动画
- **代码流动效果**：模拟代码在屏幕上流动
- **渐变光晕**：多层渐变和光束效果
- **粒子系统**：浮动的粒子增强动感
- **响应式设计**：适配不同屏幕尺寸

### 🎮 交互控制

- **空格键**：暂停/继续动画
- **上/下箭头**：调整动画速度
- **R 键**：重置所有动画
- **鼠标移动**：鼠标位置出现光晕效果
- **鼠标点击**：触发粒子爆发效果

### 📸 截图功能

在浏览器控制台中运行：

```javascript
// 获取截图数据
coverDesign.screenshot()

// 下载截图
coverDesign.downloadScreenshot('my-cover.png')
```

## 自定义配置

### 修改颜色方案

编辑 `css/styles.css` 中的 CSS 变量：

```css
:root {
  --primary-dark: #1A568E;      /* 主色 */
  --accent: #CC3333;           /* 强调色 */
  --gradient-start: #667EEA;    /* 渐变起始色 */
  --gradient-end: #F093FB;      /* 渐变结束色 */
  --dark-bg: #0D1117;          /* 背景色 */
}
```

### 修改标题文本

编辑 `index.html` 中的文本内容：

```html
<h1 class="main-title">
  <span class="title-cn">H# 程序设计教程</span>
  <span class="title-en">H# Programming Tutorial</span>
</h1>
```

### 调整动画参数

编辑 `js/code-flow.js` 中的代码片段：

```javascript
this.codeSnippets = [
  'fn main() {',
  '  let x = 42;',
  // 添加更多代码片段
];
```

### 修改粒子数量

在 `js/animation.js` 中调整：

```javascript
this.particleCount = 50; // 粒子数量
```

## 响应式断点

- **移动端** (< 768px): 小字体，少量代码流
- **平板端** (768px - 1024px): 中等字体和粒子数
- **桌面端** (> 1024px): 大字体，多代码流

## 浏览器兼容性

- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+

## 性能优化

- 使用 `requestAnimationFrame` 确保流畅的60fps动画
- Canvas 批量绘制优化
- 粒子系统对象池复用
- 自动降级的响应式设计

## 导出为静态图像

### 方法1：截图工具

1. 在浏览器中打开封面
2. 使用系统截图工具（macOS: Cmd+Shift+4）
3. 或使用浏览器的"开发者工具 > 截图"功能

### 方法2：Canvas 截图

1. 暂停动画（按空格键）
2. 打开浏览器控制台（F12）
3. 运行：`coverDesign.downloadScreenshot('hsharp-cover.png')`

### 方法3：打印为PDF

1. 暂停动画
2. 浏览器中选择"打印"（Cmd+P）
3. 选择"保存为PDF"
4. 在"更多设置"中取消勾选"页眉和页脚"

## 常见问题

### Q: 动画不流畅？
A: 确保使用支持硬件加速的浏览器，并检查是否有其他占用资源的标签页。

### Q: 无法显示中文字体？
A: 确保网络连接正常以加载 Google Fonts，或将字体文件下载到本地。

### Q: 如何移除动画效果？
A: 按空格键暂停，或修改代码移除动画实例。

## 技术栈

- **HTML5 Canvas**: 2D 图形渲染
- **CSS3**: 样式和布局
- **Vanilla JavaScript**: 无框架依赖
- **Google Fonts**: Noto Sans SC, Source Code Pro

## 许可

本封面设计仅供 H# 编程教程使用。

---

**版本**: 1.0  
**更新日期**: 2026-05-30  
**作者**: AI Assistant
