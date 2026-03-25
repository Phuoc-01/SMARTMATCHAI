const API_BASE = 'http://localhost:5000';

let allApplications = [];
let currentFilter = 'all';
let pendingWithdrawId = null;

// ── Utility ──────────────────────────────────────────────
function setStatus(msg, type = '') {
  const s = document.getElementById('statusMessage');
  s.textContent = msg;
  s.className = type; // 'error' | 'success' | ''
}

function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `show ${type}`;
  setTimeout(() => { t.className = ''; }, 3000);
}

function logout() {
  ['sm_token','sm_user','sm_user_id','sm_role'].forEach(k => localStorage.removeItem(k));
  window.location.href = 'auth.html';
}

document.getElementById('logoutBtn').addEventListener('click', logout);

// ── Auth header ───────────────────────────────────────────
function authHeaders() {
  return { 'Authorization': `Bearer ${localStorage.getItem('sm_token')}` };
}

// ── Stats ─────────────────────────────────────────────────
function updateStats(apps) {
  const total    = apps.length;
  const accepted = apps.filter(a => a.status?.toLowerCase() === 'accepted').length;
  const rejected = apps.filter(a => a.status?.toLowerCase() === 'rejected').length;
  const pending  = total - accepted - rejected;

  document.getElementById('statTotal').textContent    = total;
  document.getElementById('statAccepted').textContent = accepted;
  document.getElementById('statPending').textContent  = pending;
  document.getElementById('statRejected').textContent = rejected;

  document.getElementById('statsRow').style.display = 'grid';
  document.getElementById('filterBar').style.display = 'flex';
}

// ── Filter ────────────────────────────────────────────────
function applyFilter(filter) {
  currentFilter = filter;

  // update button styles
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.className = 'filter-btn';
    if (btn.dataset.filter === filter) {
      const classMap = {
        all: 'active', pending: 'active-amber',
        accepted: 'active-green', rejected: 'active-red'
      };
      btn.classList.add(classMap[filter] || 'active');
    }
  });

  const filtered = filter === 'all'
    ? allApplications
    : allApplications.filter(a => (a.status || 'pending').toLowerCase() === filter);

  renderApplications(filtered);
}

// ── Detail Modal ──────────────────────────────────────────
function scoreColor(score) {
  if (score >= 75) return '#22c55e';
  if (score >= 50) return '#f59e0b';
  return '#f87171';
}

function scoreRingSVG(score, color) {
  const r = 22; const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  return `
    <div class="score-ring-wrap">
      <svg width="56" height="56" viewBox="0 0 56 56">
        <circle cx="28" cy="28" r="${r}" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="5"/>
        <circle cx="28" cy="28" r="${r}" fill="none" stroke="${color}" stroke-width="5"
          stroke-dasharray="${fill} ${circ}" stroke-linecap="round"/>
      </svg>
      <div class="score-ring-label" style="color:${color};">${score}%</div>
    </div>`;
}

async function openDetailModal(appId) {
  const app = allApplications.find(a => (a.id || a._id) === appId);
  if (!app) return;

  // Open modal immediately with basic info
  document.getElementById('detailTitle').textContent = app.project_title || 'Unknown Project';
  document.getElementById('detailBadges').innerHTML = statusBadge(app.status);
  document.getElementById('detailBody').innerHTML = `<div class="detail-loading">Đang tải chi tiết dự án…</div>`;
  document.getElementById('detailFooter').innerHTML = '';
  document.getElementById('detailModal').classList.add('open');

  const score = Math.round(app.match_score || 0);
  const color = scoreColor(score);
  const status = (app.status || 'pending').toLowerCase();

  // Try fetching full project details
  let project = null;
  const projectId = app.project_id || app.projectId;
  if (projectId) {
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}`, {
        headers: authHeaders()
      });
      if (res.ok) project = await res.json();
    } catch (_) {}
  }

  // Build detail body (use project data if available, fallback to app fields)
  const desc = project?.description || app.project_description || 'Không có mô tả.';
  const skills = project?.required_skills || app.required_skills || [];
  const deadline = project?.deadline || app.deadline;
  const slots = project?.slots ?? project?.max_members ?? app.slots ?? '–';
  const category = project?.category || app.project_category || '–';
  const owner = project?.owner_name || project?.created_by || app.owner_name || '–';
  const dateStr = app.applied_at
    ? new Date(app.applied_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })
    : 'N/A';
  const deadlineStr = deadline
    ? new Date(deadline).toLocaleDateString('vi-VN', { dateStyle: 'medium' })
    : '–';

  const skillsHTML = skills.length
    ? skills.map(s => `<span class="skill-tag">${s}</span>`).join('')
    : '<span style="color:var(--text-muted);font-size:0.82rem;">Chưa có thông tin</span>';

  document.getElementById('detailBody').innerHTML = `
    <!-- Match score -->
    <div>
      <div class="detail-section-label">Match Score</div>
      <div class="detail-score-big">
        ${scoreRingSVG(score, color)}
        <div class="score-ring-desc">
          <strong>${score >= 75 ? 'Phù hợp cao' : score >= 50 ? 'Phù hợp trung bình' : 'Phù hợp thấp'}</strong>
          Dựa trên kỹ năng và hồ sơ của bạn so với yêu cầu dự án.
        </div>
      </div>
    </div>

    <!-- Description -->
    <div>
      <div class="detail-section-label">Mô tả dự án</div>
      <div class="detail-desc">${desc}</div>
    </div>

    <!-- Required skills -->
    <div>
      <div class="detail-section-label">Kỹ năng yêu cầu</div>
      <div class="skills-wrap">${skillsHTML}</div>
    </div>

    <!-- Meta grid -->
    <div>
      <div class="detail-section-label">Thông tin chung</div>
      <div class="detail-grid">
        <div class="detail-kv">
          <div class="dk-label">Danh mục</div>
          <div class="dk-val">${category}</div>
        </div>
        <div class="detail-kv">
          <div class="dk-label">Số lượng</div>
          <div class="dk-val">${slots} người</div>
        </div>
        <div class="detail-kv">
          <div class="dk-label">Chủ dự án</div>
          <div class="dk-val">${owner}</div>
        </div>
        <div class="detail-kv">
          <div class="dk-label">Deadline</div>
          <div class="dk-val">${deadlineStr}</div>
        </div>
        <div class="detail-kv">
          <div class="dk-label">Ngày ứng tuyển</div>
          <div class="dk-val">${dateStr}</div>
        </div>
        <div class="detail-kv">
          <div class="dk-label">Trạng thái</div>
          <div class="dk-val">${status.charAt(0).toUpperCase() + status.slice(1)}</div>
        </div>
      </div>
    </div>
  `;

  // Footer actions
  document.getElementById('detailFooter').innerHTML = `
    <button class="btn-modal-cancel" onclick="closeDetailModal()">Đóng</button>
    ${status === 'pending'
      ? `<button class="btn btn-danger" style="font-size:0.82rem;padding:9px 20px;"
           onclick="closeDetailModal(); openWithdrawModal('${appId}', '${(app.project_title||'').replace(/'/g,"\\'")}', ${score})">
           Rút đơn
         </button>`
      : ''}
  `;
}

function closeDetailModal() {
  document.getElementById('detailModal').classList.remove('open');
}

document.getElementById('detailModal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeDetailModal();
});


// ── Status badge ──────────────────────────────────────────
function statusBadge(status) {
  const s = (status || 'pending').toLowerCase();
  const labels = { accepted: 'Accepted', rejected: 'Rejected', pending: 'Pending' };
  const cls    = { accepted: 'badge-accepted', rejected: 'badge-rejected', pending: 'badge-pending' };
  return `<span class="badge ${cls[s] || 'badge-pending'}">${labels[s] || 'Pending'}</span>`;
}

// ── Render ────────────────────────────────────────────────
function renderApplications(apps) {
  const container = document.getElementById('applicationsList');
  const empty     = document.getElementById('emptyState');

  container.innerHTML = '';

  if (!apps || apps.length === 0) {
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  apps.forEach((app, i) => {
    const score   = Math.round(app.match_score || 0);
    const color   = scoreColor(score);
    const dateStr = app.applied_at
      ? new Date(app.applied_at).toLocaleString('vi-VN', { dateStyle: 'medium', timeStyle: 'short' })
      : 'N/A';
    const status  = (app.status || 'pending').toLowerCase();

    const card = document.createElement('div');
    card.className = 'app-card';
    card.style.animationDelay = `${i * 0.05}s`;
    card.dataset.appId = app.id || app._id || '';

    card.innerHTML = `
      <div class="app-left">
        <div class="app-title">${app.project_title || 'Unknown Project'}</div>
        <div class="app-meta">
          <div class="score-wrap">
            <div class="score-bar-bg">
              <div class="score-bar-fill" style="width:${score}%; background:${color};"></div>
            </div>
            <span class="score-text" style="color:${color};">${score}%</span>
          </div>
          <div class="meta-item">
            <span class="meta-icon">🕐</span>
            <span>${dateStr}</span>
          </div>
          ${app.project_category ? `<div class="meta-item"><span class="meta-icon">🏷</span><span>${app.project_category}</span></div>` : ''}
          <div class="meta-item" style="color:var(--accent);font-size:0.72rem;">Xem chi tiết →</div>
        </div>
      </div>
      <div class="app-right">
        ${statusBadge(app.status)}
        ${status === 'pending' || status === ''
          ? `<button class="btn btn-danger" onclick="event.stopPropagation(); openWithdrawModal('${card.dataset.appId}', '${(app.project_title || '').replace(/'/g, "\\'")}', ${score})">Rút đơn</button>`
          : ''}
      </div>
    `;

    card.addEventListener('click', () => openDetailModal(card.dataset.appId));

    container.appendChild(card);
  });
}

// ── Withdraw modal ────────────────────────────────────────
function openWithdrawModal(appId, projectTitle, score) {
  pendingWithdrawId = appId;
  document.getElementById('modalInfo').innerHTML = `
    <div class="mi-row"><span class="mi-label">Dự án</span><span class="mi-val">${projectTitle}</span></div>
    <div class="mi-row"><span class="mi-label">Match score</span><span class="mi-val" style="color:${scoreColor(score)}">${score}%</span></div>
  `;
  document.getElementById('withdrawModal').classList.add('open');
}

function closeModal() {
  document.getElementById('withdrawModal').classList.remove('open');
  pendingWithdrawId = null;
}

// close on overlay click
document.getElementById('withdrawModal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});

async function confirmWithdraw() {
  if (!pendingWithdrawId) return;
  const btn = document.getElementById('confirmWithdrawBtn');
  btn.disabled = true;
  btn.textContent = 'Đang xử lý...';

  try {
    const res = await fetch(`${API_BASE}/api/student/applications/${pendingWithdrawId}`, {
      method: 'DELETE',
      headers: authHeaders()
    });

    if (res.status === 401) { logout(); return; }

    if (res.ok) {
      allApplications = allApplications.filter(
        a => (a.id || a._id) !== pendingWithdrawId
      );
      closeModal();
      updateStats(allApplications);
      applyFilter(currentFilter);
      showToast('✓ Đã rút đơn thành công', 'success');
      setStatus(`Còn lại ${allApplications.length} đơn ứng tuyển.`, 'success');
    } else {
      const data = await res.json().catch(() => ({}));
      showToast(data.message || 'Không thể rút đơn.', 'error');
    }
  } catch (err) {
    console.error(err);
    showToast('Lỗi kết nối server.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Xác nhận rút đơn';
  }
}

// ── Skeleton loader ───────────────────────────────────────
function showSkeleton() {
  const container = document.getElementById('applicationsList');
  container.innerHTML = Array(4).fill(0).map(() =>
    `<div class="skeleton-card"></div>`
  ).join('');
}

// ── Load ──────────────────────────────────────────────────
async function loadApplications() {
  const token = localStorage.getItem('sm_token');
  if (!token) { window.location.href = 'auth.html'; return; }

  showSkeleton();
  setStatus('Đang tải dữ liệu...', '');

  try {
    const res = await fetch(`${API_BASE}/api/student/applications`, {
      headers: authHeaders()
    });

    if (res.status === 401) { logout(); return; }

    const data = await res.json();
    if (!res.ok) {
      setStatus(data.message || 'Không thể tải danh sách ứng tuyển.', 'error');
      document.getElementById('applicationsList').innerHTML = '';
      return;
    }

    allApplications = data.applications || [];
    updateStats(allApplications);
    applyFilter('all');
    setStatus(`Đã tải ${allApplications.length} đơn ứng tuyển.`, 'success');

  } catch (err) {
    console.error(err);
    document.getElementById('applicationsList').innerHTML = '';
    setStatus('Lỗi kết nối với server.', 'error');
  }
}

loadApplications();