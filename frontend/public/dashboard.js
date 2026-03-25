/* ═══════════════════════════════════
   Smart Match AI – dashboard.js
   Handles both student & lecturer views
═══════════════════════════════════ */

const API = `http://${location.hostname}:5000`;

/* ── Helpers ── */
const $  = id  => document.getElementById(id);
const q  = sel => document.querySelector(sel);

function toast(msg, type = 'success') {
  const t = $('toast');
  t.textContent = msg;
  t.className = type;
  setTimeout(() => { t.className = 'hidden'; }, 3500);
}

function parseList(str) {
  return (str || '').split(',').map(s => s.trim()).filter(Boolean);
}

function difficultyLabel(d) {
  return { easy: 'Dễ', medium: 'Trung bình', hard: 'Khó' }[d] || d || '—';
}

function statusTag(s) {
  const map = {
    pending:  ['tag-yellow', 'Chờ duyệt'],
    accepted: ['tag-green',  'Chấp nhận'],
    rejected: ['tag-red',    'Từ chối'],
    open:     ['tag-blue',   'Đang mở'],
    closed:   ['tag-gray',   'Đã đóng'],
    completed:['tag-green',  'Hoàn thành'],
  };
  const [cls, label] = map[s] || ['tag-gray', s || '—'];
  return `<span class="tag ${cls}">${label}</span>`;
}

/* ── Auth guard ── */
const token = localStorage.getItem('sm_token');
const role  = localStorage.getItem('sm_role');
const user  = JSON.parse(localStorage.getItem('sm_user') || '{}');

if (!token) { location.href = 'auth.html'; }

/* ── Sidebar user info ── */
$('sidebarUser').textContent = user.full_name || user.email || '';

/* ── Role-specific nav ── */
if (role === 'lecturer') {
  $('navApplications').href = 'lecturer_applications.html';
  $('navApplyLabel').textContent = 'Quản lý ứng tuyển';
  $('navProfile').href = 'profile.html';
}

/* ── Logout ── */
$('logoutBtn').addEventListener('click', () => {
  ['sm_token','sm_user','sm_user_id','sm_role'].forEach(k => localStorage.removeItem(k));
  location.href = 'auth.html';
});

/* ══════════════════════════════════════
   STUDENT DASHBOARD
══════════════════════════════════════ */
async function initStudent() {
  $('roleBadge').textContent = 'Sinh viên';
  $('roleBadge').className = 'role-badge role-student';
  $('pageSubtitle').textContent = 'Dự án gợi ý được cá nhân hóa từ hồ sơ của bạn.';
  $('studentView').style.display = '';
  $('lecturerView').style.display = 'none';

  // Top actions
  $('topActions').innerHTML = `
    <a href="profile.html" class="btn btn-outline">Cập nhật hồ sơ</a>
    <a href="my_applications.html" class="btn btn-primary">Đơn ứng tuyển của tôi</a>`;

  const grid = $('projectGrid');
  grid.innerHTML = '<div class="empty"><div class="spinner"></div><p style="margin-top:12px;">Đang tải gợi ý...</p></div>';

  try {
    const [recRes, appRes] = await Promise.all([
      fetch(`${API}/api/student/projects/recommended`, { headers: { Authorization: `Bearer ${token}` } }),
      fetch(`${API}/api/student/applications`,          { headers: { Authorization: `Bearer ${token}` } }),
    ]);

    if (recRes.status === 401) { location.href = 'auth.html'; return; }

    const recData = await recRes.json();
    const appData = appRes.ok ? await appRes.json() : { applications: [] };

    const recs  = recData.recommendations || [];
    const apps  = appData.applications    || [];

    // Stats
    $('statsRow').innerHTML = `
      <div class="stat-card"><div class="label">Gợi ý</div><div class="value">${recs.length}</div><div class="sub">dự án phù hợp</div></div>
      <div class="stat-card"><div class="label">Đã ứng tuyển</div><div class="value">${apps.length}</div><div class="sub">tổng đơn</div></div>
      <div class="stat-card"><div class="label">Chờ duyệt</div><div class="value">${apps.filter(a=>a.status==='pending').length}</div><div class="sub">đơn đang xử lý</div></div>
      <div class="stat-card"><div class="label">Match cao nhất</div><div class="value">${recs.length ? Math.round((recs[0].score || 0)*100) + '%' : '—'}</div><div class="sub">điểm tốt nhất</div></div>`;

    $('recCount').textContent = `${recs.length} dự án`;

    if (!recs.length) {
      grid.innerHTML = `<div class="empty">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M8 15s1.5-2 4-2 4 2 4 2M9 9h.01M15 9h.01"/></svg>
        <p>Chưa có dự án phù hợp.<br/>Hãy cập nhật hồ sơ và kỹ năng của bạn.</p>
        <a href="profile.html" class="btn btn-primary" style="margin-top:14px;">Cập nhật hồ sơ</a></div>`;
      return;
    }

    grid.innerHTML = '';
    recs.forEach(p => {
      const pct     = Math.round((p.score || 0) * 100);
      const applied = p.has_applied;
      const appStatus = p.application_status;
      const card = document.createElement('div');
      card.className = 'project-card';
      card.innerHTML = `
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
          <h3>${p.title}</h3>
          ${statusTag(p.status)}
        </div>
        <p style="-webkit-line-clamp:3;display:-webkit-box;-webkit-box-orient:vertical;overflow:hidden;">${p.description}</p>
        <div class="card-meta">
          ${p.research_field ? `<span class="tag tag-blue">${p.research_field}</span>` : ''}
          <span class="tag tag-gray">${difficultyLabel(p.difficulty_level)}</span>
          ${(p.required_skills||[]).slice(0,3).map(s=>`<span class="tag tag-gray">${s}</span>`).join('')}
        </div>
        <div>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--gray-400);margin-bottom:4px;">
            <span>Độ phù hợp</span><span class="score-label">${pct}%</span>
          </div>
          <div class="score-bar-wrap"><div class="score-bar" style="width:${pct}%"></div></div>
        </div>
        <div style="font-size:11.5px;color:var(--gray-600);line-height:1.4;margin-top:2px;">${p.explanation || ''}</div>
        <div class="card-footer">
          <div style="font-size:11px;color:var(--gray-400);">
            ${p.lecturer_name ? `👤 ${p.lecturer_name}` : ''}
            ${p.duration_weeks ? ` · ${p.duration_weeks} tuần` : ''}
            ${p.deadline ? ` · HSD: ${p.deadline}` : ''}
          </div>
          ${applied
            ? `<span class="tag ${appStatus==='accepted'?'tag-green':appStatus==='rejected'?'tag-red':'tag-yellow'}">${appStatus==='accepted'?'Chấp nhận':appStatus==='rejected'?'Từ chối':'Đã ứng tuyển'}</span>`
            : `<button class="btn btn-primary btn-sm apply-btn" data-id="${p.id}" data-title="${p.title.replace(/"/g,'')}">${p.status!=='open'?'Đã đóng':'Ứng tuyển'}</button>`
          }
        </div>`;
      if (!applied && p.status === 'open') {
        card.querySelector('.apply-btn').addEventListener('click', () => openApplyModal(p.id, p.title));
      } else if (!applied) {
        card.querySelector('.apply-btn').disabled = true;
      }
      grid.appendChild(card);
    });

  } catch (err) {
    console.error(err);
    grid.innerHTML = '<div class="empty"><p>Lỗi kết nối server.</p></div>';
  }
}

/* ── Apply modal ── */
let _applyProjectId = null;
function openApplyModal(id, title) {
  _applyProjectId = id;
  $('applyModalTitle').textContent = `Ứng tuyển: ${title}`;
  $('applyText').value = '';
  $('applyModal').classList.remove('hidden');
}
$('closeApply').addEventListener('click',  () => $('applyModal').classList.add('hidden'));
$('cancelApply').addEventListener('click', () => $('applyModal').classList.add('hidden'));
$('applyModal').addEventListener('click', e => { if (e.target === $('applyModal')) $('applyModal').classList.add('hidden'); });

$('confirmApply').addEventListener('click', async () => {
  if (!_applyProjectId) return;
  $('confirmApply').disabled = true;
  $('confirmApply').textContent = 'Đang gửi...';
  try {
    const res = await fetch(`${API}/api/student/projects/${_applyProjectId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ application_text: $('applyText').value })
    });
    const data = await res.json();
    $('applyModal').classList.add('hidden');
    if (res.ok) {
      toast('Ứng tuyển thành công!', 'success');
      initStudent();
    } else {
      toast(data.message || 'Ứng tuyển thất bại', 'error');
    }
  } catch(err) {
    toast('Lỗi kết nối', 'error');
  } finally {
    $('confirmApply').disabled = false;
    $('confirmApply').textContent = 'Nộp đơn';
  }
});

/* ══════════════════════════════════════
   LECTURER DASHBOARD
══════════════════════════════════════ */
async function initLecturer() {
  $('roleBadge').textContent = 'Giảng viên';
  $('roleBadge').className = 'role-badge role-lecturer';
  $('pageSubtitle').textContent = 'Quản lý dự án nghiên cứu và đơn ứng tuyển.';
  $('studentView').style.display = 'none';
  $('lecturerView').style.display = '';
  $('navApplications').style.display = 'none';

  $('topActions').innerHTML = `<button class="btn btn-primary" id="topNewProject">+ Tạo dự án mới</button>`;
  $('topNewProject').addEventListener('click', openProjectModal);

  await loadLecturerProjects();
}

async function loadLecturerProjects() {
  const grid = $('lecProjectGrid');
  grid.innerHTML = '<div class="empty"><div class="spinner"></div><p style="margin-top:12px;">Đang tải...</p></div>';

  try {
    const res = await fetch(`${API}/api/lecturer/projects`, { headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 401) { location.href = 'auth.html'; return; }
    const data = await res.json();
    const projects = data.projects || [];

    // Stats
    const total   = projects.length;
    const open    = projects.filter(p => p.status === 'open').length;
    const pending = projects.reduce((s, p) => s + (p.pending_applications || 0), 0);
    const total_a = projects.reduce((s, p) => s + (p.applications_count  || 0), 0);

    $('statsRow').innerHTML = `
      <div class="stat-card"><div class="label">Dự án</div><div class="value">${total}</div><div class="sub">tổng số</div></div>
      <div class="stat-card"><div class="label">Đang mở</div><div class="value">${open}</div><div class="sub">nhận ứng tuyển</div></div>
      <div class="stat-card"><div class="label">Ứng tuyển</div><div class="value">${total_a}</div><div class="sub">tổng đơn</div></div>
      <div class="stat-card"><div class="label">Chờ duyệt</div><div class="value">${pending}</div><div class="sub">cần xử lý</div></div>`;

    if (!projects.length) {
      grid.innerHTML = `<div class="empty">
        <p>Chưa có dự án nào.<br/>Tạo dự án đầu tiên để bắt đầu nhận ứng tuyển.</p>
        <button class="btn btn-primary" style="margin-top:14px;" onclick="openProjectModal()">+ Tạo dự án</button></div>`;
      return;
    }

    grid.innerHTML = '';
    projects.forEach(p => {
      const card = document.createElement('div');
      card.className = 'project-card';
      card.innerHTML = `
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
          <h3>${p.title}</h3>
          ${statusTag(p.status)}
        </div>
        <p style="-webkit-line-clamp:2;display:-webkit-box;-webkit-box-orient:vertical;overflow:hidden;">${p.description}</p>
        <div class="card-meta">
          ${p.research_field ? `<span class="tag tag-blue">${p.research_field}</span>` : ''}
          <span class="tag tag-gray">${difficultyLabel(p.difficulty_level)}</span>
        </div>
        <div class="card-footer" style="margin-top:8px;">
          <div style="font-size:12px;color:var(--gray-600);">
            <b>${p.applications_count || 0}</b> ứng tuyển
            ${p.pending_applications ? ` · <b style="color:#b45309;">${p.pending_applications} chờ duyệt</b>` : ''}
          </div>
          <div style="display:flex;gap:6px;">
            <button class="btn btn-outline btn-sm view-apps-btn" data-id="${p.id}" data-title="${p.title.replace(/"/g,'')}">Xem đơn</button>
            <button class="btn btn-outline btn-sm toggle-btn" data-id="${p.id}" data-status="${p.status}">${p.status==='open'?'Đóng':'Mở lại'}</button>
          </div>
        </div>`;

      card.querySelector('.view-apps-btn').addEventListener('click', () => openAppPanel(p.id, p.title));
      card.querySelector('.toggle-btn').addEventListener('click', () => toggleProject(p.id, p.status));
      grid.appendChild(card);
    });

  } catch(err) {
    console.error(err);
    grid.innerHTML = '<div class="empty"><p>Lỗi kết nối server.</p></div>';
  }
}

/* ── Toggle project status ── */
async function toggleProject(id, currentStatus) {
  const newStatus = currentStatus === 'open' ? 'closed' : 'open';
  try {
    const res = await fetch(`${API}/admin/project/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      toast(`Dự án đã ${newStatus === 'open' ? 'mở lại' : 'đóng'}.`, 'success');
      loadLecturerProjects();
    } else {
      // Try lecturer-specific update
      const res2 = await fetch(`${API}/api/lecturer/projects`, { headers: { Authorization: `Bearer ${token}` } });
      toast('Không thể thay đổi trạng thái', 'error');
    }
  } catch(err) { toast('Lỗi kết nối', 'error'); }
}

/* ── Create project modal ── */
function openProjectModal() {
  ['pTitle','pDesc','pField','pSkills','pPrefSkills','pDeadline'].forEach(id => $(id).value = '');
  $('pDifficulty').value = 'medium';
  $('pWeeks').value = '';
  $('pMax').value = '1';
  $('projectModal').classList.remove('hidden');
}
$('btnNewProject').addEventListener('click', openProjectModal);
$('closeProject').addEventListener('click',  () => $('projectModal').classList.add('hidden'));
$('cancelProject').addEventListener('click', () => $('projectModal').classList.add('hidden'));
$('projectModal').addEventListener('click', e => { if (e.target === $('projectModal')) $('projectModal').classList.add('hidden'); });

$('confirmProject').addEventListener('click', async () => {
  const title = $('pTitle').value.trim();
  const desc  = $('pDesc').value.trim();
  if (!title || !desc) { toast('Vui lòng nhập tiêu đề và mô tả', 'error'); return; }

  $('confirmProject').disabled = true;
  $('confirmProject').textContent = 'Đang tạo...';
  try {
    const payload = {
      title, description: desc,
      research_field:   $('pField').value.trim() || null,
      difficulty_level: $('pDifficulty').value,
      duration_weeks:   $('pWeeks').value    ? parseInt($('pWeeks').value)  : null,
      max_students:     $('pMax').value      ? parseInt($('pMax').value)    : 1,
      required_skills:  parseList($('pSkills').value),
      preferred_skills: parseList($('pPrefSkills').value),
      deadline:         $('pDeadline').value || null,
      is_public:        true,
    };

    const res = await fetch(`${API}/api/lecturer/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    $('projectModal').classList.add('hidden');
    if (res.ok) {
      toast('Tạo dự án thành công!', 'success');
      loadLecturerProjects();
    } else {
      toast(data.message || 'Tạo dự án thất bại', 'error');
    }
  } catch(err) { toast('Lỗi kết nối', 'error'); }
  finally {
    $('confirmProject').disabled = false;
    $('confirmProject').textContent = 'Tạo dự án';
  }
});

/* ── Applications panel ── */
async function openAppPanel(projectId, title) {
  $('panelTitle').textContent = `Ứng tuyển: ${title}`;
  $('panelContent').innerHTML = '<div class="empty"><div class="spinner"></div></div>';
  $('appPanel').classList.remove('hidden');

  try {
    const res = await fetch(`${API}/api/lecturer/projects/${projectId}/applications`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const data = await res.json();
    const apps = data.applications || [];

    if (!apps.length) {
      $('panelContent').innerHTML = '<div class="empty"><p>Chưa có đơn ứng tuyển nào.</p></div>';
      return;
    }

    $('panelContent').innerHTML = `
      <p style="font-size:12px;color:var(--gray-400);margin-bottom:12px;">${apps.length} đơn ứng tuyển</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sinh viên</th>
              <th>Match</th>
              <th>Trạng thái</th>
              <th>Hành động</th>
            </tr>
          </thead>
          <tbody id="appTableBody"></tbody>
        </table>
      </div>`;

    const tbody = $('appTableBody');
    apps.forEach(app => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <div style="font-weight:600;font-size:13px;">${app.student_name || '—'}</div>
          <div style="font-size:11px;color:var(--gray-400);">${(app.student_skills||[]).slice(0,3).join(', ')}</div>
          ${app.application_text ? `<div style="font-size:11px;color:var(--gray-600);margin-top:3px;font-style:italic;">"${app.application_text.substring(0,80)}${app.application_text.length>80?'…':''}"</div>` : ''}
        </td>
        <td><b style="color:var(--blue);">${Math.round(app.match_score||0)}%</b></td>
        <td>${statusTag(app.status)}</td>
        <td>
          ${app.status === 'pending' ? `
            <div style="display:flex;gap:4px;">
              <button class="btn btn-success btn-sm" data-appid="${app.id}" data-action="accepted">✓ Chấp nhận</button>
              <button class="btn btn-danger btn-sm"  data-appid="${app.id}" data-action="rejected">✗ Từ chối</button>
            </div>` : '<span style="color:var(--gray-400);font-size:12px;">Đã xử lý</span>'}
        </td>`;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', () => reviewApp(btn.dataset.appid, btn.dataset.action, projectId, title));
    });

  } catch(err) {
    $('panelContent').innerHTML = '<div class="empty"><p>Lỗi tải dữ liệu.</p></div>';
  }
}

async function reviewApp(appId, status, projectId, title) {
  try {
    const res = await fetch(`${API}/api/lecturer/applications/${appId}/review`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ status })
    });
    if (res.ok) {
      toast(status === 'accepted' ? 'Đã chấp nhận đơn!' : 'Đã từ chối đơn.', 'success');
      openAppPanel(projectId, title);
      loadLecturerProjects();
    } else {
      const d = await res.json();
      toast(d.message || 'Lỗi cập nhật', 'error');
    }
  } catch(err) { toast('Lỗi kết nối', 'error'); }
}

$('closePanel').addEventListener('click',  () => $('appPanel').classList.add('hidden'));
$('appPanel').addEventListener('click', e => { if (e.target === $('appPanel')) $('appPanel').classList.add('hidden'); });

/* ══════════════════════════════════════
   INIT
══════════════════════════════════════ */
if (role === 'lecturer') {
  initLecturer();
} else {
  initStudent();
}