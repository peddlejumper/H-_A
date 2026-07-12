#!/usr/bin/env node
import express from 'express';
import cors from 'cors';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// 项目根目录 (H# 源码位置)
const PROJECT_ROOT = path.resolve(__dirname, '../../../');

app.use(cors({ origin: '*' }));
app.use(express.json({ limit: '10mb' }));

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'ZZW Code server is running' });
});

// 列出目录内容
app.post('/api/browse', (req, res) => {
  try {
    const { dirPath } = req.body;
    const fullPath = dirPath ? path.resolve(PROJECT_ROOT, dirPath) : PROJECT_ROOT;

    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ error: 'Directory not found' });
    }

    const entries = fs.readdirSync(fullPath, { withFileTypes: true });
    const result = entries
      .filter(entry => !entry.name.startsWith('.') || entry.name === '.git')
      .map(entry => ({
        name: entry.name,
        isDirectory: entry.isDirectory(),
        path: path.join(dirPath || '', entry.name),
        extension: path.extname(entry.name).toLowerCase(),
      }))
      .sort((a, b) => {
        if (a.isDirectory !== b.isDirectory) {
          return b.isDirectory ? 1 : -1;
        }
        return a.name.localeCompare(b.name);
      });

    res.json({ currentPath: dirPath || '/', entries });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 读取文件内容
app.post('/api/read', (req, res) => {
  try {
    const { filePath } = req.body;
    const fullPath = path.resolve(PROJECT_ROOT, filePath);

    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ error: 'File not found' });
    }

    const content = fs.readFileSync(fullPath, 'utf-8');
    const stat = fs.statSync(fullPath);

    res.json({
      content,
      name: path.basename(filePath),
      path: filePath,
      size: stat.size,
      modified: stat.mtimeMs,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 保存文件内容
app.post('/api/save', (req, res) => {
  try {
    const { filePath, content } = req.body;
    const fullPath = path.resolve(PROJECT_ROOT, filePath);

    // 确保目录存在
    const dir = path.dirname(fullPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    fs.writeFileSync(fullPath, content, 'utf-8');
    res.json({ success: true, message: 'File saved successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建文件
app.post('/api/create', (req, res) => {
  try {
    const { filePath, content = '' } = req.body;
    const fullPath = path.resolve(PROJECT_ROOT, filePath);

    const dir = path.dirname(fullPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    if (fs.existsSync(fullPath)) {
      return res.status(409).json({ error: 'File already exists' });
    }

    fs.writeFileSync(fullPath, content, 'utf-8');
    res.json({ success: true, message: 'File created successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 删除文件
app.post('/api/delete', (req, res) => {
  try {
    const { filePath } = req.body;
    const fullPath = path.resolve(PROJECT_ROOT, filePath);

    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ error: 'File not found' });
    }

    fs.unlinkSync(fullPath);
    res.json({ success: true, message: 'File deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 重命名文件
app.post('/api/rename', (req, res) => {
  try {
    const { oldPath, newPath } = req.body;
    const oldFullPath = path.resolve(PROJECT_ROOT, oldPath);
    const newFullPath = path.resolve(PROJECT_ROOT, newPath);

    if (!fs.existsSync(oldFullPath)) {
      return res.status(404).json({ error: 'File not found' });
    }

    if (fs.existsSync(newFullPath)) {
      return res.status(409).json({ error: 'Target file already exists' });
    }

    fs.renameSync(oldFullPath, newFullPath);
    res.json({ success: true, message: 'Renamed successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 创建目录
app.post('/api/mkdir', (req, res) => {
  try {
    const { dirPath } = req.body;
    const fullPath = path.resolve(PROJECT_ROOT, dirPath);

    if (fs.existsSync(fullPath)) {
      return res.status(409).json({ error: 'Directory already exists' });
    }

    fs.mkdirSync(fullPath, { recursive: true });
    res.json({ success: true, message: 'Directory created successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 删除目录
app.post('/api/rmdir', (req, res) => {
  try {
    const { dirPath } = req.body;
    const fullPath = path.resolve(PROJECT_ROOT, dirPath);

    if (!fs.existsSync(fullPath)) {
      return res.status(404).json({ error: 'Directory not found' });
    }

    // 递归删除
    function rmrf(p) {
      if (fs.statSync(p).isDirectory()) {
        fs.readdirSync(p).forEach(child => rmrf(path.join(p, child)));
        fs.rmdirSync(p);
      } else {
        fs.unlinkSync(p);
      }
    }
    rmrf(fullPath);

    res.json({ success: true, message: 'Directory deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 运行 H# 代码
app.post('/api/run', (req, res) => {
  try {
    const { content } = req.body;

    // 将代码写入临时文件
    const tempFile = path.join(PROJECT_ROOT, '.tmp', `zzw-run-${Date.now()}.hto`);
    const tempDir = path.dirname(tempFile);
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    fs.writeFileSync(tempFile, content, 'utf-8');

    // 使用 Python 解释器执行
    const pythonCmd = process.env.PYTHON || 'python3';
    const interpreterPath = path.join(PROJECT_ROOT, 'interpreter.py');

    const output = [];
    const proc = spawn(pythonCmd, [interpreterPath, tempFile], {
      cwd: PROJECT_ROOT,
    });

    proc.stdout.on('data', (data) => {
      output.push(data.toString());
    });

    proc.stderr.on('data', (data) => {
      output.push(data.toString());
    });

    proc.on('close', (code) => {
      // 清理临时文件
      try { fs.unlinkSync(tempFile); } catch {}

      res.json({
        success: code === 0,
        exitCode: code,
        output: output.join(''),
      });
    });

    proc.on('error', (error) => {
      try { fs.unlinkSync(tempFile); } catch {}
      res.status(500).json({
        success: false,
        exitCode: 1,
        output: `Failed to spawn process: ${error.message}`,
      });
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      exitCode: 1,
      output: error.message,
    });
  }
});

// 获取项目信息
app.get('/api/project-info', (req, res) => {
  try {
    const rootExists = fs.existsSync(PROJECT_ROOT);
    const files = rootExists ? fs.readdirSync(PROJECT_ROOT).slice(0, 20) : [];
    res.json({
      projectRoot: PROJECT_ROOT,
      rootExists,
      files,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║  ZZW Code Backend Server                                    ║
╚════════════════════════════════════════════════════════════╝

  Server running at: http://localhost:${PORT}
  Project root: ${PROJECT_ROOT}
  Available endpoints:
    GET  /api/health             - Health check
    POST /api/browse            - Browse directories
    POST /api/read              - Read file content
    POST /api/save              - Save file content
    POST /api/create            - Create new file
    POST /api/delete            - Delete file
    POST /api/rename            - Rename file
    POST /api/mkdir             - Create directory
    POST /api/rmdir             - Delete directory
    POST /api/run               - Execute H# code
    GET  /api/project-info      - Get project info
`);
});
