// AI Coach - Wizard & Navigation

document.addEventListener('DOMContentLoaded', () => {

  // ── Wizard ──────────────────────────────────────────────────────────────

  const wizard = document.getElementById('wizard-form');
  if (!wizard) return;

  const steps = wizard.querySelectorAll('.wizard-step');
  const dots = document.querySelectorAll('.dot');
  const labels = document.querySelectorAll('.label');
  const backBtn = document.getElementById('wizard-back');
  const nextBtn = document.getElementById('wizard-next');
  const skillNameSpan = document.querySelector('.hl-skill');
  let currentStep = 1;
  const selections = {};

  // Pre-select skill from URL param
  const urlParams = new URLSearchParams(window.location.search);
  const preselectSkill = urlParams.get('skill');

  function showStep(step) {
    steps.forEach(s => s.classList.toggle('active', +s.dataset.step === step));
    dots.forEach(d => {
      const s = +d.dataset.step;
      d.classList.toggle('active', s === step);
      d.classList.toggle('done', s < step);
    });
    labels.forEach(l => {
      l.classList.toggle('active', +l.dataset.step <= step);
    });

    backBtn.style.visibility = step === 1 ? 'hidden' : 'visible';
    if (step === 5) {
      nextBtn.style.display = 'none';
      backBtn.style.display = 'none';
    } else {
      nextBtn.style.display = '';
      backBtn.style.display = '';
    }

    // Update question text context
    if (step === 2 && selections.skill) {
      const skillName = getSkillName(selections.skill);
      if (skillNameSpan) skillNameSpan.textContent = skillName;
    }
  }

  function getSkillName(skillId) {
    const card = document.querySelector(`.option-card[data-value="${skillId}"]`);
    return card ? card.dataset.name : '';
  }

  // Handle option card clicks
  document.querySelectorAll('.option-card').forEach(card => {
    card.addEventListener('click', () => {
      const step = card.closest('.wizard-step');
      if (!step) return;

      // Deselect siblings
      step.querySelectorAll('.option-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
    });
  });

  // Next button
  nextBtn.addEventListener('click', () => {
    const currentEl = document.querySelector(`.wizard-step[data-step="${currentStep}"]`);
    if (!currentEl) return;

    // Validate: must have a selection
    const selected = currentEl.querySelector('.option-card.selected');
    if (!selected) {
      const hint = currentEl.querySelector('.option-card');
      if (hint) {
        nextBtn.textContent = '请先选择一个选项';
        setTimeout(() => { nextBtn.textContent = '下一步'; }, 1000);
      }
      return;
    }

    // Save selection
    const value = selected.dataset.value;
    const stepMapping = {
      1: 'skill',
      2: 'level',
      3: 'target_months',
      4: 'daily_minutes',
    };
    selections[stepMapping[currentStep]] = value;

    if (currentStep < 4) {
      currentStep++;
      showStep(currentStep);
    } else if (currentStep === 4) {
      // All selections complete, proceed to generating
      selections.daily_minutes = value;
      currentStep = 5;
      showStep(5);
      submitGoal();
    }
  });

  // Back button
  backBtn.addEventListener('click', () => {
    if (currentStep > 1 && currentStep < 5) {
      currentStep--;
      showStep(currentStep);
    }
  });

  // Submit goal to API
  async function submitGoal() {
    const genSteps = document.querySelectorAll('.gen-steps li');

    function markStep(idx) {
      if (genSteps[idx]) genSteps[idx].classList.add('done');
    }

    markStep(0); // level assessment

    await sleep(400);
    markStep(1); // planning stages

    await sleep(400);
    markStep(2); // planning knowledge points

    await sleep(400);

    try {
      const resp = await fetch('/api/goals/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: parseInt(selections.skill),
          level: selections.level,
          target_months: parseInt(selections.target_months),
          daily_minutes: parseInt(selections.daily_minutes),
        }),
      });

      const data = await resp.json();

      if (data.ok) {
        markStep(3); // generating roadmap
        await sleep(300);
        window.location.href = '/roadmap';
      } else {
        document.querySelector('.gen-sub').textContent = '生成失败：' + (data.error || '未知错误');
      }
    } catch (err) {
      document.querySelector('.gen-sub').textContent = '网络错误，请重试';
    }
  }

  function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  // Init – handle preselect
  if (preselectSkill) {
    const targetCard = document.querySelector(`.option-card[data-value="${preselectSkill}"]`);
    if (targetCard) {
      setTimeout(() => { targetCard.click(); }, 100);
    }
  }

  showStep(1);
});
