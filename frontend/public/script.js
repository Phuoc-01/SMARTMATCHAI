/* ═══════════════════════════════════════════════════
   Smart Match AI – script.js
   Landing Page Interactions
═══════════════════════════════════════════════════ */

/* ──────────────────────────────────────
   NAVBAR – shrink on scroll
────────────────────────────────────── */
const navbar = document.getElementById('navbar');

window.addEventListener('scroll', () => {
  if (window.scrollY > 20) {
    navbar.classList.add('scrolled');
  } else {
    navbar.classList.remove('scrolled');
  }
}, { passive: true });

/* ──────────────────────────────────────
   HAMBURGER – mobile menu toggle
────────────────────────────────────── */
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('nav-links');

hamburger.addEventListener('click', () => {
  navLinks.classList.toggle('open');
  // animate hamburger to X
  const spans = hamburger.querySelectorAll('span');
  const isOpen = navLinks.classList.contains('open');
  if (isOpen) {
    spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
    spans[1].style.opacity   = '0';
    spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
  } else {
    spans[0].style.transform = '';
    spans[1].style.opacity   = '';
    spans[2].style.transform = '';
  }
});

// close menu when a nav link is clicked
navLinks.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
    hamburger.querySelectorAll('span').forEach(s => {
      s.style.transform = '';
      s.style.opacity   = '';
    });
  });
});

/* ──────────────────────────────────────
   SCROLL ANIMATION – Intersection Observer
────────────────────────────────────── */
const animatedEls = document.querySelectorAll('[data-animate]');

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const delay = entry.target.dataset.delay || 0;
      setTimeout(() => {
        entry.target.classList.add('in-view');
      }, parseInt(delay));
      observer.unobserve(entry.target);
    }
  });
}, {
  threshold: 0.12,
  rootMargin: '0px 0px -40px 0px'
});

animatedEls.forEach(el => observer.observe(el));

/* ──────────────────────────────────────
   ACTIVE NAV LINK on scroll
────────────────────────────────────── */
const sections = document.querySelectorAll('section[id]');

const navObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle(
          'active',
          link.getAttribute('href') === '#' + entry.target.id
        );
      });
    }
  });
}, { threshold: 0.4 });

sections.forEach(sec => navObserver.observe(sec));

/* ──────────────────────────────────────
   SMOOTH SCROLL for anchor links
────────────────────────────────────── */
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', e => {
    const target = document.querySelector(anchor.getAttribute('href'));
    if (target) {
      e.preventDefault();
      const offset = target.getBoundingClientRect().top + window.scrollY - 72;
      window.scrollTo({ top: offset, behavior: 'smooth' });
    }
  });
});

/* ──────────────────────────────────────
   STATS COUNTER ANIMATION
────────────────────────────────────── */
function animateCounter(el, target, suffix, duration = 1400) {
  let start = 0;
  const step = Math.ceil(target / (duration / 16));
  const timer = setInterval(() => {
    start += step;
    if (start >= target) {
      el.textContent = target.toLocaleString() + suffix;
      clearInterval(timer);
    } else {
      el.textContent = start.toLocaleString() + suffix;
    }
  }, 16);
}

// trigger counters when stats row enters view
const statsRow = document.querySelector('.hero-stats');
if (statsRow) {
  const statsObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      const nums = statsRow.querySelectorAll('.stat-num');
      const data = [
        { val: 1200, suffix: '+' },
        { val: 340,  suffix: '+' },
        { val: 92,   suffix: '%' },
      ];
      nums.forEach((el, i) => animateCounter(el, data[i].val, data[i].suffix));
      statsObserver.unobserve(statsRow);
    }
  }, { threshold: 0.5 });
  statsObserver.observe(statsRow);
}

/* ──────────────────────────────────────
   NAV BUTTONS – sync with auth.html
────────────────────────────────────── */
// The nav "Đăng ký" goes to register mode, "Đăng nhập" to login mode.
// We pass a query param so auth.html can pick the right tab.
document.querySelectorAll('[href="auth.html"]').forEach(btn => {
  btn.addEventListener('click', e => {
    const label = btn.textContent.trim();
    if (label.includes('Đăng nhập')) {
      btn.href = 'auth.html?mode=login';
    } else if (label.includes('Đăng ký')) {
      btn.href = 'auth.html?mode=register';
    }
  });
});