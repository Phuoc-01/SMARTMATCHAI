/* ═══════════════════════════════════════════════════
   Smart Match AI – auth.js  (fixed v3)
═══════════════════════════════════════════════════ */

const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

function showToast(msg, type = 'success') {
  const t = $('toast');
  if (!t) { alert(msg); return; }
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(() => { t.className = 'toast hidden'; }, 3500);
}

function getRole() {
  return document.querySelector('.role-tab.active')?.dataset.role || 'student';
}

/* ── MODE SWITCHING ── */
function switchMode(mode) {
  $$('.mode-tab').forEach(t => t.classList.toggle('active', t.dataset.mode === mode));
  $('login-form').classList.toggle('hidden',    mode !== 'login');
  $('register-form').classList.toggle('hidden', mode !== 'register');
}

$$('.mode-tab').forEach(tab => tab.addEventListener('click', () => switchMode(tab.dataset.mode)));
$('nav-login-btn').addEventListener('click',    () => switchMode('login'));
$('nav-register-btn').addEventListener('click', () => switchMode('register'));
$$('.switch-link').forEach(link => {
  link.addEventListener('click', e => { e.preventDefault(); switchMode(link.dataset.switch); });
});

/* ── ROLE SWITCHING ── */
function switchRole(role) {
  $$('.role-tab').forEach(t => t.classList.toggle('active', t.dataset.role === role));

  const studentFields  = document.querySelector('.student-fields');
  const lecturerFields = document.querySelector('.lecturer-fields');

  studentFields.classList.toggle('hidden',  role !== 'student');
  lecturerFields.classList.toggle('hidden', role !== 'lecturer');

  studentFields.querySelectorAll('input, select, textarea').forEach(el => {
    el.disabled = (role !== 'student');
    if (role !== 'student') el.removeAttribute('required');
  });

  lecturerFields.querySelectorAll('input, select, textarea').forEach(el => {
    el.disabled = (role !== 'lecturer');
    if (role !== 'lecturer') el.removeAttribute('required');
  });

  console.log('[auth.js] switchRole ->', role);
}

$$('.role-tab').forEach(tab => tab.addEventListener('click', () => switchRole(tab.dataset.role)));

/* ── PASSWORD TOGGLE ── */
$$('.eye-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = $(btn.dataset.target);
    if (!input) return;
    input.type = input.type === 'text' ? 'password' : 'text';
    btn.textContent = input.type === 'text' ? 'HIDE' : 'SHOW';
  });
});

/* ── API BASE ── */
const API_BASE = `http://${window.location.hostname}:5000`;
console.log('[auth.js] API_BASE:', API_BASE);

/* ── VALIDATION ── */
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((email || '').trim());
}

/* ── LOGIN ── */
const loginForm = $('login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async e => {
    e.preventDefault();
    const emailInput = loginForm.querySelector('input[type="email"]');
    const passInput  = $('login-password');
    if (!isValidEmail(emailInput.value)) return showToast('Email khong hop le', 'error');
    if (passInput.value.length < 6)      return showToast('Mat khau toi thieu 6 ky tu', 'error');
    try {
      const res  = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailInput.value.trim(), password: passInput.value })
      });
      const data = await res.json();
      if (!res.ok) return showToast(data.message || 'Dang nhap that bai', 'error');
      localStorage.setItem('sm_token',   data.token);
      localStorage.setItem('sm_user',    JSON.stringify(data.user));
      localStorage.setItem('sm_user_id', data.user.id);
      localStorage.setItem('sm_role',    data.user.role);
      showToast('Dang nhap thanh cong!', 'success');
      setTimeout(() => { window.location.href = 'dashboard.html'; }, 700);
    } catch (err) { showToast('Loi ket noi server.', 'error'); }
  });
}

/* ── REGISTER ── */
const registerForm = $('register-form');
if (registerForm) {
  registerForm.addEventListener('submit', async e => {
    e.preventDefault();

    const role = getRole();
    console.log('[auth.js] register submit, role =', role);

    let email, password, confirmPassword, fullName;

    if (role === 'student') {
      email           = $('reg-stu-email')?.value.trim() || '';
      password        = $('reg-pass')?.value    || '';
      confirmPassword = $('reg-confirm')?.value || '';
      fullName        = $('reg-stu-name')?.value.trim() || '';
    } else {
      email           = $('reg-lec-email')?.value.trim()  || '';
      password        = $('reg-lec-pass')?.value          || '';
      confirmPassword = $('reg-lec-confirm')?.value       || '';
      fullName        = $('reg-lec-name')?.value.trim()   || '';
    }

    console.log('[auth.js] values:', { role, email, fullName, passLen: password.length });

    if (!isValidEmail(email))          return showToast('Email khong hop le', 'error');
    if (password.length < 8)           return showToast('Mat khau toi thieu 8 ky tu', 'error');
    if (password !== confirmPassword)  return showToast('Mat khau khong khop', 'error');
    if (!fullName)                     return showToast('Vui long nhap ho ten', 'error');

    let payload;
    if (role === 'student') {
      payload = {
        role, email, password, full_name: fullName,
        student_id: $('reg-stu-id')?.value.trim() || '',
        faculty:    '',
        skills: [], research_interests: [],
      };
    } else {
      payload = {
        role, email, password, full_name: fullName,
        position:        $('reg-lec-position')?.value.trim() || '',
        department:      $('reg-lec-dept')?.value.trim()     || '',
        research_fields: [],
      };
    }

    console.log('[auth.js] sending payload:', JSON.stringify(payload));

    try {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      let data;
      try   { data = await res.json(); }
      catch { return showToast('Server tra ve phan hoi khong hop le', 'error'); }

      console.log('[auth.js] response:', res.status, data);

      if (!res.ok) return showToast(data.error || data.message || 'Dang ky that bai', 'error');

      localStorage.setItem('sm_token',   data.token);
      localStorage.setItem('sm_user',    JSON.stringify(data.user));
      localStorage.setItem('sm_user_id', data.user.id);
      localStorage.setItem('sm_role',    data.user.role);
      showToast('Dang ky thanh cong!', 'success');
      setTimeout(() => { window.location.href = 'dashboard.html'; }, 1000);

    } catch (err) {
      console.error('[auth.js] fetch error:', err);
      showToast('Loi ket noi: ' + err.message, 'error');
    }
  });
}

/* ── INIT ── */
switchMode('register');
switchRole('student');