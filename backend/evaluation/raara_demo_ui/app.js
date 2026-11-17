const $ = (selector, root = document) => root.querySelector(selector);
const create = (tag, className, text) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status}).`);
  return payload;
}

function statusTone(status) {
  if (status === "CONFLICTING_SOURCES") return "conflict";
  if (["NOT_FOUND", "NEEDS_CLARIFICATION", "ABSTAINED"].includes(status)) return "warn";
  return "";
}

function renderEvidence(row, citedIds = []) {
  const card = create("article", "evidence-card");
  const top = create("div", "evidence-top");
  top.append(create("strong", "", row.title));
  top.append(create("span", "id-chip", row.evidence_id));
  top.append(create("span", "id-chip", row.policy_id));
  card.append(top);
  const metadata = [row.category, `Version ${row.version}`, row.provenance, row.authority_status];
  if (row.is_official_university_policy === false) metadata.push("Not official");
  for (const label of metadata) card.append(create("span", "meta-chip", label));
  card.append(create("p", "", row.exact_text));
  if (typeof row.score === "number") {
    card.append(create("p", "score-note", `Cosine similarity: ${row.score.toFixed(6)}. This is a retrieval score, not a confidence probability.`));
  }
  const isCited = citedIds.includes(row.evidence_id);
  if (isCited) card.append(create("p", "provenance-line", "Cited by the displayed answer; citation metadata matched this retrieved record."));
  return card;
}

function showAnswer(payload) {
  const area = $("#answer-area");
  area.replaceChildren();
  area.className = "answer-area";
  const answer = payload.answer;
  const card = create("article", `answer-card status-${answer.status}`);
  const heading = create("div", "answer-title-row");
  heading.append(create("h3", "", "RAARA response"));
  heading.append(create("span", `status-pill ${statusTone(answer.status)}`, answer.status));
  card.append(heading);
  card.append(create("p", "answer-text", answer.answer));
  card.append(create("p", "provenance-line", `Provenance: PROJECT_AUTHORED · GENERIC_PROJECT_POLICY · NOT_OFFICIAL · citations validated: ${payload.citations_validated ? "yes" : "no"}`));
  card.append(create("p", "disclaimer", answer.disclaimer));
  if (answer.citations.length) {
    card.append(create("h4", "", "Answer citations"));
    const cited = create("div", "evidence-list");
    for (const cite of answer.citations) cited.append(renderEvidence(cite, [cite.evidence_id]));
    card.append(cited);
  } else {
    card.append(create("p", "provenance-line", "No answer citations were returned."));
  }
  const allRetrieved = create("details", "retrieved-details");
  const summary = create("summary", "", `Inspect retrieved evidence (${payload.retrieved_evidence.length})`);
  allRetrieved.append(summary);
  const list = create("div", "evidence-list");
  const citedIds = answer.citations.map((cite) => cite.evidence_id);
  for (const row of payload.retrieved_evidence) list.append(renderEvidence(row, citedIds));
  if (!payload.retrieved_evidence.length) list.append(create("p", "muted", "No evidence passed the local relevance threshold."));
  allRetrieved.append(list);
  card.append(allRetrieved);
  area.append(card);
}

async function submitQuestion(question) {
  const error = $("#ask-error");
  const submit = $("#ask-submit");
  error.hidden = true;
  submit.disabled = true;
  submit.textContent = "Checking evidence…";
  const area = $("#answer-area");
  area.className = "answer-area empty-state";
  area.replaceChildren(create("span", "empty-icon", "…"), create("p", "", "Retrieving and checking local evidence…"));
  try {
    showAnswer(await request("/api/ask", { method: "POST", body: JSON.stringify({ question }) }));
  } catch (err) {
    error.textContent = err.message;
    error.hidden = false;
    area.replaceChildren(create("p", "muted", "No answer was produced. Check the question or restart the local demo."));
  } finally {
    submit.disabled = false;
    submit.innerHTML = 'Ask RAARA <span aria-hidden="true">→</span>';
  }
}

function renderExamples(groups) {
  const root = $("#example-groups");
  root.replaceChildren();
  for (const [name, questions] of Object.entries(groups)) {
    if (!questions.length) continue;
    const details = create("details", "example-group");
    details.append(create("summary", "", `${name} (${questions.length})`));
    const menu = create("div", "example-menu");
    for (const item of questions) {
      const button = create("button", "example-question", `${item.question_id} · ${item.question}`);
      button.type = "button";
      button.addEventListener("click", () => {
        $("#question-input").value = item.question;
        details.open = false;
        submitQuestion(item.question);
      });
      menu.append(button);
    }
    details.append(menu);
    root.append(details);
  }
}

function renderStats(data) {
  const stats = $("#stats");
  stats.replaceChildren();
  const summary = data.summary;
  const cards = [
    [data.policy_count, "Project-authored policy records"],
    [data.question_count, "Existing demonstration questions"],
    [data.retrieval_test_count, "Question runs in this evaluation"],
    [`${summary.passed_questions}/${data.question_count}`, "Questions meeting the diagnostic pass rule"],
  ];
  for (const [value, label] of cards) {
    const card = create("div", "stat-card");
    card.append(create("strong", "", value), create("span", "", label));
    stats.append(card);
  }
  $("#dashboard-label").textContent = `${data.test_suite_display} · Dataset ${data.dataset_version}`;
}

function renderEvaluation(data) {
  const summaryRoot = $("#evaluation-summary");
  summaryRoot.replaceChildren();
  const summary = data.summary;
  const expectedEvidence = summary.answerable_questions;
  const metrics = [
    [`${summary.status_matches}/${data.question_count}`, "Expected status matched"],
    [`${summary.citation_validations_passed}/${data.question_count}`, "Citation metadata checks passed"],
    [`${summary.abstentions_correct}/${summary.abstentions_expected}`, "Expected abstentions correct"],
    [`${summary.answerable_questions_with_all_expected_evidence_retrieved}/${expectedEvidence}`, "Answerable items with all expected evidence retrieved"],
    [`${summary.numerical_calculation_status_matches}/${summary.numerical_calculation_questions}`, "Numerical question statuses matched"],
    [`${summary.passed_questions} pass · ${summary.failed_questions} fail`, "Combined diagnostic"],
  ];
  for (const [value, label] of metrics) {
    const chip = create("div", "eval-chip");
    chip.append(create("strong", "", value), document.createTextNode(label));
    summaryRoot.append(chip);
  }
  const body = $("#evaluation-rows");
  body.replaceChildren();
  for (const row of data.results) {
    const tr = document.createElement("tr");
    const values = [
      row.question_id,
      row.question,
      row.expected_answerability,
      row.actual_status,
      `${row.expected_evidence_retrieved === null ? "—" : row.expected_evidence_retrieved ? "All expected found" : "Expected evidence missing"} · ${row.retrieved_evidence_ids.join(", ") || "none"}`,
      row.citation_validity ? "Yes" : "No",
      row.abstention_correctness === null ? "—" : row.abstention_correctness ? "Yes" : "No",
      row.passed ? "PASS" : "FAIL",
    ];
    values.forEach((value, index) => {
      const td = create("td", index === 7 ? (row.passed ? "pass-text" : "fail-text") : "", value);
      tr.append(td);
    });
    body.append(tr);
  }
}

function renderTour(cases) {
  const root = $("#tour-results");
  root.replaceChildren();
  for (const item of cases) {
    const article = create("article", "tour-case");
    const head = create("div", "tour-case-head");
    head.append(create("strong", "", `Case ${item.case_id}: ${item.title}`));
    head.append(create("span", `case-status ${item.status_match ? "pass-text" : "fail-text"}`, `${item.expected_status} → ${item.actual_status}`));
    article.append(head);
    article.append(create("p", "", item.question));
    article.append(create("p", "", item.answer));
    article.append(create("p", "", `Evidence IDs: ${item.citations.map((cite) => cite.evidence_id).join(", ") || "none cited"}. Citation metadata check: ${item.citations_validated ? "passed" : "failed"}.`));
    article.append(create("p", "", item.disclaimer));
    const passages = create("details", "case-passages");
    passages.append(create("summary", "", `Inspect retrieved passages (${item.evidence.length})`));
    const evidenceList = create("div", "evidence-list");
    const citedIds = item.citations.map((cite) => cite.evidence_id);
    for (const evidence of item.evidence) evidenceList.append(renderEvidence(evidence, citedIds));
    passages.append(evidenceList);
    article.append(passages);
    root.append(article);
  }
}

$("#ask-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuestion($("#question-input").value);
});
$("#clear-question").addEventListener("click", () => {
  $("#question-input").value = "";
  $("#answer-area").className = "answer-area empty-state";
  $("#answer-area").replaceChildren(create("span", "empty-icon", "✳"), create("p", "", "Your answer, cited evidence and provenance will appear here."));
  $("#ask-error").hidden = true;
});
$("#run-tour").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "Running five cases…";
  try { renderTour(await request("/api/demo-sequence")); }
  catch (err) { $("#tour-results").replaceChildren(create("p", "error-message", err.message)); }
  finally { button.disabled = false; button.innerHTML = 'Run the five cases <span aria-hidden="true">↗</span>'; }
});

function collectCalculation(form) {
  const kind = form.dataset.calculation;
  if (kind === "attendance") return { calculation: kind, attended: Number(form.elements.attended.value), held: Number(form.elements.held.value) };
  if (kind === "course_total") return { calculation: kind, internal_score: Number(form.elements.internal_score.value), exam_score: Number(form.elements.exam_score.value) };
  const courses = [...form.querySelectorAll(".pair-row")].map((row) => ({ credits: Number($("[data-credit]", row).value), grade_point: Number($("[data-grade]", row).value) }));
  return { calculation: kind, courses };
}

function renderCalculation(result, error = false) {
  const root = $("#calculation-result");
  root.replaceChildren();
  if (error) return root.append(create("p", "calc-error", result));
  root.append(create("p", "", result.label));
  root.append(create("p", "", `Inputs: ${JSON.stringify(result.inputs)}`));
  root.append(create("p", "", `Formula: ${result.formula}`));
  root.append(create("p", "", `Steps: ${result.steps}`));
  root.append(create("p", "", `Result: ${result.result}`));
  root.append(create("p", "", `Dataset evidence: ${result.evidence.evidence_id} · ${result.evidence.title} · ${result.evidence.authority_status}`));
  root.append(create("p", "", result.evidence.exact_text));
}

document.querySelectorAll(".calc-card").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    try { renderCalculation(await request("/api/calculate", { method: "POST", body: JSON.stringify(collectCalculation(form)) })); }
    catch (err) { renderCalculation(err.message, true); }
  });
  const addButton = $(`[data-add-pair]`, form);
  if (addButton) addButton.addEventListener("click", () => {
    const row = create("div", "pair-row");
    const creditLabel = create("label", "", "Credits");
    const credit = document.createElement("input");
    credit.type = "number"; credit.min = "0.01"; credit.step = "any"; credit.value = "3"; credit.required = true; credit.dataset.credit = "";
    creditLabel.append(credit);
    const gradeLabel = create("label", "", "Grade points");
    const grade = document.createElement("input");
    grade.type = "number"; grade.min = "0"; grade.step = "any"; grade.value = "8"; grade.required = true; grade.dataset.grade = "";
    gradeLabel.append(grade);
    row.append(creditLabel, gradeLabel);
    $("[data-pairs]", form).append(row);
  });
});

async function initialize() {
  try {
    const [health, dashboard, examples] = await Promise.all([
      request("/api/health"), request("/api/dashboard"), request("/api/examples"),
    ]);
    $("#connection-status").textContent = health.status === "ok" ? "Demo ready" : "Unavailable";
    renderStats(dashboard);
    renderEvaluation(dashboard.evaluation);
    renderExamples(examples);
    $("#metric-note").textContent = dashboard.evaluation_note;
  } catch (error) {
    $("#connection-status").textContent = "Connection error";
    $("#dashboard-label").textContent = error.message;
  }
}

$("#refresh-evaluation").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "Evaluating…";
  try { renderEvaluation(await request("/api/evaluation")); }
  catch (err) { $("#evaluation-summary").replaceChildren(create("p", "error-message", err.message)); }
  finally { button.disabled = false; button.textContent = "Run evaluation again"; }
});

initialize();
