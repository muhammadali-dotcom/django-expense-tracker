// Expenzo — shared, lightweight page behavior (sidebar toggle, toasts, split selector).

document.addEventListener('DOMContentLoaded', function () {
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebarOverlay');
  var toggle = document.getElementById('sidebarToggle');

  if (toggle && sidebar && overlay) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('show');
    });
    overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
    });
  }

  var themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    var themeIcon = themeToggle.querySelector('i');
    var syncIcon = function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      themeIcon.classList.toggle('bi-moon-stars', !isDark);
      themeIcon.classList.toggle('bi-sun', isDark);
    };
    syncIcon();
    themeToggle.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      syncIcon();
    });
  }

  document.querySelectorAll('.toast-custom').forEach(function (t) {
    setTimeout(function () {
      t.style.transition = 'all .3s ease';
      t.style.opacity = '0';
      t.style.transform = 'translateX(20px)';
      setTimeout(function () { t.remove(); }, 300);
    }, 4000);
  });
});
