(() => {
  'use strict';

  const uniqueText = values => [...new Set((values || []).filter(Boolean).map(value => String(value).trim()).filter(Boolean))];

  function targetNames(item) {
    return uniqueText((item?.targets || item?.compatible_avatars || []).map(target => {
      if (typeof target === 'string') return target;
      return target?.name || target?.code || '';
    }));
  }

  function derivedSearchLabels(item) {
    return uniqueText([
      ...(item?.style || item?.tag_set?.style || []),
      ...(item?.color || item?.tag_set?.color || []),
      ...(item?.feature || item?.tag_set?.feature || []),
      ...(item?.platform || item?.tag_set?.platform || []),
      ...(item?.tags || item?.tags_raw || []),
    ]).slice(0, 12);
  }

  function formatObservation(value) {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat('ja-JP', {
      dateStyle: 'medium',
      timeStyle: 'short',
      timeZone: 'Asia/Tokyo',
    }).format(date);
  }

  function addEvidenceRow(section, labelText, valueText, modifier) {
    const row = document.createElement('div');
    row.className = `compatibility-evidence__row${modifier ? ` ${modifier}` : ''}`;

    const label = document.createElement('div');
    label.className = 'compatibility-evidence__label';
    label.textContent = labelText;

    const value = document.createElement('div');
    value.className = 'compatibility-evidence__value';
    value.textContent = valueText;

    row.append(label, value);
    section.append(row);
  }

  function renderCompatibilityEvidence(item) {
    const modal = document.querySelector('#detail-dialog');
    const right = modal?.querySelector('.modal-right');
    const boothLink = modal?.querySelector('#modal-booth-link');
    if (!right || !boothLink) return;

    right.querySelector('.compatibility-evidence')?.remove();

    const section = document.createElement('section');
    section.className = 'compatibility-evidence';
    section.setAttribute('aria-label', '購入前の互換性確認');

    const heading = document.createElement('h4');
    heading.textContent = '購入前の互換性確認';
    section.append(heading);

    const targets = targetNames(item);
    if (targets.length) {
      addEvidenceRow(
        section,
        '販売ページ記載から抽出',
        targets.join(' / '),
        'compatibility-evidence__row--observed',
      );
    } else {
      addEvidenceRow(
        section,
        '対応アバター',
        '不明 — このデータから販売者明示の対応先を確認できません。',
        'compatibility-evidence__row--unknown',
      );
    }

    const derived = derivedSearchLabels(item);
    if (derived.length) {
      addEvidenceRow(
        section,
        '検索補助（派生）',
        `${derived.join(' / ')} — 検索・分類用であり、互換性の根拠ではありません。`,
        'compatibility-evidence__row--derived',
      );
    }

    const observedAt = formatObservation(item?.last_observed_at || item?.last_changed_at);
    addEvidenceRow(
      section,
      'データ観測',
      observedAt ? `${observedAt} JST` : '観測日時なし',
      '',
    );

    const note = document.createElement('p');
    note.className = 'compatibility-evidence__note';
    note.textContent = '購入・導入前の最終判断は、販売者が管理するBOOTH商品ページの最新説明・利用条件を確認してください。';
    section.append(note);

    const linkLabel = boothLink.querySelector('span');
    if (linkLabel) linkLabel.textContent = 'BOOTHで最新情報を確認';
    boothLink.rel = 'noopener noreferrer';
    boothLink.insertAdjacentElement('afterend', section);
  }

  function sharedItemId() {
    const match = /^#item-(.+)$/.exec(location.hash);
    if (!match) return null;
    try {
      return decodeURIComponent(match[1]);
    } catch {
      return null;
    }
  }

  function writeSharedItem(id) {
    const hash = `#item-${encodeURIComponent(String(id))}`;
    history.replaceState(null, '', `${location.pathname}${location.search}${hash}`);
  }

  function clearSharedItem() {
    if (!sharedItemId()) return;
    history.replaceState(null, '', `${location.pathname}${location.search}`);
  }

  function restoreSharedItem() {
    const id = sharedItemId();
    if (!id || typeof allItems === 'undefined' || !Array.isArray(allItems)) return false;
    const exists = allItems.some(item => String(item?.id || item?.item_id || '') === id);
    if (!exists) return false;
    const modal = document.querySelector('#detail-dialog');
    if (modal?.open && String(modal.dataset.sharedItem || '') === id) return true;
    window.openModal(id);
    if (modal) modal.dataset.sharedItem = id;
    return true;
  }

  function install() {
    if (typeof window.fillModal !== 'function' || typeof window.openModal !== 'function') return false;

    if (!window.fillModal.__compatibilityEvidenceWrapped) {
      const originalFillModal = window.fillModal;
      const wrappedFillModal = function wrappedFillModal(item) {
        originalFillModal(item);
        renderCompatibilityEvidence(item);
      };
      wrappedFillModal.__compatibilityEvidenceWrapped = true;
      window.fillModal = wrappedFillModal;
    }

    if (!window.openModal.__sharedDetailWrapped) {
      const originalOpenModal = window.openModal;
      const wrappedOpenModal = function wrappedOpenModal(id) {
        originalOpenModal(id);
        const modal = document.querySelector('#detail-dialog');
        if (modal) modal.dataset.sharedItem = String(id);
        writeSharedItem(id);
      };
      wrappedOpenModal.__sharedDetailWrapped = true;
      window.openModal = wrappedOpenModal;
    }

    const modal = document.querySelector('#detail-dialog');
    if (modal && !modal.dataset.sharedDetailCloseBound) {
      modal.dataset.sharedDetailCloseBound = 'true';
      modal.addEventListener('close', () => {
        delete modal.dataset.sharedItem;
        clearSharedItem();
      });
      modal.addEventListener('cancel', () => queueMicrotask(clearSharedItem));
    }

    const closeButton = document.querySelector('#modal-close-btn');
    if (closeButton && !closeButton.dataset.sharedDetailCloseBound) {
      closeButton.dataset.sharedDetailCloseBound = 'true';
      closeButton.addEventListener('click', () => queueMicrotask(clearSharedItem));
    }
    return true;
  }

  function restoreWhenReady() {
    if (restoreSharedItem()) return;
    const timer = window.setInterval(() => {
      if (restoreSharedItem()) window.clearInterval(timer);
    }, 50);
    window.setTimeout(() => window.clearInterval(timer), 20000);
  }

  function start() {
    if (install()) {
      restoreWhenReady();
      return;
    }
    const timer = window.setInterval(() => {
      if (install()) {
        window.clearInterval(timer);
        restoreWhenReady();
      }
    }, 50);
    window.setTimeout(() => window.clearInterval(timer), 20000);
  }

  window.addEventListener('hashchange', () => {
    const modal = document.querySelector('#detail-dialog');
    if (sharedItemId()) {
      restoreSharedItem();
    } else if (modal?.open) {
      modal.close();
    }
  });

  start();
})();
