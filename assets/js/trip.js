(function() {
  checkAuth();

  var tripId = getUrlParam('id');
  if (!tripId) { window.location.href = 'trips.html'; return; }

  var currentTrip = null;

  // DOM 引用
  var tripTitleEl = document.getElementById('tripTitle');
  var tripInfoEl = document.getElementById('tripInfo');
  var statsBarEl = document.getElementById('statsBar');
  var recordCountEl = document.getElementById('recordCount');
  var recordListEl = document.getElementById('recordList');
  var summaryAreaEl = document.getElementById('summaryArea');
  var backBtn = document.getElementById('backBtn');
  var exportBtn = document.getElementById('exportBtn');
  var editTripBtn = document.getElementById('editTripBtn');
  var deleteTripBtn = document.getElementById('deleteTripBtn');
  // 添加记录表单
  var recCategoryEl = document.getElementById('recCategory');
  var recAmountEl = document.getElementById('recAmount');
  var customCatGroup = document.getElementById('customCatGroup');
  var recCustomCatEl = document.getElementById('recCustomCat');
  var recPayerEl = document.getElementById('recPayer');
  var newPayerGroup = document.getElementById('newPayerGroup');
  var recNewPayerEl = document.getElementById('recNewPayer');
  var recDateEl = document.getElementById('recDate');
  var recNoteEl = document.getElementById('recNote');
  var addRecordBtn = document.getElementById('addRecordBtn');
  // 编辑旅行模态
  var editTripModal = document.getElementById('editTripModal');
  var closeEditTrip = document.getElementById('closeEditTrip');
  var editTripNameEl = document.getElementById('editTripName');
  var editTripStartEl = document.getElementById('editTripStart');
  var editTripEndEl = document.getElementById('editTripEnd');
  var editTripNoteEl = document.getElementById('editTripNote');
  var saveEditTripBtn = document.getElementById('saveEditTripBtn');
  // 编辑记录模态
  var editRecordModal = document.getElementById('editRecordModal');
  var closeEditRecord = document.getElementById('closeEditRecord');
  var editRecCategoryEl = document.getElementById('editRecCategory');
  var editCustomCatGroup = document.getElementById('editCustomCatGroup');
  var editRecCustomCatEl = document.getElementById('editRecCustomCat');
  var editRecAmountEl = document.getElementById('editRecAmount');
  var editRecPayerEl = document.getElementById('editRecPayer');
  var editNewPayerGroup = document.getElementById('editNewPayerGroup');
  var editRecNewPayerEl = document.getElementById('editRecNewPayer');
  var editRecDateEl = document.getElementById('editRecDate');
  var editRecNoteEl = document.getElementById('editRecNote');
  var saveEditRecordBtn = document.getElementById('saveEditRecordBtn');

  var editingRecordId = null;

  function normalizeNameList(items) {
    var names = [];
    for (var i = 0; i < (items || []).length; i++) {
      var item = items[i];
      if (typeof item === 'string') {
        names.push(item);
      } else if (item && typeof item === 'object' && item.name) {
        names.push(item.name);
      }
    }
    return names;
  }

  // ===== 填充下拉框 =====
  function fillCategorySelect(sel, categories, selectedVal) {
    var names = normalizeNameList(categories);
    sel.innerHTML = '';
    for (var i = 0; i < names.length; i++) {
      var opt = document.createElement('option');
      opt.value = names[i]; opt.textContent = names[i];
      if (names[i] === selectedVal) opt.selected = true;
      sel.appendChild(opt);
    }
    var customOpt = document.createElement('option');
    customOpt.value = '__custom__'; customOpt.textContent = '+ 自定义类别';
    sel.appendChild(customOpt);
    if (selectedVal && names.indexOf(selectedVal) === -1) {
      var existOpt = document.createElement('option');
      existOpt.value = selectedVal; existOpt.textContent = selectedVal;
      existOpt.selected = true;
      sel.insertBefore(existOpt, customOpt);
    }
  }

  function fillPayerSelect(sel, payers, selectedVal) {
    var names = normalizeNameList(payers);
    sel.innerHTML = '';
    var emptyOpt = document.createElement('option');
    emptyOpt.value = ''; emptyOpt.textContent = '-- 选择支付人 --';
    sel.appendChild(emptyOpt);
    for (var i = 0; i < names.length; i++) {
      var opt = document.createElement('option');
      opt.value = names[i]; opt.textContent = names[i];
      if (names[i] === selectedVal) opt.selected = true;
      sel.appendChild(opt);
    }
    var newOpt = document.createElement('option');
    newOpt.value = '__new__'; newOpt.textContent = '+ 新增支付人';
    sel.appendChild(newOpt);
  }

  // ===== 类别/支付人下拉联动 =====
  recCategoryEl.addEventListener('change', function() {
    customCatGroup.style.display = this.value === '__custom__' ? 'block' : 'none';
  });
  editRecCategoryEl.addEventListener('change', function() {
    editCustomCatGroup.style.display = this.value === '__custom__' ? 'block' : 'none';
  });
  recPayerEl.addEventListener('change', function() {
    newPayerGroup.style.display = this.value === '__new__' ? 'block' : 'none';
  });
  editRecPayerEl.addEventListener('change', function() {
    editNewPayerGroup.style.display = this.value === '__new__' ? 'block' : 'none';
  });

  // ===== 加载全部数据并渲染 =====
  function refresh() {
    Promise.all([
      api.getTrip(tripId),
      api.getPayers(),
      api.getCategories()
    ]).then(function(results) {
      currentTrip = results[0];
      var payers = results[1];
      var categories = results[2];
      if (!currentTrip) { window.location.href = 'trips.html'; return; }
      renderTripInfo();
      renderStats();
      initForm(categories, payers);
      renderRecords();
      renderSummary();
    }).catch(function(err) {
      showToast('加载失败: ' + err.message);
    });
  }

  // ===== 旅行信息 =====
  function renderTripInfo() {
    tripTitleEl.textContent = currentTrip.name;
    var dateStr = '';
    if (currentTrip.start_date) {
      dateStr = '📅 ' + currentTrip.start_date;
      if (currentTrip.end_date && currentTrip.end_date !== currentTrip.start_date)
        dateStr += ' ~ ' + currentTrip.end_date;
    }
    tripInfoEl.innerHTML =
      '<div class="card-title">' + escapeHtml(currentTrip.name) + '</div>' +
      (dateStr ? '<div class="card-meta">' + dateStr + '</div>' : '') +
      (currentTrip.note ? '<div class="card-meta" style="margin-top:4px;">' + escapeHtml(currentTrip.note) + '</div>' : '');
  }

  // ===== 统计栏 =====
  function renderStats() {
    var records = currentTrip.records || [];
    var total = Number(currentTrip.total_amount) || 0;
    var payerCount = Object.keys(currentTrip.by_payer || {}).length;
    statsBarEl.innerHTML =
      '<div class="stat-item"><div class="stat-value">' + records.length + '</div><div class="stat-label">记录数</div></div>' +
      '<div class="stat-item"><div class="stat-value">' + formatMoney(total) + '</div><div class="stat-label">总金额</div></div>' +
      '<div class="stat-item"><div class="stat-value">' + payerCount + '</div><div class="stat-label">参与人</div></div>';
  }

  // ===== 初始化表单 =====
  function initForm(categories, payers) {
    fillCategorySelect(recCategoryEl, categories);
    fillPayerSelect(recPayerEl, payers);
    recDateEl.value = todayStr();
    customCatGroup.style.display = 'none';
    newPayerGroup.style.display = 'none';
  }

  // ===== 添加记录 =====
  addRecordBtn.addEventListener('click', function() {
    var category = recCategoryEl.value;
    if (category === '__custom__') {
      category = recCustomCatEl.value.trim();
      if (!category) { showToast('请输入自定义类别名称'); return; }
    }
    var amount = parseFloat(recAmountEl.value);
    if (!amount || amount <= 0) { showToast('请输入有效金额'); return; }
    var payer = recPayerEl.value;
    if (payer === '__new__') {
      payer = recNewPayerEl.value.trim();
      if (!payer) { showToast('请输入支付人姓名'); return; }
    }
    if (!payer) { showToast('请选择支付人'); return; }

    addRecordBtn.disabled = true;
    api.createRecord(tripId, {
      category: category,
      amount: amount,
      payer: payer,
      date: recDateEl.value || todayStr(),
      note: recNoteEl.value.trim()
    }).then(function() {
      recAmountEl.value = '';
      recCustomCatEl.value = '';
      recNewPayerEl.value = '';
      recNoteEl.value = '';
      customCatGroup.style.display = 'none';
      newPayerGroup.style.display = 'none';
      showToast('添加成功');
      addRecordBtn.disabled = false;
      refresh();
    }).catch(function(err) {
      showToast('添加失败: ' + err.message);
      addRecordBtn.disabled = false;
    });
  });

  // ===== 渲染记录列表 =====
  function renderRecords() {
    var records = currentTrip.records || [];
    recordCountEl.textContent = records.length;
    if (records.length === 0) {
      recordListEl.innerHTML = '<div class="empty-state" style="padding:24px;"><div class="empty-state-icon">📝</div><div class="empty-state-text">暂无记录，请添加</div></div>';
      return;
    }
    var html = '';
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      var cs = getCategoryStyle(r.category);
      html +=
        '<div class="record-item">' +
          '<div class="record-icon ' + cs.cls + '">' + cs.icon + '</div>' +
          '<div class="record-info">' +
            '<div class="record-info-top">' +
              '<span class="record-category">' + escapeHtml(r.category) + '</span>' +
              '<span class="record-amount">' + formatMoney(r.amount) + '</span>' +
            '</div>' +
            '<div class="record-info-bottom">' +
              '<span>' + escapeHtml(r.payer) + '</span>' +
              '<span>' + (r.date || '') + '</span>' +
              (r.note ? '<span>' + escapeHtml(r.note) + '</span>' : '') +
            '</div>' +
          '</div>' +
          '<div class="record-actions">' +
            '<button class="btn btn-sm btn-outline edit-rec-btn" data-id="' + r.id + '">编辑</button>' +
            '<button class="btn btn-sm btn-danger del-rec-btn" data-id="' + r.id + '">删除</button>' +
          '</div>' +
        '</div>';
    }
    recordListEl.innerHTML = html;

    // 绑定编辑/删除
    var editBtns = recordListEl.querySelectorAll('.edit-rec-btn');
    var delBtns = recordListEl.querySelectorAll('.del-rec-btn');
    for (var j = 0; j < editBtns.length; j++) {
      editBtns[j].addEventListener('click', function(e) {
        e.stopPropagation();
        openEditRecord(this.getAttribute('data-id'));
      });
    }
    for (var k = 0; k < delBtns.length; k++) {
      delBtns[k].addEventListener('click', function(e) {
        e.stopPropagation();
        var rid = this.getAttribute('data-id');
        showConfirm('确定要删除这条记录吗？', function() {
          api.deleteRecord(rid).then(function() {
            showToast('已删除');
            refresh();
          }).catch(function(err) {
            showToast('删除失败: ' + err.message);
          });
        });
      });
    }
  }

  // ===== 编辑记录 =====
  function openEditRecord(recId) {
    var rec = null;
    var records = currentTrip.records || [];
    for (var i = 0; i < records.length; i++) {
      if (records[i].id === recId) { rec = records[i]; break; }
    }
    if (!rec) return;
    editingRecordId = recId;

    Promise.all([api.getCategories(), api.getPayers()]).then(function(results) {
      fillCategorySelect(editRecCategoryEl, results[0], rec.category);
      fillPayerSelect(editRecPayerEl, results[1], rec.payer);
      editRecAmountEl.value = rec.amount;
      editRecDateEl.value = rec.date || '';
      editRecNoteEl.value = rec.note || '';
      editCustomCatGroup.style.display = 'none';
      editNewPayerGroup.style.display = 'none';
      editRecordModal.classList.add('show');
    });
  }
  closeEditRecord.addEventListener('click', function() { editRecordModal.classList.remove('show'); });
  editRecordModal.addEventListener('click', function(e) { if (e.target === editRecordModal) editRecordModal.classList.remove('show'); });

  saveEditRecordBtn.addEventListener('click', function() {
    var category = editRecCategoryEl.value;
    if (category === '__custom__') {
      category = editRecCustomCatEl.value.trim();
      if (!category) { showToast('请输入自定义类别名称'); return; }
    }
    var amount = parseFloat(editRecAmountEl.value);
    if (!amount || amount <= 0) { showToast('请输入有效金额'); return; }
    var payer = editRecPayerEl.value;
    if (payer === '__new__') {
      payer = editRecNewPayerEl.value.trim();
      if (!payer) { showToast('请输入支付人姓名'); return; }
    }
    if (!payer) { showToast('请选择支付人'); return; }

    saveEditRecordBtn.disabled = true;
    api.updateRecord(editingRecordId, {
      category: category,
      amount: amount,
      payer: payer,
      date: editRecDateEl.value || todayStr(),
      note: editRecNoteEl.value.trim()
    }).then(function() {
      editRecordModal.classList.remove('show');
      showToast('修改成功');
      saveEditRecordBtn.disabled = false;
      refresh();
    }).catch(function(err) {
      showToast('修改失败: ' + err.message);
      saveEditRecordBtn.disabled = false;
    });
  });

  // ===== 总结区域 =====
  function renderSummary() {
    var records = currentTrip.records || [];
    if (records.length === 0) {
      summaryAreaEl.innerHTML = '<div class="card" style="text-align:center;color:var(--text-muted);padding:20px;">暂无数据</div>';
      return;
    }
    var total = Number(currentTrip.total_amount) || 0;
    var byPayer = currentTrip.by_payer || {};
    var byCategory = currentTrip.by_category || {};

    var html = '';
    // 按支付人
    html += '<div class="card summary-section"><div class="summary-title">👤 按支付人</div>';
    var payers = Object.keys(byPayer);
    for (var i = 0; i < payers.length; i++) {
      html += '<div class="summary-row"><span class="summary-row-label">' + escapeHtml(payers[i]) + '</span><span class="summary-row-value">' + formatMoney(byPayer[payers[i]]) + '</span></div>';
    }
    html += '</div>';

    // 按类别
    html += '<div class="card summary-section"><div class="summary-title">📂 按类别</div>';
    var cats = Object.keys(byCategory);
    for (var j = 0; j < cats.length; j++) {
      var cs = getCategoryStyle(cats[j]);
      html += '<div class="summary-row"><span class="summary-row-label">' + cs.icon + ' ' + escapeHtml(cats[j]) + '</span><span class="summary-row-value">' + formatMoney(byCategory[cats[j]]) + '</span></div>';
    }
    html += '</div>';

    // 总计
    html += '<div class="summary-total"><span class="summary-total-label">总计</span><span class="summary-total-value">' + formatMoney(total) + '</span></div>';

    summaryAreaEl.innerHTML = html;
  }

  // ===== 编辑旅行信息 =====
  editTripBtn.addEventListener('click', function() {
    editTripNameEl.value = currentTrip.name;
    editTripStartEl.value = currentTrip.start_date || '';
    editTripEndEl.value = currentTrip.end_date || '';
    editTripNoteEl.value = currentTrip.note || '';
    editTripModal.classList.add('show');
  });
  closeEditTrip.addEventListener('click', function() { editTripModal.classList.remove('show'); });
  editTripModal.addEventListener('click', function(e) { if (e.target === editTripModal) editTripModal.classList.remove('show'); });

  saveEditTripBtn.addEventListener('click', function() {
    var name = editTripNameEl.value.trim();
    if (!name) { showToast('请输入旅行名称'); return; }
    saveEditTripBtn.disabled = true;
    api.updateTrip(tripId, {
      name: name,
      startDate: editTripStartEl.value,
      endDate: editTripEndEl.value,
      note: editTripNoteEl.value.trim()
    }).then(function() {
      editTripModal.classList.remove('show');
      showToast('保存成功');
      saveEditTripBtn.disabled = false;
      refresh();
    }).catch(function(err) {
      showToast('保存失败: ' + err.message);
      saveEditTripBtn.disabled = false;
    });
  });

  // ===== 删除旅行 =====
  deleteTripBtn.addEventListener('click', function() {
    showConfirm('确定要删除整个旅行「' + (currentTrip ? currentTrip.name : '') + '」及其所有记录吗？', function() {
      api.deleteTrip(tripId).then(function() {
        showToast('已删除');
        window.location.href = 'trips.html';
      }).catch(function(err) {
        showToast('删除失败: ' + err.message);
      });
    });
  });

  // ===== 返回 =====
  backBtn.addEventListener('click', function() {
    window.location.href = 'trips.html';
  });

  // ===== 导出Excel =====
  exportBtn.addEventListener('click', function() {
    if (!currentTrip || !currentTrip.records || currentTrip.records.length === 0) {
      showToast('暂无数据可导出');
      return;
    }
    api.exportTrip(tripId);
  });

  // 初始化
  refresh();
})();
