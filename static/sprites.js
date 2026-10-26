'use strict';
(async function () {
  const catalog = JSON.parse(document.getElementById('sprite-catalog').textContent);
  const config = JSON.parse(document.getElementById('sprite-config').textContent);
  const $ = id => document.getElementById(id);
  const valid = new Set(catalog.filter(x => x.released).map(x => x.id));
  const key = 'fortnite-hub:sprites:v1:' + (config.userId ? config.userId + ':' + (config.username || '') : 'guest');
  let storageOk = true, owned = new Set(), ready = false;
  let queue = Promise.resolve();
  let pending = [];
  const status = text => { $('sprite-save-status').textContent = text; };
  function readLocal() {
    try {
      const value = JSON.parse(localStorage.getItem(key) || '[]');
      return Array.isArray(value) ? value.filter(x => typeof x === 'string' && valid.has(x)) : [];
    } catch (_) { storageOk = false; return []; }
  }
  const backup = new Set(readLocal());
  owned = new Set(backup);
  function persist() {
    backup.clear(); owned.forEach(id => backup.add(id));
    try { localStorage.setItem(key, JSON.stringify([...owned])); }
    catch (_) { storageOk = false; status('Salvataggio nel browser non disponibile. Esporta una copia prima di uscire.'); }
  }
  async function request(body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('/api/sprites/collection', {
        method: body ? 'POST' : 'GET', credentials: 'same-origin',
        headers: body ? {'Content-Type': 'application/json'} : {},
        body: body ? JSON.stringify(body) : undefined, signal: controller.signal
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Salvataggio non riuscito');
      return data;
    } finally { clearTimeout(timeout); }
  }
  function save(body) {
    persist();
    if (!config.userId) {
      status(storageOk ? 'Salvato in questo browser. Accedi per usare anche il salvataggio nell’account.' : 'Esporta una copia: il browser non consente il salvataggio.');
      return Promise.resolve();
    }
    status('Salvataggio nell’account…');
    queue = queue.then(async () => {
      try {
        await request(body);
        status(storageOk ? 'Salvato nell’account e in questo browser.' : 'Salvato nell’account. Esporta una copia di sicurezza.');
      } catch (_) {
        pending.push(body);
        status(storageOk ? 'Account non raggiungibile: la modifica resta in questo browser. Usa Ripristina per sincronizzarla.' : 'Salvataggio non riuscito. Esporta subito una copia.');
        $('sprite-restore').hidden = false;
      }
    });
    return queue;
  }
  function text(tag, content, className) {
    const node = document.createElement(tag); node.textContent = content;
    if (className) node.className = className;
    return node;
  }
  const families = [...new Set(catalog.map(x => x.family))].sort((a,b) => a.localeCompare(b,'it'));
  families.forEach(family => {
    const option = text('option', family); option.value = family; $('sprite-family').append(option);
  });
  const cards = catalog.map(item => {
    const card = document.createElement('article'); card.className = 'sprite-card';
    const fallback = text('div', '👻', 'sprite-fallback'); fallback.setAttribute('aria-hidden','true');
    if (item.image) {
      const img = document.createElement('img'); img.src = item.image; img.alt = ''; img.loading = 'lazy';
      img.className = 'sprite-art'; img.referrerPolicy = 'no-referrer';
      img.onerror = () => img.replaceWith(fallback); card.append(img);
    } else card.append(fallback);
    card.append(text('h2', item.family));
    card.append(text('p', config.styles[item.style] || item.style));
    card.append(text('span', item.archived ? 'Archiviato' : item.released ? 'Pubblicato' : 'Non confermato', 'sprite-badge'));
    card.append(text('p', item.name));
    if (!item.name_official) card.append(text('p', 'Nome della community'));
    const label = document.createElement('label');
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox';
    checkbox.setAttribute('aria-label', 'Possiedo ' + item.name);
    const caption = text('span', 'Da raccogliere');
    label.append(checkbox, caption); card.append(label);
    checkbox.addEventListener('change', () => {
      checkbox.checked ? owned.add(item.id) : owned.delete(item.id);
      void save({id: item.id, owned: checkbox.checked}); render();
    });
    $('sprite-grid').append(card);
    return {item, card, checkbox, caption};
  });
  function render() {
    const query = $('sprite-search').value.trim().toLocaleLowerCase('it');
    const family = $('sprite-family').value, style = $('sprite-style').value;
    const filter = $('sprite-status').value, season = $('sprite-season').value;
    let visible = 0;
    cards.forEach(({item,card,checkbox,caption}) => {
      const has = owned.has(item.id);
      const eligible = season === 'active' ? item.active && item.released :
        season === 'archived' ? item.archived && item.released :
        season === 'upcoming' ? !item.released : item.released;
      const match = eligible && (!family || item.family === family) && (!style || item.style === style)
        && (!query || (item.name + ' ' + item.family).toLocaleLowerCase('it').includes(query))
        && (filter === 'all' || (filter === 'owned' ? has : item.released && !has));
      card.hidden = !match; if (match) visible++;
      checkbox.checked = has; checkbox.disabled = !ready || !item.released;
      caption.textContent = !item.released ? 'Non ancora selezionabile' : has ? 'Posseduto' : 'Da raccogliere';
      card.classList.toggle('is-owned', has);
    });
    const count = [...owned].filter(id => valid.has(id)).length;
    const percent = valid.size ? Math.round(count / valid.size * 100) : 0;
    $('sprite-owned').textContent = count; $('sprite-missing').textContent = valid.size - count;
    $('sprite-percent').textContent = percent + '%'; $('sprite-progress').value = percent;
    $('sprite-results').textContent = visible ? visible + ' varianti visualizzate · ' + valid.size + ' pubblicate nel catalogo completo' : 'Nessuna variante corrisponde ai filtri.';
  }
  for (const id of ['sprite-search','sprite-family','sprite-style','sprite-status','sprite-season']) $(id).addEventListener('input',render);
  $('sprite-export').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify({format:'fortnite-hub-sprites',version:1,exported_at:new Date().toISOString(),ids:[...owned]},null,2)],{type:'application/json'});
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = 'fortnite-hub-spiritelli.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('sprite-import').addEventListener('change', async event => {
    const file = event.target.files[0]; if (!file) return;
    try {
      if (file.size > 200000) throw new Error('File troppo grande.');
      const data = JSON.parse(await file.text());
      if (data.format !== 'fortnite-hub-sprites' || data.version !== 1 || !Array.isArray(data.ids)
          || data.ids.length > 2000 || data.ids.some(id => typeof id !== 'string')) throw new Error('Copia non valida.');
      const accepted = data.ids.filter(id => valid.has(id));
      accepted.forEach(id => owned.add(id)); render();
      await save({ids: accepted});
      if (accepted.length !== data.ids.length) status('Importazione completata. Alcuni ID non sono presenti nel catalogo e sono stati ignorati. Conserva il file originale.');
    } catch (error) { status('Importazione non riuscita: ' + error.message); }
    finally { event.target.value = ''; }
  });
  $('sprite-restore').addEventListener('click', async () => {
    backup.forEach(id => owned.add(id)); render();
    $('sprite-restore').hidden = true;
    const retry = pending; pending = [];
    for (const change of retry) await save(change);
    await save({ids:[...owned]});
  });
  render();
  if (config.userId) {
    try {
      const data = await request(); const server = new Set(data.ids.filter(id => valid.has(id)));
      if (server.size || !backup.size) {
        owned = server;
        status('Collezione caricata dall’account.');
        if ([...backup].some(id => !server.has(id))) {
          $('sprite-restore').hidden = false;
          status('Collezione caricata. Nel browser esiste anche una copia: puoi aggiungerla con Ripristina.');
        } else persist();
      } else {
        $('sprite-restore').hidden = false;
        status('Account senza selezioni: è visibile la copia del browser. Premi Ripristina per salvarla nell’account.');
      }
    } catch (_) {
      $('sprite-restore').hidden = false;
      status('Account non raggiungibile. Puoi continuare con la copia nel browser ed esportarla.');
    }
  } else status(storageOk ? 'Collezione salvata in questo browser. Nessun accesso richiesto.' : 'Memoria del browser non disponibile. Usa Esporta per conservare le selezioni.');
  ready = true; render();
})();
