(() => {
  'use strict';

  const MAX_COMPARE = 4;
  const compareIds = new Set();
  let lastModalTrigger = null;
  let restored = false;
  let suppressUrlWrite = false;
  let sidebarHome = null;

  const escapeHtml = (value = '') => String(value).replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  })[character]);

  const itemId = item => String(item?.id || item?.item_id || '');
  const creatorName = item => String(item?.author || item?.creator_name || '不明');
  const itemThumbnail = item => String(item?.thumbnail || item?.thumbnail_url || '');
  const boothUrl = item => String(item?.source_url || item?.booth_url || `https://booth.pm/ja/items/${itemId(item)}`);
  const explicitTargets = item => (item?.compatible_avatars || item?.targets || [])
    .map(target => typeof target === 'string' ? target : (target?.name || target?.code || ''))
    .filter(Boolean);
  const priceLabel = item => Number(item?.price || 0) === 0 ? '無料' : `¥${Number(item?.price || 0).toLocaleString('ja-JP')}`;
  const normalizeList = values => [...new Set(values.filter(Boolean).map(value => String(value).trim()))];

  function itemById(id) {
    return allItems.find(item => itemId(item) === String(id));
  }

  function provenance(item) {
    const hasTargets = explicitTargets(item).length > 0;
    const hasNormalized = Boolean(item?.tag_set && Object.values(item.tag_set).some(value => Array.isArray(value) && value.length));
    const hasDerived = Boolean(item?.category || item?.similar_items?.length);
    return [
      {kind: 'observed', label: '販売ページ観測', detail: '商品名・価格・販売者・BOOTH URL'},
      hasTargets
        ? {kind: 'observed', label: '明示対応あり', detail: `${explicitTargets(item).length}件の対応表記`}
        : {kind: 'unknown', label: '対応不明', detail: '対応アバターの明示情報を確認できません'},
      hasNormalized
        ? {kind: 'normalized', label: '正規化タグ', detail: '販売ページの表記を統制語彙へ対応'}
        : {kind: 'unknown', label: '正規化なし', detail: '統制語彙への対応情報がありません'},
      hasDerived
        ? {kind: 'derived', label: '派生分類', detail: 'カテゴリ・類似度などシステム生成値を含む'}
        : {kind: 'unknown', label: '派生値なし', detail: '派生分類を確認できません'},
    ];
  }

  function addSkipLink() {
    if (document.querySelector('.ux-skip-link')) return;
    const link = document.createElement('a');
    link.className = 'ux-skip-link';
    link.href = '#asset-grid';
    link.textContent = '商品一覧へ移動';
    document.body.prepend(link);
  }

  function addMobileFilterUi() {
    const header = document.querySelector('body > header');
    const sidebar = document.querySelector('body > aside');
    if (!header || !sidebar || document.querySelector('#ux-filter-dialog')) return;

    sidebarHome = {parent: sidebar.parentNode, next: sidebar.nextSibling};
    const openButton = document.createElement('button');
    openButton.type = 'button';
    openButton.className = 'ux-filter-open';
    openButton.innerHTML = '<span aria-hidden="true">☰</span><span>絞り込み</span>';
    header.append(openButton);

    const dialog = document.createElement('dialog');
    dialog.id = 'ux-filter-dialog';
    dialog.innerHTML = `
      <div class="ux-filter-shell">
        <div class="ux-filter-head"><h2>商品を絞り込む</h2><button type="button" data-filter-close aria-label="閉じる">×</button></div>
        <div data-filter-slot></div>
        <div class="ux-filter-footer"><button type="button" data-filter-clear>全解除</button><button type="button" class="primary" data-filter-apply>結果を見る</button></div>
      </div>`;
    document.body.append(dialog);

    const restoreSidebar = () => {
      if (!sidebarHome || !dialog.contains(sidebar)) return;
      sidebarHome.parent.insertBefore(sidebar, sidebarHome.next);
    };
    const close = () => {
      dialog.close();
      restoreSidebar();
      openButton.focus();
    };
    openButton.addEventListener('click', () => {
      dialog.querySelector('[data-filter-slot]').append(sidebar);
      dialog.showModal();
      dialog.querySelector('[data-filter-close]').focus();
    });
    dialog.querySelector('[data-filter-close]').addEventListener('click', close);
    dialog.querySelector('[data-filter-apply]').addEventListener('click', close);
    dialog.querySelector('[data-filter-clear]').addEventListener('click', () => {
      clearAll();
      syncControlsFromFilters();
    });
    dialog.addEventListener('cancel', event => {
      event.preventDefault();
      close();
    });
    dialog.addEventListener('click', event => {
      if (event.target === dialog) close();
    });
  }

  function createComparisonUi() {
    const main = document.querySelector('body > main');
    const grid = document.querySelector('#asset-grid');
    if (!main || !grid || document.querySelector('#ux-compare-tray')) return;

    const tray = document.createElement('section');
    tray.id = 'ux-compare-tray';
    tray.className = 'ux-compare-tray';
    tray.hidden = true;
    tray.setAttribute('aria-labelledby', 'ux-compare-title');
    tray.innerHTML = `
      <div class="ux-compare-copy"><strong id="ux-compare-title"><span data-compare-count>0</span>件を比較に選択</strong><span>2〜${MAX_COMPARE}件を同じ項目で比較できます</span><div class="ux-compare-chips" data-compare-chips></div></div>
      <div class="ux-compare-actions"><button type="button" class="primary" data-show-comparison disabled>比較を見る</button><button type="button" data-clear-comparison>選択解除</button></div>`;

    const panel = document.createElement('section');
    panel.id = 'ux-comparison-panel';
    panel.className = 'ux-comparison-panel';
    panel.hidden = true;
    panel.setAttribute('aria-labelledby', 'ux-comparison-title');
    panel.innerHTML = `
      <div class="ux-comparison-head"><div><h2 id="ux-comparison-title">選択商品の比較</h2><p>販売ページ観測、明示対応、正規化、派生分類を混在させずに確認します。</p></div><button type="button" data-close-comparison>比較を閉じる</button></div>
      <div class="ux-comparison-scroll" tabindex="0" aria-label="商品比較表。横方向にスクロールできます。" data-comparison-table></div>
      <div class="ux-comparison-cards" data-comparison-cards></div>`;

    const controlPanel = main.querySelector('.control-panel');
    if (controlPanel?.nextSibling) main.insertBefore(tray, controlPanel.nextSibling);
    else main.prepend(tray);
    main.insertBefore(panel, grid);

    tray.querySelector('[data-show-comparison]').addEventListener('click', showComparison);
    tray.querySelector('[data-clear-comparison]').addEventListener('click', () => {
      compareIds.clear();
      panel.hidden = true;
      updateComparisonUi();
      enhanceCards();
      writeUrlState();
    });
    panel.querySelector('[data-close-comparison]').addEventListener('click', () => {
      panel.hidden = true;
      tray.querySelector('[data-show-comparison]').focus();
    });
  }

  function provenanceBadges(item) {
    return provenance(item).map(entry => `<span class="provenance-badge provenance-${entry.kind}" title="${escapeHtml(entry.detail)}">${escapeHtml(entry.label)}</span>`).join('');
  }

  function enhanceCards() {
    document.querySelectorAll('.asset-card').forEach(card => {
      const id = card.dataset.id;
      const item = itemById(id);
      if (!item) return;
      card.tabIndex = 0;
      card.setAttribute('role', 'group');
      card.setAttribute('aria-label', `${item.title}、${creatorName(item)}、${priceLabel(item)}`);
      const image = card.querySelector('.asset-thumb');
      if (image) {
        image.alt = `${item.title}の商品画像`;
        image.width = 640;
        image.height = 480;
        image.decoding = 'async';
      }
      const info = card.querySelector('.asset-info');
      if (!info) return;

      let provenanceRow = info.querySelector('.asset-provenance');
      if (!provenanceRow) {
        provenanceRow = document.createElement('div');
        provenanceRow.className = 'asset-provenance';
        info.append(provenanceRow);
      }
      provenanceRow.innerHTML = provenanceBadges(item);

      let actions = info.querySelector('.asset-actions');
      if (!actions) {
        actions = document.createElement('div');
        actions.className = 'asset-actions';
        info.append(actions);
      }
      actions.innerHTML = `
        <button type="button" class="asset-action" data-open-detail="${escapeHtml(id)}">詳細と根拠</button>
        <a class="asset-action asset-action-primary" href="${escapeHtml(boothUrl(item))}" target="_blank" rel="noopener noreferrer">BOOTH ↗</a>
        <label class="asset-compare"><input type="checkbox" data-compare-item="${escapeHtml(id)}" ${compareIds.has(id) ? 'checked' : ''}><span>${compareIds.has(id) ? '比較中' : '比較'}</span></label>`;

      actions.querySelectorAll('button,a,label,input').forEach(control => control.addEventListener('click', event => event.stopPropagation()));
      actions.querySelector('[data-open-detail]').addEventListener('click', event => {
        lastModalTrigger = event.currentTarget;
        openModal(id);
      });
      actions.querySelector('[data-compare-item]').addEventListener('change', event => toggleComparison(id, event.currentTarget.checked, event.currentTarget));
      card.addEventListener('keydown', event => {
        if ((event.key === 'Enter' || event.key === ' ') && event.target === card) {
          event.preventDefault();
          lastModalTrigger = card;
          openModal(id);
        }
      });
    });
  }

  function toggleComparison(id, checked, input) {
    if (checked && !compareIds.has(id) && compareIds.size >= MAX_COMPARE) {
      input.checked = false;
      announce(`比較できるのは最大${MAX_COMPARE}件です。`);
      return;
    }
    if (checked) compareIds.add(id); else compareIds.delete(id);
    updateComparisonUi();
    enhanceCards();
    writeUrlState();
  }

  function selectedItems() {
    return [...compareIds].map(itemById).filter(Boolean);
  }

  function updateComparisonUi() {
    const tray = document.querySelector('#ux-compare-tray');
    const panel = document.querySelector('#ux-comparison-panel');
    if (!tray || !panel) return;
    const items = selectedItems();
    tray.hidden = items.length === 0;
    tray.querySelector('[data-compare-count]').textContent = String(items.length);
    tray.querySelector('[data-show-comparison]').disabled = items.length < 2;
    tray.querySelector('[data-compare-chips]').innerHTML = items.map(item => `<button type="button" data-remove-compare="${escapeHtml(itemId(item))}" aria-label="${escapeHtml(item.title)}を比較から外す">${escapeHtml(item.title)} ×</button>`).join('');
    tray.querySelectorAll('[data-remove-compare]').forEach(button => button.addEventListener('click', () => {
      compareIds.delete(button.dataset.removeCompare);
      if (compareIds.size < 2) panel.hidden = true;
      updateComparisonUi();
      enhanceCards();
      writeUrlState();
    }));
  }

  function comparisonRows(items) {
    const row = (label, renderer) => `<tr><th scope="row">${escapeHtml(label)}</th>${items.map(item => `<td>${renderer(item)}</td>`).join('')}</tr>`;
    return [
      row('価格', item => `<strong>${escapeHtml(priceLabel(item))}</strong>`),
      row('販売者', item => escapeHtml(creatorName(item))),
      row('カテゴリ', item => `<span class="provenance-badge provenance-normalized">${escapeHtml(item.category || 'UNKNOWN')}</span><small>正規化または派生分類</small>`),
      row('明示対応', item => explicitTargets(item).length ? `<strong>${explicitTargets(item).length}件</strong><small>${escapeHtml(explicitTargets(item).slice(0, 5).join('、'))}</small>` : '<span class="provenance-badge provenance-unknown">対応不明</span>'),
      row('正規化タグ', item => item.tag_set ? `<strong>あり</strong><small>販売ページ表記を統制語彙へ対応</small>` : '<span class="provenance-badge provenance-unknown">なし</span>'),
      row('監査状態', item => escapeHtml(item.audit_status || 'UNKNOWN')),
      row('BOOTH', item => `<a href="${escapeHtml(boothUrl(item))}" target="_blank" rel="noopener noreferrer">商品ページ ↗</a>`),
    ].join('');
  }

  function comparisonCard(item) {
    const targets = explicitTargets(item);
    return `<article class="ux-comparison-card"><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(creatorName(item))} · ${escapeHtml(priceLabel(item))}</p><div class="asset-provenance">${provenanceBadges(item)}</div><dl><div><dt>カテゴリ</dt><dd>${escapeHtml(item.category || 'UNKNOWN')}</dd></div><div><dt>明示対応</dt><dd>${targets.length ? escapeHtml(targets.slice(0, 5).join('、')) : '対応不明'}</dd></div><div><dt>監査状態</dt><dd>${escapeHtml(item.audit_status || 'UNKNOWN')}</dd></div></dl><a class="asset-action asset-action-primary" href="${escapeHtml(boothUrl(item))}" target="_blank" rel="noopener noreferrer">BOOTHを開く ↗</a></article>`;
  }

  function showComparison() {
    const items = selectedItems();
    if (items.length < 2) return;
    const panel = document.querySelector('#ux-comparison-panel');
    panel.querySelector('[data-comparison-table]').innerHTML = `<table class="ux-comparison-table"><caption>選択した${items.length}商品の比較</caption><thead><tr><th scope="col">項目</th>${items.map(item => `<th scope="col">${escapeHtml(item.title)}<small>${escapeHtml(creatorName(item))}</small></th>`).join('')}</tr></thead><tbody>${comparisonRows(items)}</tbody></table>`;
    panel.querySelector('[data-comparison-cards]').innerHTML = items.map(comparisonCard).join('');
    panel.hidden = false;
    panel.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
  }

  function enhanceFilterPills() {
    document.querySelectorAll('.tag-pill').forEach(pill => {
      pill.tabIndex = 0;
      pill.setAttribute('role', 'button');
      pill.setAttribute('aria-pressed', String(pill.classList.contains('active')));
      pill.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          pill.click();
          pill.setAttribute('aria-pressed', String(pill.classList.contains('active')));
        }
      });
    });
    document.querySelectorAll('.filter-btn').forEach(button => {
      button.setAttribute('aria-pressed', String(button.classList.contains('active')));
      button.addEventListener('click', () => queueMicrotask(() => button.setAttribute('aria-pressed', String(button.classList.contains('active')))));
    });
  }

  function activeFilterEntries() {
    const entries = [];
    if (filters.query) entries.push({label: `検索: ${filters.query}`, remove: () => { filters.query = ''; document.querySelector('#search-bar').value = ''; }});
    if (filters.avatar) {
      const avatar = metaAvatars.find(value => value.code === filters.avatar);
      entries.push({label: `アバター: ${avatar?.name || filters.avatar}`, remove: () => { filters.avatar = null; }});
    }
    if (filters.cat !== 'all') entries.push({label: `カテゴリ: ${filters.cat}`, remove: () => { filters.cat = 'all'; }});
    if (filters.price !== 'all') entries.push({label: `価格: ${filters.price}`, remove: () => { filters.price = 'all'; }});
    filters.features.forEach(value => entries.push({label: `機能: ${value}`, remove: () => filters.features.delete(value)}));
    filters.styles.forEach(value => entries.push({label: `スタイル: ${value}`, remove: () => filters.styles.delete(value)}));
    filters.colors.forEach(value => entries.push({label: `色: ${value}`, remove: () => filters.colors.delete(value)}));
    return entries;
  }

  function renderActiveSummary() {
    const row = document.querySelector('#active-filters-row');
    if (!row) return;
    const entries = activeFilterEntries();
    row.replaceChildren();
    const summary = document.createElement('div');
    summary.className = 'ux-results-summary';
    summary.innerHTML = `<strong>${filtered.length.toLocaleString('ja-JP')}件</strong><span>${entries.length ? `${entries.length}条件で絞り込み` : '全商品を表示'}</span>`;
    row.append(summary);
    entries.forEach(entry => {
      const chip = document.createElement('span');
      chip.className = 'filter-chip';
      const label = document.createElement('span');
      label.textContent = entry.label;
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'filter-chip-remove';
      remove.textContent = '×';
      remove.setAttribute('aria-label', `${entry.label}を解除`);
      remove.addEventListener('click', () => {
        entry.remove();
        syncControlsFromFilters();
        applyFiltersDeferred();
      });
      chip.append(label, remove);
      row.append(chip);
    });
    if (entries.length) {
      const clear = document.createElement('button');
      clear.type = 'button';
      clear.className = 'clear-filters-btn';
      clear.textContent = 'すべて解除';
      clear.addEventListener('click', () => {
        clearAll();
        syncControlsFromFilters();
      });
      row.append(clear);
    }
  }

  function syncControlsFromFilters() {
    const search = document.querySelector('#search-bar');
    const sort = document.querySelector('#sort-select');
    if (search) search.value = filters.query || '';
    if (sort) sort.value = filters.sort;
    document.querySelectorAll('.avatar-btn').forEach(button => button.classList.toggle('active', button.dataset.code === filters.avatar));
    document.querySelectorAll('.category-btn').forEach(button => button.classList.toggle('active', button.dataset.cat === filters.cat));
    document.querySelectorAll('.price-preset-btn').forEach(button => button.classList.toggle('active', button.dataset.price === filters.price));
    document.querySelectorAll('.feature-tag').forEach(pill => pill.classList.toggle('active', filters.features.has(pill.dataset.val)));
    document.querySelectorAll('.style-tag').forEach(pill => pill.classList.toggle('active', filters.styles.has(pill.dataset.val)));
    document.querySelectorAll('.color-tag').forEach(pill => pill.classList.toggle('active', filters.colors.has(pill.dataset.val)));
    enhanceFilterPills();
  }

  function stateParams() {
    const params = new URLSearchParams();
    if (filters.query) params.set('q', filters.query);
    if (filters.avatar) params.set('avatar', filters.avatar);
    if (filters.cat !== 'all') params.set('category', filters.cat);
    if (filters.price !== 'all') params.set('price', filters.price);
    if (filters.sort !== 'popular') params.set('sort', filters.sort);
    if (filters.features.size) params.set('features', [...filters.features].join(','));
    if (filters.styles.size) params.set('styles', [...filters.styles].join(','));
    if (filters.colors.size) params.set('colors', [...filters.colors].join(','));
    if (displayedCount > 40) params.set('limit', String(displayedCount));
    if (compareIds.size) params.set('compare', [...compareIds].join(','));
    if (DOM.dialog?.open) {
      const title = document.querySelector('#modal-title')?.dataset.itemId;
      if (title) params.set('item', title);
    }
    return params;
  }

  function writeUrlState() {
    if (suppressUrlWrite || !restored) return;
    const params = stateParams();
    history.replaceState(null, '', `${location.pathname}${params.size ? `?${params}` : ''}${location.hash}`);
  }

  function readSet(params, key) {
    return new Set(normalizeList((params.get(key) || '').split(',')));
  }

  function restoreUrlState() {
    if (restored || !allItems.length || !metaAvatars.length) return;
    suppressUrlWrite = true;
    const params = new URLSearchParams(location.search);
    filters.query = params.get('q') || '';
    filters.cat = params.get('category') || 'all';
    filters.price = params.get('price') || 'all';
    filters.sort = params.get('sort') || 'popular';
    filters.features = readSet(params, 'features');
    filters.styles = readSet(params, 'styles');
    filters.colors = readSet(params, 'colors');
    const avatarParam = params.get('avatar');
    if (avatarParam) {
      const avatar = metaAvatars.find(value => value.code.toLowerCase() === avatarParam.toLowerCase() || value.name.toLowerCase() === avatarParam.toLowerCase());
      filters.avatar = avatar?.code || null;
    }
    compareIds.clear();
    (params.get('compare') || '').split(',').filter(Boolean).slice(0, MAX_COMPARE).forEach(id => compareIds.add(id));
    renderStaticFilters();
    syncControlsFromFilters();
    applyFilters();
    const requestedLimit = Math.max(40, Number(params.get('limit')) || 40);
    displayedCount = Math.min(filtered.length, requestedLimit);
    renderGrid();
    restored = true;
    suppressUrlWrite = false;
    renderActiveSummary();
    updateComparisonUi();
    writeUrlState();
    const selected = params.get('item');
    if (selected && itemById(selected)) openModal(selected);
  }

  function addModalProvenance(item) {
    const right = document.querySelector('.modal-right');
    if (!right || !item) return;
    let section = right.querySelector('.ux-provenance-section');
    if (!section) {
      section = document.createElement('section');
      section.className = 'modal-sub-section ux-provenance-section';
      const action = right.querySelector('#modal-booth-link');
      action?.insertAdjacentElement('afterend', section);
    }
    const targets = explicitTargets(item);
    section.innerHTML = `<h4>情報の来歴</h4><div class="ux-provenance-list">
      <div class="ux-provenance-row"><strong>販売ページ観測</strong><span>商品名、価格、販売者、商品URL</span></div>
      <div class="ux-provenance-row"><strong>対応情報</strong><span>${targets.length ? `${targets.length}件の明示表記` : 'UNKNOWN — 明示情報なし'}</span></div>
      <div class="ux-provenance-row"><strong>正規化</strong><span>${item.tag_set ? '統制語彙へ対応済み' : 'UNKNOWN'}</span></div>
      <div class="ux-provenance-row"><strong>派生値</strong><span>カテゴリ・類似商品はシステム生成値</span></div>
      <div class="ux-provenance-row"><strong>監査状態</strong><span>${escapeHtml(item.audit_status || 'UNKNOWN')}</span></div>
    </div>`;
    document.querySelector('#modal-title').dataset.itemId = itemId(item);
  }

  function announce(message) {
    const status = document.querySelector('#results-meta');
    if (status) status.textContent = message;
  }

  function wrapExistingFunctions() {
    const originalRenderGrid = renderGrid;
    renderGrid = function wrappedRenderGrid() {
      originalRenderGrid();
      const empty = DOM.grid.querySelector('.ux-empty-state');
      if (!filtered.length && !empty) DOM.grid.innerHTML = '<div class="ux-empty-state"><strong>条件に一致する商品がありません</strong><p>絞り込み条件を解除してください。</p></div>';
      enhanceCards();
      updateComparisonUi();
      writeUrlState();
    };

    const originalRenderChips = renderChips;
    renderChips = function wrappedRenderChips() {
      originalRenderChips();
      renderActiveSummary();
      writeUrlState();
    };

    const originalRenderStaticFilters = renderStaticFilters;
    renderStaticFilters = function wrappedRenderStaticFilters() {
      originalRenderStaticFilters();
      enhanceFilterPills();
      syncControlsFromFilters();
    };

    const originalFillModal = fillModal;
    fillModal = function wrappedFillModal(item) {
      originalFillModal(item);
      addModalProvenance(item);
      writeUrlState();
    };

    const originalOpenModal = openModal;
    openModal = async function wrappedOpenModal(id) {
      const result = await originalOpenModal(id);
      document.querySelector('#modal-title').dataset.itemId = id;
      writeUrlState();
      return result;
    };

    DOM.dialog.addEventListener('close', () => {
      delete document.querySelector('#modal-title').dataset.itemId;
      writeUrlState();
      if (lastModalTrigger?.isConnected) lastModalTrigger.focus();
    });
  }

  function bootstrap() {
    addSkipLink();
    addMobileFilterUi();
    createComparisonUi();
    wrapExistingFunctions();
    const timer = window.setInterval(() => {
      if (allItems.length && metaAvatars.length) {
        window.clearInterval(timer);
        restoreUrlState();
      }
    }, 50);
    window.setTimeout(() => window.clearInterval(timer), 20000);
    window.addEventListener('popstate', () => {
      restored = false;
      restoreUrlState();
    });
  }

  bootstrap();
})();
