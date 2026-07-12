async function request<T>(method: string, endpoint: string, body?: unknown): Promise<T> {
  const options: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  // Uses Vite proxy in dev mode, direct URL in production
  const url = endpoint;
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// 健康检查
export async function healthCheck(): Promise<{ status: string }> {
  return request('GET', '/api/health');
}

// 列出目录
export interface BrowseEntry {
  name: string;
  isDirectory: boolean;
  path: string;
  extension: string;
}

export async function browseDirectory(dirPath: string = ''): Promise<{
  currentPath: string;
  entries: BrowseEntry[];
}> {
  return request('POST', '/api/browse', { dirPath });
}

// 读取文件
export interface ReadFileResult {
  content: string;
  name: string;
  path: string;
  size: number;
  modified: number;
}

export async function readFile(filePath: string): Promise<ReadFileResult> {
  return request('POST', '/api/read', { filePath });
}

// 保存文件
export async function saveFile(filePath: string, content: string): Promise<{ success: boolean }> {
  return request('POST', '/api/save', { filePath, content });
}

// 创建文件
export async function createFile(filePath: string, content: string = ''): Promise<{ success: boolean }> {
  return request('POST', '/api/create', { filePath, content });
}

// 删除文件
export async function deleteFile(filePath: string): Promise<{ success: boolean }> {
  return request('POST', '/api/delete', { filePath });
}

// 重命名文件
export async function renameFile(oldPath: string, newPath: string): Promise<{ success: boolean }> {
  return request('POST', '/api/rename', { oldPath, newPath });
}

// 创建目录
export async function createDirectory(dirPath: string): Promise<{ success: boolean }> {
  return request('POST', '/api/mkdir', { dirPath });
}

// 删除目录
export async function deleteDirectory(dirPath: string): Promise<{ success: boolean }> {
  return request('POST', '/api/rmdir', { dirPath });
}

// 运行 H# 代码
export interface RunResult {
  success: boolean;
  exitCode: number;
  output: string;
}

export async function runCode(content: string): Promise<RunResult> {
  return request('POST', '/api/run', { content });
}

// 获取项目信息
export async function getProjectInfo(): Promise<{
  projectRoot: string;
  rootExists: boolean;
  files: string[];
}> {
  return request('GET', '/api/project-info');
}