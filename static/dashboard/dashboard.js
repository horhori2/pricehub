/* ================================================================
   dashboard.js — 대시보드 공통 유틸리티
   사용: card_list.html, favorites.html
   ================================================================ */

/* ── CSRF 헬퍼 ── */
function getCsrf() {
  return document.querySelector('meta[name="csrf-token"]').content;
}

/* ── 카드/확장팩 이미지 로드 실패 시 플레이스홀더로 대체 ──
   외부 이미지 서버(포켓몬코리아 등)가 장애일 때 브라우저 기본 "깨진 이미지"
   아이콘 대신 보여줌. onerror="cardImgFallback(this)" 로 사용. */
const CARD_IMG_FALLBACK_SRC = 'data:image/svg+xml,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 140">'
  + '<rect width="100" height="140" rx="10" fill="#20263a"/>'
  + '<text x="50" y="80" font-size="42" text-anchor="middle" dominant-baseline="middle">🃏</text>'
  + '</svg>'
);
function cardImgFallback(img) {
  img.onerror = null;
  img.src = CARD_IMG_FALLBACK_SRC;
}

/* ── 토스트 ── */
function showToast(msg) {
  const t = document.getElementById('fav-toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2200);
}

/* ── 모달 헬퍼 ── */
function showModal(icon, title, desc, btnsHtml) {
  document.getElementById('modalIcon').textContent  = icon;
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalDesc').innerHTML    = desc;
  document.getElementById('modalBtns').innerHTML    = btnsHtml;
  document.getElementById('resetModal').classList.add('show');
}
function hideModal() {
  document.getElementById('resetModal').classList.remove('show');
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') hideModal(); });

/* ── 즐겨찾기 토글 (card_list용) ──
   btn: .star-toggle 버튼 엘리먼트
   TOGGLE_FAV_BASE: 각 페이지에서 const로 선언 */
async function toggleFavorite(btn) {
  const cardId = btn.dataset.cardId;
  btn.classList.add('popping');
  btn.addEventListener('animationend', () => btn.classList.remove('popping'), { once: true });

  try {
    const res  = await fetch(`${TOGGLE_FAV_BASE}${cardId}/favorite/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error);

    const nowFav         = data.is_favorite;
    btn.textContent      = nowFav ? '⭐' : '☆';
    btn.dataset.favorite = nowFav ? 'true' : 'false';
    btn.title            = nowFav ? '즐겨찾기 해제' : '즐겨찾기 추가';
    btn.classList.toggle('active', nowFav);

    const badge = document.getElementById('favCountBadge');
    if (badge) {
      badge.textContent = Math.max(0, (parseInt(badge.textContent) || 0) + (nowFav ? 1 : -1));
    }
    showToast(nowFav ? '⭐ 즐겨찾기에 추가했어요' : '☆ 즐겨찾기에서 제거했어요');
  } catch (err) {
    console.error(err);
    showToast('오류가 발생했어요');
  }
}

/* ── 즐겨찾기 해제 + 행 제거 (favorites용) ── */
async function removeFavorite(btn) {
  const cardId = btn.dataset.cardId;
  btn.classList.add('popping');
  btn.addEventListener('animationend', () => btn.classList.remove('popping'), { once: true });

  try {
    const res  = await fetch(`${TOGGLE_FAV_BASE}${cardId}/favorite/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error);

    if (!data.is_favorite) {
      const row = document.getElementById(`fav-row-${cardId}`);
      row.style.transition = 'max-height 0.25s ease, opacity 0.25s ease';
      row.style.maxHeight  = row.offsetHeight + 'px';
      row.style.overflow   = 'hidden';
      requestAnimationFrame(() => { row.style.maxHeight = '0'; row.style.opacity = '0'; });
      setTimeout(() => row.remove(), 260);

      const countEl = document.getElementById('favCount');
      if (countEl) countEl.textContent = Math.max(0, (parseInt(countEl.textContent) || 0) - 1) + '개';
      showToast('즐겨찾기에서 제거했어요');
    }
  } catch {
    showToast('오류가 발생했어요');
  }
}

/* ── 인라인 판매가 편집 (favorites용) ── */
function startEdit(cardId) {
  document.getElementById(`price-display-${cardId}`).classList.add('hidden');
  document.getElementById(`price-edit-${cardId}`).classList.add('show');
  const input = document.getElementById(`price-val-${cardId}`);
  input.focus();
  input.select();
}
function cancelEdit(cardId) {
  document.getElementById(`price-display-${cardId}`).classList.remove('hidden');
  document.getElementById(`price-edit-${cardId}`).classList.remove('show');
}
async function savePrice(cardId) {
  const price = parseInt(document.getElementById(`price-val-${cardId}`).value) || 0;
  try {
    const res  = await fetch(`${SET_PRICE_BASE}${cardId}/set-price/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ selling_price: price }),
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error);
    document.getElementById(`price-display-${cardId}`).innerHTML = price > 0
      ? `<span class="price-set">${price.toLocaleString()}원</span>`
      : `<span class="price-unset">미설정</span>`;
    cancelEdit(cardId);
    showToast('판매가를 저장했어요');
  } catch { showToast('저장 중 오류가 발생했어요'); }
}

/* ── 판매가 초기화 모달 공통 ── */
function showResetModal() {
  showModal(
    '⚠️', '판매가 초기화',
    document.getElementById('resetModalDesc')?.innerHTML
      || '판매가를 초기화하시겠습니까?<br>설정된 판매가가 전부 미설정(0)으로 변경됩니다.',
    `<button class="modal-cancel" onclick="hideModal()">취소</button>
     <button class="modal-confirm" id="confirmBtn" onclick="doReset()">초기화</button>`
  );
}
async function doReset() {
  const btn = document.getElementById('confirmBtn');
  btn.disabled = true;
  btn.textContent = '초기화 중...';
  try {
    const res  = await fetch(RESET_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    });
    const data = await res.json();
    if (data.success) {
      showModal('✅', '초기화 완료',
        `<strong>${data.count}개</strong> 카드의 판매가가 초기화됐습니다.`,
        `<button class="modal-confirm" onclick="location.reload()" style="background:var(--success);">확인</button>`
      );
    } else { throw new Error(data.error); }
  } catch (err) {
    showModal('❌', '오류 발생',
      err.message || '알 수 없는 오류가 발생했습니다.',
      `<button class="modal-cancel" onclick="hideModal()">닫기</button>`
    );
  }
}


/* ================================================================
   expansion_list.js — 확장팩 목록 페이지 전용
   ================================================================ */

let _searchTimer = null;

function onSearchInput(val) {
  document.getElementById('searchClear').style.display = val ? 'block' : 'none';
  clearTimeout(_searchTimer);
  if (!val.trim()) { clearSearch(); return; }
  _searchTimer = setTimeout(() => searchCards(), 400);
}

function clearSearch() {
  document.getElementById('cardSearchInput').value = '';
  document.getElementById('searchClear').style.display = 'none';
  document.getElementById('searchResults').classList.remove('show');
}

async function searchCards() {
  const q = document.getElementById('cardSearchInput').value.trim();
  if (!q) return;
  const results = document.getElementById('searchResults');
  const body    = document.getElementById('searchResultsBody');
  const title   = document.getElementById('searchResultsTitle');
  const count   = document.getElementById('searchResultsCount');
  results.classList.add('show');
  title.textContent = `"${q}" 검색 결과`;
  body.innerHTML = '<div class="search-loading"><span class="spinner"></span>검색 중...</div>';
  count.textContent = '';
  try {
    const res   = await fetch(`${CARD_SEARCH_URL}?name=${encodeURIComponent(q)}&page_size=30`);
    const data  = await res.json();
    const cards = data.results || data;
    if (!cards.length) {
      body.innerHTML = `<div class="search-empty">검색 결과가 없습니다.</div>`;
      count.textContent = '0개';
      return;
    }
    count.textContent = `${cards.length}개`;
    body.innerHTML = cards.map(item => {
      const sellingPrice = item.selling_price && item.selling_price > 0
        ? `<div class="result-selling-price">${parseInt(item.selling_price).toLocaleString()}원</div>`
        : `<div class="result-selling-price unset">미설정</div>`;
      const latestPrice = item.latest_price
        ? `<div class="result-market-price">시장가 ${parseInt(item.latest_price).toLocaleString()}원</div>`
        : '';
      return `<a href="${CARD_DETAIL_BASE_URL}${item.id}/" class="search-result-item">
        ${item.image_url
          ? `<img src="${item.image_url}" class="result-thumb" loading="lazy" onerror="cardImgFallback(this)">`
          : `<div class="result-thumb" style="display:flex;align-items:center;justify-content:center;font-size:18px;">🃏</div>`}
        <div class="result-info">
          <div class="result-name">${item.name}</div>
          <div class="result-meta">
            <span class="result-rarity">${item.rarity}</span>
            ${item.expansion?.name || ''} · No.${item.card_number}
          </div>
        </div>
        <div class="result-price">${sellingPrice}${latestPrice}</div>
      </a>`;
    }).join('');
  } catch {
    body.innerHTML = `<div class="search-empty">검색 중 오류가 발생했습니다.</div>`;
  }
}

let _pendingCode = null;

function showResetModal(code, name) {
  _pendingCode = code;
  showModal(
    '⚠️', '판매가 초기화',
    `<strong>${name}</strong>의 모든 카드 판매가를 초기화하시겠습니까?<br>설정된 판매가가 전부 미설정(0)으로 변경됩니다.`,
    `<button class="modal-cancel" onclick="hideModal()">취소</button>
     <button class="modal-confirm" id="confirmBtn" onclick="doResetExpansion()">초기화</button>`
  );
}

async function doResetExpansion() {
  const btn = document.getElementById('confirmBtn');
  btn.disabled = true; btn.textContent = '초기화 중...';
  try {
    const res  = await fetch(`${RESET_URL_PREFIX}${_pendingCode}/reset-prices/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    });
    const data = await res.json();
    if (data.success) {
      showModal('✅', '초기화 완료',
        `<strong>${data.count}개</strong> 카드의 판매가가 초기화됐습니다.`,
        `<button class="modal-confirm" onclick="location.reload()" style="background:var(--success);">확인</button>`
      );
    } else { throw new Error(data.error); }
  } catch (err) {
    showModal('❌', '오류 발생', err.message || '알 수 없는 오류',
      `<button class="modal-cancel" onclick="hideModal()">닫기</button>`);
  }
}

function showResetAllModal() {
  showModal(
    '⚠️', '전체 판매가 초기화',
    `<strong>전체</strong> 확장팩의 모든 카드 판매가를 초기화하시겠습니까?<br>
     <span style="color:var(--danger);font-weight:700;">이 작업은 되돌릴 수 없습니다.</span>`,
    `<button class="modal-cancel" onclick="hideModal()">취소</button>
     <button class="modal-confirm" id="confirmBtn" onclick="doResetAll()">전체 초기화</button>`
  );
}

async function doResetAll() {
  const btn = document.getElementById('confirmBtn');
  btn.disabled = true; btn.textContent = '초기화 중...';
  try {
    const res  = await fetch(RESET_ALL_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
    });
    const data = await res.json();
    if (data.success) {
      showModal('✅', '초기화 완료',
        `<strong>${data.count}개</strong> 카드의 판매가가 초기화됐습니다.`,
        `<button class="modal-confirm" onclick="location.reload()" style="background:var(--success);">확인</button>`
      );
    } else { throw new Error(data.error); }
  } catch (err) {
    showModal('❌', '오류 발생', err.message || '알 수 없는 오류',
      `<button class="modal-cancel" onclick="hideModal()">닫기</button>`);
  }
}


/* ================================================================
   card_detail.js — 카드 상세 페이지 전용
   ================================================================ */

function setPrice(price) {
  document.getElementById('sellingPriceInput').value = price;
}

async function savePriceDetail() {
  const input    = document.getElementById('sellingPriceInput');
  const resultEl = document.getElementById('saveResult');
  const price    = parseInt(input.value) || 0;
  try {
    const res  = await fetch(SET_PRICE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ selling_price: price }),
    });
    const data = await res.json();
    resultEl.style.display = 'block';
    if (data.success) {
      resultEl.className   = 'save-result success';
      resultEl.textContent = `✅ 저장 완료: ${data.selling_price ? data.selling_price.toLocaleString() + '원' : '미설정으로 변경'}`;
    } else {
      resultEl.className   = 'save-result error';
      resultEl.textContent = '❌ ' + data.error;
    }
    setTimeout(() => { resultEl.style.display = 'none'; }, 3000);
  } catch {
    resultEl.style.display = 'block';
    resultEl.className     = 'save-result error';
    resultEl.textContent   = '❌ 네트워크 오류';
  }
}

function initPriceChart(marketItems) {
  if (!marketItems.length) return;
  const ctx    = document.getElementById('priceChart').getContext('2d');
  const labels = marketItems.map(i => i.mallName);
  const prices = marketItems.map(i => i.price_int);
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '판매가 (원)',
        data: prices,
        backgroundColor: prices.map((_, i) => i === 0 ? 'rgba(74,222,128,0.8)' : 'rgba(108,99,255,0.7)'),
        borderColor:     prices.map((_, i) => i === 0 ? '#4ade80' : '#6c63ff'),
        borderWidth: 1, borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      onClick: (event, elements) => {
        if (elements.length > 0) setPrice(prices[elements[0].index]);
      },
      onHover: (event, elements) => {
        event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `${ctx.parsed.y.toLocaleString()}원` } },
      },
      scales: {
        x: { ticks: { color: '#6b6f85', font: { size: 11 } }, grid: { color: 'rgba(42,45,58,0.5)' } },
        y: {
          ticks: { color: '#6b6f85', font: { size: 11 }, callback: v => v.toLocaleString() + '원' },
          grid: { color: 'rgba(42,45,58,0.8)' }
        }
      },
    }
  });
}

const WEEKLY_CHART_PALETTE = [
  '#6c63ff','#4ade80','#fbbf24','#f87171','#60a5fa',
  '#a78bfa','#34d399','#fb923c','#e879f9','#38bdf8',
  '#facc15','#f472b6','#818cf8','#2dd4bf','#c084fc',
];

let _priceHistoryUrl   = null;
let _priceHistoryCache = {};
let _priceHistoryRange = 'week';
let _weeklyChartInstance = null;
let _weeklyChartHiddenShops = new Set();

function initWeeklyChart(historyData, historyUrl) {
  _priceHistoryUrl = historyUrl || null;
  _priceHistoryCache = { week: historyData || [] };
  _priceHistoryRange = 'week';
  _weeklyChartHiddenShops = new Set();
  renderRangeButtons();
  renderWeeklyChart(_priceHistoryCache.week);
}

function renderRangeButtons() {
  const wrap = document.getElementById('rangeFilterWrap');
  if (!wrap) return;
  const ranges = [['week', '1주'], ['month', '1개월'], ['year', '1년']];
  wrap.innerHTML = ranges.map(([key, label]) => `
    <button type="button" class="range-filter-btn ${key === _priceHistoryRange ? 'active' : ''}" onclick="switchPriceRange('${key}')">${label}</button>
  `).join('');
}

async function switchPriceRange(range) {
  if (range === _priceHistoryRange) return;
  _priceHistoryRange = range;
  renderRangeButtons();

  if (_priceHistoryCache[range]) {
    renderWeeklyChart(_priceHistoryCache[range]);
    return;
  }
  if (!_priceHistoryUrl) return;

  const wrap = document.getElementById('rangeFilterWrap');
  if (wrap) wrap.style.opacity = '0.5';
  try {
    const res  = await fetch(`${_priceHistoryUrl}?range=${range}`);
    const data = await res.json();
    _priceHistoryCache[range] = data.history || [];
    renderWeeklyChart(_priceHistoryCache[range]);
  } catch (e) {
    // 조용히 실패 — 그래프는 이전 상태 유지
  } finally {
    if (wrap) wrap.style.opacity = '1';
  }
}

function renderWeeklyChart(historyData) {
  const emptyEl = document.getElementById('weeklyChartEmpty');
  const canvasEl = document.getElementById('weeklyChart');

  if (_weeklyChartInstance) { _weeklyChartInstance.destroy(); _weeklyChartInstance = null; }

  if (!historyData || !historyData.length) {
    emptyEl.style.display = 'block';
    canvasEl.style.display = 'none';
    return;
  }
  emptyEl.style.display = 'none';
  canvasEl.style.display = 'block';

  const shopSet = new Set();
  historyData.forEach(p => (p.prices || []).forEach(i => { if (i.mallName) shopSet.add(i.mallName); }));
  const allShops  = [...shopSet];
  const labels    = historyData.map(p => p.date);
  const dense     = labels.length > 60;  // 1개월/1년처럼 점이 많으면 점 표시를 줄여서 안 지저분하게
  const datasets  = allShops.map((shop, idx) => {
    const color  = WEEKLY_CHART_PALETTE[idx % WEEKLY_CHART_PALETTE.length];
    const hidden = _weeklyChartHiddenShops.has(shop);
    return {
      label: shop,
      data: historyData.map(p => {
        const item = (p.prices || []).find(i => i.mallName === shop);
        return item ? item.price : null;
      }),
      borderColor: color, backgroundColor: color + '22',
      pointBackgroundColor: color, pointRadius: dense ? 0 : 4, pointHoverRadius: 6, pointHitRadius: 8,
      borderWidth: 2, tension: 0.3, spanGaps: true, hidden,
    };
  });

  const filterWrap = document.getElementById('shopFilterWrap');

  function renderFilterBtns(chart) {
    filterWrap.innerHTML = '';
    const allBtn = document.createElement('button');
    allBtn.textContent = '전체';
    allBtn.style.cssText = `padding:3px 10px;border-radius:5px;font-size:11px;font-weight:700;border:1px solid var(--border2);background:var(--accent2);color:#fff;cursor:pointer;font-family:inherit;`;
    allBtn.onclick = () => {
      _weeklyChartHiddenShops.clear();
      chart.data.datasets.forEach((_, i) => chart.setDatasetVisibility(i, true));
      chart.update(); renderFilterBtns(chart);
    };
    filterWrap.appendChild(allBtn);
    allShops.forEach((shop, idx) => {
      const color  = WEEKLY_CHART_PALETTE[idx % WEEKLY_CHART_PALETTE.length];
      const hidden = _weeklyChartHiddenShops.has(shop);
      const btn    = document.createElement('button');
      btn.textContent = shop;
      btn.style.cssText = `padding:3px 10px;border-radius:5px;font-size:11px;font-weight:700;
        border:1px solid ${color};background:${hidden ? 'none' : color + '22'};
        color:${hidden ? 'var(--text-muted)' : color};cursor:pointer;font-family:inherit;transition:all 0.15s;`;
      btn.onclick = () => {
        if (_weeklyChartHiddenShops.has(shop)) { _weeklyChartHiddenShops.delete(shop); chart.setDatasetVisibility(idx, true); }
        else { _weeklyChartHiddenShops.add(shop); chart.setDatasetVisibility(idx, false); }
        chart.update(); renderFilterBtns(chart);
      };
      filterWrap.appendChild(btn);
    });
  }

  _weeklyChartInstance = new Chart(canvasEl.getContext('2d'), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1d27', borderColor: '#2a2d3a', borderWidth: 1,
          titleColor: '#e8e9f0', bodyColor: '#9ca3af', padding: 12,
          callbacks: { label: ctx => ctx.parsed.y === null ? null : `  ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()}원` }
        },
      },
      scales: {
        x: { ticks: { color: '#6b6f85', font: { size: 10 }, maxRotation: 30, autoSkip: true, maxTicksLimit: 16 }, grid: { color: 'rgba(42,45,58,0.6)' } },
        y: { ticks: { color: '#6b6f85', font: { size: 11 }, callback: v => v.toLocaleString() + '원' }, grid: { color: 'rgba(42,45,58,0.8)' } }
      },
    }
  });
  renderFilterBtns(_weeklyChartInstance);
}


/* ================================================================
   bulk_price.js — 일괄 판매가 설정 페이지 전용
   ================================================================ */

function toggleRarityChip(rarity, checkbox) {
  const label = checkbox.closest('.rarity-chip');
  if (checkbox.checked) { selectedRarities.add(rarity); label.classList.add('active'); }
  else { selectedRarities.delete(rarity); label.classList.remove('active'); }
  if (typeof updateRarityDisplay === 'function') updateRarityDisplay();
  if (typeof applyRarityFilter  === 'function') applyRarityFilter();
}

function selectRaritiesChips(rarities) {
  selectedRarities = new Set(rarities);
  document.querySelectorAll('.rarity-chip').forEach(chip => {
    const val = chip.querySelector('input').value, active = selectedRarities.has(val);
    chip.classList.toggle('active', active); chip.querySelector('input').checked = active;
  });
  if (typeof updateRarityDisplay === 'function') updateRarityDisplay();
  if (typeof applyRarityFilter  === 'function') applyRarityFilter();
}

function submitBulkFilter() {
  const expansion = document.querySelector('select[name="expansion"]').value;
  const params = new URLSearchParams();
  if (expansion) params.append('expansion', expansion);
  selectedRarities.forEach(r => params.append('rarities', r));
  location.href = BULK_PRICE_URL + '?' + params.toString();
}

function updateBulkRarityDisplay() {
  const el = document.getElementById('selectedRaritiesDisplay');
  if (el) el.textContent = selectedRarities.size > 0 ? `레어도 필터: ${[...selectedRarities].join(', ')}` : '';
}

let _currentRankFilter = 'all';
function filterShops(f, btn) {
  _currentRankFilter = f;
  document.querySelectorAll('.rank-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderRankTable();
}
function renderRankTable() {
  let shops = SHOPS;
  if (_currentRankFilter === 'cheap') shops = shops.filter(s => s.cheaper);
  if (_currentRankFilter === 'exp')   shops = shops.filter(s => !s.cheaper);
  document.getElementById('rankBody').innerHTML = shops.map(s => {
    const rank = SHOPS.indexOf(s) + 1;
    const rc   = rank === 1 ? 'r1' : rank === 2 ? 'r2' : rank === 3 ? 'r3' : 'rn';
    const bw   = Math.round((s.count / MAX_COUNT) * 60);
    const dc   = s.diff < 0 ? 'diff-cheap' : s.diff > 0 ? 'diff-exp' : 'diff-same';
    const dl   = s.diff < 0 ? '▼' : s.diff > 0 ? '▲' : '=';
    return `<tr class="clickable" onclick="addToPriority('${s.name.replace(/'/g, "\\'")}')">
      <td><span class="rank-badge-sm ${rc}">${rank}</span></td>
      <td style="font-weight:600;">${s.name}</td>
      <td><div class="count-bar-wrap"><div class="count-bar" style="width:${bw}px"></div><span class="count-val">${s.count}</span></div></td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:12px;">${s.avg.toLocaleString()}원</td>
      <td><span class="diff-badge ${dc}">${dl} ${Math.abs(s.diff_pct)}%</span></td>
    </tr>`;
  }).join('');
}

function addToPriority(name) {
  for (let i = 1; i <= 5; i++) {
    if (document.getElementById(`p${i}`).value.trim() === name) { highlightPriorityInput(i); return; }
  }
  for (let i = 1; i <= 5; i++) {
    if (!document.getElementById(`p${i}`).value.trim()) { document.getElementById(`p${i}`).value = name; highlightPriorityInput(i); return; }
  }
  document.getElementById('p5').value = name; highlightPriorityInput(5);
}
function highlightPriorityInput(idx) {
  const input = document.getElementById(`p${idx}`);
  input.style.borderColor = 'var(--accent2)'; input.style.background = 'rgba(124,107,255,0.06)';
  setTimeout(() => { input.style.borderColor = ''; input.style.background = ''; }, 800);
}
function clearPriority(idx) {
  document.getElementById(`p${idx}`).value = '';
  saveBulkSettings();
}

/* ================================================================
   판매처 설정 자동 저장 / 불러오기 (localStorage)
   저장 키: pricehub_bulk_settings_{BULK_PRICE_URL}
   저장 항목: priorities(5개), minPrice, fallbackMode, skipPriced
   ================================================================ */

function _bulkSettingsKey() {
  /* BULK_PRICE_URL이 카테고리별로 달라서 키를 URL 기반으로 분리 */
  return 'pricehub_bulk:' + (typeof BULK_PRICE_URL !== 'undefined' ? BULK_PRICE_URL : 'default');
}

function saveBulkSettings() {
  try {
    const settings = {
      priorities: [1,2,3,4,5].map(i => (document.getElementById(`p${i}`)?.value || '').trim()),
      minPrice:   document.getElementById('minPrice')?.value || '',
      fallback:   _fallbackMode,
      skip:       document.getElementById('skipPriced')?.checked || false,
    };
    localStorage.setItem(_bulkSettingsKey(), JSON.stringify(settings));
    _showSaveIndicator();
  } catch (e) { /* localStorage 비활성화 환경 무시 */ }
}

function loadBulkSettings() {
  try {
    const raw = localStorage.getItem(_bulkSettingsKey());
    if (!raw) return;
    const s = JSON.parse(raw);

    /* 우선순위 복원 */
    if (Array.isArray(s.priorities)) {
      s.priorities.slice(0, 5).forEach((name, i) => {
        const el = document.getElementById(`p${i + 1}`);
        if (el && name) el.value = name;
      });
    }

    /* 희망 최저가 복원 */
    const minEl = document.getElementById('minPrice');
    if (minEl && s.minPrice) minEl.value = s.minPrice;

    /* 미매칭 처리 방식 복원 */
    if (s.fallback !== undefined) setFallback(s.fallback);

    /* 덮어쓰기 체크박스 복원 */
    const skipEl = document.getElementById('skipPriced');
    if (skipEl && s.skip !== undefined) skipEl.checked = s.skip;

    _showLoadedIndicator(s.priorities.filter(Boolean));
  } catch (e) { /* 파싱 오류 무시 */ }
}

function clearBulkSettings() {
  try {
    localStorage.removeItem(_bulkSettingsKey());
    [1,2,3,4,5].forEach(i => { const el = document.getElementById(`p${i}`); if (el) el.value = ''; });
    const minEl = document.getElementById('minPrice');
    if (minEl) minEl.value = '';
    setFallback('');
    const skipEl = document.getElementById('skipPriced');
    if (skipEl) skipEl.checked = false;
    _updateSaveStatusEl('설정 초기화됨', '#e86060', 2000);
  } catch (e) { /* 무시 */ }
}

function _showSaveIndicator() {
  const now = new Date();
  const timeStr = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  _updateSaveStatusEl(`✓ ${timeStr} 저장됨`, 'var(--success, #3dd68c)', 2500);
}

function _showLoadedIndicator(priorities) {
  if (!priorities.length) return;
  _updateSaveStatusEl(`↺ 마지막 설정 불러옴 (${priorities.length}개 판매처)`, 'var(--accent2)', 3500);
}

function _updateSaveStatusEl(msg, color, duration) {
  const el = document.getElementById('bulkSaveStatus');
  if (!el) return;
  el.textContent = msg;
  el.style.color   = color;
  el.style.opacity = '1';
  clearTimeout(el._timer);
  if (duration) el._timer = setTimeout(() => { el.style.opacity = '0'; }, duration);
}

function showAutocomplete(idx, val) {
  const list = document.getElementById(`ac${idx}`), q = val.trim();
  const matches = q ? allMalls.filter(m => m.name.includes(q)).slice(0, 8) : allMalls.slice(0, 8);
  if (!matches.length) { list.style.display = 'none'; return; }
  list.innerHTML = matches.map(m =>
    `<div class="autocomplete-item" onmousedown="pickAutocomplete(${idx},'${m.name.replace(/'/g, "\\'")}')">
      <span>${m.name}</span><span class="autocomplete-count">${m.count}</span>
    </div>`
  ).join('');
  list.style.display = 'block';
}
function hideAutocomplete(idx) {
  setTimeout(() => { const el = document.getElementById(`ac${idx}`); if (el) el.style.display = 'none'; }, 150);
}
function pickAutocomplete(idx, name) {
  document.getElementById(`p${idx}`).value = name;
  document.getElementById(`ac${idx}`).style.display = 'none';
}
function getBulkPriorities() {
  return [1, 2, 3, 4, 5].map(i => document.getElementById(`p${i}`).value.trim()).filter(Boolean);
}

let _fallbackMode = '';
let _bulkLoadingSettings = false;  /* 로드 중 저장 트리거 방지 플래그 */
function setFallback(mode) {
  _fallbackMode = mode;
  const map = { avg: 'btnFallbackAvg', max: 'btnFallbackMax', '': 'btnFallbackNone' };
  Object.values(map).forEach(id => {
    const btn = document.getElementById(id);
    if (!btn) return;
    const active = map[mode] === id;
    btn.style.borderColor = active ? 'var(--accent2)' : 'var(--border2)';
    btn.style.background  = active ? 'rgba(124,107,255,0.1)' : 'none';
    btn.style.color       = active ? 'var(--accent2)' : 'var(--text-muted)';
  });
  if (!_bulkLoadingSettings) saveBulkSettings();
}

async function runBulk() {
  const priorities = getBulkPriorities();
  if (!priorities.length) { alert('판매처 우선순위를 1개 이상 입력해주세요.'); return; }
  saveBulkSettings();  /* 실행 직전에 현재 설정 저장 */

  /* 덮어쓰기 경고 */
  const skipPriced = document.getElementById('skipPriced');
  if (skipPriced && !skipPriced.checked) {
    const confirmed = await new Promise(resolve => {
      const modal   = document.getElementById('overwriteModal');
      const cancelB = document.getElementById('overwriteCancelBtn');
      const confirmB= document.getElementById('overwriteConfirmBtn');
      if (!modal) { resolve(true); return; }   /* 모달 없으면 그냥 진행 */
      modal.style.display = 'flex';
      const close = (val) => { modal.style.display = 'none'; resolve(val); };
      cancelB.onclick  = () => close(false);
      confirmB.onclick = () => close(true);
      modal.onclick    = (e) => { if (e.target === modal) close(false); };
    });
    if (!confirmed) return;
  }

  const btn = document.getElementById('runBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner-sm"></span>적용 중...';
  try {
    const res = await fetch(BULK_RUN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({
        priorities,
        expansion_code: document.getElementById('expansionSelect').value,
        skip_priced:    document.getElementById('skipPriced').checked,
        rarities:       [...selectedRarities],
        min_price:      parseInt(document.getElementById('minPrice').value) || 0,
        fallback_mode:  _fallbackMode,
      }),
    });
    const data = await res.json();
    if (!data.success) { alert(data.error || '오류 발생'); return; }
    document.getElementById('rSet').textContent    = data.set_count.toLocaleString();
    document.getElementById('rReview').textContent = data.needs_review_count.toLocaleString();
    document.getElementById('rSkip').textContent   = data.skipped_count.toLocaleString();
    /* 하락/상승 대기 카운트 표시 */
    const rDrop = document.getElementById('rDrop');
    if (rDrop) rDrop.textContent = (data.drop_count || 0).toLocaleString();
    const rRise = document.getElementById('rRise');
    if (rRise) rRise.textContent = (data.rise_count || 0).toLocaleString();
    const expCode = document.getElementById('expansionSelect').value;
    const dropSuffix = expCode ? `?expansion=${expCode}` : '';
    const btnDrop = document.getElementById('btnDrop');
    const btnRise = document.getElementById('btnRise');
    const btnUnpriced = document.getElementById('btnUnpriced');
    if (btnDrop) btnDrop.href = BULK_DROP_URL + dropSuffix;
    if (btnRise) btnRise.href = BULK_RISE_URL + dropSuffix;
    if (btnUnpriced) btnUnpriced.href = BULK_UNPRICED_URL + dropSuffix;
    /* 버튼은 항상 표시 — 카운트 0이면 흐리게만 */
    if (btnDrop)     btnDrop.style.opacity     = data.drop_count          > 0 ? '1' : '0.4';
    if (btnRise)     btnRise.style.opacity     = data.rise_count         > 0 ? '1' : '0.4';
    if (btnUnpriced) btnUnpriced.style.opacity = data.needs_review_count  > 0 ? '1' : '0.4';
    document.getElementById('resultBox').classList.add('show');

    /* ── result-box 버튼 카운트 + 강조 ── */
    const dropCount     = data.drop_count || 0;
    const riseCount     = data.rise_count || 0;
    const unpricedCount = data.needs_review_count || 0;
    const btnDropCount     = document.getElementById('btnDropCount');
    const btnRiseCount     = document.getElementById('btnRiseCount');
    const btnUnpricedCount = document.getElementById('btnUnpricedCount');
    if (btnDropCount)     btnDropCount.textContent     = dropCount > 0     ? dropCount + '개'     : '';
    if (btnRiseCount)     btnRiseCount.textContent     = riseCount > 0     ? riseCount + '개'     : '';
    if (btnUnpricedCount) btnUnpricedCount.textContent = unpricedCount > 0 ? unpricedCount + '개' : '';

    /* 해당 카운트가 있는 버튼만 pulse 강조 */
    const btnDrop2     = document.getElementById('btnDrop');
    const btnRise2      = document.getElementById('btnRise');
    const btnUnpriced2 = document.getElementById('btnUnpriced');
    if (btnDrop2)     btnDrop2.classList.toggle('issues-link-urgent',     dropCount > 0);
    if (btnRise2)     btnRise2.classList.toggle('issues-link-urgent',     riseCount > 0);
    if (btnUnpriced2) btnUnpriced2.classList.toggle('issues-link-urgent', unpricedCount > 0);

    /* r-mini 칸도 강조 */
    document.querySelector('.r-mini-drop')?.classList.toggle('r-mini-urgent',   dropCount > 0);
    document.querySelector('.r-mini-rise')?.classList.toggle('r-mini-urgent',   riseCount > 0);
    document.querySelector('.r-mini-review')?.classList.toggle('r-mini-urgent', unpricedCount > 0);
  } catch (e) { alert('오류: ' + e.message); }
  finally { btn.disabled = false; btn.textContent = '⚡ 일괄 판매가 설정 실행'; }
}
function resetBulkResult() {
  document.getElementById('resultBox').classList.remove('show');
  const btnDrop     = document.getElementById('btnDrop');
  const btnRise     = document.getElementById('btnRise');
  const btnUnpriced = document.getElementById('btnUnpriced');
  if (btnDrop)     { btnDrop.style.display = '';     btnDrop.classList.remove('issues-link-urgent'); }
  if (btnRise)     { btnRise.style.display = '';     btnRise.classList.remove('issues-link-urgent'); }
  if (btnUnpriced) { btnUnpriced.style.display = ''; btnUnpriced.classList.remove('issues-link-urgent'); }
  document.querySelector('.r-mini-drop')?.classList.remove('r-mini-urgent');
  document.querySelector('.r-mini-rise')?.classList.remove('r-mini-urgent');
  document.querySelector('.r-mini-review')?.classList.remove('r-mini-urgent');
  const btnDropCount     = document.getElementById('btnDropCount');
  const btnRiseCount     = document.getElementById('btnRiseCount');
  const btnUnpricedCount = document.getElementById('btnUnpricedCount');
  if (btnDropCount)     btnDropCount.textContent = '';
  if (btnRiseCount)     btnRiseCount.textContent = '';
  if (btnUnpricedCount) btnUnpricedCount.textContent = '';
}



/* ================================================================
   bulk_drop / bulk_unpriced 페이지 전용 (구 bulk_issues)
   ================================================================ */

/* 페이지에서 선언해야 하는 변수:
   const APPROVE_URL, EDIT_URL, SET_PRICE_URL_PREFIX, CARD_RAW
   let   selectedRarities (Set)
   _issuesRemainCount, _activeCardId 는 이 파일에서 선언 */

let _issuesRemainCount = 0;
let _activeCardId      = null;

/* ── 토스트 ── */
function showIssueToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = `toast ${type}`; t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3000);
}

/* ── 하락 바 색상 (클래스 방식 — style 직접 조작 없음) ── */
function initDropBarColors() {
  document.querySelectorAll('.drop-bar-fill').forEach(bar => {
    const pct = parseFloat(bar.dataset.pct);
    if      (pct < 10) bar.classList.add('drop-low');
    else if (pct < 30) bar.classList.add('drop-mid');
    else               bar.classList.add('drop-high');
  });
  // 초기 색상 적용 완료 후 transition 활성화 (로드 시 width 애니메이션 방지)
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document.querySelectorAll('.drop-bar-fill').forEach(bar => bar.classList.add('animate'));
    });
  });
}

/* ── resize 중 transition 일시 비활성화 ── */
let _resizeTimer = null;
window.addEventListener('resize', () => {
  document.documentElement.classList.add('no-transitions');
  clearTimeout(_resizeTimer);
  _resizeTimer = setTimeout(() => {
    document.documentElement.classList.remove('no-transitions');
  }, 150);
}, { passive: true });

/* ── 필터/정렬 ── */
function submitIssuesFilter() {
  const form = document.getElementById('filterForm');
  form.querySelectorAll('input[name="rarities"]').forEach(el => el.remove());
  selectedRarities.forEach(r => {
    const inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = 'rarities'; inp.value = r;
    form.appendChild(inp);
  });
  // 필터/정렬 변경 시 항상 1페이지로 돌아가기
  let pageInp = form.querySelector('input[name="page"]');
  if (!pageInp) {
    pageInp = document.createElement('input');
    pageInp.type = 'hidden'; pageInp.name = 'page';
    form.appendChild(pageInp);
  }
  pageInp.value = '1';
  form.submit();
}
/* bulk_price.js의 toggleRarityChip/selectRaritiesChips가 호출하는 훅 */
function applyRarityFilter()          { submitIssuesFilter(); }
function submitIssuesExpansionFilter() { submitIssuesFilter(); }

function changeSort(val) {
  document.getElementById('sortInput').value = val;
  submitIssuesFilter();
}

/* ── 체크박스 ── */
function toggleAllIssues(cb) {
  document.querySelectorAll('#cardTableBody tr:not(.resolved) .row-check')
    .forEach(c => c.checked = cb.checked);
}

/* ── 사이드 패널 ── */
function showIssuesSidePanel(cardId) {
  if (_activeCardId) {
    document.getElementById(`row-${_activeCardId}`)?.classList.remove('active-row');
  }
  _activeCardId = cardId;

  const row = document.getElementById(`row-${cardId}`);
  row.classList.add('active-row');

  /* 이미지 */
  const imgEl = document.getElementById('sideCardImage');
  const imgSrc = row.dataset.image;
  if (imgSrc) { imgEl.src = imgSrc; imgEl.style.display = 'block'; }
  else          imgEl.style.display = 'none';

  /* 카드명·정보 */
  document.getElementById('sideCardName').textContent = row.dataset.name;
  document.getElementById('sideCardName').style.color = 'var(--text)';
  document.getElementById('sideCardInfo').textContent =
    `${row.dataset.number} · ${row.dataset.rarity}`;

  /* 하락/상승 요약 (부호로 방향 판단) */
  const summaryEl = document.getElementById('sidePriceSummary');
  if (summaryEl) {
    const selling  = parseInt(row.dataset.selling);
    const modified = parseInt(row.dataset.modified);
    const diff     = modified - selling;
    const isRise   = diff > 0;
    const diffPct  = ((Math.abs(diff) / selling) * 100).toFixed(1);
    document.getElementById('sideOldPrice').textContent = selling.toLocaleString() + '원';
    document.getElementById('sideNewPrice').textContent = modified.toLocaleString() + '원';
    document.getElementById('sideDropPct').textContent  = `${isRise ? '+' : '-'}${diffPct}%`;
    document.getElementById('sideDropAmt').textContent  = `${isRise ? '▲' : '▼'} ${Math.abs(diff).toLocaleString()}원`;
    const sideBar = document.getElementById('sideDropBar');
    sideBar.style.width = Math.min(parseFloat(diffPct), 100) + '%';
    const pct = parseFloat(diffPct);
    sideBar.style.background = isRise
      ? (pct < 10 ? 'linear-gradient(90deg,#4ade80,#22c55e)'
         : pct < 30 ? 'linear-gradient(90deg,#22c55e,#16a34a)'
         : 'linear-gradient(90deg,#16a34a,#15803d)')
      : (pct < 10 ? 'linear-gradient(90deg,#f5a623,#f06060)'
         : pct < 30 ? 'linear-gradient(90deg,#f06060,#c43c3c)'
         : 'linear-gradient(90deg,#c43c3c,#9b1f1f)');
    summaryEl.style.display = 'block';
  }

  /* 판매처 목록 (JSON key는 항상 문자열) */
  const raw   = (typeof CARD_RAW !== 'undefined') ? CARD_RAW[String(cardId)] : null;
  const empty = document.getElementById('sideEmpty');
  const list  = document.getElementById('sideStoreList');

  if (!raw || !Array.isArray(raw) || !raw.length) {
    document.getElementById('sideEmptyText').textContent = '판매처 데이터가 없습니다.';
    empty.style.display = 'flex'; list.style.display = 'none';
  } else {
    const sorted = [...raw].sort((a, b) => parseInt(a.lprice) - parseInt(b.lprice));
    list.innerHTML = sorted.map((item, idx) => {
      const price    = parseInt(item.lprice);
      const mall     = item.mallName || '알 수 없음';
      const thumbSrc = item.image || '';
      const title    = (item.title || '').replace(/<[^>]+>/g, '');
      return `
        <div class="side-store-row${idx === 0 ? ' cheapest' : ''}"
             onclick="fillIssuePrice(${cardId}, ${price})">
          <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0;">
            ${thumbSrc
              ? `<img src="${thumbSrc}" alt="" style="width:48px;height:48px;object-fit:contain;
                   border-radius:6px;background:var(--surface2);border:1px solid var(--border);flex-shrink:0;">`
              : `<div style="width:48px;height:48px;border-radius:6px;background:var(--surface2);
                   border:1px solid var(--border);flex-shrink:0;"></div>`}
            <div style="min-width:0;">
              <div class="side-store-name">${mall}</div>
              <div style="font-size:11px;color:var(--text-muted);margin-top:2px;
                   white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                   title="${title}">${title}</div>
              <div class="side-store-price${idx === 0 ? ' cheapest' : ''}" style="margin-top:3px;">
                ${price.toLocaleString()}원
              </div>
            </div>
          </div>
        </div>`;
    }).join('');
    empty.style.display = 'none'; list.style.display = 'block';
  }

  const input = document.getElementById(`input-${cardId}`);
  if (input && !input.disabled) setTimeout(() => input.focus(), 50);
}

/* ── 판매처 클릭 → 가격 입력창 채우기 ── */
function fillIssuePrice(cardId, price) {
  /* issues 페이지: id="input-{id}", card_list 페이지: id="inp-{id}" */
  const input = document.getElementById(`input-${cardId}`)
             || document.getElementById(`inp-${cardId}`);
  if (!input) return;
  input.value = price; input.classList.add('prefilled'); input.focus();
  document.getElementById(`row-${cardId}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ── edit: 직접 입력한 가격으로 저장 ── */
async function saveIssueEdit(cardId) {
  const input = document.getElementById(`input-${cardId}`);
  const price = parseInt(input?.value);
  if (!price || price <= 0) {
    input.style.borderColor = 'var(--danger)';
    setTimeout(() => input.style.borderColor = '', 800);
    return;
  }
  try {
    const res  = await fetch(EDIT_URL, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body:    JSON.stringify({ card_id: cardId, price }),
    });
    const data = await res.json();
    if (data.success) {
      markIssueDone(cardId);
      showIssueToast(`💾 저장 완료 (${data.new_price.toLocaleString()}원)`, 'ok');
    } else {
      showIssueToast('❌ ' + (data.error || '오류'), 'err');
    }
  } catch {
    showIssueToast('❌ 네트워크 오류', 'err');
  }
}

/* ── 병렬 저장 헬퍼: 최대 concurrency개 동시 실행 ── */
async function _runParallel(ids, taskFn, concurrency = 20) {
  let idx = 0;
  async function worker() {
    while (idx < ids.length) {
      const id = ids[idx++];
      await taskFn(id);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, ids.length) }, worker));
}

/* ── 체크된 카드 저장 ── */
async function approveChecked() {
  const ids = [...document.querySelectorAll('.row-check:checked')]
    .map(cb => parseInt(cb.dataset.id));
  if (!ids.length) { showIssueToast('체크된 카드가 없습니다.', 'err'); return; }
  if (!confirm(`${ids.length}개 카드를 저장할까요?`)) return;
  const btn = document.getElementById('saveAllBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-sm"></span>저장 중...';
  await _runParallel(ids, saveIssueEdit);
  btn.disabled = false; btn.textContent = '💾 체크된 카드 저장';
}

/* ── 전체 저장 ── */
async function approveAll() {
  const ids = [...document.querySelectorAll('#cardTableBody tr:not(.resolved) .row-check')]
    .map(cb => parseInt(cb.dataset.id));
  if (!ids.length) return;
  if (!confirm(`전체 ${ids.length}개 카드를 저장할까요?`)) return;
  await _runParallel(ids, saveIssueEdit);
}

/* ── N% 이하 변동 카드만 일괄 approve (bulk_drop / bulk_rise 페이지 공용) ── */
async function approveByPct() {
  const trend = document.body.dataset.trend === 'rise' ? '상승' : '하락';
  const threshold = parseFloat(document.getElementById('dropPctThreshold')?.value) || 10;
  const rows = [...document.querySelectorAll('#cardTableBody tr:not(.resolved):not(.done)')]
    .filter(r => {
      const pct = parseFloat(r.dataset.dropPct);
      return !isNaN(pct) && pct <= threshold;
    });
  if (!rows.length) {
    showIssueToast(`${trend}폭 ${threshold}% 이하 카드가 없습니다.`, 'err');
    return;
  }
  if (!confirm(`${trend}폭 ${threshold}% 이하 카드 ${rows.length}개에 ${trend}가를 반영할까요?`)) return;

  const btn = document.getElementById('approveByPctBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-sm"></span>처리 중...'; }

  let done = 0;
  await _runParallel(rows.map(r => parseInt(r.dataset.id)), async (cardId) => {
    try {
      const res  = await fetch(APPROVE_URL, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body:    JSON.stringify({ card_id: cardId }),
      });
      const data = await res.json();
      if (data.success) { markIssueDone(cardId); done++; }
    } catch { /* 개별 오류는 무시하고 계속 */ }
  });

  if (btn) { btn.disabled = false; btn.textContent = `≤${threshold}% 일괄 반영`; }
  showIssueToast(`✅ ${done}개 반영 완료 (${threshold}% 이하)`, 'ok');
}

/* ── 행 완료 처리 ── */
function markIssueDone(cardId) {
  const row   = document.getElementById(`row-${cardId}`);
  const input = document.getElementById(`input-${cardId}`);
  const badge = document.getElementById(`badge-${cardId}`);
  if (!row) return;

  row.classList.add('done');
  setTimeout(() => {
    row.classList.add('resolved');
    setTimeout(() => row.remove(), 400);
  }, 600);

  if (input) { input.classList.add('saved'); input.disabled = true; }
  if (badge) badge.classList.add('show');
  const cb = row.querySelector('.row-check'); if (cb) cb.checked = false;
  _issuesRemainCount = Math.max(0, _issuesRemainCount - 1);
  document.getElementById('remainCount').textContent = `${_issuesRemainCount}개`;
}

/* ── (구) bulk_issues 함수들 — 레거시 2차 판매가 설정 페이지 호환용 ── */
function applyIssuesRarityFilter() {
  let visible = 0;
  document.querySelectorAll('#cardTableBody tr').forEach(row => {
    const show = selectedRarities.size === 0 || selectedRarities.has(row.dataset.rarity);
    row.classList.toggle('hidden', !show);
    if (show) visible++;
  });
  const el = document.getElementById('filteredCount');
  if (el) el.textContent = selectedRarities.size > 0 ? `(필터: ${visible}개)` : '';
  document.getElementById('checkAll').checked = false;
}
function applyIssuesBulkPrice(mode) {
  const minFloor = parseInt(document.getElementById('bulkMinPrice').value) || 0;
  let applied = 0;
  document.querySelectorAll('#cardTableBody tr:not(.hidden):not(.done)').forEach(row => {
    const cardId = row.dataset.id, raw = CARD_RAW[cardId];
    const input  = document.getElementById(`input-${cardId}`);
    if (!input || input.disabled) return;
    const prices = Array.isArray(raw) ? raw.map(i => parseInt(i.lprice)).filter(p => p > 0) : [];
    if (!prices.length) return;
    let price = mode === 'avg'
      ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)
      : Math.max(...prices);
    price = Math.round(price / 100) * 100;
    if (minFloor > 0 && price < minFloor) price = minFloor;
    input.value = price; input.classList.add('prefilled');
    const cb = row.querySelector('.row-check'); if (cb) cb.checked = true;
    applied++;
  });
  showIssueToast(`✅ ${applied}개 카드에 ${mode === 'avg' ? '평균가' : '최고가'} 반영됐어요.`, 'ok');
}
function applyIssuesMinPrice() {
  const minFloor = parseInt(document.getElementById('bulkMinPrice').value) || 0;
  if (!minFloor) { showIssueToast('희망 최저가를 입력해주세요.', 'err'); return; }
  let applied = 0;
  document.querySelectorAll('#cardTableBody tr:not(.hidden):not(.done)').forEach(row => {
    const input = document.getElementById(`input-${row.dataset.id}`);
    if (!input || input.disabled) return;
    input.value = minFloor; input.classList.add('prefilled');
    const cb = row.querySelector('.row-check'); if (cb) cb.checked = true;
    applied++;
  });
  showIssueToast(`✅ ${applied}개 카드에 ${minFloor.toLocaleString()}원 반영됐어요.`, 'ok');
}
async function saveAllIssues() {
  const checked = [...document.querySelectorAll('.row-check:checked')];
  if (!checked.length) { showIssueToast('체크된 카드가 없습니다.', 'err'); return; }
  const targets = checked
    .map(cb => ({ cardId: cb.dataset.id, input: document.getElementById(`input-${cb.dataset.id}`) }))
    .filter(t => t.input && !t.input.disabled && t.input.value && parseInt(t.input.value) > 0);
  if (!targets.length) { showIssueToast('입력된 가격이 없습니다.', 'err'); return; }
  const btn = document.getElementById('saveAllBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-sm"></span>저장 중...';
  let saved = 0, failed = 0;
  let tIdx = 0;
  const total = targets.length;
  async function worker() {
    while (tIdx < total) {
      const { cardId, input } = targets[tIdx++];
      const price = parseInt(input.value);
      try {
        const res  = await fetch(`${SET_PRICE_URL_PREFIX}${cardId}/set-price/`, {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
          body: JSON.stringify({ selling_price: price }),
        });
        const data = await res.json();
        if (data.success) { markIssueDone(cardId); saved++; } else failed++;
      } catch { failed++; }
    }
  }
  await Promise.all(Array.from({ length: Math.min(20, total) }, worker));
  btn.disabled = false; btn.textContent = '⚡ 체크된 카드 저장';
  showIssueToast(
    failed === 0 ? `✅ ${saved}개 저장 완료!` : `✅ ${saved}개 완료 / ❌ ${failed}개 실패`,
    failed === 0 ? 'ok' : 'err'
  );
}
function renderIssuesStats(cardRaw) {
  for (const [cardId, raw] of Object.entries(cardRaw)) {
    const prices = Array.isArray(raw) ? raw.map(i => parseInt(i.lprice)).filter(p => p > 0) : [];
    const el = document.getElementById(`stats-${cardId}`);
    if (!el) continue;
 
    if (!prices.length) {
      el.innerHTML = `<span class="stat-no-data">데이터 없음</span>`;
      continue;
    }
 
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const avg = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);
 
    el.innerHTML = `
      <div class="market-stats-row">
        <span class="stat-count">${prices.length}개</span>
        <div class="market-pills">
          <span class="stat-pill stat-min"
                onclick="event.stopPropagation();fillIssuePrice(${cardId},${min})"
                title="최저가 클릭 시 입력">
            <span class="pill-label">최저</span>${min.toLocaleString()}
          </span>
          <span class="stat-pill stat-avg"
                onclick="event.stopPropagation();fillIssuePrice(${cardId},${avg})"
                title="평균가 클릭 시 입력">
            <span class="pill-label">평균</span>${avg.toLocaleString()}
          </span>
          <span class="stat-pill stat-max"
                onclick="event.stopPropagation();fillIssuePrice(${cardId},${max})"
                title="최고가 클릭 시 입력">
            <span class="pill-label">최고</span>${max.toLocaleString()}
          </span>
        </div>
      </div>`;
  }
}
async function saveIssuePrice(cardId) {
  const input = document.getElementById(`input-${cardId}`);
  const price = parseInt(input.value);
  if (!price || price <= 0) {
    input.style.borderColor = 'var(--danger)';
    setTimeout(() => input.style.borderColor = '', 800); return;
  }
  try {
    const res  = await fetch(`${SET_PRICE_URL_PREFIX}${cardId}/set-price/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ selling_price: price }),
    });
    const data = await res.json();
    if (data.success) { markIssueDone(cardId); showIssueToast(`✅ ${price.toLocaleString()}원 저장됐어요.`, 'ok'); }
    else showIssueToast('❌ ' + (data.error || '오류'), 'err');
  } catch { showIssueToast('❌ 네트워크 오류', 'err'); }
}


/* ================================================================
   shop_stats.js — 경쟁 샵 랭킹 페이지 전용
   ================================================================ */

function initShopCharts(shops, overallAvg) {
  const TOP = shops.slice(0, 15);
  const chartBase = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: '#1a1e2a', borderColor: '#2f3650', borderWidth: 1, titleColor: '#dde2f0', bodyColor: '#9aa0c0' },
    },
    scales: {
      x: { ticks: { color: '#5a6080', font: { size: 10 }, maxRotation: 35 }, grid: { color: 'rgba(37,42,58,0.8)' } },
      y: { ticks: { color: '#5a6080', font: { size: 10, family: 'JetBrains Mono' } }, grid: { color: 'rgba(37,42,58,0.8)' } },
    },
  };
  const countEl = document.getElementById('countChart');
  if (countEl && TOP.length) {
    new Chart(countEl, {
      type: 'bar',
      data: {
        labels: TOP.map(s => s.name),
        datasets: [{
          data: TOP.map(s => s.count),
          backgroundColor: TOP.map((_, i) => i === 0 ? 'rgba(245,166,35,0.75)' : i < 3 ? 'rgba(124,107,255,0.65)' : 'rgba(91,141,239,0.45)'),
          borderColor:     TOP.map((_, i) => i === 0 ? '#f5a623' : i < 3 ? '#7c6bff' : '#5b8def'),
          borderWidth: 1, borderRadius: 5,
        }],
      },
      options: { ...chartBase,
        plugins: { ...chartBase.plugins, tooltip: { ...chartBase.plugins.tooltip, callbacks: { label: c => `  상품 ${c.parsed.y}개` } } },
        scales: { ...chartBase.scales, y: { ...chartBase.scales.y, ticks: { ...chartBase.scales.y.ticks, callback: v => v + '개' } } },
      },
    });
  }
  const avgEl = document.getElementById('avgChart');
  if (avgEl && TOP.length) {
    new Chart(avgEl, {
      type: 'bar',
      data: {
        labels: TOP.map(s => s.name),
        datasets: [
          { label: '샵 평균가', data: TOP.map(s => s.avg),
            backgroundColor: TOP.map(s => s.cheaper ? 'rgba(61,214,140,0.6)' : 'rgba(240,96,96,0.6)'),
            borderColor:     TOP.map(s => s.cheaper ? '#3dd68c' : '#f06060'), borderWidth: 1, borderRadius: 5 },
          { label: '전체 평균', data: TOP.map(() => overallAvg), type: 'line',
            borderColor: 'rgba(245,166,35,0.7)', borderWidth: 2, borderDash: [5, 4], pointRadius: 0, fill: false },
        ],
      },
      options: { ...chartBase,
        plugins: { ...chartBase.plugins,
          legend: { display: true, labels: { color: '#5a6080', font: { size: 10 } } },
          tooltip: { ...chartBase.plugins.tooltip, callbacks: { label: c => `  ${c.dataset.label}: ${c.parsed.y.toLocaleString()}원` } },
        },
        scales: { ...chartBase.scales, y: { ...chartBase.scales.y, ticks: { ...chartBase.scales.y.ticks, callback: v => v.toLocaleString() + '원' } } },
      },
    });
  }
}

let _shopFilter = 'all';
function filterShopStats(f, btn) {
  _shopFilter = f;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderShopRank();
}
function renderShopRank() {
  let shops = SHOPS;
  if (_shopFilter === 'cheap') shops = shops.filter(s => s.cheaper);
  if (_shopFilter === 'exp')   shops = shops.filter(s => !s.cheaper);
  document.getElementById('rankBody').innerHTML = shops.map(s => {
    const rank = SHOPS.indexOf(s) + 1;
    const rc   = rank === 1 ? 'r1' : rank === 2 ? 'r2' : rank === 3 ? 'r3' : 'rn';
    const bw   = Math.round((s.count / MAX_COUNT) * 70);
    const dc   = s.diff < 0 ? 'diff-cheap' : s.diff > 0 ? 'diff-exp' : 'diff-same';
    const dl   = s.diff < 0 ? '▼' : s.diff > 0 ? '▲' : '=';
    return `<tr class="clickable" onclick="addShopToPriority('${s.name.replace(/'/g, "\\'")}')">
      <td><span class="rank-badge ${rc}">${rank}</span></td>
      <td style="font-weight:600;font-size:13px;">${s.name}</td>
      <td><div class="count-bar-wrap"><div class="count-bar" style="width:${bw}px"></div><span class="count-val">${s.count}</span></div></td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:12px;">${s.avg.toLocaleString()}원</td>
      <td><span class="diff-badge ${dc}">${dl} ${Math.abs(s.diff_pct)}%</span></td>
    </tr>`;
  }).join('');
}

function addShopToPriority(name) {
  for (let i = 1; i <= 5; i++) {
    if (document.getElementById(`p${i}`).value.trim() === name) { highlightShopInput(i); return; }
  }
  for (let i = 1; i <= 5; i++) {
    if (!document.getElementById(`p${i}`).value.trim()) { document.getElementById(`p${i}`).value = name; highlightShopInput(i); return; }
  }
  document.getElementById('p5').value = name; highlightShopInput(5);
}
function highlightShopInput(idx) {
  const input = document.getElementById(`p${idx}`);
  input.style.borderColor = 'var(--accent2)'; input.style.background = 'rgba(124,107,255,0.06)';
  setTimeout(() => { input.style.borderColor = ''; input.style.background = ''; }, 800);
  input.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function clearShopP(idx) { document.getElementById(`p${idx}`).value = ''; }

async function runShopBulk() {
  const priorities = [1, 2, 3, 4, 5].map(i => document.getElementById(`p${i}`).value.trim()).filter(Boolean);
  if (!priorities.length) { showShopToast('우선순위를 1개 이상 입력해주세요.', 'err'); return; }
  const btn = document.getElementById('runBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>적용 중...';
  try {
    const res  = await fetch(BULK_RUN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({
        priorities,
        expansion_code: document.getElementById('expSelect').value,
        skip_priced:    document.getElementById('skipPriced').checked,
      }),
    });
    const data = await res.json();
    if (!data.success) { showShopToast(data.error || '오류 발생', 'err'); return; }
    document.getElementById('rSet').textContent    = data.set_count.toLocaleString();
    document.getElementById('rReview').textContent = data.needs_review_count.toLocaleString();
    document.getElementById('resultBox').classList.add('show');
    if (data.needs_review_count === 0) document.getElementById('issuesLink').style.display = 'none';
    showShopToast(`✅ ${data.set_count.toLocaleString()}개 판매가 적용 완료!`, 'ok');
  } catch { showShopToast('네트워크 오류', 'err'); }
  finally { btn.disabled = false; btn.textContent = '⚡ 일괄 판매가 설정'; }
}

function showShopToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = `toast ${type}`; t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3500);
}

/* ================================================================
   card_list.js — 카드 목록 페이지 전용
   ================================================================ */

/* SET_PRICE_BASE: 각 페이지에서 const로 선언 */

function openPriceInput(cardId, currentPrice) {
  document.getElementById('disp-' + cardId).style.display = 'none';
  const wrap = document.getElementById('edit-' + cardId);
  wrap.classList.add('show');
  const inp = document.getElementById('inp-' + cardId);
  inp.value = currentPrice || '';
  /* 편집 시작하면 "수정됨" 표시 제거 */
  const row = document.getElementById('row-' + cardId);
  if (row) row.classList.remove('row--saved');
  setTimeout(() => { inp.focus(); inp.select(); }, 50);
}

function closePriceInput(cardId) {
  document.getElementById('disp-' + cardId).style.display = '';
  document.getElementById('edit-' + cardId).classList.remove('show');
}

function handlePriceKey(e, cardId) {
  if (e.key === 'Enter')  saveInlinePrice(cardId);
  if (e.key === 'Escape') closePriceInput(cardId);
}

async function saveInlinePrice(cardId) {
  const inp   = document.getElementById('inp-' + cardId);
  const price = parseInt(inp.value, 10) || 0;
  const url   = SET_PRICE_BASE + '/' + cardId + '/set-price/';
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  try {
    const res  = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ selling_price: price }),
    });
    const data = await res.json();
    if (data.success) {
      const disp = document.getElementById('disp-' + cardId);
      disp.innerHTML = price > 0
        ? `<span class="price-set">${price.toLocaleString()}원</span><span class="price-saved-badge">✓ 수정됨</span><span class="price-edit-hint">✎</span>`
        : `<span class="price-unset">미설정</span><span class="price-edit-hint">✎</span>`;
      const row = document.getElementById('row-' + cardId);
      if (row) { row.dataset.selling = price; row.classList.add('row--saved'); }
      closePriceInput(cardId);
      showToast('저장됐습니다.');
    } else {
      showToast('저장 실패: ' + (data.error || ''));
    }
  } catch {
    showToast('오류가 발생했습니다.');
  }
}

/* ── Shift+클릭 범위 선택 ──────────────────────────────────────
   ⚠ bulk_drop.html 은 자체 완결형 핸들러(window.__rangeSelectBound)를
     내부 인라인 스크립트로 사용합니다. 이 파일의 아래 핸들러는
     그 가드를 존중하여, 이미 바인딩됐으면 다시 붙지 않습니다.
   ─────────────────────────────────────────────────────────── */
let _lastCardChecked = null;

if (!window.__rangeSelectBound) {
  window.__rangeSelectBound = true;
  document.addEventListener('click', function(e) {
    const cb = e.target;
    if (!cb || !cb.classList) return;
    const isCard = cb.classList.contains('card-check');
    const isRow  = cb.classList.contains('row-check');
    if (!isCard && !isRow) return;

    const sel = isCard ? '.card-check' : '.row-check';
    const visible = [...document.querySelectorAll(sel)].filter(el => {
      const row = el.closest('tr');
      return !row || (!row.classList.contains('hidden') && !row.classList.contains('resolved'));
    });

    if (_lastCardChecked && e.shiftKey && _lastCardChecked !== cb && visible.includes(_lastCardChecked)) {
      const a = visible.indexOf(_lastCardChecked);
      const b = visible.indexOf(cb);
      if (a !== -1 && b !== -1) {
        const targetState = cb.checked;
        const [lo, hi] = a < b ? [a, b] : [b, a];
        for (let i = lo; i <= hi; i++) visible[i].checked = targetState;
        if (window.getSelection) window.getSelection().removeAllRanges();
      }
      return;
    }
    _lastCardChecked = cb;
  }, true);
}

function toggleAllCards(masterCb) {
  document.querySelectorAll('.card-check').forEach(cb => cb.checked = masterCb.checked);
  _lastCardChecked = null;
  updateBulkBar();
}

function updateBulkBar() {
  const checked = document.querySelectorAll('.card-check:checked');
  const master  = document.getElementById('checkAll');
  const all     = document.querySelectorAll('.card-check');
  document.getElementById('bulkCount').textContent = `${checked.length}개 선택`;
  master.indeterminate = checked.length > 0 && checked.length < all.length;
  master.checked = checked.length === all.length && all.length > 0;
}

function clearBulkSelection() {
  document.querySelectorAll('.card-check').forEach(cb => cb.checked = false);
  document.getElementById('checkAll').checked = false;
  document.getElementById('checkAll').indeterminate = false;
  _lastCardChecked = null;
  updateBulkBar();
}

async function saveBulkPrice() {
  const price = parseInt(document.getElementById('bulkPriceInput').value, 10) || 0;
  const checked = [...document.querySelectorAll('.card-check:checked')];
  if (!checked.length) return;

  const useMinFilter = document.getElementById('minPriceToggle').checked;
  const threshold    = price;
  const csrfToken    = document.querySelector('meta[name="csrf-token"]').content;
  let successCount = 0, skippedCount = 0;

  await Promise.all(checked.map(async cb => {
    const cardId = cb.dataset.id;
    if (useMinFilter && threshold > 0) {
      const row = document.getElementById('row-' + cardId);
      const currentPrice = row ? (parseInt(row.dataset.selling, 10) || 0) : 0;
      if (currentPrice >= threshold) { skippedCount++; return; }
    }
    try {
      const res  = await fetch(SET_PRICE_BASE + '/' + cardId + '/set-price/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ selling_price: price }),
      });
      const data = await res.json();
      if (data.success) {
        successCount++;
        const disp = document.getElementById('disp-' + cardId);
        if (disp) {
          disp.innerHTML = price > 0
            ? `<span class="price-set">${price.toLocaleString()}원</span><span class="price-saved-badge">✓ 수정됨</span><span class="price-edit-hint">✎</span>`
            : `<span class="price-unset">미설정</span><span class="price-edit-hint">✎</span>`;
        }
        const row = document.getElementById('row-' + cardId);
        if (row) { row.dataset.selling = price; row.classList.add('row--saved'); }
        document.getElementById('edit-' + cardId)?.classList.remove('show');
        disp && (disp.style.display = '');
      }
    } catch {}
  }));

  const msg = skippedCount > 0
    ? `${successCount}개 적용, ${skippedCount}개 스킵 (${threshold.toLocaleString()}원 이상)`
    : `${successCount}개 카드에 ${price > 0 ? price.toLocaleString() + '원' : '미설정'} 적용됐습니다.`;
  showToast(msg);
  clearBulkSelection();
  document.getElementById('bulkPriceInput').value = '';
}

function toggleCardListRarity(rarity, btn) {
  if (_cardListRarities.has(rarity)) {
    _cardListRarities.delete(rarity);
    btn.classList.remove('active');
  } else {
    _cardListRarities.add(rarity);
    btn.classList.add('active');
  }
  applyCardListRarityFilter();
}

function selectCardListRarities(rarities) {
  _cardListRarities = new Set(rarities);
  document.querySelectorAll('.rarity-chip').forEach(btn => {
    btn.classList.toggle('active', _cardListRarities.has(btn.dataset.rarity));
  });
  applyCardListRarityFilter();
}

function applyCardListRarityFilter() {
  const params = new URLSearchParams();
  params.set('filter', _cardListFilterType || 'all');
  params.set('sort',   _cardListSort || 'number');
  _cardListRarities.forEach(r => params.append('rarities', r));
  location.href = '?' + params.toString();
}


/* ================================================================
   bulk_drop / bulk_unpriced — 일괄 가격 적용 (SET_PRICE_URL_PREFIX 사용)
   bulk_drop: underOnly 옵션 지원
   bulk_unpriced: underOnly 없음
   ================================================================ */

/**
 * 체크된 카드에 일괄 가격 적용
 * @param {boolean} [withUnderOnly=false]  true이면 현재 판매가 미만인 카드만 적용 (bulk_drop용)
 */
/* ── bulk_drop: 체크된 카드에 일괄 가격 적용 (판매가 미만만 적용 옵션 포함) ── */
async function bulkSetPriceDrop() {
  const price = parseInt(document.getElementById('bulkSetPriceInput').value, 10);
  if (!price || price <= 0) {
    showIssueToast('가격을 입력해주세요.', 'err'); return;
  }

  const underOnly = document.getElementById('bulkSetUnderOnly')?.checked;
  const checked   = [...document.querySelectorAll('.row-check:checked')];
  if (!checked.length) { showIssueToast('체크된 카드가 없습니다.', 'err'); return; }

  const targets = checked.filter(cb => {
    if (!underOnly) return true;
    const row     = document.getElementById('row-' + cb.dataset.id);
    const current = parseInt(row?.dataset.selling || '0', 10);
    return current > price;
  });

  if (!targets.length) {
    showIssueToast('조건에 맞는 카드가 없습니다.', 'err'); return;
  }
  if (!confirm(`${targets.length}개 카드에 ${price.toLocaleString()}원을 적용할까요?`)) return;

  let success = 0, skip = 0;
  await Promise.all(targets.map(async cb => {
    const cardId = cb.dataset.id;
    try {
      const res  = await fetch(`${SET_PRICE_URL_PREFIX}${cardId}/set-price/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({ selling_price: price }),
      });
      const data = await res.json();
      if (data.success) {
        const row = document.getElementById('row-' + cardId);
        if (row) row.dataset.selling = price;
        const input = document.getElementById('input-' + cardId);
        if (input) { input.value = price; input.classList.add('saved'); }
        success++;
      } else skip++;
    } catch { skip++; }
  }));

  const msg = skip > 0
    ? `✅ ${success}개 적용, ${skip}개 실패`
    : `✅ ${success}개에 ${price.toLocaleString()}원 적용 완료`;
  showIssueToast(msg, success > 0 ? 'ok' : 'err');
  document.getElementById('bulkSetPriceInput').value = '';
}

/* ── bulk_unpriced: 체크된 카드에 일괄 가격 적용 ── */
async function bulkSetPriceUnpriced() {
  const price = parseInt(document.getElementById('bulkSetPriceInput').value, 10);
  if (!price || price <= 0) {
    showIssueToast('가격을 입력해주세요.', 'err'); return;
  }

  const checked = [...document.querySelectorAll('.row-check:checked')];
  if (!checked.length) { showIssueToast('체크된 카드가 없습니다.', 'err'); return; }
  if (!confirm(`${checked.length}개 카드에 ${price.toLocaleString()}원을 적용할까요?`)) return;

  let success = 0, skip = 0;
  await Promise.all(checked.map(async cb => {
    const cardId = cb.dataset.id;
    try {
      const res  = await fetch(`${SET_PRICE_URL_PREFIX}${cardId}/set-price/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({ selling_price: price }),
      });
      const data = await res.json();
      if (data.success) {
        const input = document.getElementById('input-' + cardId);
        if (input) { input.value = price; input.classList.add('saved'); }
        success++;
      } else skip++;
    } catch { skip++; }
  }));

  const msg = skip > 0
    ? `✅ ${success}개 적용, ${skip}개 실패`
    : `✅ ${success}개에 ${price.toLocaleString()}원 적용 완료`;
  showIssueToast(msg, success > 0 ? 'ok' : 'err');
  document.getElementById('bulkSetPriceInput').value = '';
}