(function() {
  var editingId = null;
  var users = [];

  function renderUserHeader(user) {
    document.getElementById('currentUser').textContent = user.username + ' / 管理员';
  }

  function loadUsers() {
    return expiryApp.api.adminUsers().then(function(data) {
      users = data;
      renderUsers();
    });
  }

  function renderUsers() {
    var list = document.getElementById('userList');
    if (!users.length) {
      list.innerHTML = '<div class="expiry-empty-state">还没有账号。</div>';
      return;
    }
    list.innerHTML = users.map(function(user) {
      return '<article class="expiry-admin-card">' +
        '<div class="expiry-admin-top">' +
          '<div><div class="expiry-resource-title">' + expiryApp.escapeHtml(user.username) + '</div>' +
          '<div class="expiry-resource-meta">' + expiryApp.escapeHtml(user.email || '未填写邮箱') + '</div></div>' +
          '<span class="expiry-state-pill ' + (user.status === 'active' ? 'state-active' : 'state-stopped') + '">' + (user.status === 'active' ? '启用中' : '已停用') + '</span>' +
        '</div>' +
        '<div class="expiry-admin-meta">' +
          '<span>角色：' + (user.role === 'admin' ? '管理员' : '普通用户') + '</span>' +
          '<span>首次改密：' + (user.must_change_password ? '未完成' : '已完成') + '</span>' +
        '</div>' +
        '<div class="expiry-action-row">' +
          '<button class="expiry-btn expiry-btn-ghost" data-edit="' + user.id + '">编辑</button>' +
          '<button class="expiry-btn expiry-btn-light" data-reset="' + user.id + '">重置密码</button>' +
          '<button class="expiry-btn ' + (user.status === 'active' ? 'expiry-btn-danger' : 'expiry-btn-primary') + '" data-toggle="' + user.id + '">' +
          (user.status === 'active' ? '停用' : '启用') + '</button>' +
        '</div>' +
      '</article>';
    }).join('');
  }

  function openEditModal(user) {
    editingId = user.id;
    document.getElementById('editUserEmail').value = user.email || '';
    document.getElementById('editUserRole').value = user.role;
    document.getElementById('editUserModal').classList.remove('hidden');
  }

  document.getElementById('logoutBtn').addEventListener('click', expiryApp.logout);
  document.getElementById('createUserBtn').addEventListener('click', function() {
    expiryApp.api.adminCreateUser({
      username: document.getElementById('newUsername').value.trim(),
      email: document.getElementById('newEmail').value.trim(),
      password: document.getElementById('newPassword').value,
      role: document.getElementById('newRole').value
    }).then(function() {
      document.getElementById('newUsername').value = '';
      document.getElementById('newEmail').value = '';
      document.getElementById('newPassword').value = '';
      document.getElementById('newRole').value = 'user';
      expiryApp.showToast('账号已创建');
      loadUsers();
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  });

  document.getElementById('saveUserBtn').addEventListener('click', function() {
    expiryApp.api.adminUpdateUser(editingId, {
      email: document.getElementById('editUserEmail').value.trim(),
      role: document.getElementById('editUserRole').value
    }).then(function() {
      document.getElementById('editUserModal').classList.add('hidden');
      expiryApp.showToast('账号已更新');
      loadUsers();
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  });

  document.getElementById('userList').addEventListener('click', function(event) {
    var editBtn = event.target.closest('[data-edit]');
    if (editBtn) {
      var user = users.find(function(item) { return item.id === editBtn.getAttribute('data-edit'); });
      if (user) openEditModal(user);
      return;
    }
    var resetBtn = event.target.closest('[data-reset]');
    if (resetBtn) {
      var customPassword = window.prompt('输入新密码，留空则自动生成：', '');
      expiryApp.api.adminResetPassword(resetBtn.getAttribute('data-reset'), customPassword || '').then(function(data) {
        expiryApp.showToast('已重置，临时密码：' + data.temporary_password);
        loadUsers();
      }).catch(function(err) {
        expiryApp.showToast(err.message);
      });
      return;
    }
    var toggleBtn = event.target.closest('[data-toggle]');
    if (toggleBtn) {
      expiryApp.api.adminToggleStatus(toggleBtn.getAttribute('data-toggle')).then(function(data) {
        expiryApp.showToast('状态已切换为：' + (data.status === 'active' ? '启用' : '停用'));
        loadUsers();
      }).catch(function(err) {
        expiryApp.showToast(err.message);
      });
    }
  });

  expiryApp.bindModalClose();

  expiryApp.ensureAuth().then(function(user) {
    if (user.role !== 'admin') {
      window.location.href = '/expiry/dashboard.html';
      return;
    }
    renderUserHeader(user);
    return loadUsers();
  }).catch(function(err) {
    if (err && err.message) expiryApp.showToast(err.message);
  });
})();
