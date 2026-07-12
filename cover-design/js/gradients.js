/**
 * H# Geometric Cover - Gradient Manager Module
 * 渐变效果管理模块
 */

class GradientManager {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.gradientCache = {};
    this.time = 0;
  }

  /**
   * 创建背景渐变
   */
  createBackgroundGradient() {
    const gradient = this.ctx.createLinearGradient(
      0, 0,
      this.canvas.width, this.canvas.height
    );
    
    gradient.addColorStop(0, '#0D1117');
    gradient.addColorStop(0.5, '#161B22');
    gradient.addColorStop(1, '#0D1117');
    
    return gradient;
  }

  /**
   * 创建动态背景渐变
   */
  createAnimatedBackgroundGradient() {
    const time = this.time;
    const centerX = this.canvas.width / 2 + Math.sin(time * 0.0005) * 200;
    const centerY = this.canvas.height / 2 + Math.cos(time * 0.0003) * 150;
    
    const gradient = this.ctx.createRadialGradient(
      centerX, centerY, 0,
      centerX, centerY, Math.max(this.canvas.width, this.canvas.height) * 0.8
    );
    
    const hue1 = (time * 0.01 + 230) % 360;
    const hue2 = (time * 0.01 + 280) % 360;
    const hue3 = (time * 0.01 + 320) % 360;
    
    gradient.addColorStop(0, `hsla(${hue1}, 70%, 50%, 0.15)`);
    gradient.addColorStop(0.5, `hsla(${hue2}, 60%, 40%, 0.1)`);
    gradient.addColorStop(1, 'transparent');
    
    return gradient;
  }

  /**
   * 创建光晕渐变
   */
  createGlowGradient(x, y, radius, color = 'rgba(102, 126, 234, 0.5)') {
    const gradient = this.ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, color);
    gradient.addColorStop(0.5, color.replace(/[\d.]+\)$/, '0.2)'));
    gradient.addColorStop(1, 'transparent');
    
    return gradient;
  }

  /**
   * 创建线性光束渐变
   */
  createBeamGradient(x1, y1, x2, y2) {
    const gradient = this.ctx.createLinearGradient(x1, y1, x2, y2);
    
    const hue = (this.time * 0.02 + 240) % 360;
    
    gradient.addColorStop(0, 'transparent');
    gradient.addColorStop(0.5, `hsla(${hue}, 70%, 60%, 0.3)`);
    gradient.addColorStop(1, 'transparent');
    
    return gradient;
  }

  /**
   * 绘制动态光束
   */
  drawDynamicBeams() {
    const ctx = this.ctx;
    const beamCount = 5;
    
    for (let i = 0; i < beamCount; i++) {
      const angle = (i / beamCount) * Math.PI * 2 + this.time * 0.0002;
      const length = Math.min(this.canvas.width, this.canvas.height) * 0.8;
      
      const startX = this.canvas.width / 2;
      const startY = this.canvas.height / 2;
      const endX = startX + Math.cos(angle) * length;
      const endY = startY + Math.sin(angle) * length;
      
      const gradient = this.createBeamGradient(startX, startY, endX, endY);
      
      ctx.save();
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2 + Math.sin(this.time * 0.003 + i) * 1;
      ctx.globalAlpha = 0.3 + Math.sin(this.time * 0.002 + i * 0.5) * 0.2;
      
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
      
      ctx.restore();
    }
  }

  /**
   * 绘制角落光晕
   */
  drawCornerGlows() {
    const ctx = this.ctx;
    const corners = [
      { x: 0, y: 0 },
      { x: this.canvas.width, y: 0 },
      { x: 0, y: this.canvas.height },
      { x: this.canvas.width, y: this.canvas.height }
    ];
    
    corners.forEach((corner, index) => {
      const radius = 200 + Math.sin(this.time * 0.001 + index) * 50;
      const hue = (240 + index * 30 + this.time * 0.01) % 360;
      
      const gradient = ctx.createRadialGradient(
        corner.x, corner.y, 0,
        corner.x, corner.y, radius
      );
      
      gradient.addColorStop(0, `hsla(${hue}, 70%, 50%, 0.2)`);
      gradient.addColorStop(1, 'transparent');
      
      ctx.save();
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
      ctx.restore();
    });
  }

  /**
   * 绘制中心光晕
   */
  drawCentralGlow() {
    const ctx = this.ctx;
    const centerX = this.canvas.width / 2;
    const centerY = this.canvas.height / 2;
    const maxRadius = Math.min(this.canvas.width, this.canvas.height) * 0.6;
    
    const pulseRadius = maxRadius * (0.8 + Math.sin(this.time * 0.002) * 0.2);
    const hue = (240 + this.time * 0.01) % 360;
    
    const gradient = ctx.createRadialGradient(
      centerX, centerY, 0,
      centerX, centerY, pulseRadius
    );
    
    gradient.addColorStop(0, `hsla(${hue}, 70%, 50%, 0.15)`);
    gradient.addColorStop(0.5, `hsla(${hue + 30}, 60%, 40%, 0.08)`);
    gradient.addColorStop(1, 'transparent');
    
    ctx.save();
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.restore();
  }

  /**
   * 创建网格渐变遮罩
   */
  createGridMask() {
    const ctx = this.ctx;
    const gridSize = 50;
    
    ctx.save();
    ctx.globalAlpha = 0.03;
    ctx.strokeStyle = '#667EEA';
    ctx.lineWidth = 1;
    
    for (let x = 0; x < this.canvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.height);
      ctx.stroke();
    }
    
    for (let y = 0; y < this.canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.canvas.width, y);
      ctx.stroke();
    }
    
    ctx.restore();
  }

  /**
   * 更新时间（用于动画）
   */
  update(deltaTime) {
    this.time += deltaTime;
  }

  /**
   * 重置时间
   */
  reset() {
    this.time = 0;
  }

  /**
   * 获取当前时间
   */
  getTime() {
    return this.time;
  }

  /**
   * 设置时间
   */
  setTime(time) {
    this.time = time;
  }
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
  module.exports = GradientManager;
}
