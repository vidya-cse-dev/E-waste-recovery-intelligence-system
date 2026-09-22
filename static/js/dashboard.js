(() => {
  const $ = (s) => document.querySelector(s);
  const rupee = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
  const css = getComputedStyle(document.documentElement);
  const colour = (name) => css.getPropertyValue(name).trim();
  const DECISION_COLOUR = {
    reusable: colour("--reusable"), repairable: colour("--repairable"),
    recycle: colour("--recycle"), testing: colour("--testing"),
  };

  const cell = (text, cls) => { const td = document.createElement("td"); td.textContent = text; if (cls) td.className = cls; return td; };

  Promise.all([fetch("/api/stats").then((r) => r.json()), fetch("/api/records?limit=15").then((r) => r.json())])
    .then(([s, rows]) => {
      $("#kTotal").textContent = s.total;
      $("#kValue").textContent = rupee.format(s.total_value);
      $("#kReuse").textContent = `${Math.round(s.reuse_rate * 100)}%`;
      $("#kCert").textContent = `${Math.round(s.avg_certainty * 100)}%`;
      if (s.sample_rows) {
        const note = $("#sampleNote");
        note.textContent = `${s.sample_rows} of these ${s.total} records are generated sample data, not real analyses.`;
        note.hidden = false;
      }
      if (!s.total) { $("#empty").hidden = false; $("#charts").hidden = true; }

      const body = $("#rows");
      rows.forEach((r) => {
        const tr = document.createElement("tr");
        const pill = document.createElement("span");
        pill.className = `pill pill--${r.decision}`;
        pill.textContent = r.decision_label;
        const decisionCell = document.createElement("td");
        decisionCell.append(pill);
        tr.append(cell(r.id), cell(r.created_at.slice(0, 10)), cell(r.component_display), cell(r.condition_label),
          decisionCell, cell(rupee.format(r.value_estimate), "num"));
        body.append(tr);
      });

      if (typeof Chart === "undefined" || !s.total) return;
      Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
      Chart.defaults.color = colour("--muted");
      const board = colour("--board");
      const bar = (id, labels, data, colours) => new Chart($(id), {
        type: "bar",
        data: { labels, datasets: [{ data, backgroundColor: colours || board, borderRadius: 4 }] },
        options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
      });
      bar("#cComponent", s.by_component.map((d) => d.name), s.by_component.map((d) => d.count));
      bar("#cCondition", s.by_condition.map((d) => d.name), s.by_condition.map((d) => d.count));
      bar("#cValue", s.by_component.map((d) => d.name), s.by_component.map((d) => d.value));
      new Chart($("#cDecision"), {
        type: "doughnut",
        data: {
          labels: s.by_decision.map((d) => d.name),
          datasets: [{ data: s.by_decision.map((d) => d.count), backgroundColor: s.by_decision.map((d) => DECISION_COLOUR[d.code]) }],
        },
        options: { maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
      });
    });
})();
