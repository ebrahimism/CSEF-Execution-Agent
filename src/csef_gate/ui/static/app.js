/* CSEF Execution Studio: same-origin API, no user text interpreted as HTML. */
(() => {
  "use strict";
  const words = {
    fa: {
      workspace:"فضای کاری",overview:"نمای کلی",projects:"پروژه‌ها",taskGraph:"گراف وظایف",activity:"فعالیت‌ها",
      system:"سیستم",settings:"تنظیمات",localOnly:"محیط محلی و محدود",localNotice:"فقط روی همین دستگاه",
      personalSpace:"فضای شخصی",localConnected:"اتصال محلی",commandCenter:"COMMAND CENTER",
      welcome:"فضای ساخت نرم‌افزار شما",welcomeSubtitle:"از یک ایدهٔ ساده تا اجرای کنترل‌شده؛ همه‌چیز در یک نمای واحد.",
      ideaToSoftware:"IDEA → SOFTWARE",heroTitle:"ایده‌ات را بنویس.\nبقیهٔ مسیر را ببین.",
      heroSubtitle:"یک شرح کوتاه از نرم‌افزاری که می‌خواهید بسازید کافی است تا برنامه‌ریزی را آغاز کنید.",
      briefLabel:"شرح پروژه",briefPlaceholder:"مثلاً: یک نرم‌افزار مدیریت موجودی با گزارش‌های ساده...",
      projectId:"شناسهٔ پروژه",createProject:"ایجاد پروژه",
      allProjects:"کل پروژه‌ها",trackedWorkspaces:"فضاهای کاری ثبت‌شده",
      plannedTasks:"وظایف پیشنهادی",notAccepted:"هنوز به معنای تأیید نیست",
      awaitingInput:"نیازمند پاسخ",ownerDecisions:"تصمیم‌های باز مالک",
      verifiedReleases:"تحویل‌های تأییدشده",notMeasured:"هنوز اندازه‌گیری نشده",
      yourWorkspace:"YOUR WORKSPACE",recentProjects:"پروژه‌های شما",searchProjects:"جست‌وجو...",
      executionPath:"EXECUTION PATH",roadmap:"مراحل توسعه",
      roadmapDisclaimer:"وضعیت‌ها محافظه‌کارانه‌اند؛ هیچ مرحله‌ای مجوز انتشار نیست.",
      workflowIntelligence:"WORKFLOW INTELLIGENCE",dependencyGraph:"گراف وابستگی وظایف",
      proposed:"پیشنهاد",ready:"آمادهٔ شروع",selectedProject:"پروژهٔ انتخاب‌شده",
      chooseProject:"انتخاب پروژه",generatePlan:"تولید طرح با AI",
      graphEmpty:"یک پروژه انتخاب کنید تا وظایف آن نمایش داده شوند.",
      noPlan:"هنوز طرحی ثبت نشده است. برای تولید پیشنهاد، روی «تولید طرح» بزنید.",
      stalePlan:"این طرح با نسخهٔ پذیرفته‌شدهٔ پروژه همخوانی ندارد. طرح جدید لازم است.",
      graphNote:"این گراف صرفاً پیشنهاد است؛ پذیرش نهایی نیازمند Gate مستقل است.",
      systemHealth:"SYSTEM STATUS",modelConnections:"اتصال مدل‌ها",
      gateEnforced:"Gate مستقل در هسته حفظ شده",
      gateExplanation:"این داشبورد نمی‌تواند PASS، اجرای ناامن یا استقرار صادر کند.",
      uiMode:"حالت رابط",privacyFoot:"Private by design · Local only",
      provider:"ارائه‌دهنده",model:"شناسهٔ مدل",
      planDialogExplain:"این درخواست فقط طرح پیشنهادی تولید می‌کند؛ کد اجرا یا منتشر نمی‌شود و ممکن است هزینهٔ API داشته باشد.",
      consent:"هزینهٔ احتمالی یک درخواست API را تأیید می‌کنم.",
      cancel:"انصراف",runPlanner:"تولید طرح",
      configured:"کلید تنظیم شده",missing:"بدون کلید",
      projectCreated:"پروژه ثبت شد.",planCreated:"طرح پیشنهادی ذخیره شد.",
      planNeedsOwner:"طرح تولید شد؛ پرسش‌های مهم باید پاسخ داده شوند.",
      busy:"در حال پردازش...",networkError:"ارتباط با داشبورد برقرار نشد.",
      noProjects:"هنوز پروژه‌ای ندارید. اولین ایده را بالا ثبت کنید.",
      noMatches:"پروژه‌ای با این عبارت پیدا نشد.",
      needsOwner:"نیازمند پاسخ",noPlanTag:"بدون طرح",planTag:"طرح پیشنهادی",
      taskAcceptance:"معیار پذیرش",dependsOn:"وابسته به",files:"فایل‌ها",
      noDependencies:"بدون وابستگی",noLiveProof:"صرفاً وضعیت تنظیم کلید؛ نه آزمون زندهٔ API",
      tasksCount:"وظیفه",errorPrefix:"خطا: ",prototype:"نمونهٔ اولیه",partial:"بخشی پیاده‌شده",
      notVerified:"تأیید نشده",baseline:"خط مبنا و هدف",planning:"نیازها و برنامه‌ریزی",
      providers:"ارائه‌دهندگان مدل",execution:"اجرا و بازیابی",verification:"ارزیابی مستقل",
      delivery:"تحویل نرم‌افزار",interface:"داشبورد دوزبانه",validation:"اثبات روی پروژهٔ واقعی",
      showDetails:"جزئیات وظیفه"
    },
    en: {
      workspace:"Workspace",overview:"Overview",projects:"Projects",taskGraph:"Task Graph",activity:"Activity",
      system:"System",settings:"Settings",localOnly:"Local, limited access",localNotice:"This device only",
      personalSpace:"Personal workspace",localConnected:"Local connection",commandCenter:"COMMAND CENTER",
      welcome:"Your software workspace",welcomeSubtitle:"From a simple idea to controlled execution, all in one place.",
      ideaToSoftware:"IDEA → SOFTWARE",heroTitle:"Describe your idea.\nSee the path forward.",
      heroSubtitle:"Start with a short description of the software you want to create.",
      briefLabel:"Project brief",briefPlaceholder:"For example: Build an inventory app with simple reporting...",
      projectId:"Project ID",createProject:"Create project",
      allProjects:"Total projects",trackedWorkspaces:"Tracked workspaces",
      plannedTasks:"Proposed tasks",notAccepted:"Not independently accepted",
      awaitingInput:"Needs input",ownerDecisions:"Owner questions and decisions",
      verifiedReleases:"Verified deliveries",notMeasured:"Not measured yet",
      yourWorkspace:"YOUR WORKSPACE",recentProjects:"Your projects",searchProjects:"Search...",
      executionPath:"EXECUTION PATH",roadmap:"Development roadmap",
      roadmapDisclaimer:"States are conservative; none of them authorizes release.",
      workflowIntelligence:"WORKFLOW INTELLIGENCE",dependencyGraph:"Task dependency graph",
      proposed:"Proposed",ready:"Ready to start",selectedProject:"Selected project",
      chooseProject:"Choose project",generatePlan:"Generate AI plan",
      graphEmpty:"Select a project to view its task graph.",
      noPlan:"No proposed plan yet. Use “Generate AI plan” to create one.",
      stalePlan:"This plan no longer matches the accepted project revision. Regenerate it.",
      graphNote:"This graph is a proposal; only the independent Gate can accept execution.",
      systemHealth:"SYSTEM STATUS",modelConnections:"Model connections",
      gateEnforced:"Independent Gate preserved",
      gateExplanation:"This dashboard cannot grant PASS, unsafe execution, or deployment.",
      uiMode:"Interface mode",privacyFoot:"Private by design · Local only",
      provider:"Provider",model:"Model identifier",
      planDialogExplain:"This call creates a planning proposal only. No code runs or deploys; API usage may be billed.",
      consent:"I approve the possible cost of one API request.",
      cancel:"Cancel",runPlanner:"Generate plan",
      configured:"Key configured",missing:"No key",
      projectCreated:"Project recorded.",planCreated:"Planning proposal saved.",
      planNeedsOwner:"Plan created; important owner questions remain.",
      busy:"Processing...",networkError:"Could not reach the dashboard.",
      noProjects:"No projects yet. Create your first project above.",
      noMatches:"No projects match your search.",
      needsOwner:"Needs input",noPlanTag:"Not planned",planTag:"Proposed plan",
      taskAcceptance:"Acceptance criterion",dependsOn:"Depends on",files:"Files",
      noDependencies:"No dependencies",noLiveProof:"Shows key configuration only, not API health",
      tasksCount:"tasks",errorPrefix:"Error: ",prototype:"Prototype",partial:"Partially implemented",
      notVerified:"Not verified",baseline:"Baseline & intent",planning:"Requirements & planning",
      providers:"Model providers",execution:"Execution & recovery",verification:"Independent verification",
      delivery:"Software delivery",interface:"Bilingual dashboard",validation:"Real-project validation",
      showDetails:"Task details"
    }
  };
  Object.assign(words.fa, {
    executionCenter:"مانیتور اجرا",verificationCenter:"ارزیابی و Gate",
    deliveryCenter:"تحویل و بازیابی",operationalWorkspace:"مرکز عملیاتی پروژه",
    operationalSubtitle:"وضعیت مستقیم از هستهٔ CSEF و شواهد موجود؛ نه پیشرفت فرضی.",
    refreshEvidence:"به‌روزرسانی شواهد",runVisibility:"اجراهای ثبت‌شده در SQLite",
    readOnly:"فقط‌خواندنی",providerUsage:"مصرف API و فراخوانی‌ها",
    gateAuthority:"اختیار مستقل",recordedEvaluations:"ارزیابی‌های ثبت‌شده",
    acceptedCheckpoints:"Checkpoint معتبر",
    verificationCaution:"Docker در حالت REVIEW اجازهٔ PASS یا تحویل خودکار نمی‌دهد.",
    evidenceFirst:"مبتنی بر شواهد",packageStatus:"بستهٔ قابل تحویل",
    unknownPackage:"رسید بستهٔ نهایی در پایگاه کنترل ثبت نشده است.",
    recoveryStatus:"وضعیت ادامهٔ اجرا",
    recoveryCaution:"اجرای مجدد نامعلوم بدون تطبیق شواهد مجاز نیست؛ فعال‌سازی کنترل‌ها به S3/S4 وابسته است.",
    noRuns:"هیچ اجرای ثبت‌شده‌ای برای این پروژه وجود ندارد.",
    noEvidence:"هنوز شواهد آزمون ثبت نشده است.",
    noCalls:"هنوز درخواست مدلی ثبت نشده است.",
    noRecovery:"هیچ اجرای نیازمند بازیابی وجود ندارد.",
    selectedRun:"اجرای انتخاب‌شده",gatePassed:"قبولی معتبر Gate",
    reviewOnly:"بازبینی",notVerifiedRun:"در انتظار شاهد معتبر",
    unknownOutcome:"نتیجهٔ نامعلوم",attemptCount:"تعداد تلاش‌ها",
    verifiedBoundary:"مرز مستقل تأییدشده",unverifiedBoundary:"مرز مستقل تأیید نشده",
    integrityOk:"گزارش سالم",integrityFailed:"گزارش بدون اعتبار کافی",
    quotaUnlimited:"سقف شمارش تعریف نشده",quotaUsed:"درخواست ثبت‌شده",
    quotaRemaining:"درخواست باقی‌مانده",unknownCost:"هزینهٔ دلاری نامعلوم",
    verificationSummary:"خلاصهٔ آزمون‌ها",passedCases:"موفق",failedCases:"ناموفق",
    blockedAction:"عملیات اجرایی تا تأیید مرز ایزوله غیرفعال است.",
    blockedStage:"مسدود",noProjectInspection:"برای نمایش شواهد یک پروژه انتخاب کنید."
  });
  Object.assign(words.en, {
    executionCenter:"Execution monitor",verificationCenter:"Verification & Gate",
    deliveryCenter:"Delivery & recovery",operationalWorkspace:"Project control plane",
    operationalSubtitle:"Evidence from the actual CSEF controller, never inferred progress.",
    refreshEvidence:"Refresh evidence",runVisibility:"Runs recorded in SQLite",
    readOnly:"Read-only",providerUsage:"API usage and calls",
    gateAuthority:"Independent authority",recordedEvaluations:"Recorded evaluations",
    acceptedCheckpoints:"Verified checkpoints",
    verificationCaution:"Docker REVIEW cannot grant PASS or automatic delivery.",
    evidenceFirst:"Evidence-based",packageStatus:"Delivery package",
    unknownPackage:"Final package receipt is not tracked by the control store.",
    recoveryStatus:"Recovery status",
    recoveryCaution:"Unknown attempts cannot be replayed without reconciliation. Controls depend on S3/S4.",
    noRuns:"This project has no recorded runs.",noEvidence:"No test evidence recorded yet.",
    noCalls:"No model calls recorded yet.",noRecovery:"No runs requiring recovery.",
    selectedRun:"Selected run",gatePassed:"Gate-verified acceptance",
    reviewOnly:"Review",notVerifiedRun:"Awaiting verified evidence",
    unknownOutcome:"Unknown outcome",attemptCount:"Attempts",
    verifiedBoundary:"Independent boundary verified",unverifiedBoundary:"Boundary not verified",
    integrityOk:"Report integrity valid",integrityFailed:"Report not independently validated",
    quotaUnlimited:"No request-count cap set",quotaUsed:"Recorded requests",
    quotaRemaining:"Requests remaining",unknownCost:"USD cost unknown",
    verificationSummary:"Test case summary",passedCases:"Passed",failedCases:"Failed",
    blockedAction:"Execution controls remain disabled until isolation is verified.",
    blockedStage:"Blocked",noProjectInspection:"Select a project to inspect its evidence."
  });
  const $ = id => document.getElementById(id);
  const state = {
    lang:localStorage.getItem("csef-lang") === "en" ? "en" : "fa",
    projects:[],selected:null,current:null,overview:null,csrf:null,busy:false
  };
  let notificationTimer;
  const tr = key => words[state.lang][key] || key;
  function make(tag, cls, label) {
    const el = document.createElement(tag);
    if (cls) el.className=cls;
    if (label !== undefined) el.textContent=String(label);
    return el;
  }
  function icon(id) {
    const el=document.createElementNS("http://www.w3.org/2000/svg","svg");
    const use=document.createElementNS("http://www.w3.org/2000/svg","use");
    use.setAttribute("href","#i-"+id);el.append(use);return el;
  }
  function toast(message,error=false) {
    const item=$("toast");
    item.textContent=message;item.classList.toggle("error",error);item.classList.add("visible");
    clearTimeout(notificationTimer);
    notificationTimer=setTimeout(()=>item.classList.remove("visible"),5500);
  }
  async function request(path,method="GET",payload=null) {
    const options={method,cache:"no-store",credentials:"same-origin",headers:{}};
    if (method !== "GET") {
      options.headers["Content-Type"]="application/json";
      options.headers["X-CSEF-CSRF"]=state.csrf;
      options.body=JSON.stringify(payload);
    }
    const response=await fetch(path,options);
    const data=await response.json();
    if (!response.ok) throw new Error(data.error || "HTTP "+response.status);
    return data;
  }
  function language(lang) {
    state.lang=lang;localStorage.setItem("csef-lang",lang);
    document.documentElement.lang=lang;document.documentElement.dir=lang==="fa"?"rtl":"ltr";
    $("language-label").textContent=lang==="fa"?"EN":"فا";
    document.querySelectorAll("[data-i18n]").forEach(el=>{
      const key=el.dataset.i18n;
      if (key==="heroTitle") {
        const lines=tr(key).split("\n");
        const parts=[];
        lines.forEach((line,index)=>{if(index)parts.push(document.createElement("br"));parts.push(document.createTextNode(line));});
        el.replaceChildren(...parts);
      } else el.textContent=tr(key);
    });
    document.querySelectorAll("[data-placeholder]").forEach(el=>el.placeholder=tr(el.dataset.placeholder));
    $("today-label").textContent=new Intl.DateTimeFormat(lang==="fa"?"fa-IR":"en-GB",{dateStyle:"medium"}).format(new Date());
    if(state.overview)renderOverview();
    renderGraph();renderOperations();
  }
  async function load() {
    try {
      state.overview=await request("/api/overview");
      state.projects=state.overview.projects;
      if(state.selected&&!state.projects.some(p=>p.slug===state.selected))state.selected=null;
      if(!state.selected&&state.projects.length)state.selected=state.projects[0].slug;
      renderOverview();
      if(state.selected)await selectProject(state.selected,false);
      else {state.current=null;state.inspection=null;renderGraph();renderOperations();}
    }catch(err){toast(tr("errorPrefix")+err.message,true);}
  }
  function renderOverview() {
    const data=state.overview;if(!data)return;
    $("stat-projects").textContent=data.summary.projects;
    $("stat-tasks").textContent=data.summary.proposed_tasks;
    $("stat-blocked").textContent=data.summary.needs_input;
    $("nav-projects").textContent=data.summary.projects;
    renderProjects();renderRoadmap(data.roadmap);renderProviders(data.providers);
    const select=$("project-select");
    select.replaceChildren(make("option","",tr("chooseProject")));select.options[0].value="";
    data.projects.forEach(p=>{const opt=make("option","",p.slug);opt.value=p.slug;select.append(opt);});
    select.value=state.selected||"";
    $("generate-plan").disabled=!state.selected;
  }
  function renderProjects() {
    const wrap=$("projects-list");wrap.replaceChildren();
    const term=$("project-filter").value.trim().toLocaleLowerCase();
    const list=state.projects.filter(p=>(p.goal+" "+p.slug).toLocaleLowerCase().includes(term));
    if(!list.length){
      const empty=make("div","empty-projects");
      empty.append(icon("layer"),make("span","",tr(term?"noMatches":"noProjects")));wrap.append(empty);return;
    }
    list.forEach(p=>{
      const row=make("button","project-row"+(p.slug===state.selected?" is-active":""));
      row.type="button";row.addEventListener("click",()=>selectProject(p.slug,true));
      row.setAttribute("aria-label",p.slug+" — "+p.goal);
      const info=make("span","project-info");
      info.append(make("strong","",p.slug),make("small","",p.goal));
      const label=p.questions_count||p.plan_state==="needs_owner"?"needsOwner":
        p.plan_state==="not_started"?"noPlanTag":"planTag";
      const badge=make("span","project-tag"+(label==="needsOwner"?" warn":""),tr(label));
      const arrow=icon("chevron");arrow.classList.add("project-arrow");
      row.append(make("span","project-emblem",p.slug.slice(0,2)),info,badge,arrow);wrap.append(row);
    });
  }
  function renderRoadmap(phases) {
    const wrap=$("roadmap-list");wrap.replaceChildren();
    phases.forEach(p=>{
      const item=make("div","roadmap-item");
      item.append(make("span","roadmap-number",p.id.slice(1)),
        make("span","roadmap-name",tr(p.name)),
        make("span","roadmap-state "+p.state,tr(p.state==="partial"?"partial":p.state==="prototype"?"prototype":p.state==="blocked"?"blockedStage":"notVerified")));
      wrap.append(item);
    });
  }
  function renderProviders(providers) {
    ["openai","anthropic"].forEach(key=>{
      const el=$(key+"-state"),exists=Boolean(providers[key]);
      el.textContent=tr(exists?"configured":"missing");
      el.classList.toggle("configured",exists);el.title=tr("noLiveProof");
    });
  }
  async function selectProject(slug,scroll) {
    state.selected=slug;$("project-select").value=slug;
    $("generate-plan").disabled=false;renderProjects();
    try {
      const [details, evidence] = await Promise.all([
        request("/api/projects/"+encodeURIComponent(slug)),
        request("/api/projects/"+encodeURIComponent(slug)+"/inspection")
      ]);
      state.current=details;state.inspection=evidence;
      renderGraph();renderOperations();if(scroll)$("graph").scrollIntoView({behavior:"smooth",block:"start"});
    }catch(err){state.current=null;state.inspection=null;renderGraph();renderOperations();toast(tr("errorPrefix")+err.message,true);}
  }
  function renderGraph() {
    const wrap=$("graph-nodes"),edges=$("graph-edges");
    wrap.replaceChildren();edges.replaceChildren();
    const plan=state.current&&state.current.plan;
    if(!plan||!plan.tasks||!plan.tasks.length||["stale","invalid"].includes(plan.state)) {
      const empty=make("div","graph-empty"),circle=make("div","empty-orbit");
      circle.append(icon("nodes"));
      empty.append(circle,make("p","",plan?tr("stalePlan"):state.selected?tr("noPlan"):tr("graphEmpty")));
      wrap.append(empty);$("graph-task-count").textContent="—";return;
    }
    $("graph-task-count").textContent=plan.tasks.length+" "+tr("tasksCount");
    const ready=new Set(plan.ready||[]);
    plan.tasks.forEach(task=>{
      const box=make("button","graph-node"+(ready.has(task.id)?" ready":""));
      box.type="button";box.dataset.taskId=task.id;box.title=tr("showDetails");
      const head=make("div","node-head");
      head.append(make("span","",task.id),make("span","node-state"));
      box.append(head,make("strong","node-title",task.title),make("span","node-sub",task.fact_ids.join(" · ")));
      box.addEventListener("click",()=>showTask(task));wrap.append(box);
    });
    requestAnimationFrame(drawEdges);
  }
  function drawEdges() {
    const wrap=$("graph-nodes"),svg=$("graph-edges"),viewport=$("graph-viewport");
    const plan=state.current&&state.current.plan;if(!plan||!plan.tasks)return;
    const w=Math.max(wrap.scrollWidth+36,viewport.clientWidth);
    const h=Math.max(wrap.scrollHeight+36,viewport.clientHeight);
    svg.setAttribute("width",w);svg.setAttribute("height",h);
    svg.setAttribute("viewBox","0 0 "+w+" "+h);svg.replaceChildren();
    const nodes=new Map([...wrap.querySelectorAll(".graph-node")].map(el=>[el.dataset.taskId,el]));
    const outer=viewport.getBoundingClientRect(),rtl=state.lang==="fa";
    plan.tasks.forEach(task=>task.depends_on.forEach(dep=>{
      const a=nodes.get(dep),b=nodes.get(task.id);if(!a||!b)return;
      const r1=a.getBoundingClientRect(),r2=b.getBoundingClientRect();
      const x1=(rtl?r1.left:r1.right)-outer.left+viewport.scrollLeft;
      const x2=(rtl?r2.right:r2.left)-outer.left+viewport.scrollLeft;
      const y1=r1.top+r1.height/2-outer.top+viewport.scrollTop;
      const y2=r2.top+r2.height/2-outer.top+viewport.scrollTop;
      const mid=(x1+x2)/2;
      const path=document.createElementNS("http://www.w3.org/2000/svg","path");
      path.setAttribute("d","M "+x1+" "+y1+" C "+mid+" "+y1+", "+mid+" "+y2+", "+x2+" "+y2);
      path.setAttribute("fill","none");path.setAttribute("stroke","#7683c0");
      path.setAttribute("stroke-width","1.7");path.setAttribute("stroke-dasharray","5 5");
      svg.append(path);
    }));
  }
  function showTask(task) {
    const deps=task.depends_on.length?task.depends_on.join(", "):tr("noDependencies");
    toast(task.id+" — "+task.title+"\n"+tr("taskAcceptance")+": "+task.acceptance+
      "\n"+tr("dependsOn")+": "+deps+"\n"+tr("files")+": "+task.files.join(", "));
  }

  function evidenceLine(title, subtitle, tone) {
    const row=make("div","evidence-row"+(tone?" "+tone:""));
    const dot=make("span","evidence-dot");
    const body=make("span","evidence-body");
    body.append(make("strong","",title),make("small","",subtitle));
    row.append(dot,body);
    return row;
  }
  function renderOperations() {
    const data=state.inspection;
    const runs=$("run-list"),evaluations=$("evaluation-list");
    const calls=$("api-call-list"),recoveries=$("recovery-list");
    [runs,evaluations,calls,recoveries].forEach(el=>el.replaceChildren());
    if(!data){
      $("run-count").textContent="—";
      $("evaluation-count").textContent="—";$("checkpoint-count").textContent="—";
      $("quota-display").textContent="—";$("delivery-state").textContent=tr("unknownPackage");
      [runs,evaluations,calls,recoveries].forEach(el=>el.append(make("p","evidence-empty",tr("noProjectInspection"))));
      return;
    }
    const gate=data.gate,recorded=gate.runs||[];
    $("run-count").textContent=String(recorded.length);
    $("evaluation-count").textContent=String((gate.evaluations||[]).length);
    $("checkpoint-count").textContent=String(gate.accepted_checkpoint_count||0);
    $("delivery-state").textContent=tr("unknownPackage");
    if(!recorded.length)runs.append(make("p","evidence-empty",tr("noRuns")));
    recorded.slice(0,12).forEach(run=>{
      const status=run.accepted_checkpoint?tr("gatePassed"):run.status;
      runs.append(evidenceLine(run.id.slice(0,16)+"… · "+status,
        tr("attemptCount")+": "+run.attempts+" · "+run.created,
        run.accepted_checkpoint?"passed":run.status==="failed_or_unknown"?"warning":""));
    });
    const checks=gate.evaluations||[];
    if(!checks.length)evaluations.append(make("p","evidence-empty",tr("noEvidence")));
    checks.slice(0,12).forEach(ev=>{
      const passed=(ev.cases||[]).filter(x=>x.passed).length;
      const total=(ev.cases||[]).length;
      const integrity=ev.report_integrity?tr("integrityOk"):tr("integrityFailed");
      const boundary=ev.verified_boundary?tr("verifiedBoundary"):tr("unverifiedBoundary");
      evaluations.append(evidenceLine(
        ev.id.slice(0,17)+"… · "+ev.status,
        tr("verificationSummary")+": "+passed+"/"+total+" · "+integrity+" · "+boundary,
        ev.status==="pass"&&ev.verified_boundary&&ev.report_integrity?"passed":
        ev.status==="fail"||!ev.report_integrity?"warning":""));
    });
    const budget=data.provider_budget,stats=budget&&budget.breakdown;
    $("quota-display").textContent=budget?
      tr("quotaUsed")+": "+budget.used_calls+" · "+
      (budget.remaining_calls===null?tr("quotaUnlimited"):tr("quotaRemaining")+": "+budget.remaining_calls):
      tr("unknownCost");
    const recordedCalls=data.calls||[];
    if(!recordedCalls.length)calls.append(make("p","evidence-empty",tr("noCalls")));
    recordedCalls.slice(0,8).forEach(call=>{
      const usage=call.receipt&&call.receipt.usage;
      const totals=usage?String(usage.input_tokens??"?")+"/"+String(usage.output_tokens??"?"):"—";
      calls.append(evidenceLine("#"+call.id+" · "+call.role+" · "+call.status,
        "tokens in/out: "+totals+" · "+tr("unknownCost"),
        call.status==="failed_or_unknown"?"warning":""));
    });
    const needs=recorded.filter(x=>!x.accepted_checkpoint);
    if(!needs.length)recoveries.append(make("p","evidence-empty",tr("noRecovery")));
    needs.slice(0,8).forEach(run=>recoveries.append(evidenceLine(
      run.id.slice(0,16)+"… · "+run.status,
      tr("blockedAction"),
      "warning"
    )));
  }
  function busy(value) {
    state.busy=value;
    [$("new-project-form").querySelector("button"),$("generate-plan"),$("run-plan")].forEach(button=>{
      button.disabled=value||(button.id==="generate-plan"&&!state.selected);
    });
    $("run-plan").textContent=tr(value?"busy":"runPlanner");
  }
  async function create(event) {
    event.preventDefault();if(state.busy)return;
    const slug=$("project-slug").value.trim(),brief=$("brief").value.trim();
    if(!slug||!brief)return;
    busy(true);
    try{
      const result=await request("/api/projects","POST",{slug,brief});
      state.selected=result.slug;$("new-project-form").reset();
      toast(tr("projectCreated"));await load();
      $("graph").scrollIntoView({behavior:"smooth",block:"start"});
    }catch(err){toast(tr("errorPrefix")+err.message,true);}
    finally{busy(false);}
  }
  async function plan(event) {
    event.preventDefault();
    if(state.busy||!state.selected||!$("confirm-spend").checked)return;
    busy(true);
    try{
      const result=await request("/api/projects/"+encodeURIComponent(state.selected)+"/plan","POST",{
        provider:$("provider").value,model:$("model").value.trim(),confirm_paid_call:true
      });
      $("plan-dialog").close();$("confirm-spend").checked=false;
      toast(tr(result.status==="needs_owner"?"planNeedsOwner":"planCreated"));await load();
    }catch(err){toast(tr("errorPrefix")+err.message,true);}
    finally{busy(false);}
  }
  async function init() {
    language(state.lang);
    document.querySelectorAll(".nav-link").forEach(button=>button.addEventListener("click",()=>{
      document.querySelectorAll(".nav-link").forEach(item=>item.classList.toggle("selected",item===button));
      const el=$(button.dataset.target);if(el)el.scrollIntoView({behavior:"smooth",block:"start"});
    }));
    $("language-toggle").addEventListener("click",()=>language(state.lang==="fa"?"en":"fa"));
    $("new-project-form").addEventListener("submit",create);
    $("project-filter").addEventListener("input",renderProjects);
    $("refresh-inspection").addEventListener("click",()=>{if(state.selected)selectProject(state.selected,false);else load();});
    $("project-select").addEventListener("change",event=>{
      if(event.target.value)selectProject(event.target.value,false);
      else{state.selected=null;state.current=null;state.inspection=null;renderProjects();renderGraph();renderOperations();$("generate-plan").disabled=true;}
    });
    $("generate-plan").addEventListener("click",()=>{if(state.selected)$("plan-dialog").showModal();});
    $("close-plan").addEventListener("click",()=>$("plan-dialog").close());
    $("cancel-plan").addEventListener("click",()=>$("plan-dialog").close());
    $("plan-form").addEventListener("submit",plan);
    window.addEventListener("resize",()=>requestAnimationFrame(drawEdges));
    try{
      state.csrf=(await request("/api/session")).csrf_token;
      await load();
    }catch(err){toast(tr("networkError")+" "+err.message,true);}
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);
  else init();
})();