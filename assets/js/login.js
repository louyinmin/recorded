(function() {
  var view = 'signin';
  var lastResetEmail = '';
  var lastResetCode = '';

  var authView = document.getElementById('lifeAuthView');
  var errorBox = document.getElementById('loginError');

  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function showMessage(message, isOk) {
    errorBox.textContent = message || '';
    errorBox.classList.toggle('show', !!message);
    errorBox.classList.toggle('ok', !!isOk);
    if (message && !isOk) {
      window.setTimeout(function() {
        errorBox.classList.remove('show');
      }, 2600);
    }
  }

  function go(url) {
    window.location.href = url;
  }

  function currentSession() {
    return window.LifeAccount ? window.LifeAccount.getSession() : null;
  }

  function setView(nextView) {
    view = nextView;
    showMessage('');
    render();
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function avatarOptions(active) {
    return ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6'].map(function(item) {
      return '<label class="life-auth-avatar ' + (active === item ? 'active' : '') + '">' +
        '<input type="radio" name="avatar" value="' + item + '" ' + (active === item ? 'checked' : '') + '>' +
        '<span class="life-auth-face ' + item.toLowerCase() + '"><i></i></span><em>' + item + '</em>' +
      '</label>';
    }).join('');
  }

  function lifecycleHtml(session) {
    var items = (session && session.lifecycle) || [
      { label: '创建账号', date: '待完成', status: 'todo' },
      { label: '完善资料', date: '待完成', status: 'todo' },
      { label: '启用安全设置', date: '待完成', status: 'todo' }
    ];
    var last = items[items.length - 1];
    return '<div class="life-auth-log-summary"><span>操作日志</span><strong>' + items.length + ' 条</strong><small>最近：' + escapeHtml(last ? last.date : '暂无') + '</small></div>';
  }

  function roleText(role) {
    return role === 'admin' ? '管理员' : '普通用户';
  }

  function renderSignin() {
    return '<form class="life-auth-form" data-auth-form="signin">' +
      '<div class="life-auth-title"><span>Life Atlas</span><h2>登录你的时间河流</h2><p>把今天、情绪、决定和记忆，安静地留给未来的自己。</p></div>' +
      '<label>邮箱<input class="form-input" name="email" type="email" placeholder="请输入邮箱地址" autocomplete="email" required></label>' +
      '<label>密码<input class="form-input" name="password" type="password" placeholder="请输入密码" autocomplete="current-password" required></label>' +
      '<div class="life-auth-row"><label class="life-auth-check"><input type="checkbox" name="remember" checked> 保持登录</label><button type="button" data-auth-view="recover">忘记密码</button></div>' +
      '<button class="life-auth-primary" type="submit">进入生活航迹</button>' +
      '<div class="life-auth-divider"><span>或</span></div>' +
      '<button class="life-auth-passkey" type="button" data-auth-action="passkey-demo">使用 Passkey 登录</button>' +
      '<div class="life-auth-socials"><button type="button" data-auth-action="social-demo" aria-label="Google 登录">G</button><button type="button" data-auth-action="social-demo" aria-label="Apple 登录">Apple</button><button type="button" data-auth-action="social-demo" aria-label="微信登录">微信</button></div>' +
      '<p class="life-auth-signup-line">还没有账号？ <button type="button" data-auth-view="signup">创建账户</button></p>' +
    '</form>';
  }

  function renderSignup() {
    return '<form class="life-auth-form" data-auth-form="signup">' +
      '<div class="life-auth-title"><span>新的航迹</span><h2>创建账号</h2><p>账号创建后会立刻进入生活航迹，并生成初始生命周期。</p></div>' +
      '<label>昵称<input class="form-input" name="name" type="text" placeholder="例如 Louise" required></label>' +
      '<label>邮箱<input class="form-input" name="email" type="email" placeholder="you@example.com" required></label>' +
      '<label>密码<input class="form-input" name="password" type="password" placeholder="至少 6 位" required></label>' +
      '<label>账号类型<div class="life-auth-role-grid"><label><input type="radio" name="role" value="user" checked><span>普通用户</span><small>记录和管理自己的生活航迹</small></label><label><input type="radio" name="role" value="admin"><span>管理员</span><small>可创建和删除其他账号</small></label></div></label>' +
      '<label>管理员邀请码<input class="form-input" name="adminCode" type="text" placeholder="普通用户可留空；管理员输入 LIFE-ADMIN"></label>' +
      '<div class="life-auth-avatar-grid">' + avatarOptions('Q2') + '</div>' +
      '<button class="life-auth-primary" type="submit">创建并进入</button>' +
      '<button class="life-auth-ghost" type="button" data-auth-view="signin">已有账号，去登录</button>' +
    '</form>';
  }

  function renderRecover() {
    return '<form class="life-auth-form" data-auth-form="recover">' +
      '<div class="life-auth-title"><span>账号恢复</span><h2>重置密码</h2><p>原型会在页面内生成验证码，方便测试完整恢复流程。</p></div>' +
      '<label>注册邮箱<input class="form-input" name="email" type="email" value="' + escapeHtml(lastResetEmail || 'louise@example.com') + '" required></label>' +
      '<button class="life-auth-primary" type="submit">生成验证码</button>' +
      (lastResetCode ? '<div class="life-auth-code">验证码 <strong>' + lastResetCode + '</strong></div>' : '') +
      '<label>验证码<input class="form-input" name="code" type="text" value="' + lastResetCode + '" placeholder="6 位验证码"></label>' +
      '<label>新密码<input class="form-input" name="password" type="password" placeholder="至少 6 位"></label>' +
      '<button class="life-auth-ghost" type="button" data-auth-action="reset-password">保存新密码</button>' +
      '<button class="life-auth-link" type="button" data-auth-view="signin">返回登录</button>' +
    '</form>';
  }

  function renderAccount() {
    var session = currentSession();
    if (!session) return renderSignin();
    return '<form class="life-auth-form" data-auth-form="account">' +
      '<div class="life-auth-title"><span>账号中心</span><h2>' + escapeHtml(session.name) + '</h2><p>' + escapeHtml(session.email) + ' · ' + roleText(session.role) + ' · 当前账号处于 active 状态。</p></div>' +
      '<div class="life-auth-avatar-grid">' + avatarOptions(session.avatar || 'Q1') + '</div>' +
      '<label>昵称<input class="form-input" name="name" type="text" value="' + escapeHtml(session.name) + '" required></label>' +
      '<label>邮箱<input class="form-input" name="email" type="email" value="' + escapeHtml(session.email) + '" required></label>' +
      '<div class="life-auth-row"><label class="life-auth-check"><input type="checkbox" name="reminder" ' + (session.preferences && session.preferences.reminder ? 'checked' : '') + '> 重要复盘提醒</label><button type="button" data-auth-action="logout">退出登录</button></div>' +
      '<button class="life-auth-primary" type="submit">保存账号资料</button>' +
      '<div class="life-auth-password"><label>当前密码<input class="form-input" name="currentPassword" type="password" placeholder="当前密码"></label><label>新密码<input class="form-input" name="nextPassword" type="password" placeholder="至少 6 位"></label><button type="button" data-auth-action="change-password">修改密码</button></div>' +
      lifecycleHtml(session) +
      (session.role === 'admin' ? renderAdminPanel(session) : '') +
      '<div class="life-auth-danger"><button type="button" data-auth-action="deactivate">停用账号</button><button type="button" data-auth-action="delete">删除当前账号</button></div>' +
    '</form>';
  }

  function renderAdminPanel(session) {
    var accounts = window.LifeAccount.listAccounts();
    return '<section class="life-admin-panel"><div class="life-admin-panel-head"><div><strong>账号管理</strong><span>管理员可创建普通用户或管理员，也可删除非当前账号。</span></div><button type="button" data-auth-action="toggle-admin-create">创建账号</button></div>' +
      '<div class="life-admin-create" hidden><div class="life-admin-create-grid"><input class="form-input" name="managedName" placeholder="昵称"><input class="form-input" name="managedEmail" placeholder="邮箱"><input class="form-input" name="managedPassword" placeholder="初始密码"><select class="form-input" name="managedRole"><option value="user">普通用户</option><option value="admin">管理员</option></select></div><button type="button" data-auth-action="admin-create">保存新账号</button></div>' +
      '<div class="life-admin-list">' + accounts.map(function(account) {
        var self = account.id === session.accountId;
        return '<div class="life-admin-row"><div><strong>' + escapeHtml(account.name) + '</strong><span>' + escapeHtml(account.email) + ' · ' + roleText(account.role) + '</span></div><em>' + escapeHtml(account.status) + '</em><button type="button" data-auth-action="admin-delete" data-account-id="' + escapeHtml(account.id) + '" ' + (self ? 'disabled' : '') + '>' + (self ? '当前账号' : '删除') + '</button></div>';
      }).join('') + '</div></section>';
  }

  function render() {
    showMessage('');
    var session = currentSession();
    if (session && view === 'signin') view = 'account';
    if (!session && view === 'account') view = 'signin';
    if (view === 'signup') authView.innerHTML = renderSignup();
    else if (view === 'recover') authView.innerHTML = renderRecover();
    else if (view === 'account') authView.innerHTML = renderAccount();
    else authView.innerHTML = renderSignin();
  }

  function formData(form) {
    var data = {};
    Array.prototype.forEach.call(form.elements, function(el) {
      if (!el.name) return;
      if (el.type === 'radio' && !el.checked) return;
      if (el.type === 'checkbox') data[el.name] = el.checked;
      else data[el.name] = el.value;
    });
    return data;
  }

  function handleForm(form) {
    var data = formData(form);
    var formType = form.getAttribute('data-auth-form');
    try {
      if (formType === 'signin') {
        window.LifeAccount.signIn(data.email, data.password, data.remember);
        go('life.html');
      }
      if (formType === 'signup') {
        window.LifeAccount.register(data);
        go('life.html');
      }
      if (formType === 'recover') {
        lastResetEmail = data.email;
        lastResetCode = window.LifeAccount.requestReset(data.email);
        showMessage('验证码已生成，请继续设置新密码', true);
        render();
      }
      if (formType === 'account') {
        window.LifeAccount.updateProfile({
          name: data.name,
          email: data.email,
          avatar: data.avatar,
          preferences: { reminder: data.reminder }
        });
        showMessage('账号资料已保存', true);
        render();
      }
    } catch (err) {
      showMessage(err.message || '操作失败');
    }
  }

  function resetPasswordFromRecover() {
    var form = $('[data-auth-form="recover"]');
    var data = formData(form);
    try {
      window.LifeAccount.resetPassword(data.email, data.code, data.password);
      showMessage('密码已重置，正在进入生活航迹', true);
      window.setTimeout(function() { go('life.html'); }, 500);
    } catch (err) {
      showMessage(err.message || '重置失败');
    }
  }

  function handleAccountAction(action, actionBtn) {
    var form = $('[data-auth-form="account"]');
    try {
      if (action === 'passkey-demo' || action === 'social-demo') {
        showMessage('第三方登录已预留入口，当前原型使用邮箱账号验证。', true);
        return;
      }
      if (action === 'logout') {
        window.LifeAccount.signOut();
        view = 'signin';
        render();
        return;
      }
      if (action === 'change-password') {
        var data = formData(form);
        window.LifeAccount.changePassword(data.currentPassword, data.nextPassword);
        showMessage('密码已修改', true);
        render();
        return;
      }
      if (action === 'deactivate') {
        if (!window.confirm('确认停用当前账号？停用后会退出登录。')) return;
        window.LifeAccount.deactivateAccount();
        view = 'signin';
        render();
        showMessage('账号已停用', true);
        return;
      }
      if (action === 'delete') {
        if (!window.confirm('确认删除当前账号？此操作会退出登录，并从可登录账号中移除。')) return;
        window.LifeAccount.deleteAccount();
        view = 'signin';
        render();
        showMessage('账号已删除', true);
      }
      if (action === 'toggle-admin-create') {
        var createBox = $('.life-admin-create');
        if (createBox) createBox.hidden = !createBox.hidden;
      }
      if (action === 'admin-create') {
        var managed = formData(form);
        window.LifeAccount.adminCreateAccount({
          name: managed.managedName,
          email: managed.managedEmail,
          password: managed.managedPassword,
          role: managed.managedRole,
          adminCode: 'LIFE-ADMIN',
          avatar: managed.managedRole === 'admin' ? 'Q1' : 'Q2'
        });
        showMessage('账号已创建', true);
        render();
      }
      if (action === 'admin-delete') {
        var target = actionBtn && actionBtn.getAttribute('data-account-id');
        if (!target) return;
        if (!window.confirm('确认删除这个账号？删除后该账号无法再登录。')) return;
        window.LifeAccount.adminDeleteAccount(target);
        showMessage('账号已删除', true);
        render();
      }
    } catch (err) {
      showMessage(err.message || '操作失败');
    }
  }

  document.addEventListener('click', function(event) {
    var viewBtn = event.target.closest('[data-auth-view]');
    if (viewBtn) {
      setView(viewBtn.getAttribute('data-auth-view'));
      return;
    }
    var actionBtn = event.target.closest('[data-auth-action]');
    if (actionBtn) {
      var action = actionBtn.getAttribute('data-auth-action');
      if (action === 'reset-password') resetPasswordFromRecover();
      else handleAccountAction(action, actionBtn);
    }
  });

  document.addEventListener('submit', function(event) {
    var form = event.target.closest('[data-auth-form]');
    if (!form) return;
    event.preventDefault();
    handleForm(form);
  });

  render();
})();
