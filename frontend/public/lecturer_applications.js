/* ═══════════════════════════════════════════════
   Smart Match AI – lecturer_applications.js
   Lecturer: review & manage all applications
   across their projects, grouped by project.
═══════════════════════════════════════════════ */

const API   = `http://${location.hostname}:5000`;
const token = localStorage.getItem('sm_token');
const role  = localStorage.getItem('sm_role');
const user  = JSON.parse(localStorage.getItem('sm_user') || '{}');

// Auth guard
if (!token || role !== 'lecturer') { location.href = 'auth.html'; }

const $ = id => document.getElementById(id);

// ── Sidebar user
$('sidebarUser').textContent = user.full_name || user.email || '';

// ── Logout
$('logoutBtn').addEventListener('click', () => {
  ['sm_token','sm_user','sm_user_id','sm_role'].forEach(k => localStorage.removeItem(k));
  location.href = 'auth.html';
});

// ── Toast
function toast(msg, type = 'success') {
  const t = $('toast');
  t.textContent = msg;
  t.className = type;
  setTimeout(() => { t.className = 'hidden'; }, 3500);
}

function setStatus(msg) {
  $('statusMsg').textContent = msg;
}

// ── State
let allProjects = [];         // [{project, applications:[]}]
let currentFilter = 'all';
let pendingReview = null;     // { appId, action, projectId }

// ── Score color
function scoreColor(s) {
  if (s >= 75) return '#16a34a';
  if (s >= 50) return '#d97706';
  return '#dc2626';
}

// ── Status tag HTML
function statusTag(s) {
  const map = {
    pending:  ['tag-pending',  'Chờ duyệt'],
    accepted: ['tag-accepted', 'Chấp nhận'],
    rejected: ['tag-rejected', 'Từ chối'],
  };
  const [cls, label] = map[s] || ['tag-pending', s];
  return `<span class="tag ${cls}">${label}</span>`;
}

// ── Count visible apps in a project group based on filter
function visibleApps(apps) {
  if (currentFilter === 'all') return apps;
  return apps.filter(a => (a.status || 'pending').toLowerCase() === currentFilter);
}

// ── Update stats
function updateStats() {
  const all = allProjects.flatMap(g => g.applications);
  const total    = all.length;
  const pending  = all.filter(a => (a.status||'pending') === 'pending').length;
  const accepted = all.filter(a => a.status === 'accepted').length;
  const rejected = all.filter(a => a.status === 'rejected').length;

  $('statTotal').textContent    = total;
  $('statPending').textContent  = pending;
  $('statAccepted').textContent = accepted;
  $('statRejected').textContent = rejected;

  $('statsRow').style.display = 'grid';
  $('filterBar').style.display = 'flex';
}

// ── Apply filter
function applyFilter(filter) {
  currentFilter = filter;

  // Update filter button styles
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.className = 'filter-btn';
    if (btn.dataset.filter === filter) {
      const cls = { all:'active', pending:'active-amber', accepted:'active-green', rejected:'active-red' };
      btn.classList.add(cls[filter] || 'active');
    }
  });

  renderGroups();
}

// ── Render all project groups
function renderGroups() {
  const container = $('projectGroups');
  container.innerHTML = '';

  // Check if any data to show
  const anyVisible = allProjects.some(g => visibleApps(g.applications).length > 0);
  if (!anyVisible) {
    container.innerHTML = `<div class="empty">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2"/></svg>
      <p style="margin-top:12px;">Không có đơn nào phù hợp với bộ lọc.</p>
    </div>`;
    return;
  }

  allProjects.forEach((group, gi) => {
    const apps = visibleApps(group.applications);
    if (!apps.length) return;

    const p = group.project;
    const pendingCount = apps.filter(a => (a.status||'pending') === 'pending').length;

    const section = document.createElement('div');
    section.className = 'project-group';

    // Group header (collapsible)
    const isOpen = gi === 0; // first group open by default
    section.innerHTML = `
      <div class="group-header" data-gi="${gi}">
        <div class="group-left">
          <span class="group-title">${p.title}</span>
          <span class="tag ${p.status==='open'?'tag-accepted':'tag-rejected'}" style="font-size:10px;">${p.status==='open'?'Đang mở':'Đã đóng'}</span>
          ${pendingCount ? `<span class="tag tag-pending" style="font-size:10px;">${pendingCount} chờ duyệt</span>` : ''}
        </div>
        <div class="group-right">
          <span class="group-count">${apps.length} đơn</span>
          <span class="chevron ${isOpen?'open'}">▼</span>
        </div>
      </div>
      <div class="app-rows ${isOpen?'open'}">
        <div class="table-header">
          <div class="th">Sinh viên</div>
          <div class="th center">Match</div>
          <div class="th">Trạng thái</div>
          <div class="th right">Hành động</div>
        </div>
        <div class="rows-body" id="rows-${gi}"></div>
      </div>
    `;

    // Toggle collapse
    section.querySelector('.group-header').addEventListener('click', () => {
      const rows  = section.querySelector('.app-rows');
      const chev  = section.querySelector('.chevron');
      rows.classList.toggle('open');
      chev.classList.toggle('open');
    });

    container.appendChild(section);

    // Render rows
    const tbody = $(`rows-${gi}`);
    apps.forEach((app, ai) => {
      const score  = Math.round(app.match_score || 0);
      const color  = scoreColor(score);
      const status = (app.status || 'pending').toLowerCase();
      const skills = (app.student_skills || []).slice(0, 4).join(', ');
      const letter = app.application_text
        ? `"${app.application_text.substring(0, 90)}${app.application_text.length > 90 ? '…' : ''}"`
        : '';

      const row = document.createElement('div');
      row.className = 'app-row';
      row.style.animationDelay = `${ai * 0.04}s`;
      row.innerHTML = `
        <div>
          <div class="app-student-name">${app.student_name || '—'}</div>
          ${skills ? `<div class="app-student-meta">${skills}</div>` : ''}
          ${letter ? `<div class="app-student-letter">${letter}</div>` : ''}
        </div>
        <div class="score-col">
          <div class="score-num" style="color:${color};">${score}%</div>
          <div class="score-bar-bg">
            <div class="score-bar-fill" style="width:${score}%;background:${color};"></div>
          </div>
        </div>
        <div>${statusTag(status)}</div>
        <div class="action-col">
          ${status === 'pending' ? `
            <button class="btn btn-success btn-sm" data-appid="${app.id}" data-action="accepted" data-pid="${p.id}">✓ Chấp nhận</button>
            <button class="btn btn-danger  btn-sm" data-appid="${app.id}" data-action="rejected" data-pid="${p.id}">✗ Từ chối</button>
          ` : `<span style="font-size:12px;color:var(--gray-400);">Đã xử lý</span>`}
        </div>
      `;

      row.querySelectorAll('[data-action]').forEach(btn => {
        btn.addEventListener('click', () => {
          openReviewModal(btn.dataset.appid, btn.dataset.action, btn.dataset.pid, app.student_name, p.title, score);
        });
      });

      tbody.appendChild(row);
    });
  });
}

// ── Review modal ──────────────────────────────
function openReviewModal(appId, action, projectId, studentName, projectTitle, score) {
  pendingReview = { appId, action, projectId };

  const isAccept = action === 'accepted';
  $('reviewModalTitle').textContent = isAccept ? 'Xác nhận chấp nhận đơn' : 'Xác nhận từ chối đơn';
  $('reviewModalDesc').textContent  = isAccept
    ? 'Sinh viên sẽ được thông báo và trạng thái đơn sẽ cập nhật ngay lập tức.'
    : 'Đơn sẽ bị từ chối. Sinh viên vẫn có thể nộp đơn cho dự án khác.';
  $('reviewModalInfo').innerHTML = `
    <div class="mi-row"><span class="mi-label">Sinh viên</span><span class="mi-val">${studentName || '—'}</span></div>
    <div class="mi-row"><span class="mi-label">Dự án</span><span class="mi-val">${projectTitle}</span></div>
    <div class="mi-row"><span class="mi-label">Match score</span><span class="mi-val" style="color:${scoreColor(score)}">${score}%</span></div>
  `;

  const confirmBtn = $('reviewConfirmBtn');
  confirmBtn.textContent = isAccept ? 'Xác nhận chấp nhận' : 'Xác nhận từ chối';
  confirmBtn.className   = `btn-confirm ${isAccept ? 'btn-confirm-accept' : 'btn-confirm-reject'}`;

  $('reviewModal').classList.remove('hidden');
}

function closeReviewModal() {
  $('reviewModal').classList.add('hidden');
  pendingReview = null;
}

$('reviewModal').addEventListener('click', e => {
  if (e.target === $('reviewModal')) closeReviewModal();
});

async function confirmReview() {
  if (!pendingReview) return;
  const { appId, action, projectId } = pendingReview;

  const btn = $('reviewConfirmBtn');
  btn.disabled = true;
  btn.textContent = 'Đang xử lý...';

  try {
    const res = await fetch(`${API}/api/lecturer/applications/${appId}/review`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ status: action })
    });

    if (res.status === 401) { location.href = 'auth.html'; return; }

    if (res.ok) {
      // Update local state
      allProjects.forEach(g => {
        const app = g.applications.find(a => a.id === appId);
        if (app) app.status = action;
      });
      closeReviewModal();
      updateStats();
      renderGroups();
      toast(action === 'accepted' ? '✓ Đã chấp nhận đơn ứng tuyển!' : '✓ Đã từ chối đơn ứng tuyển.', 'success');
    } else {
      const data = await res.json().catch(() => ({}));
      toast(data.message || 'Không thể cập nhật trạng thái.', 'error');
    }
  } catch (err) {
    console.error(err);
    toast('Lỗi kết nối server.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = pendingReview
      ? (pendingReview.action === 'accepted' ? 'Xác nhận chấp nhận' : 'Xác nhận từ chối')
      : 'Xác nhận';
  }
}

// ── Skeleton loader
function showSkeleton() {
  $('projectGroups').innerHTML = Array(3).fill(0).map(() => `
    <div class="skeleton-row"><div class="skel-line"></div><div class="skel-line short"></div></div>
  `).join('');
}

// ── Load data ─────────────────────────────────
async function load() {
  showSkeleton();
  setStatus('Đang tải dữ liệu...');

  try {
    // 1. Get lecturer's projects
    const projRes = await fetch(`${API}/api/lecturer/projects`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (projRes.status === 401) { location.href = 'auth.html'; return; }
    const projData = await projRes.json();
    const projects = projData.projects || [];

    if (!projects.length) {
      $('projectGroups').innerHTML = `<div class="empty">
        <p>Bạn chưa có dự án nào. <a href="dashboard.html" style="color:var(--blue);">Tạo dự án đầu tiên →</a></p>
      </div>`;
      setStatus('');
      return;
    }

    // 2. Fetch applications for each project in parallel
    const groups = await Promise.all(projects.map(async p => {
      try {
        const res = await fetch(`${API}/api/lecturer/projects/${p.id}/applications`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const data = res.ok ? await res.json() : { applications: [] };
        // Sort by match score desc
        const apps = (data.applications || []).sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
        return { project: p, applications: apps };
      } catch (_) {
        return { project: p, applications: [] };
      }
    }));

    // Sort groups: projects with pending apps first
    groups.sort((a, b) => {
      const pa = a.applications.filter(x => (x.status||'pending') === 'pending').length;
      const pb = b.applications.filter(x => (x.status||'pending') === 'pending').length;
      return pb - pa;
    });

    allProjects = groups;

    updateStats();
    applyFilter('all');

    const total = groups.reduce((s, g) => s + g.applications.length, 0);
    setStatus(`Đã tải ${total} đơn ứng tuyển từ ${projects.length} dự án.`);

  } catch (err) {
    console.error(err);
    $('projectGroups').innerHTML = '<div class="empty"><p>Lỗi kết nối server.</p></div>';
    setStatus('Lỗi kết nối.', 'error');
  }
}

load();