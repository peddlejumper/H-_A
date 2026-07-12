// ═══════════════════════════════════════════════════════════════════════════
// api.js — API 客户端封装
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE = 'http://localhost:5000/api/v1';

const Api = {
  token: localStorage.getItem('ct_token') || '',

  async request(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;

    const resp = await fetch(url, { ...options, headers });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ message: '请求失败' }));
      throw new Error(err.message || `HTTP ${resp.status}`);
    }
    return resp.status === 204 ? null : resp.json();
  },

  // 题目
  listProblems: (page = 1, size = 20) => Api.request(`/problems?page=${page}&pageSize=${size}`),
  getProblem: (id) => Api.request(`/problems/${id}`),
  createProblem: (data) => Api.request('/problems', { method: 'POST', body: JSON.stringify(data) }),
  updateProblem: (id, data) => Api.request(`/problems/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProblem: (id) => Api.request(`/problems/${id}`, { method: 'DELETE' }),

  // 用户
  login: (username, password) => Api.request('/users/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  register: (data) => Api.request('/users/register', { method: 'POST', body: JSON.stringify(data) }),
  listUsers: (page = 1, size = 20) => Api.request(`/users?page=${page}&pageSize=${size}`),
  updateRole: (userId, role) => Api.request(`/users/${userId}/role?role=${role}`, { method: 'PATCH' }),

  // 提交
  listSubmissions: (page = 1, size = 20, status = null) =>
    Api.request(`/submissions?page=${page}&pageSize=${size}${status ? `&status=${status}` : ''}`),
  rejudge: (id) => Api.request(`/submissions/${id}/rejudge`, { method: 'POST' }),

  // 仪表盘
  getStats: () => Api.request('/dashboard/stats'),

  // 控制面板
  listScripts: () => Api.request('/panel/scripts'),
  runScript: (name) => Api.request(`/panel/run/${name}`, { method: 'POST' }),
};
