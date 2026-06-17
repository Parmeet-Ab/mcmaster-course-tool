const searchBtn = document.getElementById('search-btn');
const courseInput = document.getElementById('course-input');
const resultDiv = document.getElementById('result');

const FLASK = 'http://localhost:8080';

function ratingColor(rating) {
  if (rating >= 4) return '#27ae60';
  if (rating >= 3) return '#e67e22';
  return '#c0392b';
}

searchBtn.addEventListener('click', async () => {
  const code = courseInput.value.trim();
  if (!code) return;

  resultDiv.innerHTML = '<p class="loading">Searching...</p>';
  searchBtn.disabled = true;

  try {
    const res = await fetch(`${FLASK}/course?code=${encodeURIComponent(code)}`);
    const data = await res.json();

    if (data.error) {
      resultDiv.innerHTML = `<p class="error">${data.error}</p>`;
    } else {
      const profs = data.professors || [];
      const courseTitle = data.course.title || code;

      let profsHtml = '<p style="color:#888;margin-top:4px;font-size:12px">No professor data found. Run the scraper first.</p>';

      if (profs.length) {
        profsHtml = profs.map(p => {
          const r = p.rating;
          const ratingHtml = r ? `
            <div class="stat"><span>Rating</span><span style="color:${ratingColor(r.avg_rating)}">${r.avg_rating}/5</span></div>
            <div class="stat"><span>Difficulty</span><span>${r.avg_difficulty}/5</span></div>
            <div class="stat"><span>Reviews</span><span>${r.num_ratings}</span></div>
          ` : '<div style="color:#888;font-size:11px;margin-top:3px">No RMP data</div>';

          return `
            <div class="term-card">
              <div class="term-label">${p.term_name}</div>
              <div class="stat"><span>Professor</span><span>${p.name}</span></div>
              ${ratingHtml}
            </div>`;
        }).join('');
      }

      resultDiv.innerHTML = `
        <div class="card">
          <div class="course-name">${courseTitle}</div>
          ${profsHtml}
        </div>`;
    }
  } catch {
    resultDiv.innerHTML = '<p class="error">Could not reach Flask server. Is it running?</p>';
  }

  searchBtn.disabled = false;
});

courseInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') searchBtn.click();
});
