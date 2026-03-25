(function() {
  // 如果已登录，直接跳转
  if (isLoggedIn()) {
    window.location.href = 'trips.html';
    return;
  }

  var usernameInput = document.getElementById('username');
  var passwordInput = document.getElementById('password');
  var loginBtn = document.getElementById('loginBtn');
  var loginError = document.getElementById('loginError');

  function doLogin() {
    var user = usernameInput.value.trim();
    var pass = passwordInput.value;
    if (!user || !pass) {
      loginError.textContent = '请输入账号和密码';
      loginError.classList.add('show');
      setTimeout(function() { loginError.classList.remove('show'); }, 2000);
      return;
    }
    loginBtn.disabled = true;
    loginBtn.textContent = '登录中...';
    api.login(user, pass).then(function(data) {
      setToken(data.token);
      window.location.href = 'trips.html';
    }).catch(function(err) {
      loginError.textContent = err.message || '账号或密码错误';
      loginError.classList.add('show');
      setTimeout(function() { loginError.classList.remove('show'); }, 2000);
      loginBtn.disabled = false;
      loginBtn.textContent = '登 录';
    });
  }

  loginBtn.addEventListener('click', doLogin);
  passwordInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') doLogin();
  });
  usernameInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') passwordInput.focus();
  });
})();
