/**
 * H# Geometric Cover - Animation Controller Module
 * 动画控制器模块
 */

class AnimationController {
  constructor() {
    this.animations = [];
    this.running = false;
    this.lastFrame = 0;
    this.fps = 60;
    this.deltaTime = 0;
    this.time = 0;
    this.speedMultiplier = 1;
  }

  /**
   * 启动动画循环
   */
  start() {
    if (this.running) return;
    
    this.running = true;
    this.lastFrame = performance.now();
    this.loop();
  }

  /**
   * 停止动画
   */
  stop() {
    this.running = false;
  }

  /**
   * 动画循环
   */
  loop(timestamp = 0) {
    if (!this.running) return;
    
    const currentTime = performance.now();
    this.deltaTime = (currentTime - this.lastFrame) * this.speedMultiplier;
    this.lastFrame = currentTime;
    this.time += this.deltaTime;
    
    // 更新FPS
    if (this.deltaTime > 0) {
      this.fps = 1000 / this.deltaTime;
    }
    
    // 更新所有动画
    this.update();
    
    // 渲染所有动画
    this.render();
    
    requestAnimationFrame(this.loop.bind(this));
  }

  /**
   * 添加动画
   */
  addAnimation(animation) {
    const id = Date.now() + Math.random();
    this.animations.push({
      id,
      animation,
      active: true
    });
    return id;
  }

  /**
   * 移除动画
   */
  removeAnimation(id) {
    this.animations = this.animations.filter(anim => anim.id !== id);
  }

  /**
   * 暂停动画
   */
  pauseAnimation(id) {
    const anim = this.animations.find(a => a.id === id);
    if (anim) {
      anim.active = false;
    }
  }

  /**
   * 恢复动画
   */
  resumeAnimation(id) {
    const anim = this.animations.find(a => a.id === id);
    if (anim) {
      anim.active = true;
    }
  }

  /**
   * 更新所有动画
   */
  update() {
    this.animations.forEach(({ animation, active }) => {
      if (active && animation.update) {
        animation.update(this.deltaTime, this.time);
      }
    });
  }

  /**
   * 渲染所有动画
   */
  render() {
    this.animations.forEach(({ animation, active }) => {
      if (active && animation.render) {
        animation.render();
      }
    });
  }

  /**
   * 设置播放速度
   */
  setSpeed(multiplier) {
    this.speedMultiplier = multiplier;
  }

  /**
   * 获取当前FPS
   */
  getFPS() {
    return this.fps;
  }

  /**
   * 获取已运行时间
   */
  getTime() {
    return this.time;
  }

  /**
   * 清除所有动画
   */
  clear() {
    this.animations = [];
  }

  /**
   * 暂停所有动画
   */
  pauseAll() {
    this.animations.forEach(anim => {
      anim.active = false;
    });
  }

  /**
   * 恢复所有动画
   */
  resumeAll() {
    this.animations.forEach(anim => {
      anim.active = true;
    });
  }
}

/**
 * 几何图形动画类
 */
class GeometricAnimation {
  constructor(shapes, canvas) {
    this.shapes = shapes;
    this.canvas = canvas;
    this.rotation = 0;
    this.scale = 1;
    this.opacity = 1;
  }

  update(deltaTime, time) {
    this.rotation = time * 0.0002;
    this.scale = 0.95 + Math.sin(time * 0.002) * 0.05;
    this.opacity = 0.2 + Math.sin(time * 0.001) * 0.1;
  }

  render() {
    const cols = Math.ceil(this.canvas.width / 90);
    const rows = Math.ceil(this.canvas.height / 80);
    const size = 40;
    
    this.shapes.drawHexagonGrid(cols, rows, size, {
      startX: 20,
      startY: 20,
      rotation: this.rotation,
      opacity: this.opacity,
      animate: true,
      time: performance.now()
    });
  }
}

/**
 * 粒子动画类
 */
class ParticleAnimation {
  constructor(shapes, canvas) {
    this.shapes = shapes;
    this.canvas = canvas;
    this.particleCount = 50;
    this.shapes.initParticles(this.particleCount, {
      width: canvas.width,
      height: canvas.height
    });
  }

  update(deltaTime, time) {
    this.shapes.updateParticles({
      width: this.canvas.width,
      height: this.canvas.height
    });
  }

  render() {
    this.shapes.drawParticles();
  }

  resize(width, height) {
    this.shapes.initParticles(this.particleCount, { width, height });
  }
}

/**
 * 代码流动画类
 */
class CodeFlowAnimation {
  constructor(codeFlow, canvas) {
    this.codeFlow = codeFlow;
    this.canvas = canvas;
    this.streamCount = 6;
    this.codeFlow.initStreams(this.streamCount);
  }

  update(deltaTime, time) {
    this.codeFlow.update(deltaTime);
  }

  render() {
    this.codeFlow.render();
  }

  resize(width, height) {
    this.codeFlow.resize(width, height);
  }

  setStreamCount(count) {
    this.streamCount = count;
    this.codeFlow.setStreamCount(count);
  }
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    AnimationController,
    GeometricAnimation,
    ParticleAnimation,
    CodeFlowAnimation
  };
}
