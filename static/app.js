const form = document.getElementById('report-form');
const submitBtn = document.getElementById('submit-btn');
const progressBar = document.getElementById('progress');
const progressPercent = document.getElementById('progress-percent');
const currentStep = document.getElementById('current-step');
const checklist = document.getElementById('checklist');
const downloadBtn = document.getElementById('download-btn');
const fileName = document.getElementById('file-name');
const errorArea = document.getElementById('error-area');
const validationErrors = document.getElementById('validation-errors');

let pollTimer = null;

function resetUi() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }

  progressBar.value = 0;
  progressPercent.textContent = '0%';
  currentStep.textContent = 'Waiting to start';

  validationErrors.hidden = true;
  validationErrors.innerHTML = '';
  errorArea.hidden = true;
  errorArea.textContent = '';

  downloadBtn.classList.add('disabled');
  downloadBtn.setAttribute('aria-disabled', 'true');
  downloadBtn.href = '#';
  fileName.textContent = 'No file generated yet.';

  for (const item of checklist.querySelectorAll('li')) {
    renderChecklistItem(item, 'pending');
  }
}

function renderChecklistItem(item, state) {
  const icon = item.querySelector('.icon');
  item.classList.remove('pending', 'active', 'done', 'error');
  item.classList.add(state);
  icon.className = `icon ${state}`;

  if (state === 'done') icon.textContent = '✓';
  else if (state === 'active') icon.textContent = '⟳';
  else if (state === 'error') icon.textContent = '✕';
  else icon.textContent = '○';
}

function updateFromStatus(status) {
  progressBar.value = status.percent;
  progressPercent.textContent = `${status.percent}%`;

  const activeStep = status.steps.find((step) => step.state === 'active');
  if (activeStep) currentStep.textContent = activeStep.label;
  else {
    const current = status.steps.find((step) => step.id === status.current_step_id);
    currentStep.textContent = current ? current.label : 'Completed';
  }

  status.steps.forEach((step) => {
    const li = checklist.querySelector(`li[data-step-id="${step.id}"]`);
    if (li) renderChecklistItem(li, step.state);
  });

  if (status.download_ready) {
    downloadBtn.classList.remove('disabled');
    downloadBtn.setAttribute('aria-disabled', 'false');
    downloadBtn.href = `/download/${window.currentJobId}`;
    fileName.textContent = status.file_name || 'Report ready';
  }

  if (status.error) {
    errorArea.hidden = false;
    errorArea.textContent = status.error;
  }
}

function showValidationErrors(errors) {
  validationErrors.hidden = false;
  validationErrors.innerHTML = `<ul>${errors.map((e) => `<li>${e}</li>`).join('')}</ul>`;
}

async function pollStatus() {
  if (!window.currentJobId) return;

  const res = await fetch(`/status/${window.currentJobId}`);
  if (!res.ok) {
    throw new Error('Unable to read job status.');
  }

  const status = await res.json();
  updateFromStatus(status);

  if (status.done || status.error) {
    clearInterval(pollTimer);
    pollTimer = null;
    submitBtn.disabled = false;
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  resetUi();
  submitBtn.disabled = true;

  const formData = new FormData(form);
  const payload = {
    username: formData.get('username'),
    password: formData.get('password'),
    start_date: formData.get('start_date'),
    end_date: formData.get('end_date'),
    debug: formData.get('debug') === 'on'
  };

  try {
    const res = await fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const data = await res.json();
      showValidationErrors(data.errors || ['Validation failed.']);
      submitBtn.disabled = false;
      return;
    }

    const data = await res.json();
    window.currentJobId = data.job_id;

    await pollStatus();
    pollTimer = setInterval(() => {
      pollStatus().catch((err) => {
        clearInterval(pollTimer);
        pollTimer = null;
        submitBtn.disabled = false;
        errorArea.hidden = false;
        errorArea.textContent = err.message;
      });
    }, 1000);
  } catch (err) {
    submitBtn.disabled = false;
    errorArea.hidden = false;
    errorArea.textContent = err.message;
  }
});
