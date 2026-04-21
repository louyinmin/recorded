(function() {
  checkAuth();

  // DOM 引用
  var backBtn = document.getElementById('backBtn');
  var oldPasswordEl = document.getElementById('oldPassword');
  var newPasswordEl = document.getElementById('newPassword');
  var confirmPasswordEl = document.getElementById('confirmPassword');
  var changePasswordBtn = document.getElementById('changePasswordBtn');
  var newPayerNameEl = document.getElementById('newPayerName');
  var addPayerBtn = document.getElementById('addPayerBtn');
  var payerListEl = document.getElementById('payerList');
  var newCategoryNameEl = document.getElementById('newCategoryName');
  var addCategoryBtn = document.getElementById('addCategoryBtn');
  var categoryListEl = document.getElementById('categoryList');
  var editModal = document.getElementById('editModal');
  var editModalTitleEl = document.getElementById('editModalTitle');
  var editLabelEl = document.getElementById('editLabel');
  var editInputEl = document.getElementById('editInput');
  var closeEditModal = document.getElementById('closeEditModal');
  var saveEditBtn = document.getElementById('saveEditBtn');

  var editingType = null; // 'payer' or 'category'
  var editingName = null;

  // ===== 加载数据 =====
  function loadData() {
    Promise.all([
      api.getPayers(),
      api.getCategories()
    ]).then(function(results) {
      renderPayers(results[0]);
      renderCategories(results[1]);
    }).catch(function(err) {
      showToast('加载失败: ' + err.message);
    });
  }

  function normalizeManageItems(items) {
    var normalized = [];
    for (var i = 0; i < (items || []).length; i++) {
      var item = items[i];
      if (typeof item === 'string') {
        normalized.push({ name: item, usedCount: 0, inUse: false });
        continue;
      }
      if (!item || typeof item !== 'object' || !item.name) continue;
      var usedCount = Number(item.used_count);
      if (!isFinite(usedCount) || usedCount < 0) usedCount = 0;
      normalized.push({
        name: item.name,
        usedCount: usedCount,
        inUse: !!item.in_use || usedCount > 0
      });
    }
    return normalized;
  }

  // ===== 渲染支付人列表 =====
  function renderPayers(rawPayers) {
    var payers = normalizeManageItems(rawPayers);
    if (payers.length === 0) {
      payerListEl.innerHTML = '<div class="empty-state" style="padding:16px;text-align:center;color:var(--text-muted);">暂无支付人</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < payers.length; i++) {
      var payer = payers[i];
      html +=
        '<div class="manage-item">' +
          '<div class="manage-item-main">' +
            '<span class="manage-item-name">' + escapeHtml(payer.name) + '</span>' +
            '<span class="manage-item-usage ' + (payer.inUse ? 'is-used' : 'is-free') + '">' +
              (payer.inUse ? ('账单使用中 · ' + payer.usedCount + ' 条') : '未被账单使用') +
            '</span>' +
          '</div>' +
          '<div class="manage-item-actions">' +
            '<button class="btn btn-sm btn-outline edit-payer-btn" data-name="' + escapeHtml(payer.name) + '">编辑</button>' +
            '<button class="btn btn-sm btn-danger del-payer-btn" data-name="' + escapeHtml(payer.name) + '" data-in-use="' + (payer.inUse ? '1' : '0') + '"' + (payer.inUse ? ' disabled title="正在被账单使用，无法删除"' : '') + '>删除</button>' +
          '</div>' +
        '</div>';
    }
    payerListEl.innerHTML = html;

    // 绑定事件
    var editBtns = payerListEl.querySelectorAll('.edit-payer-btn');
    var delBtns = payerListEl.querySelectorAll('.del-payer-btn');
    for (var j = 0; j < editBtns.length; j++) {
      editBtns[j].addEventListener('click', function() {
        openEditModal('payer', this.getAttribute('data-name'));
      });
    }
    for (var k = 0; k < delBtns.length; k++) {
      delBtns[k].addEventListener('click', function() {
        var name = this.getAttribute('data-name');
        if (this.getAttribute('data-in-use') === '1') {
          showToast('该支付人正在被账单使用，无法删除');
          return;
        }
        showConfirm('确定要删除支付人「' + name + '」吗？删除后不可恢复。', function() {
          api.deletePayer(name).then(function() {
            showToast('已删除');
            loadData();
          }).catch(function(err) {
            showToast('删除失败: ' + err.message);
          });
        });
      });
    }
  }

  // ===== 渲染类别列表 =====
  function renderCategories(rawCategories) {
    var categories = normalizeManageItems(rawCategories);
    if (categories.length === 0) {
      categoryListEl.innerHTML = '<div class="empty-state" style="padding:16px;text-align:center;color:var(--text-muted);">暂无类别</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < categories.length; i++) {
      var category = categories[i];
      html +=
        '<div class="manage-item">' +
          '<div class="manage-item-main">' +
            '<span class="manage-item-name">' + escapeHtml(category.name) + '</span>' +
            '<span class="manage-item-usage ' + (category.inUse ? 'is-used' : 'is-free') + '">' +
              (category.inUse ? ('账单使用中 · ' + category.usedCount + ' 条') : '未被账单使用') +
            '</span>' +
          '</div>' +
          '<div class="manage-item-actions">' +
            '<button class="btn btn-sm btn-outline edit-cat-btn" data-name="' + escapeHtml(category.name) + '">编辑</button>' +
            '<button class="btn btn-sm btn-danger del-cat-btn" data-name="' + escapeHtml(category.name) + '" data-in-use="' + (category.inUse ? '1' : '0') + '"' + (category.inUse ? ' disabled title="正在被账单使用，无法删除"' : '') + '>删除</button>' +
          '</div>' +
        '</div>';
    }
    categoryListEl.innerHTML = html;

    // 绑定事件
    var editBtns = categoryListEl.querySelectorAll('.edit-cat-btn');
    var delBtns = categoryListEl.querySelectorAll('.del-cat-btn');
    for (var j = 0; j < editBtns.length; j++) {
      editBtns[j].addEventListener('click', function() {
        openEditModal('category', this.getAttribute('data-name'));
      });
    }
    for (var k = 0; k < delBtns.length; k++) {
      delBtns[k].addEventListener('click', function() {
        var name = this.getAttribute('data-name');
        if (this.getAttribute('data-in-use') === '1') {
          showToast('该类别正在被账单使用，无法删除');
          return;
        }
        showConfirm('确定要删除类别「' + name + '」吗？删除后不可恢复。', function() {
          api.deleteCategory(name).then(function() {
            showToast('已删除');
            loadData();
          }).catch(function(err) {
            showToast('删除失败: ' + err.message);
          });
        });
      });
    }
  }

  // ===== 修改密码 =====
  changePasswordBtn.addEventListener('click', function() {
    var oldPwd = oldPasswordEl.value;
    var newPwd = newPasswordEl.value;
    var confirmPwd = confirmPasswordEl.value;
    if (!oldPwd || !newPwd || !confirmPwd) {
      showToast('请填写完整');
      return;
    }
    if (newPwd !== confirmPwd) {
      showToast('两次输入的新密码不一致');
      return;
    }
    if (newPwd.length < 3) {
      showToast('新密码至少3位');
      return;
    }
    changePasswordBtn.disabled = true;
    api.changePassword(oldPwd, newPwd).then(function() {
      showToast('密码修改成功');
      oldPasswordEl.value = '';
      newPasswordEl.value = '';
      confirmPasswordEl.value = '';
      changePasswordBtn.disabled = false;
    }).catch(function(err) {
      showToast('修改失败: ' + err.message);
      changePasswordBtn.disabled = false;
    });
  });

  // ===== 添加支付人 =====
  addPayerBtn.addEventListener('click', function() {
    var name = newPayerNameEl.value.trim();
    if (!name) {
      showToast('请输入支付人姓名');
      return;
    }
    addPayerBtn.disabled = true;
    api.createPayer(name).then(function() {
      showToast('添加成功');
      newPayerNameEl.value = '';
      addPayerBtn.disabled = false;
      loadData();
    }).catch(function(err) {
      showToast('添加失败: ' + err.message);
      addPayerBtn.disabled = false;
    });
  });

  // ===== 添加类别 =====
  addCategoryBtn.addEventListener('click', function() {
    var name = newCategoryNameEl.value.trim();
    if (!name) {
      showToast('请输入类别名称');
      return;
    }
    addCategoryBtn.disabled = true;
    api.createCategory(name).then(function() {
      showToast('添加成功');
      newCategoryNameEl.value = '';
      addCategoryBtn.disabled = false;
      loadData();
    }).catch(function(err) {
      showToast('添加失败: ' + err.message);
      addCategoryBtn.disabled = false;
    });
  });

  // ===== 编辑模态框 =====
  function openEditModal(type, name) {
    editingType = type;
    editingName = name;
    editModalTitleEl.textContent = type === 'payer' ? '编辑支付人' : '编辑类别';
    editLabelEl.textContent = type === 'payer' ? '支付人姓名' : '类别名称';
    editInputEl.value = name;
    editModal.classList.add('show');
  }

  closeEditModal.addEventListener('click', function() {
    editModal.classList.remove('show');
  });
  editModal.addEventListener('click', function(e) {
    if (e.target === editModal) editModal.classList.remove('show');
  });

  saveEditBtn.addEventListener('click', function() {
    var newName = editInputEl.value.trim();
    if (!newName) {
      showToast('名称不能为空');
      return;
    }
    saveEditBtn.disabled = true;
    var apiCall = editingType === 'payer' ? api.updatePayer : api.updateCategory;
    apiCall(editingName, newName).then(function() {
      editModal.classList.remove('show');
      showToast('修改成功');
      saveEditBtn.disabled = false;
      loadData();
    }).catch(function(err) {
      showToast('修改失败: ' + err.message);
      saveEditBtn.disabled = false;
    });
  });

  // ===== 返回 =====
  backBtn.addEventListener('click', function() {
    window.location.href = 'trips.html';
  });

  // 初始化
  loadData();
})();
