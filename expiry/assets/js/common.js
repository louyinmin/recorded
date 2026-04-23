var expiryApp = (function() {
  var STORAGE_KEY = 'expiry_token';
  var USER_KEY = 'expiry_user';

  function getToken() {
    return localStorage.getItem(STORAGE_KEY) || '';
  }

  function setToken(token) {
    localStorage.setItem(STORAGE_KEY, token || '');
  }

  function clearToken() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function setUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user || {}));
  }

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || '{}');
    } catch (err) {
      return {};
    }
  }

  function request(url, options) {
    var opts = options || {};
    opts.headers = opts.headers || {};
    if (!opts.headers['Content-Type'] && opts.body && !(opts.body instanceof FormData)) {
      opts.headers['Content-Type'] = 'application/json';
    }
    var token = getToken();
    if (token) {
      opts.headers.Authorization = 'Bearer ' + token;
    }
    return fetch(url, opts).then(function(resp) {
      if (resp.status === 401) {
        clearToken();
        window.location.href = '/expiry/login.html';
        return Promise.reject(new Error('登录已过期'));
      }
      return resp.json().then(function(data) {
        if (!resp.ok) {
          return Promise.reject(new Error(data.error || '请求失败'));
        }
        return data;
      });
    });
  }

  function ensureAuth() {
    if (!getToken()) {
      window.location.href = '/expiry/login.html';
      return Promise.reject(new Error('未登录'));
    }
    return api.me().then(function(user) {
      setUser(user);
      return user;
    });
  }

  function logout() {
    return api.logout().catch(function() {
      return null;
    }).then(function() {
      clearToken();
      window.location.href = '/expiry/login.html';
    });
  }

  function formatMoney(value) {
    var num = Number(value || 0);
    return '¥' + num.toFixed(2);
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(text || ''));
    return div.innerHTML;
  }

  function statusLabel(state) {
    return {
      active: '仍在使用',
      upcoming: '即将到期',
      expired: '已过期',
      stopped: '已停用'
    }[state] || '未知状态';
  }

  function cycleLabel(cycle) {
    return {
      monthly: '月付',
      yearly: '年付',
      none: '一次性'
    }[cycle] || '-';
  }

  function formatDate(value) {
    return value || '--';
  }

  function showToast(message) {
    var el = document.getElementById('expiryToast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'expiryToast';
      el.className = 'expiry-toast';
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(function() {
      el.classList.remove('show');
    }, 2200);
  }

  function closeModalById(id) {
    var modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
  }

  function bindModalClose() {
    var closers = document.querySelectorAll('[data-close]');
    for (var i = 0; i < closers.length; i++) {
      closers[i].addEventListener('click', function() {
        closeModalById(this.getAttribute('data-close'));
      });
    }
  }

  var api = {
    login: function(username, password) {
      return request('/api/expiry/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username: username, password: password })
      });
    },
    logout: function() {
      return request('/api/expiry/auth/logout', { method: 'POST' });
    },
    me: function() {
      return request('/api/expiry/auth/me');
    },
    changePassword: function(oldPassword, newPassword) {
      return request('/api/expiry/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
      });
    },
    getDashboard: function() {
      return request('/api/expiry/dashboard');
    },
    getStats: function(year) {
      return request('/api/expiry/stats?year=' + encodeURIComponent(year));
    },
    getResources: function(params) {
      var query = new URLSearchParams(params || {});
      return request('/api/expiry/resources?' + query.toString());
    },
    createResource: function(data) {
      return request('/api/expiry/resources', {
        method: 'POST',
        body: JSON.stringify(data)
      });
    },
    getResource: function(id) {
      return request('/api/expiry/resources/' + encodeURIComponent(id));
    },
    updateResource: function(id, data) {
      return request('/api/expiry/resources/' + encodeURIComponent(id), {
        method: 'PUT',
        body: JSON.stringify(data)
      });
    },
    deleteResource: function(id) {
      return request('/api/expiry/resources/' + encodeURIComponent(id), {
        method: 'DELETE'
      });
    },
    stopResource: function(id) {
      return request('/api/expiry/resources/' + encodeURIComponent(id) + '/stop', { method: 'POST' });
    },
    resumeResource: function(id) {
      return request('/api/expiry/resources/' + encodeURIComponent(id) + '/resume', { method: 'POST' });
    },
    getNotifications: function() {
      return request('/api/expiry/notifications');
    },
    readNotification: function(id) {
      return request('/api/expiry/notifications/' + encodeURIComponent(id) + '/read', { method: 'POST' });
    },
    getProfile: function() {
      return request('/api/expiry/settings/profile');
    },
    saveProfile: function(data) {
      return request('/api/expiry/settings/profile', {
        method: 'PUT',
        body: JSON.stringify(data)
      });
    },
    getEmailSettings: function() {
      return request('/api/expiry/settings/email');
    },
    saveEmailSettings: function(data) {
      return request('/api/expiry/settings/email', {
        method: 'PUT',
        body: JSON.stringify(data)
      });
    },
    testEmailSettings: function() {
      return request('/api/expiry/settings/email/test', {
        method: 'POST'
      });
    },
    getReminderSettings: function() {
      return request('/api/expiry/settings/reminders');
    },
    saveReminderSettings: function(data) {
      return request('/api/expiry/settings/reminders', {
        method: 'PUT',
        body: JSON.stringify(data)
      });
    },
    adminUsers: function() {
      return request('/api/expiry/admin/users');
    },
    adminCreateUser: function(data) {
      return request('/api/expiry/admin/users', {
        method: 'POST',
        body: JSON.stringify(data)
      });
    },
    adminUpdateUser: function(id, data) {
      return request('/api/expiry/admin/users/' + encodeURIComponent(id), {
        method: 'PUT',
        body: JSON.stringify(data)
      });
    },
    adminResetPassword: function(id, password) {
      return request('/api/expiry/admin/users/' + encodeURIComponent(id) + '/reset-password', {
        method: 'POST',
        body: JSON.stringify(password ? { password: password } : {})
      });
    },
    adminToggleStatus: function(id) {
      return request('/api/expiry/admin/users/' + encodeURIComponent(id) + '/toggle-status', {
        method: 'POST'
      });
    }
  };

  return {
    api: api,
    getToken: getToken,
    setToken: setToken,
    clearToken: clearToken,
    setUser: setUser,
    getUser: getUser,
    ensureAuth: ensureAuth,
    logout: logout,
    formatMoney: formatMoney,
    formatDate: formatDate,
    escapeHtml: escapeHtml,
    statusLabel: statusLabel,
    cycleLabel: cycleLabel,
    showToast: showToast,
    bindModalClose: bindModalClose
  };
})();
