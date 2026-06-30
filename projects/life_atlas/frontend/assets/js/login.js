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

  function setView(nextView) {
    view = nextView === 'signup' || nextView === 'recover' ? nextView : 'signin';
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

  function renderSignin() {
    return '<form class="life-auth-form" data-auth-form="signin">' +
      '<div class="life-auth-title"><span>Life Atlas</span><h2>登录你的时间河流</h2><p>把今天、情绪、决定和记忆，安静地留给未来的自己。</p></div>' +
      '<label>账号<input class="form-input" name="email" type="text" placeholder="请输入账号" autocomplete="username" required></label>' +
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
      '<label>账号<input class="form-input" name="email" type="text" placeholder="例如 admin" autocomplete="username" required></label>' +
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
      '<label>注册账号<input class="form-input" name="email" type="text" value="' + escapeHtml(lastResetEmail) + '" placeholder="请输入注册账号" autocomplete="username" required></label>' +
      '<button class="life-auth-primary" type="submit">生成验证码</button>' +
      (lastResetCode ? '<div class="life-auth-code">验证码 <strong>' + lastResetCode + '</strong></div>' : '') +
      '<label>验证码<input class="form-input" name="code" type="text" value="' + escapeHtml(lastResetCode) + '" placeholder="6 位验证码"></label>' +
      '<label>新密码<input class="form-input" name="password" type="password" placeholder="至少 6 位"></label>' +
      '<button class="life-auth-ghost" type="button" data-auth-action="reset-password">保存新密码</button>' +
      '<button class="life-auth-link" type="button" data-auth-view="signin">返回登录</button>' +
    '</form>';
  }

  function render() {
    if (view === 'signup') authView.innerHTML = renderSignup();
    else if (view === 'recover') authView.innerHTML = renderRecover();
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
    if (formType === 'signin') {
      return window.LifeAccount.signIn(data.email, data.password, data.remember).then(function() {
        go('life.html');
      });
    }
    if (formType === 'signup') {
      return window.LifeAccount.register(data).then(function() {
        go('life.html');
      });
    }
    if (formType === 'recover') {
      lastResetEmail = data.email;
      return window.LifeAccount.requestReset(data.email).then(function(code) {
        lastResetCode = code;
        showMessage('验证码已生成，请继续设置新密码', true);
        render();
      });
    }
    return Promise.resolve(true);
  }

  function resetPasswordFromRecover() {
    var form = $('[data-auth-form="recover"]');
    var data = formData(form);
    return window.LifeAccount.resetPassword(data.email, data.code, data.password).then(function() {
      showMessage('密码已重置，正在进入生活航迹', true);
      window.setTimeout(function() { go('life.html'); }, 500);
    });
  }

  function handleAuthAction(action) {
    if (action === 'passkey-demo' || action === 'social-demo') {
      showMessage('第三方登录已预留入口，当前原型使用账号密码验证。', true);
      return Promise.resolve(true);
    }
    if (action === 'reset-password') return resetPasswordFromRecover();
    return Promise.resolve(true);
  }

  document.addEventListener('click', function(event) {
    var viewBtn = event.target.closest('[data-auth-view]');
    if (viewBtn) {
      setView(viewBtn.getAttribute('data-auth-view'));
      return;
    }
    var actionBtn = event.target.closest('[data-auth-action]');
    if (!actionBtn) return;
    showMessage('');
    handleAuthAction(actionBtn.getAttribute('data-auth-action')).catch(function(err) {
      showMessage(err.message || '操作失败');
    });
  });

  document.addEventListener('submit', function(event) {
    var form = event.target.closest('[data-auth-form]');
    if (!form) return;
    event.preventDefault();
    showMessage('');
    handleForm(form).catch(function(err) {
      showMessage(err.message || '操作失败');
    });
  });

  window.LifeAccount.refreshSession().then(function() {
    render();
  }).catch(function() {
    render();
  });
})();
