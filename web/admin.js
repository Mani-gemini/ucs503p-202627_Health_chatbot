"use strict";
const $ = id => document.getElementById(id);
let token = "";
try { token = sessionStorage.getItem("hb_admin") || ""; } catch (e) {}

function cell(text) { const td = document.createElement("td"); td.textContent = text; return td; }
function setStatus(id, msg, ok) {
  const n = $(id); n.textContent = msg; n.className = "status " + (ok ? "ok" : "bad");
}

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: Object.assign({ "X-Admin-Token": token }, body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || ("Request failed (" + res.status + ")"));
  return data;
}

async function loadStats() {
  const s = await api("GET", "/api/admin/stats");
  const box = $("stats");
  box.replaceChildren();
  const add = (label, value) => {
    const d = document.createElement("div"); d.className = "stat";
    const b = document.createElement("b"); b.textContent = value;
    d.appendChild(b); d.appendChild(document.createTextNode(label)); box.appendChild(d);
  };
  add("total questions", s.total);
  ["answer", "fallback", "emergency", "error"].forEach(p => add(p, s.by_path[p] || 0));
  const tb = $("logRows"); tb.replaceChildren();
  s.recent.forEach(r => {
    const tr = document.createElement("tr");
    [r.id, r.time, r.query, r.path, r.distance === null ? "-" : r.distance].forEach(v => tr.appendChild(cell(v)));
    tb.appendChild(tr);
  });
}

async function loadDiseases() {
  const list = await (await fetch("/api/diseases")).json();
  const tb = $("diseaseRows"); tb.replaceChildren();
  list.forEach(d => {
    const tr = document.createElement("tr");
    tr.appendChild(cell(d.key)); tr.appendChild(cell(d.name));
    const td = document.createElement("td");
    const edit = document.createElement("button"); edit.className = "btn"; edit.type = "button"; edit.textContent = "Edit";
    edit.addEventListener("click", async () => {
      try {
        const entry = await api("GET", "/api/admin/diseases/" + encodeURIComponent(d.key));
        $("key").value = d.key; $("entry").value = JSON.stringify(entry, null, 2);
        setStatus("saveStatus", "Loaded '" + d.key + "'. Edit the JSON and press Save.", true);
        $("key").scrollIntoView({ behavior: "smooth" });
      } catch (e) { setStatus("saveStatus", e.message, false); }
    });
    const del = document.createElement("button"); del.className = "btn danger"; del.type = "button"; del.textContent = "Delete";
    del.addEventListener("click", async () => {
      if (!confirm("Delete '" + d.name + "' and its chunks from the knowledge base?")) return;
      try { await api("DELETE", "/api/admin/diseases/" + encodeURIComponent(d.key)); await loadDiseases(); }
      catch (e) { setStatus("saveStatus", e.message, false); }
    });
    td.appendChild(edit); td.appendChild(del); tr.appendChild(td); tb.appendChild(tr);
  });
}

async function unlock() {
  token = $("token").value || token;
  try {
    await api("GET", "/api/admin/check");
    try { sessionStorage.setItem("hb_admin", token); } catch (e) {}
    $("login").classList.add("hidden"); $("dash").classList.remove("hidden");
    await Promise.all([loadStats(), loadDiseases()]);
  } catch (e) { setStatus("loginStatus", e.message, false); }
}

$("unlock").addEventListener("click", unlock);
$("token").addEventListener("keydown", e => { if (e.key === "Enter") unlock(); });

$("template").addEventListener("click", () => {
  $("entry").value = JSON.stringify({
    name: "Cholera",
    source: "World Health Organization - Cholera fact sheet",
    key_facts: ["Cholera is an acute diarrhoeal infection caused by ingesting contaminated food or water."],
    symptoms: ["Profuse watery diarrhoea", "Vomiting", "Leg cramps"],
    prevention: ["Safe water", "Sanitation", "Hand washing", "Oral cholera vaccines"]
  }, null, 2);
});

$("save").addEventListener("click", async () => {
  let entry;
  try { entry = JSON.parse($("entry").value); }
  catch (e) { setStatus("saveStatus", "That is not valid JSON: " + e.message, false); return; }
  const key = $("key").value.trim();
  setStatus("saveStatus", "Saving and re-indexing ...", true);
  $("save").disabled = true;
  try {
    const r = await api("PUT", "/api/admin/diseases/" + encodeURIComponent(key), { entry });
    setStatus("saveStatus", "Disease " + r.action + ": " + r.chunks + " chunks indexed. The chatbot can use it immediately.", true);
    await loadDiseases();
  } catch (e) { setStatus("saveStatus", e.message, false); }
  finally { $("save").disabled = false; }
});

if (token) { $("token").value = token; unlock(); }
