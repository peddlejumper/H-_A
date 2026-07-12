/**
 * H# Geometric Cover - Code Flow Effect Module
 * 代码流动效果模块
 */

class CodeStream {
  constructor(x, y, text, speed, color) {
    this.x = x;
    this.y = y;
    this.text = text;
    this.speed = speed;
    this.color = color;
    this.opacity = 1;
    this.charIndex = 0;
    this.maxOpacity = 0.8;
    this.fadeSpeed = 0.02;
  }

  update(canvasHeight, deltaTime) {
    this.y += this.speed * deltaTime * 0.05;
    
    // 周期性重置
    if (this.y > canvasHeight + 20) {
      this.y = -20;
      this.charIndex = 0;
    }

    // 透明度渐变
    if (this.y < 50) {
      this.opacity = Math.min(this.maxOpacity, this.opacity + this.fadeSpeed);
    } else if (this.y > canvasHeight - 50) {
      this.opacity = Math.max(0, this.opacity - this.fadeSpeed);
    }
  }

  render(ctx) {
    if (this.charIndex < this.text.length) {
      this.charIndex += 0.3; // 字符渐显速度
    }

    const displayText = this.text.substring(0, Math.floor(this.charIndex));
    
    ctx.save();
    ctx.font = '13px "Source Code Pro", monospace';
    ctx.fillStyle = this.color;
    ctx.globalAlpha = this.opacity;
    
    // 添加文字阴影
    ctx.shadowColor = this.color;
    ctx.shadowBlur = 10;
    
    ctx.fillText(displayText, this.x, this.y);
    ctx.restore();
  }
}

class CodeFlowEffect {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.streams = [];
    this.codeSnippets = [
      'fn main() {',
      '  let x = 42;',
      '  print(x);',
      '}',
      'class Point {',
      '  let x = 0;',
      '  let y = 0;',
      '  fn init(px, py) {',
      '    x = px;',
      '    y = py;',
      '  }',
      '}',
      'if (x > 0) {',
      '  return true;',
      '} else {',
      '  return false;',
      '}',
      'while (i < n) {',
      '  sum = sum + i;',
      '  i = i + 1;',
      '}',
      'for (let item in arr) {',
      '  process(item);',
      '}',
      'import "module";',
      'return result;',
      'try {',
      '  execute();',
      '} catch (e) {',
      '  handle(e);',
      '}'
    ];
    this.colors = [
      '#FF79C6', // keyword
      '#F1FA8C', // string
      '#6272A4', // comment
      '#8BE9FD', // function
      '#50FA7B', // number
      '#FFB86C'  // operator
    ];
  }

  /**
   * 添加代码流
   */
  addStream(x, y, text = null, speed = null, color = null) {
    const codeText = text || this.getRandomCode();
    const codeSpeed = speed || (Math.random() * 1.5 + 0.5);
    const codeColor = color || this.getRandomColor();
    
    const stream = new CodeStream(x, y, codeText, codeSpeed, codeColor);
    this.streams.push(stream);
    return stream;
  }

  /**
   * 获取随机代码片段
   */
  getRandomCode() {
    return this.codeSnippets[Math.floor(Math.random() * this.codeSnippets.length)];
  }

  /**
   * 获取随机颜色
   */
  getRandomColor() {
    return this.colors[Math.floor(Math.random() * this.colors.length)];
  }

  /**
   * 初始化多个代码流
   */
  initStreams(count) {
    this.streams = [];
    const spacing = this.canvas.width / (count + 1);
    
    for (let i = 0; i < count; i++) {
      const x = spacing * (i + 1) + (Math.random() - 0.5) * spacing * 0.5;
      const y = Math.random() * this.canvas.height;
      this.addStream(x, y);
    }
  }

  /**
   * 更新所有代码流
   */
  update(deltaTime) {
    this.streams.forEach(stream => {
      stream.update(this.canvas.height, deltaTime);
    });
  }

  /**
   * 绘制所有代码流
   */
  render() {
    this.streams.forEach(stream => {
      stream.render(this.ctx);
    });
  }

  /**
   * 清除所有代码流
   */
  clear() {
    this.streams = [];
  }

  /**
   * 设置代码流数量
   */
  setStreamCount(count) {
    const currentCount = this.streams.length;
    
    if (count > currentCount) {
      // 添加更多代码流
      for (let i = currentCount; i < count; i++) {
        const x = Math.random() * this.canvas.width;
        const y = Math.random() * this.canvas.height;
        this.addStream(x, y);
      }
    } else if (count < currentCount) {
      // 移除多余的代码流
      this.streams = this.streams.slice(0, count);
    }
  }

  /**
   * 更新窗口大小
   */
  resize(width, height) {
    // 调整代码流位置以适应新尺寸
    this.streams.forEach((stream, index) => {
      if (stream.x > width) {
        stream.x = (stream.x / this.canvas.width) * width;
      }
      if (stream.y > height) {
        stream.y = (stream.y / this.canvas.height) * height;
      }
    });
  }
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CodeFlowEffect;
}
