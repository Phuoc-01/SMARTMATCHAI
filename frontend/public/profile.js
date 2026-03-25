/* ═══════════════════════════════════
   Smart Match AI – profile.js
   Handles student & lecturer profiles
═══════════════════════════════════ */

const API  = `http://${location.hostname}:5000`;
const token = localStorage.getItem('sm_token');
const role  = localStorage.getItem('sm_role');
const cachedUser = JSON.parse(localStorage.getItem('sm_user') || '{}');

if (!token) { location.href = 'auth.html'; }

/* ── Helpers ── */
const $  = id => document.getElementById(id);
const setVal = (id, v) => { const el = $(id); if (el) el.value = v ?? ''; };
const getVal = id => { const el = $(id); return el ? el.value.trim() : ''; };
const joinList = arr => Array.isArray(arr) ? arr.join(', ') : (arr || '');

function showStatus(msg, type = 'success') {
  const el = $('statusMsg');
  el.textContent = msg;
  el.className = type;
  setTimeout(() => { el.className = ''; el.textContent = ''; }, 4000);
}

function statusTag(s) {
  const map = { pending: ['tag-yellow','Chờ duyệt'], accepted: ['tag-green','Chấp nhận'], rejected: ['tag-red','Từ chối'] };
  const [cls, label] = map[s] || ['tag-gray', s || '—'];
  return `<span class="tag ${cls}">${label}</span>`;
}

/* ── Logout ── */
$('logoutBtn').addEventListener('click', () => {
  ['sm_token','sm_user','sm_user_id','sm_role'].forEach(k => localStorage.removeItem(k));
  location.href = 'auth.html';
});

/* ── Sidebar user ── */
$('sidebarUser').textContent = cachedUser.full_name || cachedUser.email || '';
if (role === 'lecturer') $('navApps').style.display = 'none';

/* ══════════════════════════════════════
   PRESET PICKER WIDGET
   Click preset tags to toggle + custom input
══════════════════════════════════════ */
function makePresetPicker(group, previewId, hiddenId, customInputId, customBtnId) {
  const preview = $(previewId);
  const hidden  = $(hiddenId);
  const customInput = $(customInputId);
  const customBtn   = $(customBtnId);

  let selected = new Set();

  function renderPreview() {
    preview.innerHTML = '';
    selected.forEach(val => {
      const chip = document.createElement('span');
      chip.className = 'selected-chip';
      // Find display label from preset tags, fallback to val itself
      const presetEl = document.querySelector(`.preset-tag[data-group="${group}"][data-val="${CSS.escape(val)}"]`);
      const label = presetEl ? presetEl.textContent : val;
      chip.innerHTML = `${label} <button type="button" title="Xoá">×</button>`;
      chip.querySelector('button').addEventListener('click', () => {
        selected.delete(val);
        // deselect preset tag if exists
        document.querySelectorAll(`.preset-tag[data-group="${group}"][data-val="${CSS.escape(val)}"]`)
          .forEach(el => el.classList.remove('selected'));
        renderPreview();
      });
      preview.appendChild(chip);
    });
    hidden.value = [...selected].join(',');
  }

  // Wire up preset tags for this group
  document.querySelectorAll(`.preset-tags[data-group="${group}"] .preset-tag`).forEach(tag => {
    tag.addEventListener('click', () => {
      const val = tag.dataset.val;
      if (selected.has(val)) {
        selected.delete(val);
        tag.classList.remove('selected');
      } else {
        selected.add(val);
        tag.classList.add('selected');
      }
      renderPreview();
    });
  });

  // Custom add
  function addCustom() {
    const raw = customInput.value.trim();
    if (!raw) return;
    raw.split(',').map(s => s.trim()).filter(Boolean).forEach(v => selected.add(v));
    customInput.value = '';
    renderPreview();
  }
  customBtn.addEventListener('click', addCustom);
  customInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); addCustom(); }
  });

  return {
    set(arr) {
      selected = new Set(Array.isArray(arr) ? arr : (arr||'').split(',').map(s=>s.trim()).filter(Boolean));
      // Sync preset tag visual state
      document.querySelectorAll(`.preset-tags[data-group="${group}"] .preset-tag`).forEach(tag => {
        tag.classList.toggle('selected', selected.has(tag.dataset.val));
      });
      renderPreview();
    },
    get() { return [...selected]; },
  };
}

/* ── GPA ring ── */
function updateGpaRing(val) {
  const v = parseFloat(val);
  const circle = $('gpaRingCircle');
  const text   = $('gpaRingText');
  if (!circle) return;
  if (isNaN(v)) { circle.style.strokeDashoffset = '163.4'; text.textContent = '—'; return; }
  const pct = Math.min(v / 4, 1);
  circle.style.strokeDashoffset = 163.4 * (1 - pct);
  text.textContent = v.toFixed(2);
}

/* ══════════════════════════════════════
   STUDENT PROFILE
══════════════════════════════════════ */
let skillsInput, interestsInput;

async function loadStudentProfile() {
  $('studentSections').style.display = '';
  $('lecturerSections').style.display = 'none';
  $('roleBadge').textContent = 'Sinh viên';
  $('roleBadge').className = 'role-badge role-student';

  skillsInput    = makePresetPicker('skills',    'skillsPreview',    'skillsHidden',    'skillCustomInput',    'skillCustomAdd');
  interestsInput = makePresetPicker('interests', 'interestsPreview', 'interestsHidden', 'interestCustomInput', 'interestCustomAdd');

  $('gpa').addEventListener('input', () => updateGpaRing($('gpa').value));

  try {
    const res = await fetch(`${API}/api/student/profile`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.status === 401) { location.href = 'auth.html'; return; }
    if (!res.ok) { showStatus('Không thể tải hồ sơ.', 'error'); return; }

    const user = await res.json();
    const name = user.full_name || user.name || 'Sinh viên';

    // Header
    $('avatarEl').textContent = name.charAt(0).toUpperCase();
    $('headerName').innerHTML = `${name} <span class="role-badge role-student">Sinh viên</span>`;
    $('headerEmail').textContent = user.email;
    $('headerSub').textContent = [user.faculty, user.student_id ? `MSSV: ${user.student_id}` : ''].filter(Boolean).join(' · ');

    // Fields
    setVal('fullName',    name);
    setVal('email',       user.email);
    setVal('studentId',   user.student_id || '');
    setVal('faculty',     user.faculty    || '');
    setVal('phone',       user.phone      || '');
    setVal('yearOfStudy', user.year_of_study ?? '');
    setVal('gpa',         user.gpa ?? '');
    updateGpaRing(user.gpa);

    skillsInput.set(user.skills || []);
    interestsInput.set(user.research_interests || []);

    // Verified skills
    const verified = user.verified_skills || [];
    if (verified.length) {
      $('verifiedList').innerHTML = `<div style="display:flex;flex-wrap:wrap;gap:6px;">${
        verified.map(v => `<span class="tag skill-verified">${v.skill}${v.level ? ` · ${v.level}` : ''}</span>`).join('')
      }</div>`;
    } else {
      $('verifiedList').innerHTML = '<p style="font-size:13px;color:var(--gray-400);">Chưa có kỹ năng nào được xác nhận bởi giảng viên.</p>';
    }

    // Recent applications
    const apps = (user.applications || []).slice(0, 5);
    if (apps.length) {
      $('recentApps').innerHTML = apps.map(a => `
        <div class="app-row">
          <div class="app-title">${a.project_title || 'Dự án không xác định'}</div>
          <div class="app-score">${Math.round(a.match_score || 0)}%</div>
          ${statusTag(a.status)}
        </div>`).join('');
    } else {
      $('recentApps').innerHTML = '<p style="font-size:13px;color:var(--gray-400);">Chưa có đơn ứng tuyển nào.</p>';
    }

  } catch (err) {
    console.error(err);
    showStatus('Lỗi kết nối server.', 'error');
  }
}

async function saveStudentProfile() {
  const payload = {
    name:               getVal('fullName'),
    faculty:            getVal('faculty'),
    phone:              getVal('phone'),
    skills:             skillsInput.get(),
    research_interests: interestsInput.get(),
    gpa:           getVal('gpa')        ? parseFloat(getVal('gpa'))        : null,
    year_of_study: getVal('yearOfStudy') ? parseInt(getVal('yearOfStudy')) : null,
  };

  try {
    const res = await fetch(`${API}/api/student/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) { showStatus(data.message || 'Không thể lưu.', 'error'); return; }

    localStorage.setItem('sm_user', JSON.stringify(data.user));
    showStatus('Lưu thành công!', 'success');

    // Update header live
    const name = payload.name || data.user?.full_name || '';
    $('avatarEl').textContent = name.charAt(0).toUpperCase();
    $('headerName').innerHTML = `${name} <span class="role-badge role-student">Sinh viên</span>`;
    updateGpaRing(payload.gpa);
  } catch (err) {
    showStatus('Lỗi kết nối server.', 'error');
  }
}

/* ══════════════════════════════════════
   LECTURER PROFILE
══════════════════════════════════════ */
let researchInput;

async function loadLecturerProfile() {
  $('studentSections').style.display = 'none';
  $('lecturerSections').style.display = '';

  $('roleBadge').textContent = 'Giảng viên';
  $('roleBadge').className = 'role-badge role-lecturer';

  researchInput = makeTagInput('researchWrap', 'researchInput', 'researchHidden');

  // Load từ cache trước để UI mượt
  const u = cachedUser;
  if (u.full_name) {
    $('avatarEl').textContent = u.full_name.charAt(0).toUpperCase();
    $('headerName').innerHTML = `${u.full_name} <span class="role-badge role-lecturer">Giảng viên</span>`;
    $('headerEmail').textContent = u.email || '';
    $('headerSub').textContent = [u.position, u.department].filter(Boolean).join(' · ');
    
    setVal('lec-fullName', u.full_name);
    setVal('lec-email',    u.email);
    setVal('lec-position', u.position || '');
    setVal('lec-dept',     u.department || '');
    setVal('lec-phone',    u.phone || '');
    researchInput.set(u.research_fields || []);
  }

  // Gọi API lấy data mới nhất
  try {
    const res = await fetch(`${API}/api/lecturer/profile`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (res.ok) {
      const user = await res.json();
      const name = user.full_name || user.name || '';

      $('avatarEl').textContent = name ? name.charAt(0).toUpperCase() : '?';
      $('headerName').innerHTML = `${name} <span class="role-badge role-lecturer">Giảng viên</span>`;
      $('headerEmail').textContent = user.email || '';
      $('headerSub').textContent = [user.position, user.department].filter(Boolean).join(' · ');

      setVal('lec-fullName', name);
      setVal('lec-email',    user.email || '');
      setVal('lec-position', user.position || '');
      setVal('lec-dept',     user.department || '');
      setVal('lec-phone',    user.phone || '');
      researchInput.set(user.research_fields || []);

      localStorage.setItem('sm_user', JSON.stringify(user));
    }
  } catch (err) {
    console.warn('Không tải được profile từ API, dùng cache', err);
  }

  // Load danh sách dự án
  try {
    const res = await fetch(`${API}/api/lecturer/projects`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const data = await res.json();
    const projects = data.projects || [];

    if (projects.length) {
      $('lecProjectList').innerHTML = projects.slice(0, 6).map(p => `
        <div class="proj-row">
          <div class="proj-title">${p.title}</div>
          <div class="proj-apps">${p.applications_count || 0} đơn</div>
          <span class="tag ${p.status==='open'?'tag-green':'tag-gray'}">${p.status==='open'?'Đang mở':'Đã đóng'}</span>
        </div>
      `).join('');
    } else {
      $('lecProjectList').innerHTML = '<p style="color:var(--gray-400);">Chưa có dự án nào. <a href="dashboard.html" style="color:var(--blue);">Tạo dự án →</a></p>';
    }
  } catch (e) {
    $('lecProjectList').innerHTML = '<p style="color:var(--gray-400);">Lỗi tải dự án.</p>';
  }
}

async function saveLecturerProfile() {
  const payload = {
    full_name: getVal('lec-fullName'),
    position:  getVal('lec-position'),
    department: getVal('lec-dept'),
    phone:     getVal('lec-phone'),
    research_fields: researchInput.get()
  };

  try {
    const res = await fetch(`${API}/api/lecturer/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      showStatus(data.message || 'Không thể lưu', 'error');
      return;
    }

    localStorage.setItem('sm_user', JSON.stringify(data.user || { ...cachedUser, ...payload }));
    showStatus('Lưu thành công!', 'success');

    // Cập nhật header ngay lập tức
    const name = payload.full_name || data.user?.full_name || '';
    if (name) $('avatarEl').textContent = name.charAt(0).toUpperCase();
    $('headerName').innerHTML = `${name} <span class="role-badge role-lecturer">Giảng viên</span>`;
    $('headerSub').textContent = [payload.position, payload.department].filter(Boolean).join(' · ');
  } catch (err) {
    showStatus('Lỗi kết nối server.', 'error');
  }
}

/* ── Save button ── */
$('saveBtn').addEventListener('click', async () => {
  $('saveBtn').disabled = true;
  $('saveBtn').textContent = 'Đang lưu...';
  try {
    if (role === 'lecturer') await saveLecturerProfile();
    else                     await saveStudentProfile();
  } finally {
    $('saveBtn').disabled = false;
    $('saveBtn').textContent = 'Lưu thay đổi';
  }
});

/* ── Init ── */
if (role === 'lecturer') loadLecturerProfile();
else                     loadStudentProfile();