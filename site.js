const themeButton = document.querySelector("[data-theme-toggle]");
const systemTheme = matchMedia("(prefers-color-scheme: dark)");
const root = document.documentElement;

function updateThemeButton() {
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : systemTheme.matches;
  themeButton.setAttribute("aria-pressed", String(dark));
}

if (themeButton) {
  themeButton.addEventListener("click", () => {
  root.dataset.theme = themeButton.getAttribute("aria-pressed") === "true" ? "light" : "dark";
  updateThemeButton();
});
systemTheme.addEventListener("change", updateThemeButton);
updateThemeButton();
themeButton.hidden = false;
}

const menuButton = document.querySelector("[data-menu-toggle]");
const menu = menuButton && document.getElementById(menuButton.getAttribute("aria-controls"));
const mobile = matchMedia("(max-width: 70rem)");

function setMenuOpen(open) {
  menu.hidden = mobile.matches && !open;
  menuButton.setAttribute("aria-expanded", String(mobile.matches && open));
}

function syncMenu() {
  const focusInMenu = menu.contains(document.activeElement);
  menuButton.hidden = !mobile.matches;
  setMenuOpen(false);
  if (mobile.matches && focusInMenu) menuButton.focus();
}

if (menuButton && menu) {
menuButton.addEventListener("click", () => setMenuOpen(menu.hidden));
menu.addEventListener("click", (event) => {
  const link = event.target.closest("a[href]");
  if (!mobile.matches || !link || link.pathname !== location.pathname || !link.hash) return;
  let destination;
  try { destination = document.getElementById(decodeURIComponent(link.hash.slice(1))); } catch { return; }
  if (!destination) return;
  setMenuOpen(false);
  destination.focus({ preventScroll: true });
});
document.querySelector(".site-header")?.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || menuButton.getAttribute("aria-expanded") !== "true") return;
  setMenuOpen(false);
  menuButton.focus();
});
mobile.addEventListener("change", syncMenu);
syncMenu();
}

const sample = document.querySelector("[data-sample]");

if (sample) {
  const tablist = sample.querySelector("[data-tablist]");
  const tabs = [...tablist.querySelectorAll("a")];
  const panels = tabs.map((tab) => document.getElementById(tab.hash.slice(1)));

  function selectTab(index, focus = false) {
    if (index < 0 || !tabs[index] || !panels[index]) return;
    tabs.forEach((tab, position) => {
      const selected = index === position;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      panels[position].hidden = !selected;
    });
    if (focus && tabs[index]) tabs[index].focus();
  }


  function syncHash() {
    const index = tabs.findIndex((tab) => tab.hash === location.hash);
    if (index >= 0) selectTab(index);
    return index;
  }

  tablist.setAttribute("role", "tablist");
  tablist.setAttribute("aria-orientation", "horizontal");
  tablist.setAttribute("aria-label", tablist.dataset.tablist);
  tabs.forEach((tab, index) => {
    const panel = panels[index];
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", panel.id);
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", tab.id);
    panel.tabIndex = 0;
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      selectTab(index, true);
    });
  });
  tablist.addEventListener("keydown", (event) => {
    const index = tabs.indexOf(event.target);
    if (index < 0) return;

    const rtl = root.dir === "rtl";
    const previous = rtl ? "ArrowRight" : "ArrowLeft";
    const next = rtl ? "ArrowLeft" : "ArrowRight";
    let destination;
    switch (event.key) {
      case "Home": destination = 0; break;
      case "End": destination = tabs.length - 1; break;
      case " ": destination = index; break;
      case previous: destination = (index + tabs.length - 1) % tabs.length; break;
      case next: destination = (index + 1) % tabs.length; break;
      default: return;
    }
    event.preventDefault();
    selectTab(destination, true);
  });
  sample.querySelectorAll("[data-sample-next]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      selectTab(tabs.findIndex((tab) => tab.hash === link.hash), true);
    });
  });
  window.addEventListener("hashchange", syncHash);
  if (syncHash() < 0) selectTab(tabs.findIndex((tab) => tab.hasAttribute("data-initial")));

  const quiz = sample.querySelector("[data-quiz]");
  const feedback = quiz?.querySelector("[role='status']");
  if (quiz && feedback) {
  quiz.addEventListener("submit", (event) => {
    event.preventDefault();
    const correct = new FormData(quiz).get("answer") === quiz.dataset.correctAnswer;
    feedback.textContent = correct ? quiz.dataset.correct : quiz.dataset.retry;
  });
  quiz.addEventListener("change", () => { feedback.textContent = ""; });
  quiz.hidden = false;
  const fallback = sample.querySelector("[data-quiz-fallback]");
  if (fallback) fallback.hidden = true;
  }
}

// Optional clipboard convenience. No storage, external requests or telemetry.
const promptLabels = {
  en: { copy: "Copy prompt", done: "Copied.", failed: "Select and copy the text manually." },
  de: { copy: "Anfrage kopieren", done: "Kopiert.", failed: "Text bitte manuell markieren und kopieren." },
  ar: { copy: "نسخ الطلب", done: "تم النسخ.", failed: "حدّد النص وانسخه يدوياً." }
};
const labels = promptLabels[root.lang] || promptLabels.en;
if (navigator.clipboard && window.isSecureContext) {
  document.querySelectorAll(".prompt-list blockquote").forEach((quote) => {
    const prompt = quote.querySelector("p");
    if (!prompt) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-prompt";
    button.textContent = labels.copy;
    const status = document.createElement("p");
    status.className = "copy-status";
    status.setAttribute("role", "status");
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(prompt.textContent.trim());
        status.textContent = labels.done;
      } catch {
        status.textContent = labels.failed;
      }
    });
    quote.append(button, status);
  });
}
