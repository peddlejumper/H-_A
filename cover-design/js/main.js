/**
 * H# Geometric Cover - Main Entry Point
 * 主入口文件
 */

class CoverDesign {
  constructor() {
    this.canvas = null;
    this.ctx = null;
    this.shapes = null;
    this.codeFlow = null;
    this.gradients = null;
    this.controller = null;
    this.animationInstances = {};
    this.initialized = false;
  }

  /**
   * 初始化所有组件
   */
  init() {
    if (this.initialized) return;

    // 获取Canvas
    this.canvas = document.getElementById('geometricCanvas');
    if (!this.canvas) {
      console.error('Canvas element not found');
      return;
    }

    this.ctx = this.canvas.getContext('2d');
    
    // 设置Canvas尺寸
    this.resize();
    
    // 初始化模块
    this.initModules();
    
    // 设置动画
    this.setupAnimations();
    
    // 绑定事件
    this.bindEvents();
    
    // 启动动画
    this.start();
    
    this.initialized = true;
    
    console.log('H# Geometric Cover initialized successfully');
  }

  /**
   * 初始化所有模块
   */
  initModules() {
    // 几何图形模块
    this.shapes = new GeometricShapes(this.canvas);
    
    // 代码流模块
    this.codeFlow = new CodeFlowEffect(this.canvas);
    
    // 渐变模块
    this.gradients = new GradientManager(this.canvas);
    
    // 动画控制器
    this.controller = new AnimationController();
  }

  /**
   * 设置动画
   */
  setupAnimations() {
    // 几何图形动画
    this.animationInstances.geometric = new GeometricAnimation(this.shapes, this.canvas);
    this.controller.addAnimation(this.animationInstances.geometric);
    
    // 粒子动画
    this.animationInstances.particles = new ParticleAnimation(this.shapes, this.canvas);
    this.controller.addAnimation(this.animationInstances.particles);
    
    // 代码流动画
    this.animationInstances.codeFlow = new CodeFlowAnimation(this.codeFlow, this.canvas);
    this.controller.addAnimation(this.animationInstances.codeFlow);
  }

  /**
   * 绘制背景
   */
  drawBackground() {
    // 基础背景色
    const bgGradient = this.gradients.createBackgroundGradient();
    this.ctx.fillStyle = bgGradient;
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // 动态光晕效果
    this.gradients.drawCentralGlow();
    this.gradients.drawCornerGlows();
    this.gradients.drawDynamicBeams();
    
    // 网格
    this.gradients.createGridMask();
  }

  /**
   * 绑定事件
   */
  bindEvents() {
    // 窗口大小改变
    window.addEventListener('resize', () => {
      this.resize();
      this.handleResize();
    });
    
    // 鼠标移动 - 交互效果
    this.canvas.addEventListener('mousemove', (e) => {
      this.handleMouseMove(e);
    });
    
    // 鼠标点击 - 特效
    this.canvas.addEventListener('click', (e) => {
      this.handleClick(e);
    });
    
    // 键盘事件
    document.addEventListener('keydown', (e) => {
      this.handleKeydown(e);
    });
  }

  /**
   * 处理窗口大小改变
   */
  handleResize() {
    // 更新粒子系统
    if (this.animationInstances.particles) {
      this.animationInstances.particles.resize(this.canvas.width, this.canvas.height);
    }
    
    // 更新代码流
    if (this.animationInstances.codeFlow) {
      const streamCount = this.getResponsiveStreamCount();
      this.animationInstances.codeFlow.setStreamCount(streamCount);
    }
  }

  /**
   * 获取响应式代码流数量
   */
  getResponsiveStreamCount() {
    const width = window.innerWidth;
    if (width < 768) return 3;
    if (width < 1024) return 5;
    return 8;
  }

  /**
   * 处理鼠标移动
   */
  handleMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    // 在鼠标位置绘制额外的光晕
    this.shapes.drawGlow(
      mouseX,
      mouseY,
      50 + Math.sin(Date.now() * 0.005) * 20,
      'rgba(102, 126, 234, 0.2)'
    );
  }

  /**
   * 处理鼠标点击
   */
  handleClick(e) {
    const rect = this.canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    // 点击时添加粒子爆发效果
    for (let i = 0; i < 10; i++) {
      const particle = {
        x: clickX,
        y: clickY,
        size: Math.random() * 4 + 2,
        speedX: (Math.random() - 0.5) * 8,
        speedY: (Math.random() - 0.5) * 8,
        color: this.shapes.getRandomColor(),
        opacity: 1,
        life: 1
      };
      
      this.animateParticleBurst(particle);
    }
  }

  /**
   * 粒子爆发动画
   */
  animateParticleBurst(particle) {
    const animate = () => {
      particle.x += particle.speedX;
      particle.y += particle.speedY;
      particle.speedX *= 0.95;
      particle.speedY *= 0.95;
      particle.life -= 0.02;
      particle.opacity = particle.life;
      
      if (particle.life > 0) {
        this.shapes.drawParticle(
          particle.x,
          particle.y,
          particle.size * particle.life,
          particle.color.replace('0.8', particle.opacity.toString())
        );
        requestAnimationFrame(animate);
      }
    };
    
    animate();
  }

  /**
   * 处理键盘事件
   */
  handleKeydown(e) {
    switch(e.key) {
      case ' ':
        // 空格键 - 暂停/继续
        if (this.controller.running) {
          this.controller.stop();
        } else {
          this.controller.start();
        }
        break;
      case 'ArrowUp':
        // 上箭头 - 增加速度
        this.controller.setSpeed(this.controller.speedMultiplier * 1.2);
        break;
      case 'ArrowDown':
        // 下箭头 - 减少速度
        this.controller.setSpeed(this.controller.speedMultiplier * 0.8);
        break;
      case 'r':
        // R键 - 重置
        this.reset();
        break;
    }
  }

  /**
   * 调整Canvas尺寸
   */
  resize() {
    const container = this.canvas.parentElement;
    this.canvas.width = container.clientWidth;
    this.canvas.height = container.clientHeight;
  }

  /**
   * 启动动画
   */
  start() {
    this.controller.start();
  }

  /**
   * 停止动画
   */
  stop() {
    this.controller.stop();
  }

  /**
   * 重置
   */
  reset() {
    this.controller.clear();
    this.gradients.reset();
    this.setupAnimations();
  }

  /**
   * 截图功能
   */
  screenshot() {
    return this.canvas.toDataURL('image/png');
  }

  /**
   * 下载截图
   */
  downloadScreenshot(filename = 'hsharp-cover.png') {
    const dataUrl = this.screenshot();
    const link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    link.click();
  }
}

// 创建全局实例
let coverDesign = null;

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
  coverDesign = new CoverDesign();
  coverDesign.init();
  
  // 暴露到全局，便于调试
  window.coverDesign = coverDesign;
  
  // 添加控制台提示
  console.log('%c🎨 H# Geometric Cover', 'font-size: 20px; font-weight: bold; color: #667EEA;');
  console.log('%cControls:', 'font-weight: bold;');
  console.log('  Space - Pause/Resume');
  console.log('  Arrow Up/Down - Adjust speed');
  console.log('  R - Reset');
  console.log('  Click - Particle burst effect');
  console.log('  coverDesign.screenshot() - Take screenshot');
  console.log('  coverDesign.downloadScreenshot() - Download screenshot');
});
