const data = window.VOC_DATA;
const fmt = new Intl.NumberFormat("zh-CN");
const pct = (value) => `${(value * 100).toFixed(1)}%`;
const short = (text, limit = 34) => (text.length > limit ? `${text.slice(0, limit - 1)}...` : text);
const buyerColors = ["#1677ff", "#13c2c2", "#fa8c16", "#722ed1", "#52c41a", "#c28a16", "#eb2f96", "#2f9bbd"];
const sceneColors = ["#1677ff", "#01c6b2", "#fa8c16", "#722ed1", "#52c41a", "#faad14", "#eb2f96", "#2f9bbd"];
const concernColors = ["#1677ff", "#13c2c2", "#fa8c16", "#722ed1", "#52c41a", "#c28a16", "#eb2f96", "#2f9bbd", "#fa541c", "#2f54eb"];

document.getElementById("subtitle").textContent = data.meta.subtitle;
document.getElementById("metaLine").textContent =
  `数据源：${data.meta.productCount} 个产品，${fmt.format(data.meta.totalReviews)} 条有效评论；评论日期 ${data.meta.dateMin} 至 ${data.meta.dateMax}`;

const positiveRate = data.meta.sentiment.positive / data.meta.totalReviews;
const neutralRate = data.meta.sentiment.neutral / data.meta.totalReviews;
const negativeRate = data.meta.sentiment.negative / data.meta.totalReviews;
document.getElementById("positiveRate").textContent = pct(positiveRate);
document.getElementById("sentimentRing").style.background =
  `conic-gradient(var(--green) 0 ${positiveRate * 360}deg, var(--orange) ${positiveRate * 360}deg ${(positiveRate + neutralRate) * 360}deg, var(--red) ${(positiveRate + neutralRate) * 360}deg 360deg)`;

function renderKpis() {
  const kpis = [
    ["有效评论", fmt.format(data.meta.totalReviews), "空文本与重复评论已过滤"],
    ["平均评分", data.meta.avgRating.toFixed(2), "5 分制电商评论评分"],
    ["低分评论", fmt.format(data.meta.lowRatingCount), `占比 ${pct(data.meta.lowRatingShare)}`],
    ["VOC 标签", fmt.format(data.tags.length), "艺术家具场景多标签体系"],
  ];
  document.getElementById("kpiGrid").innerHTML = kpis.map(([label, value, note]) => `
    <article class="kpi-card">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-note">${note}</div>
    </article>
  `).join("");
}

function barChart(target, rows, options = {}) {
  const max = Math.max(...rows.map((row) => row.value), 1);
  target.innerHTML = rows.map((row) => {
    const width = Math.max(2, (row.value / max) * 100);
    return `
      <div class="bar-row">
        <div class="bar-label" title="${row.label}">${row.label}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${width}%;background:${row.color || options.color || "var(--blue)"}"></div></div>
        <div class="bar-value">${row.display || row.value}</div>
      </div>
    `;
  }).join("");
}

function renderCharts() {
  barChart(
    document.getElementById("tagChart"),
    data.tags.map((tag) => ({
      label: tag.name,
      value: tag.reviewCount,
      display: `${tag.reviewCount} | ${tag.avgRating}`,
      color: tag.negativeShare > 0.12 ? "var(--orange)" : "var(--blue)",
    })),
  );

  const riskRows = data.tags
    .filter((tag) => tag.negativeCount > 0)
    .sort((a, b) => b.negativeCount - a.negativeCount)
    .map((tag) => ({
      label: tag.name,
      value: tag.negativeCount,
      display: `${tag.negativeCount} / ${pct(tag.negativeShare)}`,
      color: tag.negativeShare > 0.12 ? "var(--red)" : "var(--orange)",
    }));
  barChart(document.getElementById("riskChart"), riskRows);
}

function taxonomyCards(filter = "all") {
  let tags = data.tags;
  if (filter === "high") tags = tags.filter((tag) => tag.share >= 0.18);
  if (filter === "risk") tags = tags.filter((tag) => tag.negativeShare >= 0.07);

  document.getElementById("taxonomyGrid").innerHTML = tags.map((tag) => `
    <article class="tag-card">
      <div class="tag-card-head">
        <div class="tag-name">${tag.name}</div>
        <span class="pill">${pct(tag.share)}</span>
      </div>
      <div class="card-desc">${tag.desc}</div>
      <div class="tag-metrics">
        <div><strong>${tag.reviewCount}</strong><span>声量</span></div>
        <div><strong>${tag.avgRating}</strong><span>均分</span></div>
        <div><strong>${pct(tag.negativeShare)}</strong><span>负向</span></div>
      </div>
      <div class="keyword-line">${tag.keywords.length ? tag.keywords.join(" / ") : "待扩展语义词库"}</div>
    </article>
  `).join("");
}

function quoteBlock(item) {
  return `
    <div class="quote">
      <blockquote>${item.text}</blockquote>
      <div class="quote-meta">${short(item.product, 46)} · ${item.rating} 分 · ${item.date}</div>
    </div>
  `;
}

function renderInsights(targetId, rows) {
  document.getElementById(targetId).innerHTML = rows.map((item) => `
    <article class="insight-card">
      <div class="insight-title"><span class="pill ${targetId === "painList" ? "danger" : ""}">${item.tag}</span>${item.title}</div>
      <p>${item.summary}</p>
      ${item.evidence.map(quoteBlock).join("")}
    </article>
  `).join("");
}

function renderBuyerLegend(targetId) {
  document.getElementById(targetId).innerHTML = data.buyerGroups.map((group, index) => `
    <span class="legend-item"><i class="legend-dot" style="background:${buyerColors[index % buyerColors.length]}"></i>${group.name}</span>
  `).join("");
}

function renderBuyerCloud() {
  const positions = [
    [45, 66], [34, 32], [62, 40], [27, 55],
    [68, 70], [76, 26], [18, 24], [82, 52],
  ];
  const max = Math.max(...data.buyerGroups.map((group) => group.mentions), 1);
  document.getElementById("buyerWordCloud").innerHTML = data.buyerGroups.map((group, index) => {
    const size = 18 + (group.mentions / max) * 42;
    const pos = positions[index % positions.length];
    return `
      <span class="cloud-word" style="left:${pos[0]}%;top:${pos[1]}%;font-size:${size}px;color:${buyerColors[index % buyerColors.length]}" title="${group.mentions} 条 · ${group.avgRating} 分">
        ${group.name}
      </span>
    `;
  }).join("");
}

function renderBuyerTrend() {
  renderLineTrend("buyerTrendChart", data.buyerTrend, data.buyerGroups.slice(0, 8).map((group) => group.name), buyerColors, "买家群体趋势图");
}

function renderLineTrend(targetId, trendRows, seriesNames, colors, label) {
  const target = document.getElementById(targetId);
  const months = trendRows.map((row) => row.month);
  const values = trendRows.flatMap((row) => seriesNames.map((name) => row[name] || 0));
  const maxValue = Math.max(...values, 1);
  const width = Math.max(820, months.length * 64);
  const height = 410;
  const pad = { left: 48, right: 24, top: 28, bottom: 56 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;
  const x = (index) => pad.left + (months.length === 1 ? chartW / 2 : (index / (months.length - 1)) * chartW);
  const y = (value) => pad.top + chartH - (value / maxValue) * chartH;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(maxValue * ratio));

  const grid = ticks.map((tick) => `
    <line class="trend-grid" x1="${pad.left}" y1="${y(tick)}" x2="${width - pad.right}" y2="${y(tick)}"></line>
    <text class="tick-label" x="${pad.left - 12}" y="${y(tick) + 4}" text-anchor="end">${tick}</text>
  `).join("");

  const lines = seriesNames.map((name, seriesIndex) => {
    const points = trendRows.map((row, index) => `${x(index)},${y(row[name] || 0)}`).join(" ");
    const dots = trendRows.map((row, index) => `
      <circle class="trend-point" cx="${x(index)}" cy="${y(row[name] || 0)}" r="3.5" fill="${colors[seriesIndex % colors.length]}"></circle>
    `).join("");
    return `
      <polyline class="trend-line" points="${points}" stroke="${colors[seriesIndex % colors.length]}"></polyline>
      ${dots}
    `;
  }).join("");

  const monthLabels = months.map((month, index) => `
    <text class="tick-label" x="${x(index)}" y="${height - 20}" text-anchor="middle">${month.replace("-", "")}</text>
  `).join("");

  target.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${label}">
      ${grid}
      <line class="trend-axis" x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}"></line>
      <line class="trend-axis" x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}"></line>
      <text class="axis-label" x="18" y="${pad.top + chartH / 2}" transform="rotate(-90 18 ${pad.top + chartH / 2})" text-anchor="middle">提及量</text>
      ${monthLabels}
      ${lines}
    </svg>
  `;
}

function renderBuyerCards() {
  document.getElementById("buyerCards").innerHTML = data.buyerGroups.map((group, index) => `
    <article class="buyer-card">
      <div class="buyer-card-head">
        <div class="buyer-name">${group.name}</div>
        <span class="pill" style="color:${buyerColors[index % buyerColors.length]};background:rgba(22,119,255,.08)">${group.mentions} 条</span>
      </div>
      <div class="tag-metrics">
        <div><strong>${group.avgRating}</strong><span>均分</span></div>
        <div><strong>${pct(group.share)}</strong><span>占比</span></div>
        <div><strong>${group.negativeCount}</strong><span>负向</span></div>
      </div>
      <div class="buyer-desc">${group.description}</div>
      <div class="keyword-line">${group.keywords.join(" / ")}</div>
      <div class="buyer-evidence">${group.evidence.map((item) => `“${item.text}”`).join("<br />")}</div>
    </article>
  `).join("");
}

function renderPurchaseConcerns() {
  const concerns = data.purchaseConcerns || [];
  const positions = [
    [47, 58], [30, 34], [66, 34], [70, 68], [26, 70],
    [50, 24], [78, 50], [18, 50], [58, 80], [38, 82],
  ];
  const max = Math.max(...concerns.map((item) => item.mentions), 1);
  document.getElementById("concernLegend").innerHTML = concerns.map((item, index) => `
    <span class="legend-item"><i class="legend-dot" style="background:${concernColors[index % concernColors.length]}"></i>${item.name}</span>
  `).join("");
  document.getElementById("concernWordCloud").innerHTML = concerns.map((item, index) => {
    const size = 18 + (item.mentions / max) * 40;
    const pos = positions[index % positions.length];
    return `
      <span class="cloud-word" style="left:${pos[0]}%;top:${pos[1]}%;font-size:${size}px;color:${concernColors[index % concernColors.length]}" title="${item.mentions} 条 · ${item.avgRating} 分">
        ${item.name}
      </span>
    `;
  }).join("");
  document.getElementById("concernCards").innerHTML = concerns.map((item, index) => `
    <article class="concern-card">
      <div class="concern-card-head">
        <div class="concern-name">${item.name}</div>
        <span class="pill" style="color:${concernColors[index % concernColors.length]};background:rgba(22,119,255,.08)">${item.mentions} 条</span>
      </div>
      <div class="tag-metrics">
        <div><strong>${item.avgRating}</strong><span>均分</span></div>
        <div><strong>${pct(item.share)}</strong><span>占比</span></div>
        <div><strong>${pct(item.negativeShare)}</strong><span>负向</span></div>
      </div>
      <div class="concern-desc">${item.description}</div>
      <div class="keyword-line">${item.keywords.join(" / ")}</div>
    </article>
  `).join("");
}

function renderBuyerSegments() {
  renderBuyerLegend("buyerLegend");
  renderBuyerLegend("buyerTrendLegend");
  renderBuyerCloud();
  renderBuyerTrend();
  renderBuyerCards();
}

function renderScenes() {
  const maxMentions = Math.max(...data.scenes.map((scene) => scene.mentions), 1);
  document.getElementById("sceneChart").innerHTML = data.scenes.map((scene) => `
    <div class="scene-meter">
      <div class="bar-label" title="${scene.name}">${scene.name}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(3, scene.mentions / maxMentions * 100)}%;background:var(--green)"></div></div>
      <div class="bar-value">${scene.mentions}</div>
    </div>
  `).join("");

  document.getElementById("sceneList").innerHTML = data.scenes.map((scene) => `
    <article class="scene-card">
      <div class="scene-card-head">
        <div class="scene-title">${scene.name}</div>
        <span class="pill">${scene.mentions} 条 · ${scene.avgRating} 分</span>
      </div>
      <div class="scene-body">${scene.takeaway}</div>
      <div class="product-tags">${scene.topTags.map((tag) => `<span class="tag-chip">${tag}</span>`).join("")}</div>
      <div class="scene-actions"><strong>场景打法：</strong>${scene.strategy}</div>
      <div class="evidence-mini">${scene.evidence.map((item) => `“${item.text}”`).join("<br />")}</div>
    </article>
  `).join("");

  document.getElementById("sceneTrendLegend").innerHTML = data.scenes.map((scene, index) => `
    <span class="legend-item"><i class="legend-dot" style="background:${sceneColors[index % sceneColors.length]}"></i>${scene.name}</span>
  `).join("");
  renderLineTrend("sceneTrendChart", data.sceneTrend, data.scenes.map((scene) => scene.name), sceneColors, "使用场景趋势图");
}

function renderUnmetNeeds() {
  document.getElementById("unmetGrid").innerHTML = data.unmetNeeds.map((need) => `
    <article class="unmet-card">
      <div class="unmet-card-head">
        <div class="unmet-title">${need.name}</div>
        <span class="pill danger">负向 ${need.negativeCount} / ${need.mentions}</span>
      </div>
      <div class="tag-metrics">
        <div><strong>${need.avgRating}</strong><span>相关均分</span></div>
        <div><strong>${pct(need.severity)}</strong><span>负向占比</span></div>
        <div><strong>${need.affectedProducts.length}</strong><span>重点产品</span></div>
      </div>
      <div class="unmet-body"><strong>需求缺口：</strong>${need.root}</div>
      <div class="unmet-actions"><strong>改进方向：</strong>${need.action}</div>
      <div class="evidence-mini">${need.evidence.map((item) => `${short(item.product, 34)}： “${item.text}”`).join("<br />")}</div>
    </article>
  `).join("");
}

function renderProducts() {
  document.getElementById("productList").innerHTML = data.products.slice(0, 10).map((product) => `
    <div class="product-row">
      ${product.image ? `<img class="product-thumb" src="${product.image}" alt="${product.name}" />` : `<div class="product-thumb"></div>`}
      <div>
        <div class="product-name" title="${product.name}">${short(product.name, 58)}</div>
        <div class="product-tags">${product.dominantTags.map((tag) => `<span class="tag-chip">${tag}</span>`).join("")}</div>
      </div>
      <div class="product-score">
        <strong>${product.avgRating.toFixed(2)}</strong>
        <span>${product.reviewCount} 条</span>
      </div>
    </div>
  `).join("");
}

function renderHeatmap() {
  const tags = data.tags.slice(0, 8).map((tag) => tag.name);
  const head = `<div class="heat-row"><div class="heat-label">产品</div>${tags.map((tag) => `<div class="heat-label">${tag}</div>`).join("")}</div>`;
  const rows = data.heatmap.map((row) => `
    <div class="heat-row">
      <div class="heat-label" title="${row.product}">${short(row.product, 22)}</div>
      ${tags.map((tag) => {
        const value = row.tags[tag] || 0;
        const alpha = Math.min(0.88, 0.08 + value * 1.2);
        return `<div class="heat-cell" style="background:rgba(22,119,255,${alpha})">${pct(value)}</div>`;
      }).join("")}
    </div>
  `).join("");
  document.getElementById("heatmap").innerHTML = head + rows;
}

function renderPriceFunctionHeatmap() {
  const payload = data.priceFunction;
  if (!payload) return;
  document.getElementById("priceFunctionNote").textContent = payload.note;
  const columns = payload.columns;
  const maxValue = Math.max(...payload.rows.flatMap((row) => row.cells.map((cell) => cell.value)), 0.01);
  const header = `
    <div class="price-heat-row">
      <div class="price-heat-head">价格段($)</div>
      ${columns.map((col) => `<div class="price-heat-head">${col}</div>`).join("")}
    </div>
  `;
  const rows = payload.rows.map((row) => `
    <div class="price-heat-row">
      <div class="price-heat-band">${row.priceBand}<br /><span class="card-desc">${row.reviewCount}条</span></div>
      ${row.cells.map((cell) => {
        const alpha = 0.12 + (cell.value / maxValue) * 0.72;
        const satisfactionColor = cell.satisfaction >= 0.6 ? "#15803d" : "#d92d20";
        const countColor = cell.value / maxValue > 0.68 ? "rgba(255,255,255,.78)" : "rgba(16,24,40,.62)";
        return `
          <div class="price-heat-cell" style="background:rgba(22,119,255,${alpha});color:${satisfactionColor}" title="${row.priceBand} · ${cell.name} · 提及${pct(cell.value)} · 满意度${pct(cell.satisfaction)} · ${cell.positiveCount}/${cell.count}条正向">
            ${pct(cell.satisfaction)}
            <small style="color:${countColor}">提及${pct(cell.value)} · ${cell.count}条</small>
          </div>
        `;
      }).join("")}
    </div>
  `).join("");
  document.getElementById("priceFunctionHeatmap").innerHTML = header + rows;

  const bandCounts = {};
  payload.productBands.forEach((item) => {
    bandCounts[item.priceBand] = (bandCounts[item.priceBand] || 0) + 1;
  });
  document.getElementById("priceBandList").innerHTML = Object.entries(bandCounts).map(([band, count]) => `
    <span class="tag-chip">${band}：${count}个产品</span>
  `).join("");
}

function renderOpportunities() {
  const head = `<div class="opp-row head"><div>优先级</div><div>标签</div><div>行动建议</div><div>跟踪指标</div></div>`;
  const rows = data.opportunities.map((item) => `
    <div class="opp-row">
      <div><span class="priority ${item.priority}">${item.priority}</span></div>
      <div><strong>${item.tag}</strong></div>
      <div>${item.action}</div>
      <div class="card-desc">${item.metric}</div>
    </div>
  `).join("");
  document.getElementById("opportunityTable").innerHTML = head + rows;
}

document.querySelectorAll("[data-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-filter]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    taxonomyCards(button.dataset.filter);
  });
});

document.querySelectorAll("[data-buyer-view]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-buyer-view]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.getElementById("buyerCloudView").classList.toggle("active", button.dataset.buyerView === "cloud");
    document.getElementById("buyerTrendView").classList.toggle("active", button.dataset.buyerView === "trend");
  });
});

document.querySelectorAll("[data-scene-view]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-scene-view]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.getElementById("sceneVolumeView").classList.toggle("active", button.dataset.sceneView === "volume");
    document.getElementById("sceneTrendView").classList.toggle("active", button.dataset.sceneView === "trend");
  });
});

const sections = [...document.querySelectorAll("main section[id]")];
const navLinks = [...document.querySelectorAll(".side-nav a")];
const observer = new IntersectionObserver((entries) => {
  const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  navLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`));
}, { rootMargin: "-20% 0px -65% 0px", threshold: [0.1, 0.25, 0.5] });
sections.forEach((section) => observer.observe(section));

renderKpis();
renderCharts();
taxonomyCards();
renderPurchaseConcerns();
renderBuyerSegments();
renderScenes();
renderUnmetNeeds();
renderInsights("painList", data.pain);
renderInsights("delightList", data.delight);
renderProducts();
renderHeatmap();
renderPriceFunctionHeatmap();
renderOpportunities();
