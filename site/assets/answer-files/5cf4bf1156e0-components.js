/**
 * UI 组件渲染函数
 * 所有函数返回 HTML 字符串，由 app.js 注入到视图容器。
 */
(function (global) {
  "use strict";

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
  }

  // 骨架屏：产品卡片网格
  function skeletonGrid(count) {
    const n = count || 6;
    let html = '<div class="product-grid" aria-hidden="true">';
    for (let i = 0; i < n; i++) {
      html += `
        <div class="skeleton-card">
          <div class="skeleton skeleton-card__media"></div>
          <div class="skeleton-card__body">
            <div class="skeleton skeleton-line skeleton-line--lg"></div>
            <div class="skeleton skeleton-line"></div>
            <div class="skeleton skeleton-line"></div>
            <div class="skeleton skeleton-line skeleton-line--sm"></div>
          </div>
        </div>`;
    }
    html += "</div>";
    return html;
  }

  // 骨架屏：表格行
  function skeletonTableRows(count) {
    const n = count || 5;
    let html = "";
    for (let i = 0; i < n; i++) {
      html += `
        <tr class="skeleton-row">
          <td><div class="skeleton" style="width:80%"></div></td>
          <td><div class="skeleton" style="width:60%"></div></td>
          <td><div class="skeleton" style="width:40%"></div></td>
          <td><div class="skeleton" style="width:50%"></div></td>
          <td><div class="skeleton" style="width:70%"></div></td>
        </tr>`;
    }
    return html;
  }

  // 空状态
  function emptyState(opts) {
    const o = opts || {};
    return `
      <div class="empty-state" role="status">
        <div class="empty-state__icon" aria-hidden="true">${o.icon || "📭"}</div>
        <h3 class="empty-state__title">${escapeHtml(o.title || "暂无数据")}</h3>
        <p class="empty-state__desc">${escapeHtml(o.desc || "没有找到符合条件的内容")}</p>
        ${o.action ? o.action : ""}
      </div>`;
  }

  // 错误状态
  function errorState(opts) {
    const o = opts || {};
    return `
      <div class="error-state" role="alert">
        <div class="error-state__icon" aria-hidden="true">⚠️</div>
        <h3 class="error-state__title">${escapeHtml(o.title || "加载失败")}</h3>
        <p class="error-state__desc">${escapeHtml(o.desc || "请稍后重试")}</p>
        ${
          o.retry !== false
            ? `<button class="btn btn--primary" data-action="retry" type="button">重新加载</button>`
            : ""
        }
      </div>`;
  }

  // 慢网络横幅
  function slowNetworkBanner(text) {
    return `
      <div class="slow-network-banner" role="status">
        <span class="slow-network-banner__spinner" aria-hidden="true"></span>
        <span>${escapeHtml(text || "网络较慢，正在努力加载…")}</span>
      </div>`;
  }

  // 产品卡片
  function productCard(product) {
    const statusMap = {
      hot: { cls: "product-card__tag--hot", text: "热销" },
      new: { cls: "product-card__tag--new", text: "新品" },
      normal: null,
    };
    const tag = statusMap[product.status];
    const stockText =
      product.stock === 0
        ? '<span class="product-card__tag" style="background:#fef2f2;color:#991b1b">缺货</span>'
        : product.stock < 10
        ? '<span class="product-card__tag" style="background:#fffbeb;color:#92400e">仅剩 ' + product.stock + " 件</span>"
        : "";
    return `
      <article class="product-card">
        <div class="product-card__media" aria-hidden="true">${product.icon}</div>
        <div class="product-card__body">
          <h3 class="product-card__title">
            <a href="#/products/${product.id}">${escapeHtml(product.name)}</a>
          </h3>
          <p class="product-card__desc">${escapeHtml(product.desc)}</p>
          <div class="product-card__meta">
            <span class="product-card__price">¥${product.price.toLocaleString()}</span>
            <span style="display:inline-flex;gap:0.25rem">
              ${tag ? '<span class="product-card__tag ' + tag.cls + '">' + tag.text + "</span>" : ""}
              ${stockText}
            </span>
          </div>
        </div>
      </article>`;
  }

  // 产品网格
  function productGrid(products) {
    if (!products.length) {
      return emptyState({
        icon: "🔍",
        title: "没有找到匹配的产品",
        desc: "试试更换关键词或调整筛选条件",
        action:
          '<button class="btn btn--secondary" data-action="clear-filters" type="button">清除筛选</button>',
      });
    }
    return (
      '<div class="product-grid">' +
      products.map(productCard).join("") +
      "</div>"
    );
  }

  // 数据表格（桌面）
  function dataTable(products) {
    if (!products.length) {
      return emptyState({
        icon: "🔍",
        title: "没有找到匹配的产品",
        desc: "试试更换关键词或调整筛选条件",
        action:
          '<button class="btn btn--secondary" data-action="clear-filters" type="button">清除筛选</button>',
      });
    }
    const rows = products
      .map(
        (p) => `
        <tr>
          <td data-label="产品"><a href="#/products/${p.id}">${escapeHtml(p.name)}</a></td>
          <td data-label="分类">${escapeHtml(p.category)}</td>
          <td data-label="价格">¥${p.price.toLocaleString()}</td>
          <td data-label="库存">${
            p.stock === 0
              ? '<span style="color:var(--color-danger)">缺货</span>'
              : p.stock
          }</td>
          <td data-label="状态">${
            p.status === "hot"
              ? "热销"
              : p.status === "new"
              ? "新品"
              : "常规"
          }</td>
          <td data-label="操作" class="col-actions">
            <a class="btn btn--ghost" href="#/products/${p.id}">查看</a>
          </td>
        </tr>`
      )
      .join("");

    return `
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">产品</th>
              <th scope="col">分类</th>
              <th scope="col">价格</th>
              <th scope="col">库存</th>
              <th scope="col">状态</th>
              <th scope="col" class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  // 统计卡片
  function statCards(stats) {
    const items = [
      { value: stats.total, label: "产品总数" },
      { value: stats.inStock, label: "在售产品" },
      { value: stats.categories, label: "产品分类" },
      { value: "¥" + stats.avgPrice.toLocaleString(), label: "平均价格" },
    ];
    return (
      '<div class="stats-grid">' +
      items
        .map(
          (item) => `
        <div class="stat-card">
          <div class="stat-card__value">${item.value}</div>
          <div class="stat-card__label">${item.label}</div>
        </div>`
        )
        .join("") +
      "</div>"
    );
  }

  global.Components = {
    escapeHtml,
    skeletonGrid,
    skeletonTableRows,
    emptyState,
    errorState,
    slowNetworkBanner,
    productCard,
    productGrid,
    dataTable,
    statCards,
  };
})(window);
