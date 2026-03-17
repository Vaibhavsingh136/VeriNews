/**
 * main.js — VeriNews Frontend Logic
 * Handles: tab switching, file dropzone, form loading states, OCR readiness
 */

document.addEventListener('DOMContentLoaded', () => {

  // ── OCR Readiness Polling ──────────────────────────────────────────────────
  // Check /ocr-status every 3s and update the image submit button
  const imageBtn = document.getElementById('btn-image-submit');
  const ocrStatusEl = document.getElementById('ocr-status-msg');

  function pollOcrStatus() {
    fetch('/ocr-status')
      .then(r => r.json())
      .then(data => {
        if (data.ocr_ready) {
          if (imageBtn) {
            imageBtn.disabled = false;
            const t = imageBtn.querySelector('.btn-text');
            if (t) t.textContent = 'Extract & Analyze';
          }
          if (ocrStatusEl) {
            ocrStatusEl.textContent = '✓ OCR model ready';
            ocrStatusEl.className = 'form-hint ocr-ready';
          }
        } else {
          // still loading — poll again in 2 seconds
          if (ocrStatusEl) {
            ocrStatusEl.textContent = '⏳ OCR model is loading in background…';
            ocrStatusEl.className = 'form-hint ocr-loading';
          }
          setTimeout(pollOcrStatus, 2000);
        }
      })
      .catch(() => { /* ignore network errors during startup */ });
  }

  // Only poll if we're on the index page (image tab exists)
  if (imageBtn || ocrStatusEl) {
    // Disable image button initially; re-enable when OCR is ready
    if (imageBtn) {
      imageBtn.disabled = true;
      const t = imageBtn.querySelector('.btn-text');
      if (t) t.textContent = 'OCR Loading…';
    }
    pollOcrStatus();
  }

  // ── Tab Switching ──────────────────────────────────────────────────────────
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanels = document.querySelectorAll('.tab-panel');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;

      // Update tab buttons
      tabBtns.forEach(b => {
        const isActive = b.dataset.tab === target;
        b.classList.toggle('active', isActive);
        b.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });

      // Update panels
      tabPanels.forEach(panel => {
        const isActive = panel.id === `panel-${target}`;
        panel.classList.toggle('active', isActive);
        if (isActive) {
          panel.removeAttribute('hidden');
        } else {
          panel.setAttribute('hidden', '');
        }
      });
    });

    // Keyboard support
    btn.addEventListener('keydown', e => {
      const idx = Array.from(tabBtns).indexOf(btn);
      if (e.key === 'ArrowRight') {
        tabBtns[(idx + 1) % tabBtns.length].focus();
      } else if (e.key === 'ArrowLeft') {
        tabBtns[(idx - 1 + tabBtns.length) % tabBtns.length].focus();
      }
    });
  });

  // ── File Dropzone ──────────────────────────────────────────────────────────
  const dropzone     = document.getElementById('dropzone');
  const fileInput    = document.getElementById('image_file');
  const content      = document.getElementById('dropzone-content');
  const preview      = document.getElementById('dropzone-preview');
  const previewImg   = document.getElementById('preview-img');
  const previewName  = document.getElementById('preview-name');

  if (dropzone && fileInput) {
    // Click on dropzone triggers file picker
    dropzone.addEventListener('click', (e) => {
      if (e.target !== fileInput) fileInput.click();
    });

    dropzone.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fileInput.click();
      }
    });

    // Drag events
    ['dragenter', 'dragover'].forEach(evt => {
      dropzone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
      });
    });

    ['dragleave', 'drop'].forEach(evt => {
      dropzone.addEventListener(evt, () => {
        dropzone.classList.remove('drag-over');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      const files = e.dataTransfer?.files;
      if (files && files[0]) {
        fileInput.files = files;
        showPreview(files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) showPreview(fileInput.files[0]);
    });

    function showPreview(file) {
      const validTypes = ['image/png', 'image/jpeg', 'image/jpg',
                          'image/gif', 'image/bmp', 'image/webp', 'image/tiff'];
      if (!validTypes.includes(file.type)) {
        showError(dropzone, 'Please select a valid image file.');
        return;
      }
      if (file.size > 16 * 1024 * 1024) {
        showError(dropzone, 'File size must be under 16 MB.');
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewImg.alt = `Preview: ${file.name}`;
        previewName.textContent = `${file.name} (${formatBytes(file.size)})`;
        content.hidden = true;
        preview.removeAttribute('hidden');
      };
      reader.readAsDataURL(file);
    }
  }

  // ── Form Loading States ────────────────────────────────────────────────────
  // Only target analysis forms (those with an input_type field), not auth forms
  const forms = Array.from(document.querySelectorAll('form')).filter(
    f => f.querySelector('[name="input_type"]')
  );

  forms.forEach(form => {
    form.addEventListener('submit', (e) => {
      const submitBtn = form.querySelector('.btn-analyze');
      if (!submitBtn || submitBtn.disabled) return;

      // Basic client-side validation
      const inputType = form.querySelector('[name="input_type"]')?.value;

      if (inputType === 'text') {
        const textarea = form.querySelector('textarea');
        if (!textarea?.value.trim() || textarea.value.trim().length < 20) {
          e.preventDefault();
          showError(textarea, 'Please enter at least 20 characters of text.');
          textarea.focus();
          return;
        }
      }

      if (inputType === 'url') {
        const urlInput = form.querySelector('input[type="url"]');
        if (!urlInput?.value.trim()) {
          e.preventDefault();
          showError(urlInput, 'Please enter a valid URL.');
          urlInput.focus();
          return;
        }
      }

      if (inputType === 'image') {
        const fileInp = form.querySelector('input[type="file"]');
        if (!fileInp?.files.length) {
          e.preventDefault();
          const dz = document.getElementById('dropzone');
          if (dz) showError(dz, 'Please select an image file.');
          return;
        }
      }

      // Show loading — use context-specific label
      const btnTextEl = submitBtn.querySelector('.btn-text');
      if (inputType === 'image' && btnTextEl) {
        btnTextEl.textContent = 'Extracting text with OCR…';
      } else if (inputType === 'url' && btnTextEl) {
        btnTextEl.textContent = 'Fetching & Analyzing…';
      }
      submitBtn.classList.add('loading');
      submitBtn.disabled = true;
    });
  });

  // ── URL Input: auto-add https:// if missing ────────────────────────────────
  const urlInput = document.getElementById('news_url');
  if (urlInput) {
    urlInput.addEventListener('blur', () => {
      const val = urlInput.value.trim();
      if (val && !val.startsWith('http://') && !val.startsWith('https://')) {
        urlInput.value = 'https://' + val;
      }
    });
  }

  // ── Confidence bar animation trigger (result page) ─────────────────────────
  const bars = document.querySelectorAll('.confidence-bar-fill, .model-bar-fill');
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(el => {
        if (el.isIntersecting) {
          el.target.style.width = el.target.style.width; // trigger repaint
        }
      });
    }, { threshold: 0.2 });
    bars.forEach(b => obs.observe(b));
  }

  // ── Flash message auto-dismiss ─────────────────────────────────────────────
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      flash.style.opacity = '0';
      flash.style.transform = 'translateY(-8px)';
      setTimeout(() => flash.remove(), 400);
    }, 6000);
  });

  // ── Helpers ────────────────────────────────────────────────────────────────
  function showError(el, message) {
    // Remove any existing error
    const prev = el?.parentElement?.querySelector('.inline-error');
    if (prev) prev.remove();

    const err = document.createElement('p');
    err.className = 'form-hint inline-error';
    err.style.color = '#FCA5A5';
    err.textContent = message;
    el?.insertAdjacentElement('afterend', err);
    setTimeout(() => err.remove(), 5000);
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

});
