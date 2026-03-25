const API_BASE = 'http://localhost:5000';

function setStatus(msg, isError = false) {
  const el = document.getElementById('status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? '#d53030' : '#1d6a35';
}

async function loadAdminStats() {
  const token = localStorage.getItem('sm_token');
  if (!token) {
    setStatus('Unauthorized. Please login as admin.', true);
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/admin/stats`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!res.ok) {
      const data = await res.json();
      setStatus(data.message || 'Cannot load stats', true);
      return;
    }

    const data = await res.json();
    setStatus('Admin stats loaded successfully');

    const statsGrid = document.getElementById('statsGrid');
    statsGrid.innerHTML = `
      <div class="card"><h3>Total Students</h3><p>${data.total_students}</p></div>
      <div class="card"><h3>Total Projects</h3><p>${data.total_projects}</p></div>
      <div class="card"><h3>Total Applications</h3><p>${data.total_applications}</p></div>
    `;

    const topSkills = document.getElementById('topSkills');
    topSkills.innerHTML = data.top_skills.map(skill => `<div class="list-item">${skill.skill} (${skill.count})</div>`).join('');
  } catch (e) {
    console.error('admin stats fetch error', e);
    setStatus('Error loading admin stats', true);
  }
}

loadAdminStats();