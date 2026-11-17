/* Evidence-first operations board. All remote and owner text uses textContent. */
(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const UI = {
    fa: {
      select: "پروژه‌ای انتخاب کنید تا شواهد واقعی نمایش داده شوند.",
      nothing: "هنوز شواهدی برای این بخش ثبت نشده است.",
      dataUnavailable: "دریافت وضعیت پروژه ناموفق بود.",
      recorded: "ثبت‌شده", proposed: "پیشنهادی", not_started: "شروع‌نشده",
      available: "در دسترس", configured_only: "فقط پیکربندی",
      not_verified: "تأییدنشده", attempted: "تلاش ثبت‌شده",
      reviewed: "بازبینی", verified: "دارای checkpoint",
      checkpoint_only: "checkpoint موجود", blocked: "مسدود",
      unknown: "نامعلوم", coded_unverified: "کدنویسی‌شده، بدون تأیید مستقل",
      manual_reconciliation: "نیازمند بررسی دستی نتیجهٔ نامعلوم",
      review_preconditions: "پیش‌شرط‌های ادامه باید بررسی شوند",
      conditional: "ادامه فقط پس از بررسی نسخه و شواهد",
      not_needed: "اجرای پذیرفته‌شده",
      not_configured: "Gate هنوز پیکربندی نشده است",
      valid: "صحت داده بررسی شد", invalid: "یکپارچگی شواهد نامعتبر است",
      passed: "موفق", failed: "ناموفق", status: "وضعیت",
      noRuns: "هیچ اجرای ثبت‌شده‌ای وجود ندارد.",
      blockedRun: "اجرای خودکار از داشبورد غیرفعال است؛ S4 هنوز تأیید امنیتی ندارد.",
      noEvaluations: "هنوز آزمونی توسط Gate اجرا نشده است.",
      noCheckpoints: "هیچ بستهٔ قابل تحویلِ تأییدشده وجود ندارد.",
      checkpoints: "checkpoint معتبر", deliveryReady: "شواهد checkpoint ثبت شده؛ خروجی هنوز نیازمند بسته‌بندی و نصب‌سنجی است.",
      testedCases: "آزمون‌های منجمد", safeNoPass: "نمایش نتیجه، به‌معنی صدور مجوز PASS نیست.",
      noFacts: "نیازمندی مستقل ثبت نشده است.",
      noAnswers: "پاسخ‌های ثبت‌شده در کادرها قابل اصلاح‌اند.",
      users: "کاربران و مسئلهٔ اصلی", workflow: "گردش‌کار مورد انتظار",
      success: "معیار موفقیت", constraints: "محدودیت‌ها",
      budgetCalls: "درخواست‌های ثبت‌شده",
      budgetRemaining: "سهمیهٔ باقی‌مانده",
      noCap: "بدون سقف شمارشی", countCap: "سقف تعداد درخواست",
      knownUnknown: "نتیجهٔ نامعلوم",
      noDollarCap: "سقف تضمینی دلاری ثبت نشده است",
      noFake: "وضعیت‌ها از شواهد گرفته شده‌اند، نه تخمین درصد.",
      saveSuccess: "پاسخ‌ها با نسخهٔ جدید مالک ثبت شدند؛ طرح‌های کهنه نیازمند بازبینی‌اند.",
      saveError: "ثبت پاسخ ناموفق بود:",
      refreshError: "دریافت شواهد ناموفق بود:",
      noChanges: "ابتدا پاسخی را تکمیل یا اصلاح کنید.",
      revision: "نسخه", noEvidence: "بدون شواهد اجرایی",
      attempts: "تلاش", tests: "آزمون", testsPassed: "آزمون موفق",
      sampleOnly: "تست‌دابل به‌معنی ایزوله‌سازی معتبر نیست.",
      runTitle: "اجرای", evidence: "شاهد", source: "منبع",
      buildDisabled: "شروع Build و Resume تنها پس از فراهم شدن محیط امن فعال می‌شوند.",
      deliveryBlocked: "تا زمان پذیرش واقعی Gate و بررسی نصب، تحویل نهایی مسدود است."
    },
    en: {
      select: "Select a project to inspect recorded evidence.",
      nothing: "No evidence recorded for this section yet.",
      dataUnavailable: "Could not retrieve project state.",
      recorded: "Recorded", proposed: "Proposed", not_started: "Not started",
      available: "Available", configured_only: "Configured only",
      not_verified: "Not verified", attempted: "Attempted",
      reviewed: "Reviewed", verified: "Checkpoint present",
      checkpoint_only: "Checkpoint only", blocked: "Blocked",
      unknown: "Unknown", coded_unverified: "Code proposed; not independently accepted",
      manual_reconciliation: "Manual reconciliation required for unknown outcome",
      review_preconditions: "Review prerequisites before resuming",
      conditional: "Resume only after checking revision and evidence",
      not_needed: "Accepted run",
      not_configured: "Gate is not configured yet",
      valid: "Evidence integrity checked", invalid: "Invalid evidence integrity",
      passed: "Passed", failed: "Failed", status: "Status",
      noRuns: "No execution runs have been recorded.",
      blockedRun: "Dashboard execution remains disabled until S4 isolation is verified.",
      noEvaluations: "No Gate evaluation has run yet.",
      noCheckpoints: "No verified deliverable evidence available.",
      checkpoints: "Validated checkpoints", deliveryReady: "Checkpoint evidence exists; packaging and install QA remain separate.",
      testedCases: "Frozen test cases", safeNoPass: "Displaying a result does not grant PASS.",
      noFacts: "No independently enumerated requirements are recorded.",
      noAnswers: "You can update the recorded owner answers below.",
      users: "Users and problem", workflow: "Expected workflow",
      success: "Success criterion", constraints: "Constraints",
      budgetCalls: "Recorded requests",
      budgetRemaining: "Remaining quota",
      noCap: "No count limit", countCap: "Call-count cap",
      knownUnknown: "Unknown outcomes",
      noDollarCap: "No enforceable USD limit is configured",
      noFake: "These states come from evidence, not invented percentages.",
      saveSuccess: "Owner revision updated; stale plans must be reviewed.",
      saveError: "Could not update owner answers:",
      refreshError: "Could not refresh evidence:",
      noChanges: "Complete or edit at least one answer first.",
      revision: "Revision", noEvidence: "No execution evidence",
      attempts: "Attempts", tests: "Tests", testsPassed: "Passed",
      sampleOnly: "A fixture-based PASS is not evidence of isolated production execution.",
      runTitle: "Run", evidence: "Evidence", source: "Source",
      buildDisabled: "Build and Resume controls remain disabled until a trusted execution boundary exists.",
      deliveryBlocked: "Final delivery is blocked until accepted Gate evidence and installation validation."
    },
  };

  let slug = null, project = null, control = null, csrf = null, generation = 0;
  const selected = () => document.documentElement.lang === "en" ? "en" : "fa";
  const t = key => UI[selected()][key] || key;
  function el(tag, css = "", content) {
    const n = document.createElement(tag);
    if (css) n.className = css;
    if (content !== undefined) n.textContent = String(content);
    return n;
  }
  function draw(target, ...elements) { target.replaceChildren(...elements); }
  function placeholder(target, key = "nothing") {
    draw(target, el("div", "ops-empty", t(key)));
  }
  function stateBadge(value) {
    const n = el("span", "ops-state", t(value));
    n.dataset.state = String(value);
    return n;
  }
  function subtitle(text) { return el("span", "ops-subtitle", text); }
  function line(label, value, state) {
    const n = el("div", "ops-line");
    const labelNode = el("span", "ops-line-main", label);
    const valueNode = state ? stateBadge(value) : el("span", "ops-line-value", value);
    n.append(labelNode, valueNode);return n;
  }
  function badgeRow(items) {
    const n = el("div", "ops-tags");
    items.forEach(item => n.append(el("span", "ops-tag", item)));
    return n;
  }
  function titleCard(name, description, stateValue) {
    const wrap = el("div", "ops-record");
    const header = el("div", "ops-record-header");
    header.append(el("strong", "", name), stateBadge(stateValue));
    wrap.append(header);
    if (description) wrap.append(subtitle(description));
    return wrap;
  }
  function stageState(code) {
    const names = {
      S0: selected() === "fa" ? "ثبت هدف" : "Owner intent",
      S1: selected() === "fa" ? "طرح و وظایف" : "Plan & tasks",
      S6a: selected() === "fa" ? "داشبورد" : "Dashboard",
      S2: selected() === "fa" ? "اتصال API" : "Model APIs",
      S3: selected() === "fa" ? "اجرا و ادامه" : "Execution",
      S4: selected() === "fa" ? "Gate و آزمون" : "Verification",
      S5: selected() === "fa" ? "بستهٔ تحویل" : "Delivery",
      S7: selected() === "fa" ? "محصول واقعی" : "Real product",
    };
    return names[code] || code;
  }
  function journey() {
    const target = $("project-journey");
    if (!control) return placeholder(target, "select");
    const list = control.journey || [];
    const items = list.map(stage => {
      const n = el("div", "journey-step");
      const header = el("div", "journey-step-head");
      header.append(el("span", "journey-index", stage.id), stateBadge(stage.state));
      n.append(header, el("strong", "journey-step-title", stageState(stage.id)),
        subtitle(stage.evidence || t("noEvidence")));
      return n;
    });
    draw(target, ...items);
  }
  function runs() {
    const target = $("runs-list"), warning = $("recovery-warning");
    if (!control) {
      $("runs-counter").textContent = "—";
      warning.textContent = t("buildDisabled");
      return placeholder(target, "select");
    }
    const rows = control.gate.runs || [];
    $("runs-counter").textContent = String(rows.length);
    if (!rows.length) {
      placeholder(target, "noRuns");
      warning.textContent = t("blockedRun");
      return;
    }
    draw(target, ...rows.slice(0, 12).map(run => {
      const n = titleCard(run.id, run.created, run.status);
      const info = el("div", "ops-meta-grid");
      info.append(subtitle(t("attempts") + ": " + run.attempts),
        subtitle(t("tests") + ": " + (run.latest_evaluation || "—")));
      n.append(info, line(t("status"), run.recovery, true));
      return n;
    }));
    warning.textContent = rows.some(x => x.unknown_attempt) ?
      t("manual_reconciliation") : t("buildDisabled");
  }
  function verification() {
    const gate = control && control.gate;
    const head = $("gate-integrity"), wrap = $("test-results");
    if (!gate) {
      $("tests-counter").textContent = "—";
      draw(head, stateBadge("not_verified"));
      return placeholder(wrap, "select");
    }
    const integrity = gate.integrity;
    draw(head, stateBadge(integrity === "not_applicable" ? "not_configured" : integrity),
      subtitle(gate.state === "not_configured" ? t("not_configured") :
        gate.max_attempts === null ? t("invalid") : t("attempts") + ": " + gate.max_attempts));
    const evaluations = gate.evaluations || [];
    $("tests-counter").textContent = String(gate.tests.length);
    const frozen = gate.tests.map(item => {
      const itemNode = el("div", "test-case");
      itemNode.append(el("span", "test-dot"),el("span", "", item.id),
        el("span", "test-state", t("testedCases")));
      return itemNode;
    });
    const sections = [el("div", "inset-heading", t("testedCases")), ...frozen];
    if (evaluations.length) {
      sections.push(el("div", "inset-heading", t("evidence")));
      evaluations.slice(0, 6).forEach(evaluation => {
        const n = titleCard(evaluation.id,
          evaluation.passed + " / " + (evaluation.total ?? "—") + " " + t("testsPassed"),
          evaluation.integrity === "valid" ? evaluation.status : "invalid");
        const chips = badgeRow([
          evaluation.measurement_only === true ? "REVIEW ONLY" : "Gate",
          evaluation.boundary_verified ? "BOUNDARY VERIFIED" : "BOUNDARY NOT VERIFIED",
        ]);
        n.append(chips);
        const cases = evaluation.cases || [];
        for(const test of cases.slice(0,12)) n.append(line(test.id, test.passed ? "passed" : "failed", true));
        sections.push(n);
      });
    } else {
      sections.push(el("div", "ops-empty", t("noEvaluations")));
    }
    draw(wrap, ...sections);
  }
  function delivery() {
    const target=$("delivery-content");
    if (!control) return placeholder(target,"select");
    const gate=control.gate;
    const items=[];
    if(gate.checkpoints?.length) {
      gate.checkpoints.forEach(cp=>{
        const item=titleCard(cp.id,cp.run_id,cp.integrity === "valid" ? "verified" : "unknown");
        item.append(subtitle(cp.created));
        items.push(item);
      });
    }
    if(!items.length) items.push(el("div","ops-empty",t("noCheckpoints")));
    items.push(el("div","delivery-halt",gate.accepted_count ? t("deliveryReady") : t("deliveryBlocked")));
    draw(target,...items);
  }
  function owner() {
    const facts=$("owner-facts"), fields=$("owner-answers-fields");
    if(!control||!project) {
      $("owner-version").textContent="—";
      placeholder(facts,"select");
      fields.replaceChildren();return;
    }
    $("owner-version").textContent="v"+project.version;
    const factNodes=project.facts.map(fact=>{
      const row=el("div","ops-record");
      row.append(el("strong","",fact.id+" · "+fact.kind),subtitle(fact.text));return row;
    });
    if(!factNodes.length)factNodes.push(el("div","ops-empty",t("noFacts")));
    draw(facts,...factNodes);
    fields.replaceChildren();
    for(const key of ["users","workflow","success","constraints"]) {
      const group=el("div","owner-field");
      const id="owner-answer-"+key;
      const label=el("label","",t(key));label.htmlFor=id;
      const input=el("textarea","owner-input");input.id=id;input.name=key;
      input.maxLength=2000;input.rows=2;input.value=project.answers?.[key]||"";
      group.append(label,input);fields.append(group);
    }
  }
  function audits() {
    const target=$("audit-events"), budgets=$("provider-budget");
    if(!control) {
      $("audit-count").textContent="—";budgets.replaceChildren();
      return placeholder(target,"select");
    }
    const budget=control.budget;
    $("audit-count").textContent=String(control.events.length);
    const summary=el("div","budget-tiles");
    const samples=[
      [t("budgetCalls"),budget.used_calls],
      [t("budgetRemaining"),budget.remaining_calls ?? t("noCap")],
      [t("knownUnknown"),budget.breakdown.provider_unknown],
    ];
    samples.forEach(([label,value])=>{
      const box=el("div","budget-tile");
      box.append(el("span","",label),el("strong","",value));summary.append(box);
    });
    budgets.replaceChildren(summary,el("p","budget-note",t("noDollarCap")));
    const entries=(control.events||[]).slice(0,16).map(event=>{
      const entry=el("div","audit-entry");
      entry.append(el("strong","",event.type),
        subtitle("#"+event.id+" · "+event.created),stateBadge(event.status));
      return entry;
    });
    draw(target,...(entries.length?entries:[el("div","ops-empty",t("nothing"))]));
  }
  function render() {
    $("control-project-pill").textContent=slug||"—";
    journey();runs();verification();delivery();owner();audits();
  }
  async function refresh() {
    const expectedSlug=slug,seq=++generation;
    if(!expectedSlug) {
      control=null;render();return;
    }
    try {
      const response=await fetch("/api/projects/"+encodeURIComponent(expectedSlug)+"/control",
        {method:"GET",cache:"no-store",credentials:"same-origin"});
      const data=await response.json();
      if(!response.ok)throw Error(data.error||"HTTP "+response.status);
      if(seq!==generation||slug!==expectedSlug)return;
      control=data;render();
      window.dispatchEvent(new CustomEvent("csef:control",{detail:data}));
    } catch(error) {
      if(seq===generation) {
        control=null;render();$("recovery-warning").textContent=t("refreshError")+" "+error.message;
      }
    }
  }
  async function save(event) {
    event.preventDefault();
    if(!project||!slug||!csrf)return;
    const answers={};
    for(const key of ["users","workflow","success","constraints"]) {
      const value=$("owner-answer-"+key)?.value.trim();
      if(value&&value!==(project.answers?.[key]||""))answers[key]=value;
    }
    if(!Object.keys(answers).length) {
      $("recovery-warning").textContent=t("noChanges");return;
    }
    const reason=$("owner-reason").value.trim();
    if(reason.length<3)return;
    const button=$("save-owner-answers");button.disabled=true;
    try {
      const resp=await fetch("/api/projects/"+encodeURIComponent(slug)+"/answers",{
        method:"POST",cache:"no-store",credentials:"same-origin",
        headers:{"Content-Type":"application/json","X-CSEF-CSRF":csrf},
        body:JSON.stringify({expected_version:project.version,reason,answers})
      });
      const data=await resp.json();
      if(!resp.ok)throw Error(data.error||"HTTP "+resp.status);
      $("owner-reason").value="";
      $("recovery-warning").textContent=t("saveSuccess");
      window.dispatchEvent(new CustomEvent("csef:refresh"));
    } catch(error) {
      $("recovery-warning").textContent=t("saveError")+" "+error.message;
    } finally {button.disabled=false;}
  }
  function init() {
    window.addEventListener("csef:project",event=>{
      slug=event.detail.slug;project=event.detail.project;csrf=event.detail.csrf;
      control=null;render();refresh();
    });
    window.addEventListener("csef:language",()=>render());
    $("refresh-evidence").addEventListener("click",()=>refresh());
    $("owner-answers-form").addEventListener("submit",save);
    render();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);
  else init();
})();