(function(global) {
  var SESSION_KEY = 'life_session_v2';
  var ACCOUNTS_CACHE_KEY = 'life_accounts_cache_v2';

  var STORE_KEYS = {
    moments: { real: 'life_moments_v1', mock: 'life_mock_moments_v1' },
    axis: { real: 'life_axis_milestones_v1', mock: 'life_mock_axis_milestones_v1' },
    decisions: { real: 'life_decisions_v1', mock: 'life_mock_decisions_v1' },
    moods: { real: 'life_mood_records_v1', mock: 'life_mock_mood_records_v1' },
    relationships: { real: 'life_relationships_v1', mock: 'life_mock_relationships_v1' },
    wishes: { real: 'life_wishes_v1', mock: 'life_mock_wishes_v1' },
    monthly: { real: 'life_monthly_v1', mock: 'life_mock_monthly_v1' },
    watch: { real: 'life_watch_v1', mock: 'life_mock_watch_v1' },
    projects: { real: 'life_projects_v1', mock: 'life_mock_projects_v1' },
    health: { real: 'life_health_records_v1', mock: 'life_mock_health_records_v1' },
    resources: { real: 'life_resources_v1', mock: 'life_mock_resources_v1' }
  };

  var STORE_MODULES = {};
  Object.keys(STORE_KEYS).forEach(function(module) {
    STORE_MODULES[STORE_KEYS[module].real] = module;
    STORE_MODULES[STORE_KEYS[module].mock] = module;
  });

  var STORE_OBJECT_MODULES = {
    axis: true,
    moods: true,
    relationships: true,
    wishes: true,
    watch: true
  };

  var LOCAL_ONLY_STORE_KEYS = [
    'life_decisions_v1_meta',
    'life_mock_decisions_v1_meta'
  ];

  function readJson(key, fallback) {
    try {
      var raw = global.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (err) {
      return fallback;
    }
  }

  function writeJson(key, value) {
    global.localStorage.setItem(key, JSON.stringify(value));
  }

  function clearSession() {
    global.localStorage.removeItem(SESSION_KEY);
  }

  function lifeDataStorageKeys() {
    var keys = [];
    Object.keys(STORE_KEYS).forEach(function(module) {
      keys.push(STORE_KEYS[module].real);
      keys.push(STORE_KEYS[module].mock);
    });
    return keys.concat(LOCAL_ONLY_STORE_KEYS);
  }

  function withStorageSyncSuppressed(work) {
    var previous = !!global.__lifeSuppressStorageSync;
    global.__lifeSuppressStorageSync = true;
    try {
      work();
    } finally {
      global.__lifeSuppressStorageSync = previous;
    }
  }

  function clearLifeDataCache() {
    withStorageSyncSuppressed(function() {
      lifeDataStorageKeys().forEach(function(key) {
        global.localStorage.removeItem(key);
      });
    });
  }

  function getSession() {
    var session = readJson(SESSION_KEY, null);
    if (!session || !session.token || !session.accountId) return null;
    if (session.expiresAt && !Number.isNaN(Date.parse(session.expiresAt)) && Date.parse(session.expiresAt) <= Date.now()) {
      clearSession();
      return null;
    }
    return session;
  }

  function setSession(token, expiresAt, user) {
    var previous = getSession();
    var account = normalizeUser(user);
    if (!previous || previous.accountId !== account.id) {
      clearLifeDataCache();
    }
    var session = {
      token: token,
      expiresAt: expiresAt,
      accountId: account.id,
      id: account.id,
      username: account.username,
      name: account.name,
      email: account.email,
      avatar: account.avatar || 'Q1',
      role: account.role || 'user',
      status: account.status || 'active',
      preferences: account.preferences || { reminder: true, theme: 'light', defaultView: 'timeline' },
      lifecycle: account.lifecycle || [],
      remember: true
    };
    writeJson(SESSION_KEY, session);
    return session;
  }

  function api(path, options) {
    var session = getSession();
    var headers = Object.assign({ 'Content-Type': 'application/json' }, (options && options.headers) || {});
    if (session && session.token) headers.Authorization = 'Bearer ' + session.token;
    return fetch(path, Object.assign({ headers: headers }, options || {})).then(function(resp) {
      return resp.json().catch(function() { return {}; }).then(function(data) {
        if (!resp.ok) {
          throw new Error(data.error || '请求失败');
        }
        return data;
      });
    });
  }

  function normalizeUser(user) {
    return {
      id: user.id,
      username: user.username || '',
      name: user.name || '',
      email: user.email || '',
      avatar: user.avatar || 'Q1',
      role: user.role || 'user',
      status: user.status || 'active',
      createdAt: user.created_at || user.createdAt || '',
      updatedAt: user.updated_at || user.updatedAt || '',
      lastLoginAt: user.last_login_at || user.lastLoginAt || '',
      deletedAt: user.deleted_at || user.deletedAt || '',
      preferences: user.preferences || { reminder: true, theme: 'light', defaultView: 'timeline' },
      lifecycle: user.lifecycle || []
    };
  }

  function cacheAccounts(items) {
    writeJson(ACCOUNTS_CACHE_KEY, (items || []).map(normalizeUser));
  }

  function listAccounts() {
    return readJson(ACCOUNTS_CACHE_KEY, []);
  }

  function refreshAccounts() {
    return api('/api/life/admin/users', { method: 'GET' }).then(function(data) {
      var items = (data.items || []).filter(function(item) { return item.status !== 'deleted'; });
      cacheAccounts(items);
      return listAccounts();
    });
  }

  function refreshSession() {
    var session = getSession();
    if (!session || !session.token) return Promise.resolve(null);
    return api('/api/life/auth/me', { method: 'GET' }).then(function(user) {
      setSession(session.token, session.expiresAt, user || {});
      return normalizeUser(user || {});
    }).catch(function(err) {
      clearSession();
      clearLifeDataCache();
      return null;
    });
  }

  function signIn(email, password, remember) {
    return api('/api/life/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: String(email || '').trim().toLowerCase(),
        password: String(password || ''),
        remember: !!remember
      })
    }).then(function(data) {
      setSession(data.token, data.expires_at, data.user || {});
      return normalizeUser(data.user || {});
    });
  }

  function register(payload) {
    return api('/api/life/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: payload.name,
        email: String(payload.email || '').trim().toLowerCase(),
        password: payload.password,
        role: payload.role,
        avatar: payload.avatar || 'Q2',
        adminCode: payload.adminCode || ''
      })
    }).then(function(data) {
      setSession(data.token, data.expires_at, data.user || {});
      return normalizeUser(data.user || {});
    });
  }

  function signOut() {
    var hadSession = !!getSession();
    if (!hadSession) return Promise.resolve(true);
    return api('/api/life/auth/logout', { method: 'POST' }).catch(function() {
      return true;
    }).then(function() {
      clearSession();
      clearLifeDataCache();
      return true;
    });
  }

  function requestReset(email) {
    return api('/api/life/auth/recover/request', {
      method: 'POST',
      body: JSON.stringify({ email: String(email || '').trim().toLowerCase() })
    }).then(function(data) { return data.code; });
  }

  function resetPassword(email, code, nextPassword) {
    return api('/api/life/auth/recover/confirm', {
      method: 'POST',
      body: JSON.stringify({
        email: String(email || '').trim().toLowerCase(),
        code: String(code || '').trim(),
        password: String(nextPassword || '')
      })
    }).then(function(data) {
      setSession(data.token, data.expires_at, data.user || {});
      return normalizeUser(data.user || {});
    });
  }

  function updateProfile(payload) {
    return api('/api/life/auth/profile', {
      method: 'PUT',
      body: JSON.stringify({
        name: payload.name,
        email: String(payload.email || '').trim().toLowerCase(),
        avatar: payload.avatar || 'Q1',
        preferences: payload.preferences || {}
      })
    }).then(function(data) {
      var session = getSession();
      if (session && data.user) {
        setSession(session.token, session.expiresAt, data.user);
      }
      return normalizeUser(data.user || {});
    });
  }

  function changePassword(currentPassword, nextPassword) {
    return api('/api/life/auth/password', {
      method: 'POST',
      body: JSON.stringify({
        oldPassword: String(currentPassword || ''),
        newPassword: String(nextPassword || '')
      })
    });
  }

  function deactivateAccount() {
    return api('/api/life/auth/deactivate', { method: 'POST' }).then(function() {
      clearSession();
      clearLifeDataCache();
      return true;
    });
  }

  function deleteAccount() {
    return api('/api/life/auth/me', { method: 'DELETE' }).then(function() {
      clearSession();
      clearLifeDataCache();
      return true;
    });
  }

  function adminCreateAccount(payload) {
    return api('/api/life/admin/users', {
      method: 'POST',
      body: JSON.stringify({
        name: payload.name,
        email: String(payload.email || '').trim().toLowerCase(),
        password: payload.password,
        role: payload.role,
        avatar: payload.avatar || (payload.role === 'admin' ? 'Q1' : 'Q2'),
        adminCode: payload.adminCode || 'LIFE-ADMIN'
      })
    }).then(function(data) {
      return refreshAccounts().then(function() { return normalizeUser(data.user || {}); });
    });
  }

  function adminDeleteAccount(accountId) {
    return api('/api/life/admin/users/' + encodeURIComponent(accountId), {
      method: 'DELETE'
    }).then(function() {
      return refreshAccounts().then(function() { return true; });
    });
  }

  function adminSetAccountStatus(accountId, status) {
    return api('/api/life/admin/users/' + encodeURIComponent(accountId), {
      method: 'PATCH',
      body: JSON.stringify({
        status: status
      })
    }).then(function(data) {
      return refreshAccounts().then(function() { return normalizeUser(data.user || {}); });
    });
  }

  function adminResetPassword(accountId, nextPassword) {
    return api('/api/life/admin/users/' + encodeURIComponent(accountId) + '/reset-password', {
      method: 'POST',
      body: JSON.stringify({
        password: String(nextPassword || '')
      })
    }).then(function() {
      return true;
    });
  }

  function syncLifeData(options) {
    var session = getSession();
    if (!session || !session.token) return Promise.resolve(null);
    var mock = !!(options && options.mock);
    return api('/api/life/bootstrap?mode=' + (mock ? 'mock' : 'real'), { method: 'GET' }).then(function(data) {
      var modules = data.data || {};
      var storage = data.storage || {};
      Object.keys(STORE_KEYS).forEach(function(module) {
        var key = mock ? STORE_KEYS[module].mock : STORE_KEYS[module].real;
        if (mock) {
          writeJson(
            key,
            Object.prototype.hasOwnProperty.call(modules, module)
              ? storageValueFromModuleRecords(module, modules[module] || [])
              : (Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : storageValueFromModuleRecords(module, []))
          );
          return;
        }
        if (!mock && Object.prototype.hasOwnProperty.call(modules, module)) {
          writeJson(key, storageValueFromModuleRecords(module, modules[module] || []));
        }
      });
      if (session && data.user) {
        setSession(session.token, session.expiresAt, data.user);
      }
      return modules;
    });
  }

  function storageValueFromModuleRecords(module, records) {
    var items = Array.isArray(records) ? records : [];
    if (module === 'monthly') {
      var first = items[0] || {};
      var monthly = Object.assign({}, first);
      delete monthly.id;
      delete monthly.isTestData;
      delete monthly.dataTag;
      delete monthly.dataScope;
      delete monthly._syncBridge;
      delete monthly.originalId;
      return monthly;
    }
    if (STORE_OBJECT_MODULES[module]) {
      return { added: items, edits: {}, deleted: [] };
    }
    return items;
  }

  function moduleRecordsFromStorageValue(module, value) {
    if (Array.isArray(value)) return value.filter(function(item) { return item && typeof item === 'object'; });
    if (!value || typeof value !== 'object') return [];
    if (module === 'monthly') {
      return [Object.assign({ id: 'monthly-state' }, value)];
    }
    var deleted = (value.deleted || []).map(function(id) { return String(id); });
    var byId = {};
    (value.added || []).forEach(function(item) {
      if (!item || typeof item !== 'object') return;
      if (deleted.indexOf(String(item.id || '')) >= 0) return;
      byId[String(item.id || ('local-' + Date.now()))] = Object.assign({}, item);
    });
    Object.keys(value.edits || {}).forEach(function(id) {
      if (deleted.indexOf(String(id)) >= 0) return;
      var item = value.edits[id];
      if (!item || typeof item !== 'object') return;
      byId[String(id)] = Object.assign({}, byId[String(id)] || { id: id }, item, { id: id });
    });
    return Object.keys(byId).map(function(id) { return byId[id]; });
  }

  function isBackendCacheRecord(item) {
    var scope = item && String(item.dataScope || '');
    return scope === 'server_mock_fixture' || scope === 'sync_bridge_test';
  }

  function pruneBackendCacheRecords(module, value) {
    if (Array.isArray(value)) {
      return value.filter(function(item) {
        return item && typeof item === 'object' && !isBackendCacheRecord(item);
      });
    }
    if (!value || typeof value !== 'object') return value;
    if (module === 'monthly') return isBackendCacheRecord(value) ? {} : value;
    if (Array.isArray(value.added) || typeof value.edits === 'object') {
      var next = Object.assign({}, value);
      next.added = (value.added || []).filter(function(item) {
        return item && typeof item === 'object' && !isBackendCacheRecord(item);
      });
      next.edits = Object.assign({}, value.edits || {});
      Object.keys(next.edits).forEach(function(id) {
        if (isBackendCacheRecord(next.edits[id])) delete next.edits[id];
      });
      next.deleted = (value.deleted || []).slice();
      return next;
    }
    return isBackendCacheRecord(value) ? {} : value;
  }

  function syncStorageItem(storageKey, value, mock) {
    var session = getSession();
    if (!session || !session.token) return Promise.resolve(true);
    var module = STORE_MODULES[storageKey];
    if (!mock && module) {
      return api('/api/life/snapshot/' + encodeURIComponent(module), {
        method: 'PUT',
        body: JSON.stringify({
          mode: 'real',
          items: moduleRecordsFromStorageValue(module, value)
        })
      }).then(function() { return true; });
    }
    return api('/api/life/storage/' + encodeURIComponent(storageKey), {
      method: 'PUT',
      body: JSON.stringify({
        mode: mock ? 'mock' : 'real',
        value: value
      })
    }).then(function() { return true; });
  }

  function syncLocalStorageToMockStorage(keys) {
    var session = getSession();
    if (!session || !session.token) return Promise.resolve(false);
    var allowed = {};
    (Array.isArray(keys) && keys.length ? keys : lifeDataStorageKeys()).forEach(function(key) {
      allowed[key] = true;
    });
    function hasModuleData(module, value) {
      if (module === 'monthly') return !!(value && typeof value === 'object' && Object.keys(value).length);
      if (Array.isArray(value)) return value.length > 0;
      if (value && typeof value === 'object') {
        if (Array.isArray(value.added) || typeof value.edits === 'object') {
          var editsSize = value.edits && typeof value.edits === 'object' ? Object.keys(value.edits).length : 0;
          return (value.added || []).length > 0 || editsSize > 0;
        }
        return Object.keys(value).length > 0;
      }
      return false;
    }
    var tasks = [];
    Object.keys(STORE_KEYS).forEach(function(module) {
      var realKey = STORE_KEYS[module].real;
      var mockKey = STORE_KEYS[module].mock;
      if (!allowed[realKey] && !allowed[mockKey]) return;
      var realExists = global.localStorage.getItem(realKey) != null;
      var mockExists = global.localStorage.getItem(mockKey) != null;
      if (!realExists && !mockExists) return;
      var realValue = realExists ? pruneBackendCacheRecords(module, readJson(realKey, [])) : null;
      var mockValue = mockExists ? pruneBackendCacheRecords(module, readJson(mockKey, [])) : null;
      var hasMockData = mockExists && hasModuleData(module, mockValue);
      var hasRealData = realExists && hasModuleData(module, realValue);
      if (hasMockData) {
        tasks.push(syncStorageItem(mockKey, mockValue, true).catch(function() {
          return false;
        }));
      }
      if (hasRealData) {
        tasks.push(syncStorageItem(realKey, realValue, true).catch(function() {
          return false;
        }));
      }
      if (!hasMockData && !hasRealData) {
        var fallbackKey = mockExists ? mockKey : realKey;
        var fallbackValue = mockExists ? mockValue : realValue;
        tasks.push(syncStorageItem(fallbackKey, fallbackValue, true).catch(function() {
          return false;
        }));
      }
    });
    if (!tasks.length) return Promise.resolve(false);
    return Promise.all(tasks).then(function() {
      return true;
    });
  }

  global.LifeAccount = {
    keys: {
      session: SESSION_KEY,
      accounts: ACCOUNTS_CACHE_KEY
    },
    listAccounts: listAccounts,
    refreshAccounts: refreshAccounts,
    refreshSession: refreshSession,
    getSession: getSession,
    register: register,
    signIn: signIn,
    signOut: signOut,
    requestReset: requestReset,
    resetPassword: resetPassword,
    updateProfile: updateProfile,
    changePassword: changePassword,
    deactivateAccount: deactivateAccount,
    deleteAccount: deleteAccount,
    adminCreateAccount: adminCreateAccount,
    adminDeleteAccount: adminDeleteAccount,
    adminSetAccountStatus: adminSetAccountStatus,
    adminResetPassword: adminResetPassword,
    syncLifeData: syncLifeData,
    syncStorageItem: syncStorageItem,
    syncLocalStorageToMockStorage: syncLocalStorageToMockStorage
  };
})(window);
