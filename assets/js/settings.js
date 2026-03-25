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

  // ===== 渲染支付人列表 =====
  function renderPayers(payers) {
    if (payers.length === 0) {
      payerListEl.innerHTML = '<div class="empty-state" style="padding:16px;text-align:center;color:var(--text-muted);">暂无支付人</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < payers.length; i++) {
      html +=
        '<div class="manage-item">' +
          '<span class="manage-item-name">' + escapeHtml(payers[i]) + '</span>' +
          '<div class="manage-item-actions">' +
            '<button class="btn btn-sm btn-outline edit-payer-btn" data-name="' + escapeHtml(payers[i]) + '">编辑</button>' +
            '<button class="btn btn-sm btn-danger del-payer-btn" data-name="' + escapeHtml(payers[i]) + '">删除</button>' +
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
        showConfirm('确定要删除支付人「' + name + '」吗？', function() {
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
  function renderCategories(categories) {
    if (categories.length === 0) {
      categoryListEl.innerHTML = '<div class="empty-state" style="padding:16px;text-align:center;color:var(--text-muted);">暂无类别</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < categories.length; i++) {
      html +=
        '<div class="manage-item">' +
          '<span class="manage-item-name">' + escapeHtml(categories[i]) + '</span>' +
          '<div class="manage-item-actions">' +
            '<button class="btn btn-sm btn-outline edit-cat-btn" data-name="' + escapeHtml(categories[i]) + '">编辑</button>' +
            '<button class="btn btn-sm btn-danger del-cat-btn" data-name="' + escapeHtml(categories[i]) + '">删除</button>' +
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
        showConfirm('确定要删除类别「' + name + '」吗？', function() {
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
