// ═══════════════════════════════════════════════════════════════════════════
// app.js — 视图渲染与交互
// ═══════════════════════════════════════════════════════════════════════════

const VIEWS = {
  dashboard: { title: '仪表盘', render: renderDashboard },
  problems: { title: '题目管理', render: renderProblems },
  users: { title: '用户管理', render: renderUsers },
  submissions: { title: '提交审阅', render: renderSubmissions },
  panel: { title: '控制面板', render: renderPanel },
};

let currentView = 'dashboard';

// ── 视图切换 ──
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', (e) => {
    e.preventDefault();
    const view = item.dataset.view;
    if (view && VIEWS[view]) {
      currentView = view;
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      item.classList.add('active');
      document.getElementById('viewTitle').textContent = VIEWS[view].title;
      VIEWS[view].render();
    }
  });
});

document.getElementById('refreshBtn').addEventListener('click', () => {
  if (VIEWS[currentView]) VIEWS[currentView].render();
});

// ── 仪表盘 ──
async function renderDashboard() {
  const el = document.getElementById('content');
  el.innerHTML = '<div class="loading">加载统计数据...</div>';
  try {
    const stats = await Api.getStats();
    const diffBars = stats.difficultyDistribution.map(d => {
      const pct = d.total > 0 ? Math.round((d.count / d.total) * 100) : 0;
      const colors = { 0: '#059669', 1: '#d97706', 2: '#dc2626' };
      const names = { 0: '简单', 1: '中等', 2: '困难' };
      return `<div class="bar" style="height:${Math.max(pct, 2)}%;background:${colors[d.difficulty]}">
        <div class="bar-label">${names[d.difficulty]} ${d.count}</div>
      </div>`;
    }).join('');

    el.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">题目总数</div>
          <div class="stat-value">${stats.totalProblems}</div>
          <div class="stat-trend up">活跃 ${stats.activeProblems}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">注册用户</div>
          <div class="stat-value">${stats.totalUsers}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">提交总数</div>
          <div class="stat-value">${stats.totalSubmissions}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">通过率</div>
          <div class="stat-value">${(stats.acceptanceRate * 100).toFixed(1)}%</div>
          <div class="stat-trend up">通过 ${stats.acceptedSubmissions}</div>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-title">难度分布</div>
        <div class="bar-chart">${diffBars}</div>
      </div>
      <div class="chart-card">
        <div class="chart-title">Top 用户</div>
        <div class="table-wrap" style="border:none">
          <table>
            <thead><tr><th>用户</th><th>提交数</th><th>通过数</th><th>通过率</th></tr></thead>
            <tbody>
              ${stats.topUsers.map(u => `
                <tr>
                  <td>${u.displayName} <span style="color:#9ca3af">@${u.username}</span></td>
                  <td>${u.totalSubmissions}</td>
                  <td>${u.accepted}</td>
                  <td>${(u.acceptanceRate * 100).toFixed(1)}%</td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="loading" style="color:#dc2626">加载失败：${e.message}</div>`;
  }
}

// ── 题目管理 ──
async function renderProblems() {
  const el = document.getElementById('content');
  el.innerHTML = '<div class="loading">加载题目列表...</div>';
  try {
    const data = await Api.listProblems(1, 50);
    const rows = data.items.map(p => `
      <tr>
        <td><span style="font-family:var(--font-mono);color:#9ca3af">${p.code}</span></td>
        <td>${p.title}</td>
        <td><span class="badge badge-${['easy','medium','hard'][p.difficulty]}">${['简单','中等','困难'][p.difficulty]}</span></td>
        <td>${p.isActive ? '<span style="color:#059669">●</span> 启用' : '<span style="color:#9ca3af">○</span> 禁用'}</td>
        <td>${p.testCaseCount}</td>
        <td><button class="btn btn-ghost" onclick="editProblem('${p.id}')">编辑</button></td>
      </tr>`).join('');
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;margin-bottom:16px">
        <div style="display:flex;gap:8px">
          <input class="btn" placeholder="搜索题目..." id="problemSearch" style="width:240px">
        </div>
        <button class="btn btn-primary" onclick="newProblem()">+ 新建题目</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>题号</th><th>标题</th><th>难度</th><th>状态</th><th>测试用例</th><th>操作</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  } catch (e) {
    el.innerHTML = `<div class="loading" style="color:#dc2626">加载失败：${e.message}</div>`;
  }
}

// ── 用户管理 ──
async function renderUsers() {
  const el = document.getElementById('content');
  el.innerHTML = '<div class="loading">加载用户列表...</div>';
  try {
    const data = await Api.listUsers(1, 50);
    const rows = data.items.map(u => `
      <tr>
        <td><div style="display:flex;align-items:center;gap:8px"><div class="avatar" style="width:28px;height:28px;font-size:12px">${u.username[0].toUpperCase()}</div>${u.displayName}</div></td>
        <td>${u.username}</td>
        <td>${u.email}</td>
        <td><span class="badge badge-${u.role===2?'hard':u.role===1?'medium':'easy'}">${['学生','教师','管理员'][u.role]}</span></td>
        <td>${u.lastLoginAt ? new Date(u.lastLoginAt).toLocaleDateString() : '—'}</td>
        <td><button class="btn btn-ghost" onclick="editUser('${u.id}')">编辑</button></td>
      </tr>`).join('');
    el.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>用户</th><th>用户名</th><th>邮箱</th><th>角色</th><th>最后登录</th><th>操作</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  } catch (e) {
    el.innerHTML = `<div class="loading" style="color:#dc2626">加载失败：${e.message}</div>`;
  }
}

// ── 提交审阅 ──
async function renderSubmissions() {
  const el = document.getElementById('content');
  el.innerHTML = '<div class="loading">加载提交记录...</div>';
  try {
    const data = await Api.listSubmissions(1, 50);
    const statusMap = { 0:'待处理',1:'评测中',2:'通过',3:'答案错误',4:'超时',5:'运行错误',6:'编译错误' };
    const statusColor = { 0:'#9ca3af',1:'#2563eb',2:'#059669',3:'#dc2626',4:'#d97706',5:'#dc2626',6:'#dc2626' };
    const rows = data.items.map(s => `
      <tr>
        <td><span style="font-family:var(--font-mono);color:#9ca3af">${s.id.slice(0,8)}</span></td>
        <td>${s.username || '—'}</td>
        <td>${s.problemCode || '—'}</td>
        <td><span style="color:${statusColor[s.status]}">${statusMap[s.status]}</span></td>
        <td><span style="font-family:var(--font-mono)">${s.score}</span></td>
        <td>${new Date(s.submittedAt).toLocaleString()}</td>
        <td><button class="btn btn-ghost" onclick="Api.rejudge('${s.id}').then(()=>renderSubmissions())">重测</button></td>
      </tr>`).join('');
    el.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>用户</th><th>题目</th><th>状态</th><th>得分</th><th>提交时间</th><th>操作</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
  } catch (e) {
    el.innerHTML = `<div class="loading" style="color:#dc2626">加载失败：${e.message}</div>`;
  }
}

// ── 控制面板（H# 脚本）──
async function renderPanel() {
  const el = document.getElementById('content');
  el.innerHTML = '<div class="loading">加载脚本列表...</div>';
  try {
    const data = await Api.listScripts();
    const cards = data.scripts.map(s => `
      <div class="stat-card" style="cursor:pointer" onclick="runHSharpScript('${s}')">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-family:var(--font-mono);font-weight:600">${s}.hto</div>
            <div style="color:#6b7280;font-size:12px;margin-top:4px">H# 控制面板脚本</div>
          </div>
          <button class="btn btn-primary">执行</button>
        </div>
      </div>`).join('');
    el.innerHTML = `<div class="stats-grid" style="grid-template-columns:repeat(2,1fr)">${cards}</div>
      <div id="scriptOutput" style="margin-top:16px"></div>`;
  } catch (e) {
    el.innerHTML = `<div class="loading" style="color:#dc2626">加载失败：${e.message}</div>`;
  }
}

async function runHSharpScript(name) {
  const out = document.getElementById('scriptOutput');
  out.innerHTML = '<div class="loading">执行中...</div>';
  try {
    const result = await Api.runScript(name);
    out.innerHTML = `<div class="chart-card">
      <div class="chart-title">${name}.hto 执行结果</div>
      <pre style="background:#f3f4f6;padding:16px;border-radius:6px;overflow-x:auto;font-family:var(--font-mono);font-size:12px">${JSON.stringify(result, null, 2)}</pre>
    </div>`;
  } catch (e) {
    out.innerHTML = `<div class="loading" style="color:#dc2626">执行失败：${e.message}</div>`;
  }
}

// 占位函数
function editProblem(id) { alert('编辑题目：' + id); }
function newProblem() { alert('新建题目'); }
function editUser(id) { alert('编辑用户：' + id); }

// 初始加载
renderDashboard();
