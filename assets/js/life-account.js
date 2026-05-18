(function(global) {
  var ACCOUNT_KEY = 'life_accounts_v1';
  var SESSION_KEY = 'life_session_v1';
  var RESET_KEY = 'life_account_resets_v1';

  var seedAccount = {
    id: 'acct_louise',
    name: 'Louise',
    email: 'louise@example.com',
    password: 'life2026',
    avatar: 'Q1',
    role: 'admin',
    status: 'active',
    createdAt: '2026-05-13',
    lastLoginAt: '',
    deletedAt: '',
    preferences: {
      reminder: true,
      theme: 'light',
      defaultView: 'timeline'
    },
    lifecycle: [
      { label: '创建账号', date: '2026-05-13', status: 'done' },
      { label: '完善资料', date: '2026-05-13', status: 'done' },
      { label: '启用安全设置', date: '2026-05-13', status: 'active' }
    ]
  };

  function nowDate() {
    var date = new Date();
    var month = String(date.getMonth() + 1).padStart(2, '0');
    var day = String(date.getDate()).padStart(2, '0');
    return date.getFullYear() + '-' + month + '-' + day;
  }

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

  function normalizeEmail(value) {
    return String(value || '').trim().toLowerCase();
  }

  function withoutPassword(account) {
    if (!account) return null;
    var clone = {};
    Object.keys(account).forEach(function(key) {
      if (key !== 'password') clone[key] = account[key];
    });
    return clone;
  }

  function ensureAccounts() {
    var accounts = readJson(ACCOUNT_KEY, null);
    if (!Array.isArray(accounts) || accounts.length === 0) {
      writeJson(ACCOUNT_KEY, [seedAccount]);
      return [seedAccount];
    }
    var changed = false;
    accounts.forEach(function(account, index) {
      if (!account.role) {
        account.role = index === 0 ? 'admin' : 'user';
        changed = true;
      }
      if (!account.preferences) {
        account.preferences = {
          reminder: true,
          theme: 'light',
          defaultView: 'timeline'
        };
        changed = true;
      }
    });
    if (changed) writeJson(ACCOUNT_KEY, accounts);
    return accounts;
  }

  function saveAccounts(accounts) {
    writeJson(ACCOUNT_KEY, accounts);
  }

  function listAccounts() {
    return ensureAccounts();
  }

  function findAccountByEmail(email) {
    var normalized = normalizeEmail(email);
    return listAccounts().filter(function(account) {
      return normalizeEmail(account.email) === normalized && account.status !== 'deleted';
    })[0] || null;
  }

  function findAccountById(id) {
    return listAccounts().filter(function(account) {
      return account.id === id && account.status !== 'deleted';
    })[0] || null;
  }

  function setSession(account, remember) {
    var session = {
      accountId: account.id,
      name: account.name,
      email: account.email,
      avatar: account.avatar || 'Q1',
      role: account.role || 'user',
      startedAt: nowDate(),
      remember: !!remember
    };
    writeJson(SESSION_KEY, session);
    return session;
  }

  function getSession() {
    var session = readJson(SESSION_KEY, null);
    if (!session || !session.accountId) return null;
    var account = findAccountById(session.accountId);
    if (!account || account.status !== 'active') return null;
    return Object.assign({}, session, withoutPassword(account));
  }

  function register(data) {
    var name = String(data.name || '').trim();
    var email = normalizeEmail(data.email);
    var password = String(data.password || '');
    if (!name) throw new Error('请输入昵称');
    if (!email || email.indexOf('@') < 1) throw new Error('请输入有效邮箱');
    if (password.length < 6) throw new Error('密码至少需要 6 位');
    if (findAccountByEmail(email)) throw new Error('这个邮箱已经注册');
    var role = data.role === 'admin' ? 'admin' : 'user';
    if (role === 'admin' && String(data.adminCode || '').trim() !== 'LIFE-ADMIN') {
      throw new Error('管理员邀请码不正确');
    }

    var accounts = listAccounts();
    var account = {
      id: 'acct_' + Date.now(),
      name: name,
      email: email,
      password: password,
      avatar: data.avatar || 'Q2',
      role: role,
      status: 'active',
      createdAt: nowDate(),
      lastLoginAt: '',
      deletedAt: '',
      preferences: {
        reminder: true,
        theme: 'light',
        defaultView: 'timeline'
      },
      lifecycle: [
        { label: '创建账号', date: nowDate(), status: 'done' },
        { label: role === 'admin' ? '设置为管理员' : '设置为普通用户', date: nowDate(), status: 'done' },
        { label: '完善资料', date: nowDate(), status: 'active' },
        { label: '启用安全设置', date: '待完成', status: 'todo' }
      ]
    };
    accounts.unshift(account);
    saveAccounts(accounts);
    setSession(account, true);
    return withoutPassword(account);
  }

  function signIn(email, password, remember) {
    var account = findAccountByEmail(email);
    if (!account || account.password !== String(password || '')) {
      throw new Error('邮箱或密码不正确');
    }
    if (account.status === 'inactive') {
      throw new Error('账号已停用，请先恢复账号');
    }
    account.lastLoginAt = nowDate();
    saveAccounts(listAccounts());
    setSession(account, remember);
    return withoutPassword(account);
  }

  function signOut() {
    global.localStorage.removeItem(SESSION_KEY);
  }

  function requestReset(email) {
    var account = findAccountByEmail(email);
    if (!account) throw new Error('没有找到这个邮箱');
    var code = String(Math.floor(100000 + Math.random() * 900000));
    var resets = readJson(RESET_KEY, {});
    resets[normalizeEmail(email)] = {
      code: code,
      requestedAt: nowDate()
    };
    writeJson(RESET_KEY, resets);
    return code;
  }

  function resetPassword(email, code, nextPassword) {
    var normalized = normalizeEmail(email);
    var resets = readJson(RESET_KEY, {});
    var reset = resets[normalized];
    if (!reset || reset.code !== String(code || '').trim()) throw new Error('验证码不正确');
    if (String(nextPassword || '').length < 6) throw new Error('新密码至少需要 6 位');
    var accounts = listAccounts();
    var account = accounts.filter(function(item) {
      return normalizeEmail(item.email) === normalized;
    })[0];
    if (!account) throw new Error('账号不存在');
    account.password = String(nextPassword);
    account.status = 'active';
    account.lifecycle = account.lifecycle || [];
    account.lifecycle.push({ label: '重置密码', date: nowDate(), status: 'done' });
    delete resets[normalized];
    saveAccounts(accounts);
    writeJson(RESET_KEY, resets);
    setSession(account, true);
    return withoutPassword(account);
  }

  function updateProfile(data) {
    var session = getSession();
    if (!session) throw new Error('请先登录');
    var accounts = listAccounts();
    var account = accounts.filter(function(item) { return item.id === session.accountId; })[0];
    var nextEmail = normalizeEmail(data.email || account.email);
    if (!String(data.name || '').trim()) throw new Error('请输入昵称');
    var emailOwner = accounts.filter(function(item) {
      return item.id !== account.id && normalizeEmail(item.email) === nextEmail && item.status !== 'deleted';
    })[0];
    if (emailOwner) throw new Error('这个邮箱已被其他账号使用');
    account.name = String(data.name).trim();
    account.email = nextEmail;
    account.avatar = data.avatar || account.avatar || 'Q1';
    account.preferences = Object.assign({}, account.preferences || {}, data.preferences || {});
    account.lifecycle = account.lifecycle || [];
    account.lifecycle.push({ label: '更新资料', date: nowDate(), status: 'done' });
    saveAccounts(accounts);
    setSession(account, true);
    return withoutPassword(account);
  }

  function changePassword(currentPassword, nextPassword) {
    var session = getSession();
    if (!session) throw new Error('请先登录');
    var accounts = listAccounts();
    var account = accounts.filter(function(item) { return item.id === session.accountId; })[0];
    if (account.password !== String(currentPassword || '')) throw new Error('当前密码不正确');
    if (String(nextPassword || '').length < 6) throw new Error('新密码至少需要 6 位');
    account.password = String(nextPassword);
    account.lifecycle = account.lifecycle || [];
    account.lifecycle.push({ label: '修改密码', date: nowDate(), status: 'done' });
    saveAccounts(accounts);
    return withoutPassword(account);
  }

  function deactivateAccount() {
    var session = getSession();
    if (!session) throw new Error('请先登录');
    var accounts = listAccounts();
    var account = accounts.filter(function(item) { return item.id === session.accountId; })[0];
    account.status = 'inactive';
    account.lifecycle = account.lifecycle || [];
    account.lifecycle.push({ label: '停用账号', date: nowDate(), status: 'done' });
    saveAccounts(accounts);
    signOut();
    return withoutPassword(account);
  }

  function deleteAccount() {
    var session = getSession();
    if (!session) throw new Error('请先登录');
    var accounts = listAccounts();
    var account = accounts.filter(function(item) { return item.id === session.accountId; })[0];
    account.status = 'deleted';
    account.deletedAt = nowDate();
    account.lifecycle = account.lifecycle || [];
    account.lifecycle.push({ label: '删除账号', date: nowDate(), status: 'done' });
    saveAccounts(accounts);
    signOut();
    return withoutPassword(account);
  }

  function requireAdmin() {
    var session = getSession();
    if (!session) throw new Error('请先登录');
    if (session.role !== 'admin') throw new Error('只有管理员可以执行此操作');
    return session;
  }

  function adminCreateAccount(data) {
    var session = requireAdmin();
    var account = register(data);
    writeJson(SESSION_KEY, session);
    return account;
  }

  function adminDeleteAccount(accountId) {
    var session = requireAdmin();
    if (accountId === session.accountId) throw new Error('管理员不能在列表中删除当前登录账号');
    var accounts = listAccounts();
    var target = accounts.filter(function(account) {
      return account.id === accountId && account.status !== 'deleted';
    })[0];
    if (!target) throw new Error('账号不存在');
    target.status = 'deleted';
    target.deletedAt = nowDate();
    target.lifecycle = target.lifecycle || [];
    target.lifecycle.push({ label: '管理员删除账号', date: nowDate(), status: 'done' });
    saveAccounts(accounts);
    return withoutPassword(target);
  }

  global.LifeAccount = {
    keys: {
      accounts: ACCOUNT_KEY,
      session: SESSION_KEY,
      resets: RESET_KEY
    },
    listAccounts: function() {
      return listAccounts().filter(function(account) {
        return account.status !== 'deleted';
      }).map(withoutPassword);
    },
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
    adminDeleteAccount: adminDeleteAccount
  };
})(window);
