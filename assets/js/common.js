/* ===== common.js - 公共工具函数（API 版） ===== */

// 类别对应图标与 CSS class
var CATEGORY_MAP = {
  '交通工具（飞机/动车/自驾）': { icon: '🚆', cls: 'cat-transport' },
  '住宿':     { icon: '🏨', cls: 'cat-hotel' },
  '餐费':     { icon: '🍜', cls: 'cat-food' },
  '打车':     { icon: '🚕', cls: 'cat-taxi' }
};

function getCategoryStyle(name) {
  return CATEGORY_MAP[name] || { icon: '📝', cls: 'cat-other' };
}

// ===== Token 管理 =====
function getToken() {
  return localStorage.getItem('travel_token') || '';
}
function setToken(token) {
  localStorage.setItem('travel_token', token);
}
function clearToken() {
  localStorage.removeItem('travel_token');
}
function isLoggedIn() {
  return !!getToken();
}
function checkAuth() {
  if (!isLoggedIn()) {
    window.location.href = 'login.html';
  }
}
function logout() {
  clearToken();
  window.location.href = 'login.html';
}

// ===== API 封装 =====
var api = {
  _headers: function() {
    var h = { 'Content-Type': 'application/json' };
    var token = getToken();
    if (token) h['Authorization'] = 'Bearer ' + token;
    return h;
  },

  _handleResponse: function(resp) {
    if (resp.status === 401) {
      clearToken();
      window.location.href = 'login.html';
      return Promise.reject(new Error('未登录'));
    }
    return resp.json().then(function(data) {
      if (!resp.ok) return Promise.reject(new Error(data.error || '请求失败'));
      return data;
    });
  },

  // 登录
  login: function(username, password) {
    return fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username, password: password })
    }).then(function(resp) {
      return resp.json().then(function(data) {
        if (!resp.ok) return Promise.reject(new Error(data.error || '登录失败'));
        return data;
      });
    });
  },

  // 旅行
  getTrips: function() {
    return fetch('/api/trips', { headers: api._headers() }).then(api._handleResponse);
  },
  createTrip: function(data) {
    return fetch('/api/trips', {
      method: 'POST', headers: api._headers(), body: JSON.stringify(data)
    }).then(api._handleResponse);
  },
  getTrip: function(id) {
    return fetch('/api/trips/' + id, { headers: api._headers() }).then(api._handleResponse);
  },
  updateTrip: function(id, data) {
    return fetch('/api/trips/' + id, {
      method: 'PUT', headers: api._headers(), body: JSON.stringify(data)
    }).then(api._handleResponse);
  },
  deleteTrip: function(id) {
    return fetch('/api/trips/' + id, {
      method: 'DELETE', headers: api._headers()
    }).then(api._handleResponse);
  },

  // 记录
  createRecord: function(tripId, data) {
    return fetch('/api/trips/' + tripId + '/records', {
      method: 'POST', headers: api._headers(), body: JSON.stringify(data)
    }).then(api._handleResponse);
  },
  updateRecord: function(recId, data) {
    return fetch('/api/records/' + recId, {
      method: 'PUT', headers: api._headers(), body: JSON.stringify(data)
    }).then(api._handleResponse);
  },
  deleteRecord: function(recId) {
    return fetch('/api/records/' + recId, {
      method: 'DELETE', headers: api._headers()
    }).then(api._handleResponse);
  },

  // 支付人
  getPayers: function() {
    return fetch('/api/payers', { headers: api._headers() }).then(api._handleResponse);
  },
  createPayer: function(name) {
    return fetch('/api/payers', {
      method: 'POST', headers: api._headers(), body: JSON.stringify({ name: name })
    }).then(api._handleResponse);
  },
  updatePayer: function(name, newName) {
    return fetch('/api/payers/' + encodeURIComponent(name), {
      method: 'PUT', headers: api._headers(), body: JSON.stringify({ name: newName })
    }).then(api._handleResponse);
  },
  deletePayer: function(name) {
    return fetch('/api/payers/' + encodeURIComponent(name), {
      method: 'DELETE', headers: api._headers()
    }).then(api._handleResponse);
  },

  // 类别
  getCategories: function() {
    return fetch('/api/categories', { headers: api._headers() }).then(api._handleResponse);
  },
  createCategory: function(name) {
    return fetch('/api/categories', {
      method: 'POST', headers: api._headers(), body: JSON.stringify({ name: name })
    }).then(api._handleResponse);
  },
  updateCategory: function(name, newName) {
    return fetch('/api/categories/' + encodeURIComponent(name), {
      method: 'PUT', headers: api._headers(), body: JSON.stringify({ name: newName })
    }).then(api._handleResponse);
  },
  deleteCategory: function(name) {
    return fetch('/api/categories/' + encodeURIComponent(name), {
      method: 'DELETE', headers: api._headers()
    }).then(api._handleResponse);
  },

  // 修改密码
  changePassword: function(oldPassword, newPassword) {
    return fetch('/api/password', {
      method: 'POST', headers: api._headers(), body: JSON.stringify({ oldPassword: oldPassword, newPassword: newPassword })
    }).then(api._handleResponse);
  },

  // 导出Excel
  exportTrip: function(tripId) {
    var token = getToken();
    window.location.href = '/api/trips/' + tripId + '/export?token=' + encodeURIComponent(token);
  }
};

// ===== 格式化 =====
function formatMoney(v) {
  var n = Number(v) || 0;
  return '¥' + n.toFixed(2);
}

// ===== URL 参数 =====
function getUrlParam(name) {
  var reg = new RegExp('[?&]' + name + '=([^&]*)');
  var m = window.location.search.match(reg);
  return m ? decodeURIComponent(m[1]) : null;
}

// ===== 今天日期 =====
function todayStr() {
  var d = new Date();
  var m = d.getMonth() + 1;
  var day = d.getDate();
  return d.getFullYear() + '-' + (m < 10 ? '0' + m : m) + '-' + (day < 10 ? '0' + day : day);
}

// ===== HTML 转义 =====
function escapeHtml(s) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(s || ''));
  return div.innerHTML;
}

// ===== Toast 提示 =====
function showToast(msg, duration) {
  duration = duration || 1500;
  var el = document.getElementById('globalToast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'globalToast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(function() { el.classList.remove('show'); }, duration);
}

// ===== 确认对话框 =====
function showConfirm(msg, onOk) {
  var overlay = document.getElementById('confirmOverlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'confirmOverlay';
    overlay.className = 'confirm-overlay';
    overlay.innerHTML =
      '<div class="confirm-box">' +
        '<div class="confirm-msg" id="confirmMsg"></div>' +
        '<div class="confirm-btns">' +
          '<button class="btn btn-outline" id="confirmCancel">取消</button>' +
          '<button class="btn btn-danger" id="confirmOk">确定</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);
  }
  document.getElementById('confirmMsg').textContent = msg;
  overlay.classList.add('show');
  var okBtn = document.getElementById('confirmOk');
  var cancelBtn = document.getElementById('confirmCancel');
  function cleanup() {
    overlay.classList.remove('show');
    okBtn.onclick = null;
    cancelBtn.onclick = null;
  }
  okBtn.onclick = function() { cleanup(); if (onOk) onOk(); };
  cancelBtn.onclick = function() { cleanup(); };
}
