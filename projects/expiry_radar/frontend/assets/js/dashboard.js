(function() {
  var currentUser = null;
  var editingId = null;
  var selectedYear = null;
  var yearMenuStart = null;
  var categoryOptions = [];
  var currentFilters = { search: '', status: '', billing_cycle: '', category: '' };
  var els = {
    summaryGrid: document.getElementById('summaryGrid'),
    barChart: document.getElementById('barChart'),
    categoryBreakdown: document.getElementById('categoryBreakdown'),
    resourceGrid: document.getElementById('resourceGrid'),
    notificationList: document.getElementById('notificationList'),
    currentUser: document.getElementById('currentUser'),
    passwordBanner: document.getElementById('passwordBanner'),
    adminLink: document.getElementById('adminLink'),
    searchInput: document.getElementById('searchInput'),
    statusFilter: document.getElementById('statusFilter'),
    cycleFilter: document.getElementById('cycleFilter'),
    categoryFilter: document.getElementById('categoryFilter'),
    statsYearLabel: document.getElementById('statsYearLabel'),
    yearControl: document.getElementById('yearControl'),
    yearPickerBtn: document.getElementById('yearPickerBtn'),
    yearPickerMenu: document.getElementById('yearPickerMenu'),
    modal: document.getElementById('resourceModal'),
    modalTitle: document.getElementById('resourceModalTitle'),
    modalTag: document.getElementById('resourceModalTag'),
    resourceError: document.getElementById('resourceError')
  };

  var form = {
    name: document.getElementById('resourceName'),
    provider: document.getElementById('resourceProvider'),
    category: document.getElementById('resourceCategory'),
    amount: document.getElementById('resourceAmount'),
    type: document.getElementById('resourceType'),
    cycle: document.getElementById('resourceCycle'),
    startDate: document.getElementById('resourceStartDate'),
    dueDate: document.getElementById('resourceDueDate'),
    autoRenew: document.getElementById('resourceAutoRenew'),
    stopped: document.getElementById('resourceStopped'),
    offsets: document.getElementById('resourceNotifyOffsets'),
    note: document.getElementById('resourceNote'),
    saveBtn: document.getElementById('saveResourceBtn')
  };

  function renderUser(user) {
    els.currentUser.textContent = user.username + ' / ' + (user.role === 'admin' ? '管理员' : '用户');
    if (user.role === 'admin') {
      els.adminLink.classList.remove('hidden');
    }
    if (user.must_change_password) {
      els.passwordBanner.classList.remove('hidden');
    }
  }

  function renderSummary(summary) {
    var cards = [
      { label: '活跃资源', value: summary.active_count },
      { label: '已停用', value: summary.stopped_count },
      { label: '7 天内到期', value: summary.due_soon_count },
      { label: '本月预计支出', value: expiryApp.formatMoney(summary.current_month_spend) },
      { label: '年度预计支出', value: expiryApp.formatMoney(summary.yearly_spend) },
      { label: '未读提醒', value: summary.unread_notifications }
    ];
    els.summaryGrid.innerHTML = cards.map(function(item) {
      return '<article class="expiry-summary-card">' +
        '<div class="expiry-summary-label">' + item.label + '</div>' +
        '<div class="expiry-summary-value">' + item.value + '</div>' +
      '</article>';
    }).join('');
  }

  function formatChartValue(value) {
    var num = Number(value || 0);
    if (num === 0) return '¥0';
    if (Math.abs(num) >= 1000) {
      return '¥' + (num / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
    }
    if (Math.abs(num) >= 100) {
      return '¥' + Math.round(num);
    }
    return '¥' + num.toFixed(1).replace(/\.0$/, '');
  }

  function renderChart(stats) {
    var max = Math.max.apply(null, stats.month_breakdown.concat([1]));
    els.barChart.innerHTML = stats.month_breakdown.map(function(item, idx) {
      var percent = Math.max(6, Math.round(item / max * 100));
      return '<div class="expiry-bar-item">' +
        '<div class="expiry-bar-column"><div class="expiry-bar-fill" style="height:' + percent + '%"></div></div>' +
        '<div class="expiry-bar-value">' + formatChartValue(item) + '</div>' +
        '<div class="expiry-bar-label">' + (idx + 1) + '月</div>' +
      '</div>';
    }).join('');
  }

  function renderBreakdown(stats) {
    if (!stats.category_breakdown.length) {
      els.categoryBreakdown.innerHTML = '<div class="expiry-empty-inline">还没有可统计的分类数据</div>';
      return;
    }
    var total = stats.category_breakdown.reduce(function(sum, item) { return sum + item.amount; }, 0) || 1;
    els.categoryBreakdown.innerHTML = stats.category_breakdown.map(function(item) {
      var percent = Math.round(item.amount / total * 100);
      return '<div class="expiry-breakdown-item">' +
        '<div class="expiry-breakdown-top"><strong>' + expiryApp.escapeHtml(item.category) + '</strong><span>' + expiryApp.formatMoney(item.amount) + '</span></div>' +
        '<div class="expiry-breakdown-bar"><span style="width:' + percent + '%"></span></div>' +
        '<div class="expiry-breakdown-foot">' + percent + '%</div>' +
      '</div>';
    }).join('');
  }

  function resourceActions(item) {
    var stateBtn = item.manual_status === 'stopped'
      ? '<button class="expiry-btn expiry-btn-light" data-action="resume" data-id="' + item.id + '">恢复</button>'
      : '<button class="expiry-btn expiry-btn-light" data-action="stop" data-id="' + item.id + '">停用</button>';
    return stateBtn +
      '<button class="expiry-btn expiry-btn-ghost" data-action="edit" data-id="' + item.id + '">编辑</button>' +
      '<button class="expiry-btn expiry-btn-danger" data-action="delete" data-id="' + item.id + '">删除</button>';
  }

  function renderResources(items) {
    if (!items.length) {
      els.resourceGrid.innerHTML = '<div class="expiry-empty-state">当前筛选条件下没有资源，试试新增一个 GPT、机场或视频会员。</div>';
      return;
    }
    els.resourceGrid.innerHTML = items.map(function(item) {
      var stateClass = 'state-' + item.state;
      var meta = [
        expiryApp.cycleLabel(item.billing_cycle),
        item.provider || '未填写服务商',
        '到期 ' + expiryApp.formatDate(item.next_due_date)
      ];
      return '<article class="expiry-resource-card">' +
        '<div class="expiry-resource-top">' +
          '<div><div class="expiry-resource-title">' + expiryApp.escapeHtml(item.name) + '</div>' +
          '<div class="expiry-resource-meta">' + meta.map(expiryApp.escapeHtml).join(' · ') + '</div></div>' +
          '<span class="expiry-state-pill ' + stateClass + '">' + expiryApp.statusLabel(item.state) + '</span>' +
        '</div>' +
        '<div class="expiry-resource-stats">' +
          '<div><span>分类</span><strong>' + expiryApp.escapeHtml(item.category) + '</strong></div>' +
          '<div><span>金额</span><strong>' + expiryApp.formatMoney(item.amount) + '</strong></div>' +
          '<div><span>提醒</span><strong>' + item.effective_notify_offsets.join(' / ') + ' 天</strong></div>' +
        '</div>' +
        '<div class="expiry-resource-foot">' +
          '<div class="expiry-muted-line">' + (item.days_left === null ? '未设日期' : (item.days_left < 0 ? '已过期 ' + Math.abs(item.days_left) + ' 天' : '距到期 ' + item.days_left + ' 天')) + '</div>' +
          '<div class="expiry-action-row">' + resourceActions(item) + '</div>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  function renderNotifications(items) {
    if (!items.length) {
      els.notificationList.innerHTML = '<div class="expiry-empty-inline">今天没有新的站内提醒</div>';
      return;
    }
    els.notificationList.innerHTML = items.map(function(item) {
      var btn = item.channel === 'site' && item.status === 'pending'
        ? '<button class="expiry-btn expiry-btn-light" data-read="' + item.id + '">标记已读</button>'
        : '';
      return '<article class="expiry-notice-card">' +
        '<div class="expiry-notice-top"><strong>' + expiryApp.escapeHtml(item.resource_name || '资源提醒') + '</strong>' +
        '<span>' + expiryApp.escapeHtml(item.channel === 'email' ? '邮件' : '站内') + '</span></div>' +
        '<p>' + expiryApp.escapeHtml(item.message) + '</p>' +
        '<div class="expiry-notice-foot"><span>' + expiryApp.escapeHtml(item.scheduled_for) + '</span>' + btn + '</div>' +
      '</article>';
    }).join('');
  }

  function fillCategoryFilter(categories) {
    categoryOptions = categories || [];
    els.categoryFilter.innerHTML = '<option value="">全部分类</option>' + categoryOptions.map(function(item) {
      return '<option value="' + expiryApp.escapeHtml(item) + '">' + expiryApp.escapeHtml(item) + '</option>';
    }).join('');
    if (currentFilters.category) els.categoryFilter.value = currentFilters.category;
  }

  function renderYearMenu() {
    if (selectedYear === null) return;
    if (yearMenuStart === null) yearMenuStart = selectedYear - 5;
    var options = '';
    for (var y = yearMenuStart; y < yearMenuStart + 12; y++) {
      options += '<button type="button" class="expiry-year-option' + (y === selectedYear ? ' active' : '') + '" data-year="' + y + '">' + y + '年</button>';
    }
    els.yearPickerMenu.innerHTML =
      '<div class="expiry-year-menu-head">' +
        '<button type="button" class="expiry-year-nav" data-shift="-6">上一段</button>' +
        '<button type="button" class="expiry-year-nav" data-shift="6">下一段</button>' +
      '</div>' +
      '<div class="expiry-year-grid">' + options + '</div>';
  }

  function closeYearMenu() {
    els.yearPickerMenu.classList.add('hidden');
  }

  function openYearMenu() {
    renderYearMenu();
    els.yearPickerMenu.classList.remove('hidden');
  }

  function syncYearLabel(year) {
    selectedYear = year;
    els.statsYearLabel.textContent = year + ' 年';
    if (yearMenuStart === null || year < yearMenuStart || year >= yearMenuStart + 12) {
      yearMenuStart = year - 5;
    }
    renderYearMenu();
  }

  function refreshYearStats() {
    if (selectedYear === null) return Promise.resolve();
    return expiryApp.api.getStats(selectedYear).then(function(stats) {
      syncYearLabel(stats.year);
      renderChart(stats);
      renderBreakdown(stats);
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  }

  function openModal(item) {
    editingId = item ? item.id : null;
    els.resourceError.textContent = '';
    els.resourceError.classList.remove('show');
    els.modal.classList.remove('hidden');
    els.modalTitle.textContent = item ? '编辑资源' : '新增资源';
    els.modalTag.textContent = item ? 'Edit' : 'Create';
    form.name.value = item ? item.name : '';
    form.provider.value = item ? item.provider : '';
    form.category.value = item ? item.category : '';
    form.amount.value = item ? item.amount : '';
    form.type.value = item ? item.resource_type : 'subscription';
    form.cycle.value = item ? item.billing_cycle : 'monthly';
    form.startDate.value = item ? item.start_date : '';
    form.dueDate.value = item ? item.next_due_date : '';
    form.autoRenew.checked = !!(item && item.auto_renew);
    form.stopped.checked = !!(item && item.manual_status === 'stopped');
    form.offsets.value = item ? item.effective_notify_offsets.join(',') : '30,7,1';
    form.note.value = item ? item.note : '';
  }

  function resourcePayload() {
    return {
      name: form.name.value.trim(),
      provider: form.provider.value.trim(),
      category: form.category.value.trim(),
      amount: form.amount.value,
      resource_type: form.type.value,
      billing_cycle: form.type.value === 'one_time' ? 'none' : form.cycle.value,
      start_date: form.startDate.value,
      next_due_date: form.dueDate.value,
      auto_renew: form.autoRenew.checked,
      manual_status: form.stopped.checked ? 'stopped' : 'active',
      notify_offsets: form.offsets.value.trim(),
      note: form.note.value.trim()
    };
  }

  function refreshResources() {
    currentFilters.search = els.searchInput.value.trim();
    currentFilters.status = els.statusFilter.value;
    currentFilters.billing_cycle = els.cycleFilter.value;
    currentFilters.category = els.categoryFilter.value;
    expiryApp.api.getResources(currentFilters).then(function(data) {
      fillCategoryFilter(data.categories);
      renderResources(data.items);
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  }

  function refreshDashboard() {
    return expiryApp.api.getDashboard().then(function(data) {
      renderSummary(data.summary);
      renderNotifications(data.notifications);
      renderResources(data.resources);
      if (selectedYear === null) {
        syncYearLabel(data.stats.year);
        renderChart(data.stats);
        renderBreakdown(data.stats);
      } else if (selectedYear === data.stats.year) {
        syncYearLabel(data.stats.year);
        renderChart(data.stats);
        renderBreakdown(data.stats);
      } else {
        refreshYearStats();
      }
      fillCategoryFilter((data.resources || []).map(function(item) { return item.category; }).filter(function(item, idx, arr) {
        return item && arr.indexOf(item) === idx;
      }).sort());
    });
  }

  function bindActions() {
    els.resourceGrid.addEventListener('click', function(event) {
      var btn = event.target.closest('button[data-action]');
      if (!btn) return;
      var id = btn.getAttribute('data-id');
      var action = btn.getAttribute('data-action');
      if (action === 'edit') {
        expiryApp.api.getResource(id).then(openModal).catch(function(err) {
          expiryApp.showToast(err.message);
        });
        return;
      }
      if (action === 'delete') {
        if (!window.confirm('确定删除这个资源吗？')) return;
        expiryApp.api.deleteResource(id).then(function() {
          expiryApp.showToast('资源已删除');
          refreshDashboard();
        }).catch(function(err) {
          expiryApp.showToast(err.message);
        });
        return;
      }
      var req = action === 'stop' ? expiryApp.api.stopResource(id) : expiryApp.api.resumeResource(id);
      req.then(function() {
        expiryApp.showToast(action === 'stop' ? '资源已停用' : '资源已恢复');
        refreshDashboard();
      }).catch(function(err) {
        expiryApp.showToast(err.message);
      });
    });

    els.notificationList.addEventListener('click', function(event) {
      var btn = event.target.closest('button[data-read]');
      if (!btn) return;
      expiryApp.api.readNotification(btn.getAttribute('data-read')).then(function() {
        refreshDashboard();
      }).catch(function(err) {
        expiryApp.showToast(err.message);
      });
    });

    els.yearPickerBtn.addEventListener('click', function(event) {
      event.stopPropagation();
      if (els.yearPickerMenu.classList.contains('hidden')) {
        openYearMenu();
      } else {
        closeYearMenu();
      }
    });

    els.yearPickerMenu.addEventListener('click', function(event) {
      var shiftBtn = event.target.closest('[data-shift]');
      if (shiftBtn) {
        yearMenuStart += Number(shiftBtn.getAttribute('data-shift')) || 0;
        renderYearMenu();
        return;
      }
      var yearBtn = event.target.closest('[data-year]');
      if (!yearBtn) return;
      selectedYear = Number(yearBtn.getAttribute('data-year'));
      closeYearMenu();
      refreshYearStats();
    });

    document.addEventListener('click', function(event) {
      if (!els.yearControl.contains(event.target)) {
        closeYearMenu();
      }
    });
  }

  document.getElementById('openResourceBtn').addEventListener('click', function() {
    openModal(null);
  });
  document.getElementById('logoutBtn').addEventListener('click', expiryApp.logout);
  form.type.addEventListener('change', function() {
    form.cycle.value = form.type.value === 'one_time' ? 'none' : 'monthly';
  });
  form.saveBtn.addEventListener('click', function() {
    form.saveBtn.disabled = true;
    var payload = resourcePayload();
    var action = editingId ? expiryApp.api.updateResource(editingId, payload) : expiryApp.api.createResource(payload);
    action.then(function() {
      expiryApp.showToast(editingId ? '资源已更新' : '资源已创建');
      document.getElementById('resourceModal').classList.add('hidden');
      refreshDashboard();
    }).catch(function(err) {
      els.resourceError.textContent = err.message;
      els.resourceError.classList.add('show');
    }).finally(function() {
      form.saveBtn.disabled = false;
    });
  });

  ['input', 'change'].forEach(function(eventName) {
    els.searchInput.addEventListener(eventName, refreshResources);
    els.statusFilter.addEventListener(eventName, refreshResources);
    els.cycleFilter.addEventListener(eventName, refreshResources);
    els.categoryFilter.addEventListener(eventName, refreshResources);
  });

  expiryApp.bindModalClose();
  bindActions();

  expiryApp.ensureAuth().then(function(user) {
    currentUser = user;
    renderUser(user);
    return refreshDashboard();
  }).catch(function(err) {
    if (err && err.message) expiryApp.showToast(err.message);
  });
})();
