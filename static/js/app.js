(() => {
  const $ = (s) => document.querySelector(s);
  const rupee = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
  const FINDING_NAMES = { crack: "Cracks", burn: "Burn marks", corrosion: "Corrosion", leakage: "Leakage or staining", broken: "Broken or missing parts" };

  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else n.setAttribute(k, v);
    }
    kids.flat().forEach((c) => n.append(c && c.nodeType ? c : document.createTextNode(c ?? "")));
    return n;
  };

  const fileInput = $("#fileInput"), drop = $("#drop"), previewImg = $("#previewImg"), dropPrompt = $("#dropPrompt");
  const select = $("#componentSelect"), analyseBtn = $("#analyseBtn"), message = $("#message");
  const result = $("#result"), stepQuestions = $("#stepQuestions"), stepVerdict = $("#stepVerdict");
  const form = $("#questionsForm");
  let current = null;

  // component list for the optional manual choice
  fetch("/api/components").then((r) => r.json()).then((list) => {
    list.forEach((c) => select.append(el("option", { value: c.key, text: c.name })));
  }).catch(() => {});

  function showMessage(text) {
    message.textContent = text || "";
    message.hidden = !text;
  }

  function preview() {
    const f = fileInput.files[0];
    if (!f) return;
    previewImg.src = URL.createObjectURL(f);
    previewImg.hidden = false;
    dropPrompt.hidden = true;
    analyseBtn.disabled = false;
    showMessage("");
  }
  fileInput.addEventListener("change", preview);
  ["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("is-over"); }));
  ["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("is-over"); }));
  drop.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; preview(); }
  });

  analyseBtn.addEventListener("click", async () => {
    const f = fileInput.files[0];
    if (!f) return showMessage("Choose a photo of the component first.");
    const body = new FormData();
    body.append("image", f);
    body.append("component", select.value);
    analyseBtn.disabled = true;
    analyseBtn.textContent = "Analysing…";
    showMessage("");
    try {
      const res = await fetch("/api/analyze", { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
      if (!data.detected) {
        result.hidden = true;
        showMessage(data.message);
        select.focus();
        return;
      }
      current = data;
      render(data);
    } catch (err) {
      showMessage(err.message);
    } finally {
      analyseBtn.disabled = false;
      analyseBtn.textContent = "Analyse photo";
    }
  });

  function render(d) {
    result.hidden = false;
    $("#annotated").src = d.annotated_url;

    const manual = d.detector_mode === "manual";
    const lead = $("#identifyLead");
    lead.replaceChildren(d.component_display);
    if (d.detector_mode === "demo") lead.append(el("span", { class: "badge", text: "Demo mode" }));
    $("#identifyMeta").textContent = manual
      ? "You chose this component."
      : `${Math.round(d.det_conf * 100)}% match.` + (d.other_detections.length
        ? ` Also spotted: ${d.other_detections.map((o) => o.component).join(", ")}.` : "");
    $("#detList").textContent = "The outlined area is what was inspected.";

    $("#inspectLead").textContent = d.condition.label;
    const list = $("#findings");
    list.replaceChildren();
    Object.entries(d.condition.findings).forEach(([k, v]) => {
      const pct = Math.round(v * 100);
      list.append(el("li", {}, FINDING_NAMES[k] || k,
        el("span", { class: "bar", "aria-hidden": "true" }, el("span", { style: `width:${pct}%` })),
        el("span", { class: "pct", text: `${pct}%` })));
    });
    $("#inspectMeta").textContent = `Confidence in this check: ${Math.round(d.condition.confidence * 100)}%. ` + d.condition.notes.join(" ");

    buildQuestions(d);
    if (d.decision) {
      stepQuestions.hidden = true;
      showVerdict(d.decision);
    } else {
      stepVerdict.hidden = true;
      stepQuestions.hidden = false;
      $("#askWhy").textContent = d.ask_reasons.join(" ");
    }
    $("#refineBtn").hidden = !d.decision;
    result.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  }

  function buildQuestions(d) {
    form.replaceChildren();
    d.questions.forEach((q) => {
      const fs = el("fieldset", { class: "q" }, el("legend", { text: q.text }));
      q.options.forEach((o) => {
        fs.append(el("label", {}, el("input", { type: "radio", name: q.id, value: o.value }), o.label));
      });
      form.append(fs);
    });
    form.append(el("div", { class: "form__actions" },
      el("button", { type: "submit", class: "btn", text: "See recommendation" }),
      el("button", { type: "button", class: "btn btn--ghost", id: "skipBtn", text: "Skip questions" })));
    $("#skipBtn").addEventListener("click", () => submitAnswers({}));
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const answers = {};
    new FormData(form).forEach((v, k) => { answers[k] = v; });
    submitAnswers(answers);
  });

  async function submitAnswers(answers) {
    try {
      const res = await fetch("/api/decide", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: current.id, answers }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Something went wrong. Try again.");
      current.decision = data;
      stepQuestions.hidden = true;
      $("#refineBtn").hidden = false;
      showVerdict(data);
    } catch (err) {
      showMessage(err.message);
    }
  }

  function showVerdict(dec) {
    const tag = $("#tag");
    const v = dec.value;
    const range = v.low === v.high ? rupee.format(v.estimate) : `${rupee.format(v.low)} – ${rupee.format(v.high)}`;
    tag.className = `tag tag--${dec.code} is-new`;
    tag.replaceChildren(
      el("h3", { class: "tag__verdict", text: dec.label }),
      el("p", { class: "tag__value" }, range, el("small", { text: "Estimated recovery value" })),
      el("p", { class: "tag__certainty", text: `Certainty: ${dec.certainty_label} (${Math.round(dec.certainty * 100)}%)` }),
      el("h3", { text: "Why" }),
      el("ul", {}, dec.reasons.map((r) => el("li", { text: r }))),
      el("h3", { text: "What to do next" }),
      el("p", { class: "tag__next", text: dec.next_step }),
      el("p", { class: "tag__basis", text: v.basis }));
    stepVerdict.hidden = false;
    stepVerdict.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  $("#refineBtn").addEventListener("click", () => {
    stepQuestions.hidden = false;
    $("#askWhy").textContent = "Your answers help us judge what a photo cannot show.";
    stepQuestions.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });

  $("#againBtn").addEventListener("click", () => {
    fileInput.value = "";
    previewImg.hidden = true;
    dropPrompt.hidden = false;
    analyseBtn.disabled = true;
    result.hidden = true;
    select.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();
