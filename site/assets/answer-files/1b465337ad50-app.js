/**
 * 项目状态仪表盘 —— 交互逻辑
 * 零依赖原生 JS。状态管理遵循 SKILL.md：本地 UI 状态用最简方案，
 * 筛选条件同步到 URL（searchParams），便于分享与刷新保持。
 */
(function () {
  'use strict';

  /* =========================================================
   * 模拟数据（本地，无外部账号/接口依赖）
   * ========================================================= */
  var STATUS_LABELS = {
    active: '进行中',
    'at-risk': '有风险',
    'on-hold': '已暂停',
    completed: '已完成'
  };

  var PRIORITY_LABELS = {
    high: '高',
    medium: '中',
    low: '低'
  };

  var mockProjects = [
    {
      id: 1,
      name: '用户增长平台重构',
      description: '统一拉新与留存链路，替换旧版埋点体系',
      owner: '张伟',
      status: 'active',
      priority: 'high',
      dueDate: '2026-09-15',
      progress: 62
    },
    {
      id: 2,
      name: '支付网关迁移',
      description: '从自建网关迁移到统一支付中台',
      owner: '李娜',
      status: 'at-risk',
      priority: 'high',
      dueDate: '2026-08-20',
      progress: 45
    },
    {
      id: 3,
      name: '移动端性能优化',
      description: '首屏加载时间降至 1.5 秒以内',
      owner: '王强',
      status: 'active',
      priority: 'medium',
      dueDate: '2026-10-01',
      progress: 78
    },
    {
      id: 4,
      name: '数据看板权限改造',
      description: '引入细粒度行列级权限控制',
      owner: '赵敏',
      status: 'on-hold',
      priority: 'low',
      dueDate: '2026-11-30',
      progress: 30
    },
    {
      id: 5,
      name: '客服工单系统 V2',
      description: '支持自动分派与 SLA 监控',
      owner: '陈晨',
      status: 'completed',
      priority: 'medium',
      dueDate: '2026-07-25',
      progress: 100
    },
    {
      id: 6,
      name: '搜索召回算法升级',
      description: '引入向量召回，提升长尾查询命中率',
      owner: '刘洋',
      status: 'active',
      priority: 'high',
      dueDate: '2026-09-30',
      progress: 55
    },
    {
      id: 7,
      name: '合规审计日志归档',
      description: '满足监管要求的日志留存与检索',
      owner: '孙磊',
      status: 'at-risk',
      priority: 'high',
      dueDate: '2026-08-10',
      progress: 35
    },
    {
      id: 8,
      name: '内部知识库改版',
      description: '统一文档入口与全文检索',
      owner: '周婷',
      status: 'on-hold',
      priority: 'low',
      dueDate: '2026-12-15',
      progress: 15
    },
    {
      id: 9,
      name: '消息推送平台',
      description: '整合 App Push、短信、站内信通道',
      owner: '吴昊',
      status: 'completed',
      priority: 'medium',
      dueDate: '2026-06-30',
      progress: 100
    },
    {
      id: 10,
      name: '开放平台 API 网关',
      description: '第三方接入鉴权、限流与计量',
      owner: '郑凯',
      status: 'active',
      priority: 'medium',
      dueDate: '2026-10-20',
      progress: 40
    },
    {
      id: 11,
      name: '财务对账自动化',
      description: 'T+1 自动对账与差异告警',
      owner: '黄丽',
      status: 'active',
      priority: 'high',
      dueDate: '2026-09-05',
      progress: 70
    },
    {
      id: 12,
      name: '旧版 CRM 下线',
      description: '数据迁移完成后停用旧系统',
      owner: '林涛',
      status: 'completed',
      priority: 'low',
      dueDate: '2026-07-10',
      progress: 100
    }
  ];

  /* =========================================================
   * DOM 引用
   * ========================================================= */
  var els = {
    search: document.getElementById('search-input'),
    statusFilter: document.getElementById('status-filter'),
    priorityFilter: document.getElementById('priority-filter'),
    clearBtn: document.getElementById('clear-filters'),
    emptyClearBtn: document.getElementById('empty-clear-filters'),
    tbody: document.getElementById('project-tbody'),
    tableWrap: document.getElementById('table-wrap'),
    emptyState: document.getElementById('empty-state'),
    loadingState: document.getElementById('loading-state'),
    resultsCount: document.getElementById('results-count')
  };

  /* =========================================================
   * 工具函数
   * ========================================================= */
  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function formatDate(dateStr) {
    var parts = dateStr.split('-');
    return parts[0] + '年' + parseInt(parts[1], 10) + '月' + parseInt(parts[2], 10) + '日';
  }

  function isOverdue(dateStr, status) {
    if (status === 'completed') return false;
    var due = new Date(dateStr + 'T00:00:00');
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    return due < today;
  }

  function getFiltersFromUrl() {
    var params = new URLSearchParams(window.location.search);
    return {
      q: params.get('q') || '',
      status: params.get('status') || 'all',
      priority: params.get('priority') || 'all'
    };
  }

  function syncFiltersToUrl(filters) {
    var params = new URLSearchParams();
    if (filters.q) params.set('q', filters.q);
    if (filters.status && filters.status !== 'all') params.set('status', filters.status);
    if (filters.priority && filters.priority !== 'all') params.set('priority', filters.priority);
    var query = params.toString();
    var newUrl = window.location.pathname + (query ? '?' + query : '');
    window.history.replaceState(null, '', newUrl);
  }

  /* =========================================================
   * 筛选逻辑
   * ========================================================= */
  function getCurrentFilters() {
    return {
      q: els.search.value.trim().toLowerCase(),
      status: els.statusFilter.value,
      priority: els.priorityFilter.value
    };
  }

  function applyFilters(projects, filters) {
    return projects.filter(function (p) {
      var matchesQuery =
        !filters.q ||
        p.name.toLowerCase().indexOf(filters.q) !== -1 ||
        p.owner.toLowerCase().indexOf(filters.q) !== -1;
      var matchesStatus = filters.status === 'all' || p.status === filters.status;
      var matchesPriority = filters.priority === 'all' || p.priority === filters.priority;
      return matchesQuery && matchesStatus && matchesPriority;
    });
  }

  /* =========================================================
   * 渲染：状态卡片
   * ========================================================= */
  function renderStats(projects) {
    var counts = { total: projects.length, active: 0, 'at-risk': 0, 'on-hold': 0, completed: 0 };
    projects.forEach(function (p) {
      counts[p.status] = (counts[p.status] || 0) + 1;
    });
    Object.keys(counts).forEach(function (key) {
      var el = document.querySelector('[data-stat="' + key + '"]');
      if (el) el.textContent = counts[key];
    });
  }

  /* =========================================================
   * 渲染：表格行
   * ========================================================= */
  function renderTable(projects) {
    if (projects.length === 0) {
      els.tableWrap.hidden = true;
      els.emptyState.hidden = false;
      els.resultsCount.textContent = '共 0 个项目';
      return;
    }

    els.emptyState.hidden = true;
    els.tableWrap.hidden = false;

    var html = projects
      .map(function (p) {
        var statusLabel = STATUS_LABELS[p.status];
        var priorityLabel = PRIORITY_LABELS[p.priority];
        var overdue = isOverdue(p.dueDate, p.status);
        var dateCell = overdue
          ? '<span class="date-overdue">' + formatDate(p.dueDate) + '（已逾期）</span>'
          : escapeHtml(formatDate(p.dueDate));

        return (
          '<tr>' +
          '<td class="project-cell" data-label="项目名称">' +
          '<span class="project-name">' + escapeHtml(p.name) + '</span>' +
          '<span class="project-desc">' + escapeHtml(p.description) + '</span>' +
          '</td>' +
          '<td data-label="负责人">' + escapeHtml(p.owner) + '</td>' +
          '<td data-label="状态">' +
          '<span class="badge badge--' + p.status + '">' +
          '<span class="status-dot" aria-hidden="true"></span>' +
          escapeHtml(statusLabel) +
          '</span>' +
          '</td>' +
          '<td data-label="优先级">' +
          '<span class="badge badge--priority-' + p.priority + '">' + escapeHtml(priorityLabel) + '</span>' +
          '</td>' +
          '<td data-label="截止日期" class="data-table__col-date">' + dateCell + '</td>' +
          '<td data-label="进度">' +
          '<span class="progress" role="group" aria-label="进度 ' + p.progress + '%">' +
          '<span class="progress__bar">' +
          '<span class="progress__fill progress__fill--' + p.status + '" style="width:' + p.progress + '%"></span>' +
          '</span>' +
          '<span class="progress__value">' + p.progress + '%</span>' +
          '</span>' +
          '</td>' +
          '</tr>'
        );
      })
      .join('');

    els.tbody.innerHTML = html;
    els.resultsCount.textContent = '共 ' + projects.length + ' 个项目';
  }

  /* =========================================================
   * 主渲染流程
   * ========================================================= */
  function render() {
    var filters = getCurrentFilters();
    syncFiltersToUrl(filters);

    var filtered = applyFilters(mockProjects, filters);
    renderStats(filtered);
    renderTable(filtered);

    var hasActiveFilter =
      filters.q !== '' || filters.status !== 'all' || filters.priority !== 'all';
    els.clearBtn.hidden = !hasActiveFilter;
  }

  function resetFilters() {
    els.search.value = '';
    els.statusFilter.value = 'all';
    els.priorityFilter.value = 'all';
    render();
    els.search.focus();
  }

  /* =========================================================
   * 模拟异步加载（展示骨架屏）
   * ========================================================= */
  function loadProjects() {
    els.loadingState.hidden = false;
    els.tableWrap.hidden = true;
    els.emptyState.hidden = true;

    // 模拟网络延迟，无真实外部请求
    setTimeout(function () {
      els.loadingState.hidden = true;
      render();
    }, 600);
  }

  /* =========================================================
   * 初始化：从 URL 恢复筛选状态 + 绑定事件
   * ========================================================= */
  function init() {
    var saved = getFiltersFromUrl();
    els.search.value = saved.q;
    if (saved.status) els.statusFilter.value = saved.status;
    if (saved.priority) els.priorityFilter.value = saved.priority;

    els.search.addEventListener('input', render);
    els.statusFilter.addEventListener('change', render);
    els.priorityFilter.addEventListener('change', render);
    els.clearBtn.addEventListener('click', resetFilters);
    els.emptyClearBtn.addEventListener('click', resetFilters);

    loadProjects();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
