// EduClass - Main JS

// Auto-dismiss alerts after 5s
document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'all 0.4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });

  // Color picker swatches
  const radios = document.querySelectorAll('input.color-radio');
  radios.forEach(radio => {
    const swatch = radio.nextElementSibling;
    radio.addEventListener('change', () => {
      radios.forEach(r => r.nextElementSibling?.classList.remove('active'));
      swatch?.classList.add('active');
    });
    if (radio.checked) swatch?.classList.add('active');
  });

  // Copy course code to clipboard
  const codeBox = document.querySelector('.course-code-box[data-code]');
  if (codeBox) {
    codeBox.style.cursor = 'pointer';
    codeBox.title = 'Click para copiar';
    codeBox.addEventListener('click', () => {
      navigator.clipboard.writeText(codeBox.dataset.code).then(() => {
        const orig = codeBox.innerHTML;
        codeBox.innerHTML += ' ✓';
        setTimeout(() => { codeBox.innerHTML = orig; }, 1500);
      });
    });
  }

  // File input label
  const fileInputs = document.querySelectorAll('input[type="file"]');
  fileInputs.forEach(input => {
    input.addEventListener('change', function() {
      const label = this.nextElementSibling;
      if (label && label.classList.contains('file-label')) {
        label.textContent = this.files[0]?.name || 'Seleccionar archivo';
      }
    });
  });

  // Confirm deletes
  const deleteForms = document.querySelectorAll('form[data-confirm]');
  deleteForms.forEach(form => {
    form.addEventListener('submit', e => {
      if (!confirm(form.dataset.confirm || '¿Confirmas esta accion?')) {
        e.preventDefault();
      }
    });
  });
});
