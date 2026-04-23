(function() {
  var loginBtn = document.getElementById('loginBtn');
  var username = document.getElementById('username');
  var password = document.getElementById('password');
  var errorEl = document.getElementById('loginError');

  if (expiryApp.getToken()) {
    expiryApp.ensureAuth().then(function() {
      window.location.href = '/expiry/dashboard.html';
    }).catch(function() {});
  }

  function submit() {
    errorEl.textContent = '';
    loginBtn.disabled = true;
    expiryApp.api.login(username.value.trim(), password.value).then(function(data) {
      expiryApp.setToken(data.token);
      expiryApp.setUser(data.user);
      window.location.href = '/expiry/dashboard.html';
    }).catch(function(err) {
      errorEl.textContent = err.message;
      errorEl.classList.add('show');
      loginBtn.disabled = false;
    });
  }

  loginBtn.addEventListener('click', submit);
  password.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') submit();
  });
})();
