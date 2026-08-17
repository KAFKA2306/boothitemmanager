(() => {
  'use strict';

  let restored = false;
  let suppressUrlWrite = false;
  let sidebarHome = null;

  const normalizeList = values => [...new Set(values.filter(Boolean).map(value => String(value).trim()))];
  const itemId = item => String(item?.id || item?.item_id || '');

  function itemById(id) {
    return allItems.find(item => itemId(item) === String(id));
  }

  function matchesSelectedAvatar(item) {
    if (!filters.avatar) return true;
    const avatar = metaAvatars.find(value => value.code === filters.avatar);
    const accepted = new Set([filters.avatar, avatar?.name].filter(Boolean).map(value => String(value).toLowerCase()));
    const targets = item.compatible_avatars || item.targets || [];
    return targets.some(target => {
      const value = typeof target === 'string' ? target : (target.name || target.code || '');
      return accepted.has(String(value).toLowerCase());
    });
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

  function enhanceCards() {
    document.querySelectorAll('.asset-card').forEach(card => {
      const id = card.dataset.id;
      const item = itemById(id);
      if (!item) return;
      card.tabIndex = 0;
      card.setAttribute('role', 'button');
      card.setAttribute('aria-label', `${item.title}の詳細を開く`);
      const image = card.querySelector('.asset-thumb');
      if (image) {
        image.alt = `${item.title}の商品画像`;
        image.width = 640;
        image.height = 480;
        image.decoding = 'async';
      }
      card.addEventListener('keydown', event => {
        if ((event.key === 'Enter' || event.key === ' ') && event.target === card) {
          event.preventDefault();
          openModal(id);
        }
      });
    });
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
    } else {
      filters.avatar = null;
    }
    renderStaticFilters();
    syncControlsFromFilters();
    applyFilters();
    const requestedLimit = Math.max(40, Number(params.get('limit')) || 40);
    displayedCount = Math.min(filtered.length, requestedLimit);
    renderGrid();
    restored = true;
    suppressUrlWrite = false;
    renderActiveSummary();
    writeUrlState();
  }

  function wrapExistingFunctions() {
    const originalRenderGrid = renderGrid;
    renderGrid = function wrappedRenderGrid() {
      originalRenderGrid();
      const empty = DOM.grid.querySelector('.ux-empty-state');
      if (!filtered.length && !empty) DOM.grid.innerHTML = '<div class="ux-empty-state"><strong>条件に一致する商品がありません</strong><p>絞り込み条件を解除してください。</p></div>';
      enhanceCards();
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

    const originalApplyFilters = applyFilters;
    applyFilters = function wrappedApplyFilters() {
      originalApplyFilters();
      if (!filters.avatar) return;
      const matched = filtered.filter(matchesSelectedAvatar);
      if (matched.length === filtered.length) return;
      filtered = matched;
      displayedCount = 40;
      renderGrid();
      renderChips();
    };
  }

  function bootstrap() {
    addSkipLink();
    addMobileFilterUi();
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
