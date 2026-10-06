const log = document.getElementById("log");
const form = document.getElementById("box");
const input = document.getElementById("text");
const sid = "web-" + Math.random().toString(36).slice(2, 8);

function add(cls, who, text) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  const small = document.createElement("small");
  small.textContent = who;
  div.appendChild(small);
  div.appendChild(document.createTextNode(text));
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  return div;
}

const TITLES = {core: "Core", web: "Web", productivity: "Productivity", system: "System", other: "More"};

fetch("/api/info").then(r => r.json()).then(info => {
  const skills = info.skills || [];
  document.getElementById("mood").textContent =
    (info.mood || "") + " · " + skills.length + " skills";
  document.getElementById("skills-count").textContent =
    "Skills (" + skills.length + ")";
  const groups = info.skill_groups || {};
  const box = document.getElementById("groups");
  Object.keys(TITLES).forEach(g => {
    const names = groups[g] || [];
    if (!names.length) return;
    const sec = document.createElement("div");
    const h = document.createElement("p");
    h.className = "group-name";
    h.textContent = TITLES[g] + " · " + names.length;
    sec.appendChild(h);
    const chips = document.createElement("div");
    chips.className = "chips";
    names.forEach(n => {
      const s = document.createElement("span");
      s.className = "chip";
      s.textContent = n;
      s.title = "Click to ask about: " + n;
      s.addEventListener("click", () => {
        input.value = n.replace(/_/g, " ");
        input.focus();
      });
      chips.appendChild(s);
    });
    sec.appendChild(chips);
    box.appendChild(sec);
  });
}).catch(() => {});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  add("you", "you", text);
  const typing = add("typing", "jarvis", "…");
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text, sid}),
    });
    const data = await r.json();
    typing.remove();
    add("", "jarvis", data.reply || JSON.stringify(data));
  } catch (err) {
    typing.remove();
    add("", "jarvis", "Request failed: " + err);
  }
});

// ---- floating HUD + one-click Library ---------------------------------
const libPanel = document.getElementById("library-panel");
const libList = document.getElementById("lib-list");
const libMsg = document.getElementById("lib-msg");
const libSearch = document.getElementById("lib-search");

function libSay(text, ok) {
  libMsg.hidden = !text;
  libMsg.textContent = text || "";
  libMsg.style.color = ok === false ? "#ff7d93" : "";
}

async function libRefresh() {
  try {
    const r = await fetch("/api/library");
    const d = await r.json();
    const packs = d.skills || [];
    document.querySelector("#library-panel summary").textContent =
      "Library (" + packs.length + ")";
    libList.innerHTML = "";
    packs.forEach(p => {
      const row = document.createElement("div");
      row.className = "lib-row";
      row.dataset.text = ((p.name || p.id || "") + " " +
        (p.description || "") + " " + (p.tags || []).join(" ")).toLowerCase();
      const info = document.createElement("div");
      info.className = "lib-info";
      const nm = document.createElement("strong");
      nm.textContent = p.name || p.id;
      const ds = document.createElement("small");
      ds.textContent = (p.description || "").slice(0, 90) +
        (p.imported ? " · imported" : "");
      info.appendChild(nm);
      info.appendChild(ds);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "lib-act";
      btn.textContent = p.installed ? "REMOVE" : "INSTALL";
      btn.dataset.action = p.installed ? "lib-remove" : "lib-install";
      btn.dataset.id = p.id || "";
      if (p.installed) btn.classList.add("danger");
      row.appendChild(info);
      row.appendChild(btn);
      libList.appendChild(row);
    });
  } catch (e) {
    libSay("Library failed to load: " + e, false);
  }
}

document.getElementById("lib-btn").addEventListener("click", () => {
  libPanel.open = !libPanel.open;
  if (libPanel.open) libRefresh();
});

libSearch.addEventListener("input", () => {
  const q = libSearch.value.toLowerCase().trim();
  libList.querySelectorAll(".lib-row").forEach(row => {
    const t = row.dataset.text || "";
    row.style.display = (!q || t.indexOf(q) >= 0) ? "" : "none";
  });
});

libList.addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const action = btn.dataset.action;
  const id = btn.dataset.id;
  btn.textContent = "…";
  fetch("/api/library/skill", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(action === "lib-remove" ? {id, remove: true} : {id}),
  }).then(r => r.json()).then(d => {
    if (d.ok) {
      libSay(action === "lib-remove"
        ? "Removed pack: " + id + " (" + (d.unregistered || []).length +
          " skills unregistered" + (d.file_deleted ? ", file deleted" : "") + ")"
        : "Installed: " + (d.skill || id), true);
    } else {
      libSay((d.detail || d.error || "request failed"), false);
    }
    libRefresh();
  }).catch(err => {
    libSay("Request failed: " + err, false);
    libRefresh();
  });
});

document.getElementById("lib-import").addEventListener("click", () => {
  const fi = document.getElementById("lib-import-file");
  if (!fi.files || !fi.files[0]) { libSay("Pick a pack .json file first.", false); return; }
  const fr = new FileReader();
  fr.onload = () => {
    let parsed;
    try { parsed = JSON.parse(fr.result); }
    catch (e) { libSay("Not valid JSON: " + e.message, false); return; }
    fetch("/api/library/import", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(parsed),
    }).then(r => r.json()).then(d => {
      if (d.error) { libSay(d.error, false); return; }
      const errs = (d.results || []).filter(x => x.error)
        .map(x => (x.id || "?") + ": " + x.error);
      libSay("Imported " + (d.imported || 0) + " pack(s)." +
        (errs.length ? " Rejected — " + errs.join("; ") : " (hit INSTALL to add)"),
        (d.imported || 0) > 0);
      libRefresh();
    }).catch(err => libSay("Import failed: " + err, false));
  };
  fr.readAsText(fi.files[0]);
});

document.getElementById("hud-btn").addEventListener("click", () => {
  fetch("/api/overlay/toggle", {method: "POST"})
    .then(r => r.json())
    .then(() => fetch("/api/overlay/state").then(r => r.json()).then(st => {
      const b = document.getElementById("hud-btn");
      b.classList.toggle("on", !!st.visible);
      b.textContent = st.visible ? "HUD ●" : "HUD";
    }))
    .catch(() => {});
});
