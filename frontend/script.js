// Mismo origen cuando la app se sirve por HTTP (local o Render): SERVER=''
// => las peticiones van a /ping, /parsear, etc. relativas al host actual.
// Si se abre el HTML como archivo suelto (file://), usa el server local.
const SERVER = (location.protocol === 'file:') ? 'http://localhost:5000' : '';

// ── Ejemplos predefinidos ──
const EJEMPLOS = {
  hola:`// Hola Mundo en DiamondLang 💎
funcion principal()
hacer
    cadena mensaje <- "¡Hola, Mundo!"
    escribir(mensaje)
fin_funcion`,
  factorial:`// Factorial recursivo
funcion factorial(entero n) retornar entero
hacer
    si n <= 1 entonces
        retornar 1
    sino
        retornar n * factorial(n - 1)
    fin_si
fin_funcion`,
  fibonacci:`// Fibonacci iterativo
funcion fibonacci(entero n) retornar entero
hacer
    entero a <- 0
    entero b <- 1
    entero i <- 0
    mientras i < n hacer
        entero temp <- a + b
        a <- b
        b <- temp
        i <- i + 1
    fin_mientras
    retornar a
fin_funcion`,
  condicional:`funcion clasificar(real nota) retornar cadena
hacer
    si nota >= 9.0 entonces
        retornar "Sobresaliente"
    sino
        si nota >= 7.0 entonces
            retornar "Aprobado"
        sino
            retornar "Reprobado"
        fin_si
    fin_si
fin_funcion`,
  error_lex:`// Con errores léxicos
funcion prueba()
hacer
    entero x <- 10
    entero y <- x @ 3
    cadena s <- "sin cerrar
    escribir(x)
fin_funcion`,
};

// ── Tabs ──
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => {
    const names = ['lexico','sintactico','tabla','sets','traduccion'];
    t.className = 'tab' + (names[i] === name ? ' active' : '');
  });
  document.querySelectorAll('.pane').forEach(p => p.className = 'pane');
  document.getElementById('pane-'+name).className = 'pane active';
  if (name === 'tabla' && document.getElementById('ll-container').querySelector('.empty')) cargarTablaLL();
  if (name === 'sets'  && document.getElementById('primero-wrap').querySelector('.empty'))  cargarTablaLL();
}

// ── Servidor ──
async function ping() {
  try {
    const r = await fetch(`${SERVER}/ping`, {signal: AbortSignal.timeout(2000)});
    const d = await r.json();
    setStatus(true, d.estado);
  } catch { setStatus(false, 'Servidor offline'); }
}
function setStatus(ok, msg) {
  document.getElementById('status-dot').className = `status-dot ${ok?'online':'offline'}`;
  document.getElementById('status-text').textContent = msg;
  document.getElementById('offline-banner').className = `offline-banner ${ok?'':'visible'}`;
  ['btn-lex','btn-parse'].forEach(id => { const b = document.getElementById(id); if(b) b.disabled = !ok; });
}

// ── Análisis léxico ──
async function analizarLexico() {
  const codigo = document.getElementById('ed1').value;
  if (!codigo.trim()) return;
  setLoading('sp1', 'btn-lex', true);
  try {
    const res  = await fetch(`${SERVER}/analizar`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({codigo})});
    const data = await res.json();
    renderTokens(data.tokens);
    renderTablaLex(data.tokens);
    renderStatsLex(data.estadisticas, data.errores);
    renderErrLog('err-lex', 'ok-lex', data.errores);
  } catch(e) { setStatus(false,'Error de conexión'); }
  finally { setLoading('sp1','btn-lex',false); }
}

// ── Análisis sintáctico ──
async function parsear() {
  const codigo  = document.getElementById('ed2').value;
  const metodo  = document.getElementById('metodo-sel').value;
  const usar_ia = document.getElementById('usar-ia').checked;
  const usar_ia_semantica = document.getElementById('usar-ia-sem').checked;
  if (!codigo.trim()) return;
  setLoading('sp2','btn-parse',true);
  try {
    const res  = await fetch(`${SERVER}/parsear`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({codigo, metodo, usar_ia, usar_ia_semantica, max_errores: 100}),
    });
    const data = await res.json();

    // Árbol (dibujado en JS con los nodos JSON)
    renderArbol(data.nodos, data.valido, data.error, metodo, (data.errores||[]).length);

    // Lista numerada de errores (Entrega 3)
    renderErroresSintacticos(data.errores || []);

    // Fase semántica (Etapa 8): errores, símbolos y banner combinado
    renderErroresSemanticos(data.errores_semanticos || []);
    renderSimbolos(data.simbolos || []);
    renderBannerEstado(data.valido, data.valido_semantico);

    // Fase C: dispara la traducción a Julia solo si el análisis es válido
    // (sintáctico Y semántico). En cualquier otro caso, deja la pestaña vacía.
    if (data.valido && data.valido_semantico) {
      lanzarTraduccion(codigo, metodo);
    } else {
      traduccionActual = null;
      renderTraduccionVacio();
    }

    // Fase 6: resaltado inline en el editor (overlay + íconos en el gutter)
    renderOverlayErrores(data.errores || [], data.errores_semanticos || []);

    // Traza (solo predictivo)
    if (metodo === 'predictivo' && data.traza) {
      renderTraza(data.traza);
    } else {
      document.getElementById('traza-body').innerHTML =
        '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:14px;font-family:\'Space Mono\',monospace;font-size:0.67rem;">— Solo disponible en el Método Predictivo —</td></tr>';
      document.getElementById('traza-count').textContent = '';
    }
  } catch(e) { setStatus(false,'Error de conexión'); }
  finally { setLoading('sp2','btn-parse',false); }
}

// ── Diagnóstico IA: habilita/deshabilita el checkbox ──
async function pingIA() {
  try {
    const res  = await fetch(`${SERVER}/ping_ia`);
    const data = await res.json();
    const lbl  = document.getElementById('ia-toggle-label');
    const chk  = document.getElementById('usar-ia');
    if (data.disponible) {
      lbl.classList.remove('disabled');
      chk.disabled = false;
      lbl.title = `Sugerencias enriquecidas con ${data.modelo}`;
    } else {
      lbl.classList.add('disabled');
      chk.disabled = true;
      chk.checked  = false;
      lbl.title = data.libreria_instalada
        ? 'IA no disponible: define ANTHROPIC_API_KEY en el servidor'
        : 'IA no disponible: pip install anthropic';
    }
  } catch(e) { /* el banner de offline ya avisa */ }
}

// ── Diagnóstico IA semántica (Etapa 9): habilita/deshabilita su checkbox ──
async function pingIASemantica() {
  try {
    const res  = await fetch(`${SERVER}/ping_ia_semantica`);
    const data = await res.json();
    const lbl  = document.getElementById('ia-sem-toggle-label');
    const chk  = document.getElementById('usar-ia-sem');
    if (data.disponible) {
      lbl.classList.remove('disabled');
      chk.disabled = false;
      lbl.title = `Sugerencias semánticas enriquecidas con ${data.modelo}`;
    } else {
      lbl.classList.add('disabled');
      chk.disabled = true;
      chk.checked  = false;
      lbl.title = data.libreria_instalada
        ? 'IA no disponible: define ANTHROPIC_API_KEY en el servidor'
        : 'IA no disponible: pip install anthropic';
    }
  } catch(e) { /* el banner de offline ya avisa */ }
}

// ── Render: lista numerada de errores sintácticos ──
function renderErroresSintacticos(errores) {
  const panel = document.getElementById('errores-panel');
  const lista = document.getElementById('errores-list');
  const cnt   = document.getElementById('errores-count');
  if (!errores.length) {
    panel.className = 'errores-panel';
    lista.innerHTML = '';
    cnt.textContent = '';
    return;
  }
  panel.className = 'errores-panel active';
  cnt.textContent = `(${errores.length})`;
  lista.innerHTML = errores.map(e => {
    const esp     = (e.tokens_esperados||[]).join(' | ') || '—';
    const fuente  = e.fuente_sugerencia==='ia'?'IA':'LOCAL';
    const fcls    = e.fuente_sugerencia==='ia'?'ia':'local';
    const lex     = (e.lexema==='$'||e.tipo_token==='$')?'fin de archivo':`'${esc(e.lexema)}'`;
    return `<li class="err-item" data-fila="${e.fila}" data-columna="${e.columna}">
      <span class="err-num">${e.indice}</span>
      <span class="err-loc">línea ${e.fila}, columna ${e.columna}</span>
      <span class="err-source ${fcls}">${fuente}</span>
      <div class="err-found">Encontrado: <b>${lex}</b> tipo=${esc(e.tipo_token)}
        <span style="color:var(--border);margin:0 6px">·</span>
        no-terminal: <b>${esc(e.no_terminal)}</b></div>
      <div class="err-expected">Esperado: <b>${esc(esp)}</b></div>
      <div class="err-suggestion">¿Quiso decir? ${esc(e.sugerencia)}</div>
    </li>`;
  }).join('');
  // Click → resaltar línea/columna en el editor
  lista.querySelectorAll('.err-item').forEach(li => {
    li.addEventListener('click', () => resaltarEnEditor(
      parseInt(li.dataset.fila, 10),
      parseInt(li.dataset.columna, 10),
    ));
  });
}

// ── Render: lista numerada de errores semánticos (Etapa 8) ──
function renderErroresSemanticos(errores) {
  const panel = document.getElementById('sem-panel');
  const lista = document.getElementById('sem-list');
  const cnt   = document.getElementById('sem-count');
  if (!errores.length) {
    panel.className = 'sem-panel';
    lista.innerHTML = '';
    cnt.textContent = '';
    return;
  }
  panel.className = 'sem-panel active';
  cnt.textContent = `(${errores.length})`;
  lista.innerHTML = errores.map(e => {
    const tienePos = (e.fila !== null && e.fila !== undefined && e.fila > 0);
    const loc = tienePos ? `línea ${e.fila}, columna ${e.columna}` : 'sin posición';
    const lex = (e.lexema !== null && e.lexema !== undefined && e.lexema !== '')
      ? `<span class="sem-lex">· '${esc(e.lexema)}'</span>` : '';
    const esIA   = (e.fuente_sugerencia === 'ia');
    // Fase 7 (C4): emojis ✨/💡 → Material Symbols (auto_awesome / lightbulb)
    const fuente = esIA
      ? `<span class="sem-source ia"><span class="material-symbols-outlined sem-src-ic">auto_awesome</span>IA</span>`
      : `<span class="sem-source local">local</span>`;
    const sug = e.sugerencia
      ? `<div class="sem-suggestion ${esIA?'ia':''}"><span class="material-symbols-outlined sug-ic">${esIA?'auto_awesome':'lightbulb'}</span>${esc(e.sugerencia)}</div>`
      : '';
    return `<li class="sem-item ${tienePos?'':'nopos'}" data-fila="${e.fila}" data-columna="${e.columna}">
      <span class="sem-num">${e.indice}</span>
      <span class="sem-rule">${esc(e.regla)}</span>
      <span class="sem-loc">${loc}</span>${lex}${e.sugerencia?fuente:''}
      <div class="sem-msg">${esc(e.mensaje)}</div>
      ${sug}
    </li>`;
  }).join('');
  // Click → resaltar línea/columna (si la regla tiene posición)
  lista.querySelectorAll('.sem-item').forEach(li => {
    const fila = parseInt(li.dataset.fila, 10);
    if (!fila || fila <= 0) return;   // sin posición: el item se muestra, el click no hace nada
    li.addEventListener('click', () => resaltarEnEditor(
      fila, parseInt(li.dataset.columna, 10),
    ));
  });
}

// ── Render: tabla de símbolos de la fase semántica (Etapa 8) ──
function renderSimbolos(simbolos) {
  const panel = document.getElementById('simbolos-panel');
  const body  = document.getElementById('simbolos-body');
  const cnt   = document.getElementById('simbolos-count');
  if (!simbolos || !simbolos.length) {
    panel.className = 'simbolos-panel';   // oculto si está vacío
    body.innerHTML = '';
    cnt.textContent = '';
    return;
  }
  panel.className = 'simbolos-panel active';
  cnt.textContent = `(${simbolos.length})`;
  body.innerHTML = simbolos.map(s => `<tr>
    <td>${esc(s.nombre)}</td>
    <td class="s-cat">${esc(s.categoria)}</td>
    <td class="s-tipo">${esc(s.tipo)}</td>
    <td class="s-amb">${esc(s.ambito)}</td>
  </tr>`).join('');
}

// ── Banner de estado combinado: sintáctico + semántico (Etapa 8) ──
function renderBannerEstado(valido, validoSem) {
  const el = document.getElementById('estado-analisis');
  let cls, ic, txt;
  // Fase 7 (C3): glifos Unicode → Material Symbols (color heredado por currentColor)
  if (valido && validoSem)        { cls='estado-ok';   ic='check_circle'; txt='Análisis sintáctico y semántico válido'; }
  else if (valido && !validoSem)  { cls='estado-sem';  ic='warning';      txt='Sintaxis OK, pero hay errores semánticos'; }
  else if (!valido && validoSem)  { cls='estado-sint'; ic='error';        txt='Hay errores sintácticos (semántica OK en el resto)'; }
  else                            { cls='estado-bad';  ic='cancel';       txt='Errores sintácticos y semánticos detectados'; }
  el.className = `estado-analisis show ${cls}`;
  el.innerHTML = `<span class="material-symbols-outlined">${ic}</span>${esc(txt)}`;
}

// Posiciona el cursor del textarea en (fila, columna) y selecciona el lexema.
function resaltarEnEditor(fila, columna) {
  if (fila <= 0) return;
  const ed = document.getElementById('ed2');
  const lineas = ed.value.split('\n');
  let offset = 0;
  for (let i = 0; i < fila - 1 && i < lineas.length; i++) {
    offset += lineas[i].length + 1;  // +1 por el '\n'
  }
  offset += Math.max(0, columna - 1);
  ed.focus();
  // Seleccionar 1 carácter como guía visual; el navegador hará scroll automático
  ed.setSelectionRange(offset, Math.min(offset + 1, ed.value.length));
}

// ── Cargar tabla LL(1) ──
async function cargarTablaLL() {
  try {
    const res  = await fetch(`${SERVER}/tabla_ll`);
    const data = await res.json();
    renderTablaLL(data);
    renderSets(data.primero, data.siguiente);
  } catch(e) {
    document.getElementById('ll-container').innerHTML =
      '<div class="empty"><div class="empty-icon">⚠</div><div>Error cargando tabla. ¿Está el servidor activo?</div></div>';
  }
}

// ── Render: tokens chips ──
const TC={KEYWORD:'var(--tok-kw)',TIPO:'var(--tok-type)',IDENTIFICADOR:'var(--tok-id)',
  ENTERO:'var(--tok-num)',REAL:'var(--tok-num)',CADENA:'var(--tok-str)',
  OPERADOR:'var(--tok-op)',SIMBOLO:'var(--tok-sym)',BOOLEANO:'var(--tok-bool)',
  COMENTARIO:'var(--tok-cmt)',ERROR:'var(--tok-err)'};

function renderTokens(tokens) {
  const c = document.getElementById('tokens-display');
  if (!tokens.length) { c.innerHTML='<div class="empty"><div class="empty-icon">◇</div><div>Sin tokens</div></div>'; return; }
  const lines={};
  tokens.forEach(t=>{(lines[t.linea]=lines[t.linea]||[]).push(t);});
  let html='';
  Object.keys(lines).sort((a,b)=>a-b).forEach(ln=>{
    html+=`<div style="margin-bottom:3px"><span style="font-family:'Space Mono',monospace;font-size:0.59rem;color:var(--muted);margin-right:6px;user-select:none">${String(ln).padStart(3,'0')}</span>`;
    lines[ln].forEach(t=>{html+=`<span class="token-chip tok-${t.tipo}" data-type="${t.tipo}">${esc(t.lexema)}</span>`;});
    html+='</div>';
  });
  c.innerHTML=html;
  document.getElementById('tok-count').textContent=`${tokens.length} tokens`;
}

function renderTablaLex(tokens) {
  const tb=document.getElementById('tabla-lex');
  if(!tokens.length){tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:var(--muted)">Sin tokens</td></tr>';return;}
  tb.innerHTML=tokens.map((t,i)=>{
    const co=TC[t.tipo]||'var(--text)';
    return `<tr><td style="color:var(--muted)">${i+1}</td><td style="font-family:'Space Mono',monospace">${esc(t.lexema)}</td>
    <td><span style="background:${co}22;color:${co};border:1px solid ${co}44;padding:1px 6px;border-radius:3px;font-size:0.6rem">${t.tipo}</span></td>
    <td style="color:var(--muted)">${t.linea}</td><td style="color:var(--muted)">${t.columna}</td></tr>`;
  }).join('');
}

function renderStatsLex(stats, errores) {
  const bar=document.getElementById('stats-lex');
  bar.style.display='flex';
  document.getElementById('s-total').textContent=stats.total||0;
  document.getElementById('s-kw').textContent=stats.KEYWORD||0;
  document.getElementById('s-id').textContent=stats.IDENTIFICADOR||0;
  const errEl=document.getElementById('s-err');
  errEl.textContent=errores.length;
  errEl.classList.toggle('s-err-active', errores.length>0);   // Fase 7 (C1)
}

function renderErrLog(errId, okId, errores) {
  const el=document.getElementById(errId), ok=document.getElementById(okId);
  if(errores.length){
    el.className='error-log active';
    el.innerHTML=errores.map(e=>`⚠ ${esc(e)}`).join('<br>');
    ok.className='ok-log';
  } else {
    el.className='error-log';
    ok.className='ok-log active';
    ok.textContent='✓ Sin errores léxicos';
  }
}

// ════════════════════════════════════════
//  DIBUJADOR DE ÁRBOL — Canvas puro (sin graphviz)
// ════════════════════════════════════════

function renderArbol(nodos, valido, error, metodo, totalErrores) {
  const wrap   = document.getElementById('arbol-wrap');
  const errEl  = document.getElementById('err-sint');
  const okEl   = document.getElementById('ok-sint');
  document.getElementById('arbol-metodo').textContent = metodo==='recursivo'?'Método 1 — Recursivo':'Método 2 — Predictivo LL';

  if (!valido) {
    const n = totalErrores||0;
    errEl.className='error-log active';
    errEl.textContent = n
      ? `✗ ${n} error(es) sintáctico(s) detectado(s) — ver detalle abajo`
      : ('✗ '+(error||'Error sintáctico'));
    okEl.className='ok-log';
  } else {
    errEl.className='error-log';
    okEl.className='ok-log active';
    okEl.textContent='✓ Cadena válida — árbol generado correctamente';
  }

  if (!nodos) {
    wrap.innerHTML=`<div class="empty"><div class="empty-icon">${valido?'✓':'✗'}</div><div>${error||'Sin árbol'}</div></div>`;
    return;
  }

  // Calcular posiciones con BFS por niveles
  const posMap = {};
  calcularPosiciones(nodos, posMap);

  // Dimensiones del canvas
  const allPos = Object.values(posMap);
  const maxX   = Math.max(...allPos.map(p=>p.x)) + 80;
  const maxY   = Math.max(...allPos.map(p=>p.y)) + 50;
  const W      = Math.max(maxX + 40, 600);
  const H      = Math.max(maxY + 40, 300);

  // Crear SVG
  let svgLines = '', svgNodes = '';

  // Dibujar aristas primero (debajo de los nodos)
  function dibujarAristas(nodo) {
    const p = posMap[nodo.id];
    if (!p) return;
    (nodo.hijos||[]).forEach(hijo => {
      const ph = posMap[hijo.id];
      if (!ph) return;
      svgLines += `<line x1="${p.x}" y1="${p.y+16}" x2="${ph.x}" y2="${ph.y-16}" stroke="#4f4537" stroke-width="1.5"/>`;
      dibujarAristas(hijo);
    });
  }

  // Dibujar nodos
  function dibujarNodos(nodo) {
    const p = posMap[nodo.id];
    if (!p) return;
    const label  = nodo.etiqueta.length > 14 ? nodo.etiqueta.substring(0,12)+'…' : nodo.etiqueta;
    const tw     = Math.max(label.length * 7 + 16, 40);

    if (nodo.es_terminal) {
      if (nodo.etiqueta === 'ε') {
        svgNodes += `<text x="${p.x}" y="${p.y+4}" text-anchor="middle" font-family="Courier New" font-size="12" fill="#d3c4b2">ε</text>`;
      } else if (nodo.es_error) {
        svgNodes += `<rect x="${p.x-tw/2}" y="${p.y-14}" width="${tw}" height="22" rx="5" fill="#3a1414" stroke="#ffb4ab" stroke-width="1.5" stroke-dasharray="3,2"/>`;
        svgNodes += `<text x="${p.x}" y="${p.y+4}" text-anchor="middle" font-family="Courier New" font-size="11" fill="#ffb4ab">${escSvg(label)}</text>`;
      } else {
        svgNodes += `<rect x="${p.x-tw/2}" y="${p.y-14}" width="${tw}" height="22" rx="5" fill="#1f3322" stroke="#4CAF50" stroke-width="1.2"/>`;
        svgNodes += `<text x="${p.x}" y="${p.y+4}" text-anchor="middle" font-family="Courier New" font-size="11" fill="#4CAF50">${escSvg(label)}</text>`;
      }
    } else {
      svgNodes += `<ellipse cx="${p.x}" cy="${p.y}" rx="${tw/2}" ry="14" fill="#3C3F41" stroke="#ffc66d" stroke-width="1.5"/>`;
      svgNodes += `<text x="${p.x}" y="${p.y+4}" text-anchor="middle" font-family="Courier New" font-size="10" fill="#ffc66d">${escSvg(label)}</text>`;
    }
    (nodo.hijos||[]).forEach(dibujarNodos);
  }

  dibujarAristas(nodos);
  dibujarNodos(nodos);

  const svgStr = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" style="background:#2B2B2B;min-width:${W}px">
    <defs><marker id="arr" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#4f4537"/>
    </marker></defs>
    ${svgLines}${svgNodes}
  </svg>`;

  wrap.innerHTML = svgStr;
}

// Calcula x,y de cada nodo usando BFS por niveles
function calcularPosiciones(raiz, posMap) {
  const SEP_X = 60;   // separación horizontal entre hermanos
  const SEP_Y = 55;   // separación vertical entre niveles

  // Primero calculamos el "ancho" de cada subárbol
  function ancho(nodo) {
    if (!nodo.hijos || !nodo.hijos.length) return 1;
    return nodo.hijos.reduce((s,h) => s + ancho(h), 0);
  }

  // Luego asignamos posiciones recursivamente
  function asignar(nodo, xOffset, nivel) {
    const a = ancho(nodo);
    const cx = xOffset + a * SEP_X / 2;
    posMap[nodo.id] = { x: cx, y: 40 + nivel * SEP_Y };

    let xHijo = xOffset;
    (nodo.hijos||[]).forEach(hijo => {
      asignar(hijo, xHijo, nivel + 1);
      xHijo += ancho(hijo) * SEP_X;
    });
  }

  asignar(raiz, 20, 0);
}

function escSvg(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Render: traza pila ──
function renderTraza(traza) {
  const tb=document.getElementById('traza-body');
  document.getElementById('traza-count').textContent=`${traza.length} pasos`;
  tb.innerHTML=traza.map(p=>{
    let clase='', badge='';
    const ac=p.accion||'';
    if(ac.includes('MATCH')){clase='traza-match';badge=`<span class="badge-match">MATCH</span>`;}
    else if(ac.includes('EXPANDIR')){clase='traza-expand';badge=`<span class="badge-expand">EXPAND</span>`;}
    else if(ac.includes('SINCRONIZAR')){clase='traza-sync';badge=`<span class="badge-sync">SINC</span>`;}
    else if(ac.includes('INSERTAR')){clase='traza-insert';badge=`<span class="badge-insert">INSERT</span>`;}
    else if(ac.includes('DESCARTAR')){clase='traza-discard';badge=`<span class="badge-discard">DESCARTA</span>`;}
    else if(ac.includes('POP'))    {clase='traza-error';badge=`<span class="badge-pop">POP</span>`;}
    else if(ac.includes('ERROR')||ac.includes('ABORT')){clase='traza-error';badge=`<span class="badge-error">ERROR</span>`;}
    else if(ac.includes('ACEPTAR')){clase='traza-accept';badge=`<span class="badge-accept">✓ ACEPTAR</span>`;}
    const pilaStr=p.pila.slice(0,5).map(s=>`<span style="color:var(--accent);margin-right:3px">${esc(s)}</span>`).join('')+(p.pila.length>5?'<span style="color:var(--muted)">…</span>':'');
    return `<tr class="${clase}">
      <td style="color:var(--muted)">${p.paso}</td>
      <td style="font-family:'Space Mono',monospace;font-size:0.61rem">${pilaStr}</td>
      <td style="color:var(--accent3)">${esc(p.lookahead)}</td>
      <td>${badge} <span style="font-size:0.61rem;color:var(--text)">${esc(ac.replace(/^(MATCH|EXPANDIR|ERROR|ACEPTAR|SINCRONIZAR|INSERTAR|DESCARTAR|POP|ABORT)[^:]*: ?/,''))}</span></td>
      <td style="color:var(--tok-kw);font-size:0.61rem">${esc(p.produccion||'')}</td>
    </tr>`;
  }).join('');
}

// ── Render: tabla LL(1) ──
function renderTablaLL(data) {
  const container=document.getElementById('ll-container');
  const {tabla, no_terminales, terminales}=data;

  // Tomar solo terminales que aparecen en alguna celda (para no hacer tabla enorme)
  const termsUsados=terminales.slice(0,30); // máx 30 columnas para legibilidad

  let html=`<table class="ll-table"><thead><tr><th>No-terminal \\ Terminal</th>`;
  termsUsados.forEach(t=>{html+=`<th>${esc(t)}</th>`;});
  html+=`</tr></thead><tbody>`;

  no_terminales.forEach(nt=>{
    html+=`<tr><td class="ll-nt">${esc(nt)}</td>`;
    termsUsados.forEach(t=>{
      const prod=tabla[nt]&&tabla[nt][t];
      if(prod){
        html+=`<td class="ll-cell-filled" title="${esc(nt)} → ${esc(prod)}">${esc(prod.length>20?prod.substring(0,18)+'…':prod)}</td>`;
      } else {
        html+=`<td class="ll-cell-empty">—</td>`;
      }
    });
    html+=`</tr>`;
  });
  html+=`</tbody></table>`;
  container.innerHTML=html;
}

// ── Render: PRIMERO / SIGUIENTE ──
function renderSets(primero, siguiente) {
  ['primero','siguiente'].forEach(tipo=>{
    const data=tipo==='primero'?primero:siguiente;
    const wrap=document.getElementById(`${tipo}-wrap`);
    let html='';
    Object.keys(data).sort().forEach(nt=>{
      const vals=data[nt];
      const chips=vals.map(v=>{
        const cls=v==='ε'||v==='$'?'set-val-e':'set-val-t';
        return `<span class="set-val ${cls}">${esc(v)}</span>`;
      }).join('');
      html+=`<div class="set-row"><span class="set-nt">${esc(nt)}</span><span class="set-vals">${chips}</span></div>`;
    });
    wrap.innerHTML=html;
  });
}

// ── Utilidades ──
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function setLoading(spId, btnId, v) {
  document.getElementById(spId).style.display=v?'block':'none';
  document.getElementById(btnId).disabled=v;
}

function cargarEjemplo(edId, selId, cb) {
  const sel=document.getElementById(selId).value;
  if(!sel) return;
  document.getElementById(edId).value=EJEMPLOS[sel]||'';
  updateLN(edId, edId==='ed1'?'ln1':'ln2');
  if(cb) cb();
}

// ── Ejemplos semánticos (Etapa 10) ──────────────────────────────
// Cache en memoria de la lista que viene de GET /ejemplos_semanticos,
// indexada por nombre de archivo. Se carga una vez al arrancar.
const EJEMPLOS_SEM = {};

async function cargarMenuEjemplosSemanticos() {
  const sel = document.getElementById('ej-sem');
  if (!sel) return;
  try {
    const res  = await fetch(`${SERVER}/ejemplos_semanticos`);
    const data = await res.json();
    // Reset (deja sólo el placeholder)
    sel.innerHTML = '<option value="">⬥ Ejemplos semánticos</option>';
    if (!Array.isArray(data) || !data.length) {
      const opt = document.createElement('option');
      opt.value = ''; opt.disabled = true; opt.textContent = 'No hay ejemplos disponibles';
      sel.appendChild(opt);
      return;
    }
    // Agrupar por "grupo" preservando el orden de llegada.
    const grupos = new Map();
    data.forEach(it => {
      EJEMPLOS_SEM[it.archivo] = it;
      if (!grupos.has(it.grupo)) grupos.set(it.grupo, []);
      grupos.get(it.grupo).push(it);
    });
    grupos.forEach((items, nombreGrupo) => {
      const og = document.createElement('optgroup');
      og.label = nombreGrupo;
      items.forEach(it => {
        const opt = document.createElement('option');
        opt.value = it.archivo;
        opt.textContent = it.titulo;
        og.appendChild(opt);
      });
      sel.appendChild(og);
    });
  } catch (e) {
    sel.innerHTML = '<option value="">⬥ Ejemplos semánticos</option>'
                  + '<option value="" disabled>No hay ejemplos disponibles</option>';
  }
}

function cargarEjemploSemantico() {
  const sel = document.getElementById('ej-sem');
  const archivo = sel.value;
  if (!archivo) return;
  const it = EJEMPLOS_SEM[archivo];
  if (!it) return;
  document.getElementById('ed2').value = it.contenido;
  updateLN('ed2','ln2');
  parsear();
  // Deja el menú abierto en su placeholder para poder elegir otro sin reset manual
  sel.value = '';
}

// ── Ejemplos sintácticos (carga ejemplos_errores/ vía GET /ejemplos_sintacticos) ──
// Mismo mecanismo que los semánticos, dropdown paralelo.
const EJEMPLOS_SINT = {};

async function cargarMenuEjemplosSintacticos() {
  const sel = document.getElementById('ej-sint');
  if (!sel) return;
  try {
    const res  = await fetch(`${SERVER}/ejemplos_sintacticos`);
    const data = await res.json();
    sel.innerHTML = '<option value="">⚠ Ejemplos sintácticos</option>';
    if (!Array.isArray(data) || !data.length) {
      const opt = document.createElement('option');
      opt.value = ''; opt.disabled = true; opt.textContent = 'No hay ejemplos disponibles';
      sel.appendChild(opt);
      return;
    }
    data.forEach(it => {
      EJEMPLOS_SINT[it.archivo] = it;
      const opt = document.createElement('option');
      opt.value = it.archivo;
      opt.textContent = it.titulo;
      sel.appendChild(opt);
    });
  } catch (e) {
    sel.innerHTML = '<option value="">⚠ Ejemplos sintácticos</option>'
                  + '<option value="" disabled>No hay ejemplos disponibles</option>';
  }
}

function cargarEjemploSintactico() {
  const sel = document.getElementById('ej-sint');
  const archivo = sel.value;
  if (!archivo) return;
  const it = EJEMPLOS_SINT[archivo];
  if (!it) return;
  document.getElementById('ed2').value = it.contenido;
  updateLN('ed2','ln2');
  parsear();
  sel.value = '';
}

function limpiar(edId,lnId,tokId,tabId,errId,okId,statsId) {
  document.getElementById(edId).value='';
  updateLN(edId,lnId);
  document.getElementById(tokId).innerHTML='<div class="empty"><div class="empty-icon">◇</div><div>Esperando análisis</div></div>';
  document.getElementById(tabId).innerHTML='<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:16px">— Esperando análisis —</td></tr>';
  document.getElementById(errId).className='error-log';
  document.getElementById(okId).className='ok-log';
  document.getElementById(statsId).style.display='none';
}

function limpiarSint() {
  document.getElementById('ed2').value='';
  updateLN('ed2','ln2');
  // Fase 6: limpiar overlay y gutter (sin íconos)
  renderOverlayErrores([], []);
  document.getElementById('arbol-wrap').innerHTML='<div class="empty"><div class="empty-icon">🌳</div><div>El árbol aparecerá aquí</div></div>';
  document.getElementById('err-sint').className='error-log';
  document.getElementById('ok-sint').className='ok-log';
  document.getElementById('errores-panel').className='errores-panel';
  document.getElementById('errores-list').innerHTML='';
  document.getElementById('errores-count').textContent='';
  // Fase semántica (Etapa 8)
  document.getElementById('estado-analisis').className='estado-analisis';
  document.getElementById('estado-analisis').textContent='';
  document.getElementById('sem-panel').className='sem-panel';
  document.getElementById('sem-list').innerHTML='';
  document.getElementById('sem-count').textContent='';
  document.getElementById('simbolos-panel').className='simbolos-panel';
  document.getElementById('simbolos-body').innerHTML='';
  document.getElementById('simbolos-count').textContent='';
  document.getElementById('traza-body').innerHTML='<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:14px">— Selecciona Método Predictivo y analiza —</td></tr>';
  document.getElementById('traza-count').textContent='';
  document.getElementById('arbol-metodo').textContent='';
  // Fase C: al limpiar el editor, descartar la traducción y volver al vacío.
  traduccionActual = null;
  renderTraduccionVacio();
}

function updateLN(edId, lnId) {
  const n=document.getElementById(edId).value.split('\n').length;
  if (lnId === 'ln2') {
    // Fase 6: gutter enriquecido (estructura .ln-row, sin íconos = estado limpio).
    // renderOverlayErrores() reconstruye estas mismas filas añadiendo los íconos.
    document.getElementById(lnId).innerHTML =
      Array.from({length:n},(_,i)=>`<div class="ln-row"><span class="ln-num">${i+1}</span></div>`).join('');
  } else {
    // #ln1 (Léxico): estructura clásica sin tocar.
    document.getElementById(lnId).innerHTML=Array.from({length:n},(_,i)=>i+1).join('<br>');
  }
}

// ── FASE 6: resaltado inline de líneas con error (overlay + gutter de #ed2) ──
// Mapea fila→tipo de error y pinta:
//   · el overlay (#ed2-overlay): una banda por línea (rojo sint / ámbar sem).
//   · el gutter (#ln2): número + ícono Material Symbol por línea con error.
// El fondo prioriza el sintáctico (más grave); el gutter muestra ambos íconos.
function renderOverlayErrores(erroresSint, erroresSem) {
  const ed  = document.getElementById('ed2');
  const ovl = document.getElementById('ed2-overlay');
  const ln  = document.getElementById('ln2');
  if (!ed || !ovl || !ln) return;

  const filasSint = new Set((erroresSint||[]).map(e => e.fila).filter(f => f > 0));
  const filasSem  = new Set((erroresSem ||[]).filter(e => e.fila != null && e.fila > 0).map(e => e.fila));

  const totalLineas = ed.value.split('\n').length;

  // Overlay: un div por línea (transparente si no hay error; sint prioriza sobre sem).
  let overlayHTML = '';
  let gutterHTML  = '';
  for (let i = 1; i <= totalLineas; i++) {
    const esSint = filasSint.has(i);
    const esSem  = filasSem.has(i);
    const cls = esSint ? 'ovl-sint' : (esSem ? 'ovl-sem' : '');
    overlayHTML += `<div class="ovl-line ${cls}"></div>`;

    const icSint = esSint
      ? '<span class="material-symbols-outlined ln-ic ln-ic-sint" title="Error sintáctico">cancel</span>' : '';
    const icSem  = esSem
      ? '<span class="material-symbols-outlined ln-ic ln-ic-sem" title="Error semántico">warning_amber</span>' : '';
    gutterHTML += `<div class="ln-row">${icSint}${icSem}<span class="ln-num">${i}</span></div>`;
  }
  ovl.innerHTML = overlayHTML;
  ln.innerHTML  = gutterHTML;

  // Alinear horizontalmente el overlay con el textarea (= ancho del gutter, dinámico).
  ovl.style.left = ln.offsetWidth + 'px';
  // Reflejar el scroll actual del textarea de inmediato (sin esperar al evento).
  ovl.scrollTop  = ed.scrollTop;
  ovl.scrollLeft = ed.scrollLeft;
}

// ── Event listeners ──
['ed1','ed2'].forEach((id,i)=>{
  const lnId=i===0?'ln1':'ln2';
  const curId=i===0?'cur1':'cur2';
  const ed=document.getElementById(id);
  const ovl=(id==='ed2')?document.getElementById('ed2-overlay'):null;
  ed.addEventListener('input',()=>{
    updateLN(id,lnId);   // reconstruye el gutter limpio (sin íconos)
    // Fase 6: al primer cambio del usuario tras un análisis, las posiciones de error
    // ya no son confiables → se borra el overlay. updateLN ya quitó los íconos del gutter.
    if(ovl) ovl.innerHTML='';
  });
  ed.addEventListener('scroll',()=>{
    document.getElementById(lnId).scrollTop=ed.scrollTop;
    // Fase 6: el overlay sigue al textarea (vertical y horizontal)
    if(ovl){ovl.scrollTop=ed.scrollTop;ovl.scrollLeft=ed.scrollLeft;}
  });
  ed.addEventListener('keyup',()=>{
    const v=ed.value.substring(0,ed.selectionStart).split('\n');
    const pos=`Ln ${v.length}, Col ${v[v.length-1].length+1}`;
    document.getElementById(curId).textContent=pos;
    document.getElementById('fs-cursor').textContent=pos;   // Fase 7 (C5): footer sigue al editor activo
  });
  ed.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();i===0?analizarLexico():parsear();}
    if(e.key==='Tab'){e.preventDefault();const s=e.target.selectionStart;e.target.value=e.target.value.substring(0,s)+'    '+e.target.value.substring(e.target.selectionEnd);e.target.selectionStart=e.target.selectionEnd=s+4;updateLN(id,lnId);if(ovl)ovl.innerHTML='';}  /* Fase 7 (C6): Tab también invalida el overlay, igual que el listener input */
  });
});

// ── Paneles colapsables: añade un chevron a cada cabecera de panel de las 4
// pestañas y permite colapsar/expandir el cuerpo. Puramente visual, ortogonal
// a la lógica .active de los paneles dinámicos. ──
function setupCollapsibles() {
  // Cabeceras reales por pestaña (las clases NO son uniformes):
  //   Léxico .lex-hdr · Sintáctico .syn-hdr + .errores-hdr/.sem-hdr/.simbolos-hdr
  //   Tabla LL(1) y Sets usan .panel-hdr.
  const SEL = '.lex-hdr, .syn-hdr, .panel-hdr, .errores-hdr, .sem-hdr, .simbolos-hdr';
  document.querySelectorAll(SEL).forEach(hdr => {
    if (hdr.dataset.collapsibleReady) return;
    const panel = hdr.parentElement;            // el contenedor del panel
    if (!panel) return;
    hdr.dataset.collapsibleReady = '1';
    hdr.classList.add('collapsible-hdr');
    const chevron = document.createElement('span');
    chevron.className = 'material-symbols-outlined panel-chevron';
    chevron.textContent = 'expand_more';   // ▼ expandido; rota a ► (-90°) al colapsar
    chevron.title = 'Colapsar / expandir panel';
    hdr.appendChild(chevron);
    hdr.addEventListener('click', e => {
      // No colapsar si el click cae en un control interactivo de la cabecera
      // (botón Cargar, selects, etc.).
      if (e.target.closest('button, input, select, textarea, a')) return;
      panel.classList.toggle('panel-collapsed');
    });
  });
}

// ── Arranque ──
updateLN('ed1','ln1'); updateLN('ed2','ln2');
ping();
pingIA();
pingIASemantica();
cargarMenuEjemplosSemanticos();
cargarMenuEjemplosSintacticos();
setupCollapsibles();
setInterval(ping, 6000);

// ══════════════════════════════════════════════════════════════════════════
// ── CHATBOT (Fase 5a) ──
// Asistente modal SOLO frontend. Sin backend: las respuestas son placeholders
// deterministas (la integración real con Claude/Gemini es Fase 5b). Este bloque
// se AÑADE: no modifica ninguna función ni listener existente.
// ══════════════════════════════════════════════════════════════════════════
let chatHistory = [];          // [{ role:'user'|'assistant', text, model?, error? }]
let chatActiveModel = 'claude';
// Fase 5b: disponibilidad de cada modelo según /ping_chat.
//   null  = aún no consultado (o servidor caído) → se intenta el fetch real.
//   {...} = consultado → si ningún modelo está, se usa el placeholder local.
let chatModelsAvailable = null;
const CHAT_MODEL_LABEL = { claude:'Claude Haiku', gemini:'Gemini Flash' };

const chatModalEl = document.getElementById('chat-modal');
const chatBodyEl  = document.getElementById('chat-body');
const chatInputEl = document.getElementById('chat-input');

function openChat() {
  chatModalEl.classList.add('open');
  chatModalEl.setAttribute('aria-hidden','false');
  renderChatBody();
  setTimeout(() => chatInputEl.focus(), 50);   // focus al textarea al abrir
}
function closeChat() {
  chatModalEl.classList.remove('open');
  chatModalEl.setAttribute('aria-hidden','true');
}
function toggleChat() {
  chatModalEl.classList.contains('open') ? closeChat() : openChat();
}

function setChatModel(name) {
  if (name !== 'claude' && name !== 'gemini') return;
  // No permitir seleccionar un modelo marcado como no disponible.
  if (chatModelsAvailable && chatModelsAvailable[name] === false) return;
  chatActiveModel = name;
  document.querySelectorAll('#chat-model-selector button').forEach(b => {
    b.classList.toggle('active', b.dataset.model === name);
  });
}

// ── Fase 5b: disponibilidad de modelos (atenúa pills sin API key) ──
async function pingChat() {
  try {
    const res  = await fetch(`${SERVER}/ping_chat`);
    const data = await res.json();
    chatModelsAvailable = { claude: !!data.claude_disponible, gemini: !!data.gemini_disponible };
    document.querySelectorAll('#chat-model-selector button').forEach(b => {
      const ok = chatModelsAvailable[b.dataset.model];
      b.classList.toggle('chat-model-disabled', !ok);
      b.disabled = !ok;
      b.title = ok ? '' : (b.dataset.model === 'gemini'
        ? 'Gemini no disponible: define GOOGLE_API_KEY en el servidor'
        : 'Claude no disponible: define ANTHROPIC_API_KEY en el servidor');
    });
    // Si el modelo activo quedó deshabilitado, saltar a uno disponible.
    if (!chatModelsAvailable[chatActiveModel]) {
      if (chatModelsAvailable.claude) setChatModel('claude');
      else if (chatModelsAvailable.gemini) setChatModel('gemini');
    }
    // Fase D: el botón "Validar y optimizar con IA" depende de Claude (Anthropic).
    // Si no hay ANTHROPIC_API_KEY, se deshabilita con tooltip explicativo.
    const iaBtn = document.getElementById('tr-ia-btn');
    if (iaBtn) {
      const ok = !!data.claude_disponible;
      iaBtn.disabled = !ok;
      iaBtn.title = ok ? ''
        : 'Análisis con IA no disponible: define ANTHROPIC_API_KEY en el servidor';
    }
  } catch (e) { /* servidor caído: se queda en null y /chat hará fallback local */ }
}

// Escape de HTML local del chatbot (no se reutiliza el esc() existente para
// no acoplarse a otra sección; mismo comportamiento).
function escChat(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderChatBody() {
  if (chatHistory.length === 0) {
    chatBodyEl.innerHTML =
      '<div class="chat-empty">' +
        '<div class="chat-empty-icon"><span class="material-symbols-outlined">auto_awesome</span></div>' +
        '<div class="chat-empty-title">Listo para ayudar</div>' +
        '<div class="chat-empty-text">Inicia una conversación para obtener ayuda con tu código DiamondLang.</div>' +
        '<div class="chat-prompts">' +
          '<button type="button" class="chat-prompt" onclick="useChatPrompt(this)">¿Qué es la regla 3?</button>' +
          '<button type="button" class="chat-prompt" onclick="useChatPrompt(this)">¿Por qué falló mi análisis?</button>' +
          '<button type="button" class="chat-prompt" onclick="useChatPrompt(this)">¿Cómo funciona el alcance de variables?</button>' +
        '</div>' +
      '</div>';
    return;
  }
  let html = '';
  chatHistory.forEach(m => {
    if (m.role === 'user') {
      html += '<div class="chat-msg chat-msg-user"><div class="chat-bubble">' + escChat(m.text) + '</div></div>';
    } else {
      const model = m.model || 'claude';
      const label = CHAT_MODEL_LABEL[model] || CHAT_MODEL_LABEL.claude;
      const bubbleCls = 'chat-bubble' + (m.error ? ' chat-err' : '');
      html += '<div class="chat-msg chat-msg-asst"><div class="' + bubbleCls + '">' + escChat(m.text) + '</div>' +
              '<div class="chat-msg-meta ' + model + '"><span class="chat-model-dot"></span>' + escChat(label) + '</div></div>';
    }
  });
  chatBodyEl.innerHTML = html;
  chatBodyEl.scrollTop = chatBodyEl.scrollHeight;
}

function addMessage(role, text, model, isError) {
  chatHistory.push({
    role, text,
    model: role === 'assistant' ? (model || chatActiveModel) : undefined,
    error: !!isError,
  });
  renderChatBody();
}

// Indicador "escribiendo…": burbuja temporal NO persistida en chatHistory.
function showChatTyping(model) {
  removeChatTyping();
  const label = CHAT_MODEL_LABEL[model] || CHAT_MODEL_LABEL.claude;
  const node = document.createElement('div');
  node.className = 'chat-msg chat-msg-asst';
  node.id = 'chat-typing-row';
  node.innerHTML =
    '<div class="chat-bubble"><span class="chat-typing"><span></span><span></span><span></span></span></div>' +
    '<div class="chat-msg-meta ' + model + '"><span class="chat-model-dot"></span>' + escChat(label) + '</div>';
  chatBodyEl.appendChild(node);
  chatBodyEl.scrollTop = chatBodyEl.scrollHeight;
}
function removeChatTyping() {
  const n = document.getElementById('chat-typing-row');
  if (n) n.remove();
}

// Respuesta local determinista según el prompt. En 5b es el FALLBACK cuando
// no hay backend disponible (servidor caído o sin API keys). Devuelve el texto
// núcleo; el llamador añade el matiz de contexto entre paréntesis.
function chatPlaceholderReply(prompt) {
  const p = prompt.toLowerCase();
  if (p.includes('regla')) {
    return 'DiamondLang valida 5 reglas semánticas:\n' +
      '1) Toda variable debe declararse antes de usarse.\n' +
      '2) No se puede redeclarar un identificador en el mismo ámbito.\n' +
      '3) El tipo asignado debe ser compatible con el de la variable (TYPE_ASSIGNMENT).\n' +
      '4) Las condiciones de si/mientras deben ser de tipo booleano (TYPE_CONDITION).\n' +
      '5) Las funciones deben llamarse con la aridad y tipos de parámetros correctos.';
  }
  if (p.includes('análisis') || p.includes('analisis')) {
    return 'El pipeline del compilador es: léxico (genera tokens) → sintáctico (parser ' +
      'predictivo LL(1) o recursivo) → semántico (tabla de símbolos + las 5 reglas). ' +
      'Si una etapa falla, el error se reporta con línea y columna y se intenta recuperar.';
  }
  if (p.includes('alcance') || p.includes('scope')) {
    return 'El alcance puede ser global (declaraciones fuera de funciones, visibles en todo el ' +
      'programa) o local (dentro de una función o bloque, visibles solo ahí). Una variable local ' +
      'puede ocultar a una global del mismo nombre mientras dura su bloque.';
  }
  return 'Puedo ayudarte con preguntas sobre tu código DiamondLang, las reglas del compilador ' +
    'o la depuración de errores. Configura una API key en el servidor para respuestas del modelo.';
}

// Envío real a /chat (Fase 5b). Con fallback gracioso al placeholder local.
async function sendChat() {
  const text = chatInputEl.value.trim();
  if (!text) return;
  const modelAtSend = chatActiveModel;   // congela el modelo del momento del envío
  // Historial PREVIO (sin el mensaje nuevo): últimos 10, solo role+text.
  const historial = chatHistory.slice(-10).map(m => ({ role: m.role, text: m.text }));

  addMessage('user', text);
  chatInputEl.value = '';

  // Modo placeholder local: el servidor confirmó que NINGÚN modelo tiene key.
  if (chatModelsAvailable && !chatModelsAvailable.claude && !chatModelsAvailable.gemini) {
    setTimeout(() => addMessage('assistant',
      chatPlaceholderReply(text) +
      '\n\n(respuesta local — configura ANTHROPIC_API_KEY o GOOGLE_API_KEY para respuestas reales)',
      modelAtSend), 350);
    return;
  }

  showChatTyping(modelAtSend);
  try {
    const res  = await fetch(`${SERVER}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mensaje: text, modelo: modelAtSend, historial }),
    });
    const data = await res.json();
    removeChatTyping();
    if (data && data.error) {
      addMessage('assistant', '⚠ ' + data.error, modelAtSend, true);   // burbuja de error discreta
    } else {
      addMessage('assistant', data.respuesta || '(respuesta vacía)', modelAtSend);
    }
  } catch (e) {
    // Red caída → fallback al placeholder local con hint explícito.
    removeChatTyping();
    addMessage('assistant',
      chatPlaceholderReply(text) + '\n\n(sin conexión al servidor — respuesta local)',
      modelAtSend);
  }
}

function clearChat() {
  chatHistory = [];
  renderChatBody();
  chatInputEl.value = '';
  if (chatModalEl.classList.contains('open')) chatInputEl.focus();
}

function useChatPrompt(btn) {
  chatInputEl.value = btn.textContent;
  chatInputEl.focus();
}

// Cierre por click en el backdrop (solo si el click cae en el overlay, no en la card)
chatModalEl.addEventListener('mousedown', e => { if (e.target === chatModalEl) closeChat(); });

// Teclado en el textarea: Enter envía, Shift+Enter inserta nueva línea (default)
chatInputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

// Esc cierra el modal (solo cuando está abierto; no interfiere con el resto)
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && chatModalEl.classList.contains('open')) closeChat();
});

// Focus trap simple: mantiene el Tab dentro del modal mientras está abierto
chatModalEl.addEventListener('keydown', e => {
  if (e.key !== 'Tab') return;
  const f = chatModalEl.querySelectorAll('button, textarea, [tabindex]:not([tabindex="-1"])');
  if (!f.length) return;
  const first = f[0], last = f[f.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
});

renderChatBody();   // pinta el estado vacío inicial
pingChat();         // Fase 5b: consulta disponibilidad de modelos del chat

// ── PESTAÑA TRADUCCIÓN (Fase C) ──
// Quinta pestaña: muestra el código Julia generado por la fase SDT cuando el
// análisis es válido (sintáctico Y semántico). Se popula automáticamente desde
// parsear(); nunca tiene botón manual de "traducir".

let traduccionActual = null;  // { julia, fuente, fecha } | null

// Disparada desde parsear() cuando data.valido && data.valido_semantico.
// Llama al endpoint /traducir (Fase B) y puebla la pestaña con el resultado.
async function lanzarTraduccion(codigoFuente, metodo) {
  if (!codigoFuente.trim()) return;
  try {
    const res = await fetch(`${SERVER}/traducir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ codigo: codigoFuente, metodo }),
    });
    const data = await res.json();
    if (data.ok) {
      traduccionActual = { julia: data.julia, fuente: codigoFuente, fecha: new Date() };
      renderTraduccion();
    } else {
      traduccionActual = null;
      renderTraduccionVacio();
    }
  } catch (e) {
    traduccionActual = null;
    renderTraduccionVacio();
  }
}

// Pinta el side-by-side (DiamondLang ↔ Julia) + encabezado + stats.
function renderTraduccion() {
  const empty   = document.getElementById('tr-empty');
  const content = document.getElementById('tr-content');
  if (!traduccionActual) {
    empty.style.display = 'flex';
    content.style.display = 'none';
    return;
  }
  empty.style.display = 'none';
  content.style.display = 'flex';
  document.getElementById('tr-src-code').textContent = traduccionActual.fuente;
  document.getElementById('tr-jl-code').textContent  = traduccionActual.julia;
  const f = traduccionActual.fecha;
  document.getElementById('tr-meta').textContent = 'generada el ' + f.toLocaleString();
  // Stats: líneas no vacías + nº de funciones en el Julia generado.
  const lineas    = traduccionActual.julia.split('\n').filter(l => l.trim() !== '').length;
  const funciones = (traduccionActual.julia.match(/^function /gm) || []).length;
  document.getElementById('tr-stats').textContent = `${lineas} líneas · ${funciones} funciones`;
  // Fase D: cada traducción nueva resetea el panel IA (la respuesta anterior
  // ya no aplica al código recién generado).
  resetPanelIA();
}

// Estado vacío explicativo (sin traducción válida disponible).
function renderTraduccionVacio() {
  document.getElementById('tr-empty').style.display = 'flex';
  document.getElementById('tr-content').style.display = 'none';
  resetPanelIA();   // Fase D: deja el panel IA en su estado vacío.
}

// Descarga el Julia generado como programa.jl.
function descargarJulia() {
  if (!traduccionActual) return;
  const blob = new Blob([traduccionActual.julia], { type: 'text/x-julia;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url;
  a.download = 'programa.jl';
  a.click();
  URL.revokeObjectURL(url);
}

// Copia el Julia generado al portapapeles, con toast de confirmación.
async function copiarJulia() {
  if (!traduccionActual) return;
  try {
    await navigator.clipboard.writeText(traduccionActual.julia);
    mostrarToast('✓ Copiado al portapapeles');
  } catch (e) {
    mostrarToast('✗ Error al copiar');
  }
}

// Toast temporal anclado al body (se crea una sola vez y se reutiliza).
function mostrarToast(mensaje) {
  let t = document.getElementById('tr-toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'tr-toast';
    t.className = 'tr-toast';
    document.body.appendChild(t);
  }
  t.textContent = mensaje;
  t.classList.add('tr-toast-show');
  setTimeout(() => t.classList.remove('tr-toast-show'), 2000);
}

// ── BONUS IA (Fase D, Modalidad C): validación + optimización del Julia ──
// Capa OPCIONAL sobre la pestaña Traducción. Envía el código Julia ya generado
// a /validar_julia (que llama a Claude Haiku) y renderiza la respuesta
// estructurada en dos secciones. Si la IA no está disponible, el botón queda
// deshabilitado (vía pingChat → /ping_chat) y nada de esto se dispara.

// Deja el panel IA en su estado inicial (placeholder visible, sin resultado).
function resetPanelIA() {
  const empty  = document.getElementById('tr-ia-empty');
  const result = document.getElementById('tr-ia-result');
  const error  = document.getElementById('tr-ia-error');
  const meta   = document.getElementById('tr-ia-meta');
  if (empty)  empty.style.display  = 'block';
  if (result) result.style.display = 'none';
  if (error)  error.style.display  = 'none';
  if (meta)   meta.textContent     = '';
}

async function solicitarAnalisisIA() {
  if (!traduccionActual) return;
  const btn    = document.getElementById('tr-ia-btn');
  const status = document.getElementById('tr-ia-status');
  btn.disabled = true;
  status.textContent = 'Analizando con Claude Haiku';
  status.classList.add('thinking');
  try {
    const res = await fetch(`${SERVER}/validar_julia`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ julia: traduccionActual.julia }),
    });
    const data = await res.json();
    if (data.ok) {
      renderAnalisisIA(data);
    } else {
      mostrarErrorIA(data.error || 'La IA no devolvió un análisis.');
    }
  } catch (e) {
    mostrarErrorIA('Error de conexión con el servidor: ' + e.message);
  } finally {
    btn.disabled = false;
    status.textContent = '';
    status.classList.remove('thinking');
  }
}

function renderAnalisisIA(data) {
  document.getElementById('tr-ia-empty').style.display  = 'none';
  document.getElementById('tr-ia-error').style.display  = 'none';
  document.getElementById('tr-ia-result').style.display = 'block';
  document.getElementById('tr-ia-meta').textContent =
    data.modelo + ' · ' + new Date().toLocaleTimeString();
  document.getElementById('tr-ia-validacion').textContent = data.validacion || '';

  // Problemas detectados (sección oculta si la lista viene vacía).
  const probEl      = document.getElementById('tr-ia-problemas');
  const probSection = document.getElementById('tr-ia-problemas-section');
  probEl.innerHTML = '';
  if (data.problemas_encontrados && data.problemas_encontrados.length > 0) {
    probSection.style.display = 'block';
    data.problemas_encontrados.forEach(p => {
      const li = document.createElement('li');
      li.textContent = p;
      probEl.appendChild(li);
    });
  } else {
    probSection.style.display = 'none';
  }

  // Sugerencias de optimización.
  const optEl = document.getElementById('tr-ia-optimizaciones');
  optEl.innerHTML = '';
  (data.optimizaciones || []).forEach(o => {
    const li = document.createElement('li');
    li.textContent = o;
    optEl.appendChild(li);
  });
}

function mostrarErrorIA(msg) {
  document.getElementById('tr-ia-empty').style.display  = 'none';
  document.getElementById('tr-ia-result').style.display = 'none';
  const errEl = document.getElementById('tr-ia-error');
  errEl.style.display = 'block';
  errEl.textContent = msg;
}

// ── MODAL DE BIENVENIDA ──
// Aparece solo en la primera visita (localStorage). Se cierra con el
// botón "Empezar", con Esc o con click en el backdrop; cualquiera de
// las tres formas marca el localStorage para no volver a mostrarlo.
// Para volver a verlo en pruebas, ejecutar en la consola del navegador:
//   localStorage.removeItem('diamondlang_welcome_shown')
(function() {
  const STORAGE_KEY = 'diamondlang_welcome_shown';
  const modal = document.getElementById('welcome-modal');
  const closeBtn = document.getElementById('welcome-close-btn');

  if (!modal || !closeBtn) return;

  // Mostrar solo si no se ha mostrado antes
  const yaVisto = localStorage.getItem(STORAGE_KEY);
  if (!yaVisto) {
    // Pequeño delay para que la página cargue completa
    setTimeout(() => {
      modal.classList.add('open');
    }, 400);
  }

  // Cerrar con el botón
  closeBtn.addEventListener('click', () => {
    modal.classList.remove('open');
    localStorage.setItem(STORAGE_KEY, '1');
  });

  // Cerrar con Esc
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('open')) {
      modal.classList.remove('open');
      localStorage.setItem(STORAGE_KEY, '1');
    }
  });

  // Cerrar con click en el backdrop (NO en la card)
  modal.addEventListener('click', (e) => {
    if (e.target.classList.contains('welcome-backdrop') ||
        e.target === modal) {
      modal.classList.remove('open');
      localStorage.setItem(STORAGE_KEY, '1');
    }
  });
})();
