/**
 * H# Geometric Cover - Geometric Shapes Module
 * 几何图形绘制模块
 */

class GeometricShapes {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.hexagons = [];
    this.lines = [];
    this.particles = [];
  }

  /**
   * 绘制六边形
   */
  drawHexagon(x, y, size, rotation = 0, style = {}) {
    const ctx = this.ctx;
    const {
      fill = false,
      stroke = true,
      strokeColor = 'rgba(102, 126, 234, 0.3)',
      lineWidth = 1,
      fillColor = 'rgba(102, 126, 234, 0.1)'
    } = style;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rotation);

    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 2;
      const hx = size * Math.cos(angle);
      const hy = size * Math.sin(angle);
      if (i === 0) {
        ctx.moveTo(hx, hy);
      } else {
        ctx.lineTo(hx, hy);
      }
    }
    ctx.closePath();

    if (fill) {
      ctx.fillStyle = fillColor;
      ctx.fill();
    }

    if (stroke) {
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }

    ctx.restore();
  }

  /**
   * 绘制六边形网格
   */
  drawHexagonGrid(cols, rows, size, options = {}) {
    const ctx = this.ctx;
    const {
      startX = 0,
      startY = 0,
      rotation = 0,
      opacity = 0.3,
      lineWidth = 1,
      animate = false,
      time = 0
    } = options;

    const horizontalSpacing = size * 1.5;
    const verticalSpacing = size * Math.sqrt(3);

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x = startX + col * horizontalSpacing;
        const y = startY + row * verticalSpacing + (col % 2) * (verticalSpacing / 2);

        const animatedRotation = animate ? rotation + (time * 0.0001 * (col + row)) : rotation;
        const animatedOpacity = animate ? opacity * (0.5 + 0.5 * Math.sin(time * 0.002 + col * 0.5 + row * 0.3)) : opacity;

        this.drawHexagon(x, y, size * 0.95, animatedRotation, {
          strokeColor: `rgba(102, 126, 234, ${animatedOpacity})`,
          lineWidth: lineWidth,
          stroke: true,
          fill: false
        });
      }
    }
  }

  /**
   * 绘制连接线
   */
  drawLine(x1, y1, x2, y2, style = {}) {
    const ctx = this.ctx;
    const {
      color = 'rgba(102, 126, 234, 0.5)',
      lineWidth = 1,
      dash = [],
      opacity = 1
    } = style;

    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.setLineDash(dash);
    ctx.globalAlpha = opacity;
    
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    
    ctx.restore();
  }

  /**
   * 绘制网格线
   */
  drawGrid(spacing = 50, style = {}) {
    const ctx = this.ctx;
    const { color = 'rgba(102, 126, 234, 0.05)', lineWidth = 1 } = style;

    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;

    // 垂直线
    for (let x = 0; x < this.canvas.width; x += spacing) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.height);
      ctx.stroke();
    }

    // 水平线
    for (let y = 0; y < this.canvas.height; y += spacing) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.canvas.width, y);
      ctx.stroke();
    }

    ctx.restore();
  }

  /**
   * 绘制圆形
   */
  drawCircle(x, y, radius, style = {}) {
    const ctx = this.ctx;
    const {
      fill = true,
      stroke = false,
      fillColor = 'rgba(102, 126, 234, 0.3)',
      strokeColor = 'rgba(102, 126, 234, 0.5)',
      lineWidth = 2
    } = style;

    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);

    if (fill) {
      ctx.fillStyle = fillColor;
      ctx.fill();
    }

    if (stroke) {
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }

    ctx.restore();
  }

  /**
   * 绘制发光效果
   */
  drawGlow(x, y, radius, color = 'rgba(102, 126, 234, 0.3)') {
    const ctx = this.ctx;
    
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, color);
    gradient.addColorStop(1, 'transparent');
    
    ctx.save();
    ctx.fillStyle = gradient;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
    ctx.restore();
  }

  /**
   * 绘制三角形
   */
  drawTriangle(x, y, size, rotation = 0, style = {}) {
    const ctx = this.ctx;
    const {
      fill = true,
      stroke = true,
      fillColor = 'rgba(102, 126, 234, 0.2)',
      strokeColor = 'rgba(102, 126, 234, 0.4)',
      lineWidth = 1
    } = style;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rotation);

    ctx.beginPath();
    ctx.moveTo(0, -size);
    ctx.lineTo(size * Math.cos(Math.PI / 6), size * Math.sin(Math.PI / 6));
    ctx.lineTo(-size * Math.cos(Math.PI / 6), size * Math.sin(Math.PI / 6));
    ctx.closePath();

    if (fill) {
      ctx.fillStyle = fillColor;
      ctx.fill();
    }

    if (stroke) {
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }

    ctx.restore();
  }

  /**
   * 绘制粒子
   */
  drawParticle(x, y, size, color = 'rgba(102, 126, 234, 0.8)') {
    const ctx = this.ctx;
    
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, size, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    
    // 添加发光效果
    ctx.shadowColor = color;
    ctx.shadowBlur = size * 2;
    ctx.fill();
    
    ctx.restore();
  }

  /**
   * 初始化粒子系统
   */
  initParticles(count, bounds) {
    this.particles = [];
    for (let i = 0; i < count; i++) {
      this.particles.push({
        x: Math.random() * bounds.width,
        y: Math.random() * bounds.height,
        size: Math.random() * 3 + 1,
        speedX: (Math.random() - 0.5) * 0.5,
        speedY: (Math.random() - 0.5) * 0.5,
        color: this.getRandomColor(),
        opacity: Math.random() * 0.5 + 0.3
      });
    }
  }

  /**
   * 更新粒子位置
   */
  updateParticles(bounds) {
    this.particles.forEach(particle => {
      particle.x += particle.speedX;
      particle.y += particle.speedY;

      // 边界检测
      if (particle.x < 0 || particle.x > bounds.width) {
        particle.speedX *= -1;
      }
      if (particle.y < 0 || particle.y > bounds.height) {
        particle.speedY *= -1;
      }
    });
  }

  /**
   * 绘制所有粒子
   */
  drawParticles() {
    this.particles.forEach(particle => {
      this.drawParticle(particle.x, particle.y, particle.size, particle.color);
    });
  }

  /**
   * 获取随机颜色
   */
  getRandomColor() {
    const colors = [
      'rgba(102, 126, 234, 0.8)',
      'rgba(118, 75, 162, 0.8)',
      'rgba(240, 147, 251, 0.8)',
      'rgba(46, 134, 171, 0.8)'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  /**
   * 清除画布
   */
  clear() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
  module.exports = GeometricShapes;
}
