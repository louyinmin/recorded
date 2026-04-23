(function() {
  var currentUser = null;
  var EMAIL_AUTH_PASSWORD = 'password';
  var EMAIL_AUTH_MICROSOFT_OAUTH2 = 'microsoft_oauth2';

  function fillUser(user) {
    currentUser = user;
    document.getElementById('currentUser').textContent = user.username + ' / ' + (user.role === 'admin' ? '管理员' : '用户');
    document.getElementById('profileUsername').value = user.username;
    document.getElementById('profileEmail').value = user.email || '';
    if (user.role === 'admin') {
      document.getElementById('adminLink').classList.remove('hidden');
    }
  }

  function renderAuthMode(mode) {
    var authMode = mode === EMAIL_AUTH_MICROSOFT_OAUTH2 ? EMAIL_AUTH_MICROSOFT_OAUTH2 : EMAIL_AUTH_PASSWORD;
    document.getElementById('smtpAuthMode').value = authMode;
    var oauthPanel = document.getElementById('oauth2Panel');
    var smtpPasswordGroup = document.getElementById('smtpPasswordGroup');
    if (authMode === EMAIL_AUTH_MICROSOFT_OAUTH2) {
      oauthPanel.classList.remove('hidden');
      smtpPasswordGroup.classList.add('hidden');
    } else {
      oauthPanel.classList.add('hidden');
      smtpPasswordGroup.classList.remove('hidden');
    }
  }

  function renderEmailStatus(emailSettings) {
    var authMode = (emailSettings.auth_mode || EMAIL_AUTH_PASSWORD);
    var smtpStatusLine = document.getElementById('smtpStatusLine');
    var oauthStatusLine = document.getElementById('oauthStatusLine');
    if (authMode === EMAIL_AUTH_MICROSOFT_OAUTH2) {
      var oauthParts = [];
      oauthParts.push(emailSettings.oauth_client_secret_configured ? 'Client Secret 已保存' : 'Client Secret 未保存');
      oauthParts.push(emailSettings.oauth_refresh_token_configured ? 'Refresh Token 已保存' : 'Refresh Token 未保存');
      oauthParts.push(emailSettings.oauth_access_token_cached ? 'Access Token 已缓存' : 'Access Token 暂未缓存');
      oauthStatusLine.textContent = 'OAuth2 状态: ' + oauthParts.join(' · ');
      smtpStatusLine.textContent = '当前为 Microsoft OAuth2 模式，SMTP Password 会被忽略。';
      return;
    }
    oauthStatusLine.textContent = '';
    smtpStatusLine.textContent = emailSettings.smtp_password_configured ? '当前已保存 SMTP 密码，留空不会覆盖。' : '当前尚未保存 SMTP 密码。';
  }

  function fillEmailSettings(data) {
    var authMode = data.auth_mode || EMAIL_AUTH_PASSWORD;
    document.getElementById('smtpHost').value = data.smtp_host || '';
    document.getElementById('smtpPort').value = data.smtp_port || 587;
    document.getElementById('smtpUsername').value = data.smtp_username || '';
    document.getElementById('smtpSecurity').value = data.smtp_security || 'starttls';
    document.getElementById('fromEmail').value = data.from_email || '';
    document.getElementById('fromName').value = data.from_name || '';
    document.getElementById('smtpEnabled').checked = !!data.enabled;
    document.getElementById('oauthTenantId').value = data.oauth_tenant_id || '';
    document.getElementById('oauthClientId').value = data.oauth_client_id || '';
    document.getElementById('smtpPassword').value = '';
    document.getElementById('oauthClientSecret').value = '';
    document.getElementById('oauthRefreshToken').value = '';
    renderAuthMode(authMode);
    renderEmailStatus(data);
  }

  function loadSettings() {
    return Promise.all([
      expiryApp.api.getProfile(),
      expiryApp.api.getReminderSettings(),
      expiryApp.api.getEmailSettings()
    ]).then(function(result) {
      fillUser(result[0]);
      document.getElementById('defaultOffsets').value = result[1].default_notify_offsets || '30,7,1';
      document.getElementById('timezone').value = result[1].timezone || 'Asia/Shanghai';
      fillEmailSettings(result[2]);
    });
  }

  document.getElementById('logoutBtn').addEventListener('click', expiryApp.logout);

  document.getElementById('saveProfileBtn').addEventListener('click', function() {
    expiryApp.api.saveProfile({
      email: document.getElementById('profileEmail').value.trim()
    }).then(function() {
      expiryApp.showToast('账号资料已保存');
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  });

  document.getElementById('saveReminderBtn').addEventListener('click', function() {
    expiryApp.api.saveReminderSettings({
      default_notify_offsets: document.getElementById('defaultOffsets').value.trim(),
      timezone: document.getElementById('timezone').value.trim()
    }).then(function() {
      expiryApp.showToast('提醒设置已更新');
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  });

  document.getElementById('saveEmailBtn').addEventListener('click', function() {
    expiryApp.api.saveEmailSettings({
      auth_mode: document.getElementById('smtpAuthMode').value,
      smtp_host: document.getElementById('smtpHost').value.trim(),
      smtp_port: document.getElementById('smtpPort').value,
      smtp_username: document.getElementById('smtpUsername').value.trim(),
      smtp_password: document.getElementById('smtpPassword').value,
      smtp_security: document.getElementById('smtpSecurity').value,
      from_email: document.getElementById('fromEmail').value.trim(),
      from_name: document.getElementById('fromName').value.trim(),
      oauth_tenant_id: document.getElementById('oauthTenantId').value.trim(),
      oauth_client_id: document.getElementById('oauthClientId').value.trim(),
      oauth_client_secret: document.getElementById('oauthClientSecret').value.trim(),
      oauth_refresh_token: document.getElementById('oauthRefreshToken').value.trim(),
      enabled: document.getElementById('smtpEnabled').checked
    }).then(function() {
      return expiryApp.api.getEmailSettings();
    }).then(function(data) {
      fillEmailSettings(data);
      expiryApp.showToast('邮件配置已保存');
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  });

  document.getElementById('testEmailBtn').addEventListener('click', function() {
    var btn = this;
    btn.disabled = true;
    expiryApp.api.testEmailSettings().then(function(resp) {
      expiryApp.showToast('测试邮件已发送到 ' + resp.recipient);
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    }).finally(function() {
      btn.disabled = false;
    });
  });

  document.getElementById('smtpAuthMode').addEventListener('change', function() {
    renderAuthMode(this.value);
  });

  document.getElementById('changePasswordBtn').addEventListener('click', function() {
    var oldPassword = document.getElementById('oldPassword').value;
    var newPassword = document.getElementById('newPassword').value;
    var confirmPassword = document.getElementById('confirmPassword').value;
    if (newPassword !== confirmPassword) {
      expiryApp.showToast('两次输入的新密码不一致');
      return;
    }
    expiryApp.api.changePassword(oldPassword, newPassword).then(function() {
      document.getElementById('oldPassword').value = '';
      document.getElementById('newPassword').value = '';
      document.getElementById('confirmPassword').value = '';
      expiryApp.showToast('密码已更新');
    }).catch(function(err) {
      expiryApp.showToast(err.message);
    });
  });

  expiryApp.ensureAuth().then(function(user) {
    fillUser(user);
    return loadSettings();
  }).catch(function(err) {
    if (err && err.message) expiryApp.showToast(err.message);
  });
})();
