(function() {
  checkAuth();

  var tripListEl = document.getElementById('tripList');
  var statsBarEl = document.getElementById('statsBar');
  var settingsBtn = document.getElementById('settingsBtn');
  var newTripBtn = document.getElementById('newTripBtn');
  var logoutBtn = document.getElementById('logoutBtn');
  var newTripModal = document.getElementById('newTripModal');
  var closeNewTrip = document.getElementById('closeNewTrip');
  var saveTripBtn = document.getElementById('saveTripBtn');
  var tripNameInput = document.getElementById('tripName');
  var tripStartInput = document.getElementById('tripStart');
  var tripEndInput = document.getElementById('tripEnd');
  var tripNoteInput = document.getElementById('tripNote');

  // 渲染页面
  function render() {
    api.getTrips().then(function(trips) {
      renderStats(trips);
      renderList(trips);
    }).catch(function(err) {
      showToast('加载失败: ' + err.message);
    });
  }

  // 统计栏
  function renderStats(trips) {
    var totalTrips = trips.length;
    var totalAmount = 0;
    for (var i = 0; i < trips.length; i++) {
      totalAmount += Number(trips[i].total_amount) || 0;
    }
    statsBarEl.innerHTML =
      '<div class="stat-item"><div class="stat-value">' + totalTrips + '</div><div class="stat-label">旅行次数</div></div>' +
      '<div class="stat-item"><div class="stat-value">' + formatMoney(totalAmount) + '</div><div class="stat-label">累计花费</div></div>';
  }

  // 旅行卡片列表
  function renderList(trips) {
    if (trips.length === 0) {
      tripListEl.innerHTML =
        '<div class="empty-state">' +
          '<div class="empty-state-icon">🧳</div>' +
          '<div class="empty-state-text">还没有旅行记录<br>点击右上角「新建旅行」开始记账</div>' +
        '</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < trips.length; i++) {
      var t = trips[i];
      var total = Number(t.total_amount) || 0;
      var payerNames = t.payers || [];
      var dateStr = '';
      if (t.start_date) {
        dateStr = t.start_date;
        if (t.end_date && t.end_date !== t.start_date) dateStr += ' ~ ' + t.end_date;
      }
      html +=
        '<div class="card card-clickable" data-id="' + t.id + '">' +
          '<div class="card-header">' +
            '<div class="card-title">' + escapeHtml(t.name) + '</div>' +
            '<div class="card-amount">' + formatMoney(total) + '</div>' +
          '</div>' +
          (dateStr ? '<div class="card-meta">📅 ' + dateStr + '</div>' : '') +
          '<div class="card-meta">' + (t.record_count || 0) + ' 条记录</div>' +
          (payerNames.length > 0 ?
            '<div class="card-tags">' + payerNames.map(function(n) { return '<span class="card-tag">' + escapeHtml(n) + '</span>'; }).join('') + '</div>'
            : '') +
        '</div>';
    }
    tripListEl.innerHTML = html;

    // 绑定点击事件
    var cards = tripListEl.querySelectorAll('.card-clickable');
    for (var j = 0; j < cards.length; j++) {
      cards[j].addEventListener('click', function() {
        window.location.href = 'trip.html?id=' + this.getAttribute('data-id');
      });
    }
  }

  // 打开/关闭新建旅行弹窗
  function openModal() {
    tripNameInput.value = '';
    tripStartInput.value = todayStr();
    tripEndInput.value = '';
    tripNoteInput.value = '';
    newTripModal.classList.add('show');
  }
  function closeModal() {
    newTripModal.classList.remove('show');
  }

  newTripBtn.addEventListener('click', openModal);
  closeNewTrip.addEventListener('click', closeModal);
  newTripModal.addEventListener('click', function(e) {
    if (e.target === newTripModal) closeModal();
  });

  // 保存新旅行
  saveTripBtn.addEventListener('click', function() {
    var name = tripNameInput.value.trim();
    if (!name) {
      showToast('请输入旅行名称');
      return;
    }
    saveTripBtn.disabled = true;
    api.createTrip({
      name: name,
      startDate: tripStartInput.value,
      endDate: tripEndInput.value,
      note: tripNoteInput.value.trim()
    }).then(function(data) {
      closeModal();
      showToast('创建成功');
      window.location.href = 'trip.html?id=' + data.id;
    }).catch(function(err) {
      showToast('创建失败: ' + err.message);
      saveTripBtn.disabled = false;
    });
  });

  // 退出
  logoutBtn.addEventListener('click', function() {
    logout();
  });

  // 设置
  settingsBtn.addEventListener('click', function() {
    window.location.href = 'settings.html';
  });

  render();
})();
