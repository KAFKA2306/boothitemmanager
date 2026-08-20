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

  function install() {
    if (typeof window.fillModal !== 'function' || window.fillModal.__compatibilityEvidenceWrapped) return false;
    const original = window.fillModal;
    const wrapped = function wrappedFillModal(item) {
      original(item);
      renderCompatibilityEvidence(item);
    };
    wrapped.__compatibilityEvidenceWrapped = true;
    window.fillModal = wrapped;
    return true;
  }

  if (!install()) {
    const timer = window.setInterval(() => {
      if (install()) window.clearInterval(timer);
    }, 50);
    window.setTimeout(() => window.clearInterval(timer), 20000);
  }
})();
