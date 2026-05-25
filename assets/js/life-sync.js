(function(global) {
  var KEY_TO_SYNC = {
    life_moments_v1: true,
    life_mock_moments_v1: true,
    life_axis_milestones_v1: true,
    life_mock_axis_milestones_v1: true,
    life_decisions_v1: true,
    life_mock_decisions_v1: true,
    life_mood_records_v1: true,
    life_mock_mood_records_v1: true,
    life_relationships_v1: true,
    life_mock_relationships_v1: true,
    life_wishes_v1: true,
    life_mock_wishes_v1: true,
    life_monthly_v1: true,
    life_mock_monthly_v1: true,
    life_watch_v1: true,
    life_mock_watch_v1: true,
    life_projects_v1: true,
    life_mock_projects_v1: true,
    life_health_records_v1: true,
    life_mock_health_records_v1: true,
    life_resources_v1: true,
    life_mock_resources_v1: true
  };

  var timers = {};
  var silent = false;
  var rawSetItem = global.localStorage.setItem.bind(global.localStorage);
  var rawRemoveItem = global.localStorage.removeItem.bind(global.localStorage);

  function isMockKey(key) {
    return String(key || '').indexOf('life_mock_') === 0;
  }

  function parseJson(text) {
    try {
      return JSON.parse(text || '[]');
    } catch (err) {
      return [];
    }
  }

  function scheduleSync(key) {
    if (!KEY_TO_SYNC[key] || !global.LifeAccount || !global.LifeAccount.syncStorageItem) return;
    if (timers[key]) clearTimeout(timers[key]);
    timers[key] = setTimeout(function() {
      var value = parseJson(global.localStorage.getItem(key));
      global.LifeAccount.syncStorageItem(key, value, isMockKey(key)).catch(function() {
        return false;
      });
    }, 380);
  }

  global.localStorage.setItem = function(key, value) {
    rawSetItem(key, value);
    if (!silent && !global.__lifeSuppressStorageSync) scheduleSync(key);
  };

  global.localStorage.removeItem = function(key) {
    rawRemoveItem(key);
    if (!silent && !global.__lifeSuppressStorageSync) scheduleSync(key);
  };

  function bootstrapFromBackend() {
    if (!global.LifeAccount || !global.LifeAccount.syncLifeData) return Promise.resolve(false);
    var mock = new URLSearchParams(global.location.search).get('mock') === '1';
    silent = true;
    var preflight = mock && global.LifeAccount.syncLocalStorageToMockStorage
      ? global.LifeAccount.syncLocalStorageToMockStorage(Object.keys(KEY_TO_SYNC))
      : Promise.resolve(false);
    return preflight.then(function() {
      return global.LifeAccount.syncLifeData({ mock: mock });
    }).then(function() {
      silent = false;
      global.dispatchEvent(new CustomEvent('life:data-synced'));
      return true;
    }).catch(function() {
      silent = false;
      return false;
    });
  }

  global.__lifeDataReady = bootstrapFromBackend();
})(window);
