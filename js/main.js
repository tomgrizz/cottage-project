// Photo viewer
(function () {
  const tiles = Array.from(document.querySelectorAll(".gallery .g"));
  const box = document.getElementById("lightbox");
  if (!tiles.length || !box || typeof box.showModal !== "function") return;

  const img = document.getElementById("lb-img");
  const cap = document.getElementById("lb-cap");
  const count = document.getElementById("lb-count");
  let index = 0;

  function show(i) {
    index = (i + tiles.length) % tiles.length;
    const tile = tiles[index];
    img.src = tile.dataset.full;
    img.alt = tile.querySelector("img").alt;
    cap.textContent = tile.dataset.caption;
    count.textContent = (index + 1) + " / " + tiles.length;
  }

  tiles.forEach((tile, i) => tile.addEventListener("click", () => { show(i); box.showModal(); }));
  box.querySelector(".lb-close").addEventListener("click", () => box.close());
  box.querySelector(".lb-prev").addEventListener("click", () => show(index - 1));
  box.querySelector(".lb-next").addEventListener("click", () => show(index + 1));
  box.addEventListener("click", (e) => { if (e.target === box) box.close(); });
  box.addEventListener("close", () => tiles[index].focus());
  box.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") show(index - 1);
    if (e.key === "ArrowRight") show(index + 1);
  });

  let startX = null;
  box.addEventListener("touchstart", (e) => { startX = e.touches[0].clientX; }, { passive: true });
  box.addEventListener("touchend", (e) => {
    if (startX === null) return;
    const dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 40) show(index + (dx < 0 ? 1 : -1));
    startX = null;
  });
})();

// Copy buttons
document.querySelectorAll("[data-copy]").forEach((btn) => {
  const label = btn.textContent;
  btn.addEventListener("click", () => {
    const el = document.getElementById(btn.dataset.copy);
    const done = () => { btn.textContent = "Copied"; setTimeout(() => { btn.textContent = label; }, 2000); };
    const selectIt = () => {
      const range = document.createRange();
      range.selectNodeContents(el);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      btn.textContent = "Selected. Press Ctrl+C to copy";
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(el.textContent).then(done, selectIt);
    } else {
      selectIt();
    }
  });
});

// Inquiry form: writes the email for the guest to send
(function () {
  const form = document.getElementById("inquiry");
  if (!form) return;
  const ready = document.getElementById("inquiry-ready");
  const text = document.getElementById("inquiry-text");
  const mail = document.getElementById("inquiry-mail");
  const arrive = document.getElementById("f-arrive");
  const depart = document.getElementById("f-depart");
  const to = form.dataset.email;

  const today = new Date();
  const iso = (d) => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  arrive.min = iso(today);
  depart.min = iso(today);

  const fmt = (v) => new Date(v + "T12:00:00").toLocaleDateString("en-CA", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
  const short = (v) => new Date(v + "T12:00:00").toLocaleDateString("en-CA", { month: "short", day: "numeric" });

  arrive.addEventListener("change", () => {
    if (arrive.value) depart.min = arrive.value;
  });
  depart.addEventListener("input", () => depart.setCustomValidity(""));

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (arrive.value && depart.value && depart.value <= arrive.value) {
      depart.setCustomValidity("Pick a leaving date after your arrival date.");
      form.reportValidity();
      return;
    }
    const d = new FormData(form);
    const nights = Math.round((Date.parse(depart.value) - Date.parse(arrive.value)) / 86400000);
    const lines = [
      "Hi,",
      "",
      "I'd like to ask about staying at Almond Lane Cottage.",
      "",
      "Arriving: " + fmt(arrive.value),
      "Leaving: " + fmt(depart.value) + " (" + nights + (nights === 1 ? " night)" : " nights)"),
      "Guests: " + d.get("guests"),
    ];
    const note = String(d.get("message") || "").trim();
    if (note) lines.push("", note);
    lines.push("", "Thanks,", d.get("name"), d.get("email"));
    const body = lines.join("\n");

    text.textContent = body;
    const subject = "Stay at Almond Lane Cottage, " + short(arrive.value) + " to " + short(depart.value);
    mail.href = "mailto:" + to + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
    ready.hidden = false;
    ready.focus();
    ready.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
})();

// Depth map: show the depth band under the pointer or finger
(function () {
  const frame = document.querySelector(".depth-frame");
  const tip = document.getElementById("depth-tip");
  const data = document.getElementById("depth-bands");
  if (!frame || !tip || !data) return;
  const labels = JSON.parse(data.textContent);
  let active = null;

  function clear() {
    if (active) active.classList.remove("is-active");
    active = null;
    tip.hidden = true;
  }

  function show(e) {
    const band = e.target.closest ? e.target.closest(".dm-band") : null;
    if (!band) { clear(); return; }
    if (active !== band) {
      if (active) active.classList.remove("is-active");
      active = band;
      band.classList.add("is-active");
      tip.textContent = labels[Number(band.dataset.band)];
    }
    const box = frame.getBoundingClientRect();
    const x = Math.min(Math.max(e.clientX - box.left, 70), box.width - 70);
    tip.style.left = x + "px";
    tip.style.top = (e.clientY - box.top) + "px";
    tip.hidden = false;
  }

  frame.addEventListener("pointermove", show);
  frame.addEventListener("pointerdown", show);
  frame.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") clear(); });
})();
