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
