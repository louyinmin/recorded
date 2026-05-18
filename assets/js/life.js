(function() {
  var STORAGE_KEY = 'life_moments_v1';
  var MOCK_STORAGE_KEY = 'life_mock_moments_v1';
  var AXIS_STORAGE_KEY = 'life_axis_milestones_v1';
  var MOCK_AXIS_STORAGE_KEY = 'life_mock_axis_milestones_v1';
  var DECISION_STORAGE_KEY = 'life_decisions_v1';
  var MOCK_DECISION_STORAGE_KEY = 'life_mock_decisions_v1';
  var MOOD_STORAGE_KEY = 'life_mood_records_v1';
  var MOCK_MOOD_STORAGE_KEY = 'life_mock_mood_records_v1';
  var RELATIONSHIP_STORAGE_KEY = 'life_relationships_v1';
  var MOCK_RELATIONSHIP_STORAGE_KEY = 'life_mock_relationships_v1';
  var WISH_STORAGE_KEY = 'life_wishes_v1';
  var MOCK_WISH_STORAGE_KEY = 'life_mock_wishes_v1';
  var MONTHLY_STORAGE_KEY = 'life_monthly_v1';
  var MOCK_MONTHLY_STORAGE_KEY = 'life_mock_monthly_v1';
  var PROJECT_STORAGE_KEY = 'life_projects_v1';
  var MOCK_PROJECT_STORAGE_KEY = 'life_mock_projects_v1';
  var HEALTH_STORAGE_KEY = 'life_health_records_v1';
  var MOCK_HEALTH_STORAGE_KEY = 'life_mock_health_records_v1';
  var state = {
    view: 'timeline',
    query: '',
    timelineFilter: '全部',
    axisCategory: '全部',
    axisYear: '全部',
    axisStage: '全部',
    axisFilterOpen: false,
    axisEditing: false,
    decisionFilter: '重要决定',
    decisionFormMode: null,
    decisionMoreOpen: false,
    moodTab: 'overview',
    moodYear: 2026,
    moodMonth: 4,
    selectedMoodDay: 13,
    moodRange: '近 14 天',
    moodSleepRange: '近 14 天',
    moodTriggerRange: '近 7 天',
    moodWeekRange: '05-04 ~ 05-10',
    moodRangeMenu: null,
    moodFormMode: null,
    moodEditingId: '',
    relationshipFilter: '全部',
    relationshipSort: '亲密度',
    relationshipFormMode: null,
    relationshipEditingId: '',
    relationshipInlineEditor: '',
    wishFilter: '愿望冷却中',
    wishCategory: '全部',
    wishSort: '按剩余天数排序',
    wishFormMode: null,
    monthlyYear: 2026,
    monthlyMonth: 4,
    monthlyLetterMode: false,
    monthlyQuoteMode: false,
    accountAdminCreateOpen: false,
    selectedMomentId: 'm1',
    selectedAxisId: 'a7',
    selectedDecisionId: 'd1',
    selectedRelationshipId: 'r1',
    selectedWishId: 'w1'
  };

  var els = {
    title: document.getElementById('lifeTitle'),
    content: document.getElementById('lifeContent'),
    aside: document.getElementById('lifeAside'),
    search: document.getElementById('lifeSearch'),
    mockModeBtn: document.getElementById('mockModeBtn'),
    toast: document.getElementById('lifeToast')
  };

  var mockMode = new URLSearchParams(window.location.search).get('mock') === '1';

  function lifeAccount() {
    return window.LifeAccount || null;
  }

  function accountSession() {
    return lifeAccount() ? lifeAccount().getSession() : null;
  }

  function accountAvatarKey(account) {
    return String((account && account.avatar) || 'Q1').toLowerCase();
  }

  function accountRoleText(account) {
    return account && account.role === 'admin' ? '管理员' : '普通用户';
  }

  var viewTitles = {
    timeline: '生活航迹',
    'life-axis': '人生时间轴',
    decisions: '决策档案馆',
    mood: '情绪天气站',
    relationships: '关系温度',
    wishes: '愿望冷却箱',
    monthly: '本月值得记住',
    add: '添加一刻',
    projects: '项目与目标',
    health: '健康与身体',
    review: '复盘与回顾',
    resources: '资源库',
    profile: '个人档案'
  };

  var seedMoments = [
    {
      id: 'm1',
      type: '情绪',
      icon: '☀',
      time: '09:30',
      date: '今天 05-13',
      title: '今日心情：晴朗 78/100',
      copy: '早上起来阳光很好，心情也跟着明亮起来。',
      location: '情绪天气站',
      people: [],
      mood: '晴朗',
      photos: ['photo-river'],
      tags: ['情绪', '睡眠 7.2h', '压力 35/100'],
      linkedMoodDate: '2026-05-13'
    },
    {
      id: 'm2',
      type: '决策',
      icon: '♎',
      time: '10:45',
      date: '今天 05-13',
      title: '是否接受新工作的 Offer？',
      copy: '我的选择：接受新 Offer；信心 70/100，计划 2026-10-20 复盘。',
      location: '决策档案馆',
      people: ['HR', '张敏'],
      mood: '期待',
      photos: [],
      tags: ['重要决定', '职业发展', '待复盘'],
      linkedDecision: 'd1'
    },
    {
      id: 'm3',
      type: '关系',
      icon: '♟',
      time: '14:20',
      date: '今天 05-13',
      title: '关系温度：张敏',
      copy: '最近联系：昨天 · 微信；亲密度 88/100，下次联系 4 天后。',
      location: '关系温度',
      people: ['张敏'],
      mood: '平静',
      photos: [],
      tags: ['关系', '朋友', '提醒'],
      linkedRelationship: 'r3'
    },
    {
      id: 'm4',
      type: '愿望',
      icon: '❄',
      time: '16:40',
      date: '今天 05-13',
      title: '愿望冷却：相机 Sony A7C II',
      copy: '剩余 12 天，当前想要程度 72%，价格 ¥12,999。',
      location: '愿望冷却箱',
      people: [],
      mood: '兴奋',
      photos: ['photo-camera'],
      tags: ['愿望', '数码', '冷却中'],
      linkedWish: 'w1'
    },
    {
      id: 'm5',
      type: '旅行',
      icon: '▣',
      time: '20:15',
      date: '今天 05-13',
      title: '苏州一日游',
      copy: '和家人一起在苏州逛园林，吃了很绵的苏帮菜。',
      location: '苏州 · 拙政园',
      people: ['妈妈', '爸爸'],
      mood: '愉快',
      photos: ['photo-garden', 'photo-river', 'photo-night'],
      tags: ['旅行', '家人', '本月值得记住'],
      linkedView: 'monthly'
    },
    {
      id: 'm6',
      type: '项目',
      icon: '✓',
      time: '09:30',
      date: '昨天 05-12',
      title: '项目与目标：个人网站改版',
      copy: '进度 60%，下一步：完成首页视觉稿。',
      location: '项目与目标',
      people: ['May', 'Emily', '陈昊'],
      mood: '充实',
      photos: ['photo-office'],
      tags: ['项目', '工作'],
      linkedView: 'projects'
    },
    {
      id: 'm7',
      type: '健康',
      icon: '☾',
      time: '22:10',
      date: '昨天 05-12',
      title: '健康轨迹：睡眠 7.2 小时',
      copy: '最近 3 天稳定，情绪评分更高；今晚继续保持睡前阅读。',
      location: '健康与身体',
      people: [],
      mood: '平静',
      photos: ['photo-book'],
      tags: ['阅读', '睡眠', '健康'],
      linkedView: 'health'
    }
  ];

  var decisions = [
    {
      id: 'd1',
      status: '待复盘',
      title: '是否接受新工作的 Offer？',
      date: '2026-04-20',
      category: '职业发展',
      choice: '接受新 Offer',
      confidence: 70,
      background: '目前在 A 公司担任产品经理 2 年，整体发展稳定，但晋升空间有限。近期收到 B 公司的 Offer，岗位级别更高，薪资涨幅明显，但需要搬到上海工作。',
      reason: ['岗位级别和职责提升，有机会带团队、积累管理经验。', '薪资涨幅约 62%，能更好地支持未来阶段目标。', 'B 公司在行业内更有影响力，对个人品牌和履历有加成。'],
      risks: ['需要搬到上海，短期生活成本上升。', '工作强度可能更高，影响生活平衡和健康。', '新环境存在不确定性，团队和文化需要时间磨合。'],
      options: [
        ['接受 Offer', '高级产品经理', '上海 · 需搬迁', '¥680,000', '更大，团队更成熟'],
        ['留在当前公司', '产品经理', '北京 · 无需搬迁', '¥420,000', '一般，晋升较慢']
      ],
      reviewDate: '2026-10-20',
      result: '已在新公司工作中，整体积极，适应中。'
    },
    {
      id: 'd2',
      status: '已复盘',
      title: '是否开始自己的副业？',
      date: '2026-02-10',
      category: '职业发展',
      choice: '开始尝试',
      confidence: 80,
      background: '希望在主业之外探索长期复利的小项目。',
      reason: ['每天固定投入 45 分钟。', '先用低成本方式验证需求。'],
      risks: ['精力被分散。', '短期收入不确定。'],
      options: [
        ['开始尝试', '小规模验证', '线上', '¥1,000', '风险低'],
        ['暂时不做', '保持现状', '无', '¥0', '稳定']
      ],
      reviewDate: '2026-08-10',
      result: '已形成固定节奏，暂不扩大投入。'
    },
    {
      id: 'd3',
      status: '已复盘',
      title: '要不要换城市发展？',
      date: '2026-03-15',
      category: '居住',
      choice: '暂不换城市',
      confidence: 60,
      background: '家庭和工作都还在当前城市，资源也足够。',
      reason: ['当前城市支持系统更稳定。', '换城市的收益不够清晰。'],
      risks: ['可能错过部分行业机会。'],
      options: [
        ['换城市', '重新开始', '上海', '成本较高', '机会更多'],
        ['暂不换', '保持稳定', '北京', '成本较低', '支持系统完整']
      ],
      reviewDate: '2026-09-15',
      result: '继续观望，半年后再判断。'
    }
  ];

  var relationships = [
    { id: 'r1', name: '妈妈', role: '母亲', group: '家人', last: '今天', channel: '微信', score: 92, next: '5 天后', trend: [52, 70, 62, 84, 76, 88], dates: ['生日 1958-06-21', '母亲节 每年 5 月第二个周日'], notes: ['妈妈说最近在学广场舞，认识了好多新朋友。', '在讨论端午节回家的计划，想我带她去拍照。'], memories: ['2024 春节', '杭州之旅', '母亲节午餐'] },
    { id: 'r2', name: '爸爸', role: '父亲', group: '家人', last: '3 天前', channel: '电话', score: 78, next: '12 天后', trend: [50, 66, 58, 70, 62, 78], dates: ['生日 1956-11-08'], notes: ['提醒我注意休息和颈椎。'], memories: ['老照片整理', '家庭晚餐'] },
    { id: 'r3', name: '张敏', role: '大学同学', group: '朋友', last: '昨天', channel: '微信', score: 88, next: '4 天后', trend: [68, 72, 88, 80, 86, 88], dates: ['认识纪念日 2012-09-01'], notes: ['聊到各自的工作近况和下次聚会时间。'], memories: ['毕业旅行', '咖啡馆聊天'] },
    { id: 'r4', name: '阿木', role: '摄影伙伴', group: '朋友', last: '6 天前', channel: '微信', score: 76, next: '10 天后', trend: [58, 62, 66, 74, 70, 76], dates: ['第一次拍摄 2023-04-02'], notes: ['约了下次外拍路线。'], memories: ['西湖拍摄', '器材讨论'] },
    { id: 'r5', name: 'May', role: '产品同事', group: '同事', last: '3 天前', channel: '企业微信', score: 72, next: '14 天后', trend: [52, 55, 68, 64, 70, 72], dates: ['入职认识 2025-01-15'], notes: ['项目合作沟通顺畅。'], memories: ['项目复盘', '午餐聊天'] }
  ];

  var wishes = [
    { id: 'w1', status: '愿望冷却中', category: '数码', name: '相机 Sony A7C II', reason: '想系统学习摄影，记录旅行和生活，提升审美和表达能力。', days: 12, due: '2026-05-25', desire: 72, price: '¥12,999', alternatives: ['先租一台相机体验', '继续用手机 + 学习构图', '购买入门机型'], plan: ['本周完成相机基础知识学习', '在周末去公园拍摄练习', '冷却期结束前再回顾一次真实需求'], photo: 'photo-camera', counterReasons: ['价格较高，短期内预算压力大', '需要花时间学习，可能半途而废', '手机摄影也能满足大部分需求'], notes: '看到很多喜欢的照片，想让自己也能拍出有故事的画面。' },
    { id: 'w2', status: '愿望冷却中', category: '旅行', name: '独自去北海道旅行', reason: '想去看看雪和温泉，给自己放个空。', days: 8, due: '2026-05-21', desire: 65, price: '约 ¥8,000', alternatives: ['先做国内短途旅行', '延后到淡季'], plan: ['确认假期', '做预算表'], photo: 'photo-mountain', counterReasons: ['旺季费用偏高', '独自旅行需要更充分的安全计划'] },
    { id: 'w3', status: '愿望冷却中', category: '数码', name: '降噪耳机 Bose QuietComfort', reason: '通勤和工作时减少干扰，提高专注。', days: 5, due: '2026-05-18', desire: 55, price: '¥1,999', alternatives: ['继续用旧耳机', '先借朋友的试用'], plan: ['连续三天记录噪音影响'], photo: 'photo-office', counterReasons: ['旧耳机还能用', '实际安静场景占比不高'] },
    { id: 'w4', status: '愿望冷却中', category: '学习', name: 'Excel 高阶课程', reason: '提升数据处理能力，帮助工作效率。', days: 3, due: '2026-05-16', desire: 48, price: '¥399', alternatives: ['先用公开课', '买书自学'], plan: ['看完试听课'], photo: 'photo-book', counterReasons: ['课程质量还没有验证', '可能和当前工作需求不匹配'] },
    { id: 'w5', status: '愿望冷却中', category: '生活', name: '半自动咖啡机', reason: '每天一杯好咖啡，提升生活品质。', days: 2, due: '2026-05-15', desire: 62, price: '¥2,499', alternatives: ['继续手冲', '买胶囊咖啡机'], plan: ['连续一周记录咖啡消费', '确认厨房台面空间'], photo: 'photo-cafe', counterReasons: ['清洁维护麻烦', '占用厨房空间'] },
    { id: 'w6', status: '愿望冷却中', category: '数码', name: 'Apple Watch Series 9', reason: '更好地记录健康和运动数据。', days: 1, due: '2026-05-14', desire: 40, price: '¥2,999', alternatives: ['继续使用手机健康记录', '买更基础的手环'], plan: ['确认真正需要的健康指标'], photo: 'photo-office', counterReasons: ['手机已经能记录大部分数据', '每天充电增加负担'] },
    { id: 'w7', status: '可以决定', category: '学习', name: '《被讨厌的勇气》纸质书', reason: '想重读并做笔记。', days: 0, due: '2026-05-13', desire: 35, price: '¥45', alternatives: ['借阅电子书', '先读笔记版'], plan: ['今晚读试看章节'], photo: 'photo-book', counterReasons: ['已经读过电子版'] },
    { id: 'w8', status: '可以决定', category: '健康', name: '游泳月卡', reason: '希望用低冲击运动改善肩颈和睡眠。', days: 0, due: '2026-05-13', desire: 74, price: '¥699', alternatives: ['继续跑步', '每周去单次票'], plan: ['确认泳池距离', '周末试游一次'], photo: 'photo-river', counterReasons: ['通勤距离可能影响频率'] },
    { id: 'w9', status: '已放弃', category: '数码', name: 'iPad Pro 11 英寸', reason: '一时冲动，实际使用场景不多。', days: 0, due: '2026-04-30', desire: 28, price: '¥6,799', alternatives: ['继续使用电脑', '借朋友设备测试'], plan: ['已放弃，半年后再看'], photo: 'photo-office', counterReasons: ['使用频率不足', '价格高'] },
    { id: 'w10', status: '已放弃', category: '生活', name: '扫地机器人旗舰款', reason: '想减少家务时间。', days: 0, due: '2026-04-22', desire: 30, price: '¥4,299', alternatives: ['先调整每周清洁计划', '买基础款'], plan: ['已放弃，先整理动线'], photo: 'photo-book', counterReasons: ['家里面积不大', '需要频繁维护'] },
    { id: 'w11', status: '已实现', category: '旅行', name: '日本京都旅行', reason: '想感受春天的京都。', days: 0, due: '2026-04-10', desire: 85, price: '¥6,500', alternatives: [], plan: ['已归档到月度回顾'], photo: 'photo-garden', counterReasons: [] },
    { id: 'w12', status: '已实现', category: '关系', name: '给妈妈做一本照片书', reason: '把过去几年的合照整理成礼物。', days: 0, due: '2026-05-01', desire: 90, price: '¥268', alternatives: ['线上相册', '打印几张照片'], plan: ['已送出并记录到关系温度'], photo: 'photo-cafe', counterReasons: [] }
  ];

  var projects = [
    { name: '个人网站改版', progress: 60, status: '设计稿还未最终确定', next: '完成首页视觉稿', people: '团队协作 8/10' },
    { name: '摄影作品集整理', progress: 35, status: '照片筛选完成一半', next: '完成 20 张精修', people: '个人项目' },
    { name: '年度阅读计划', progress: 58, status: '已读 7 / 12 本', next: '完成《长期主义》读书笔记', people: '个人目标' }
  ];

  var health = [
    { name: '睡眠', value: '7.2 小时', note: '最近 3 天稳定，情绪评分更高。' },
    { name: '运动', value: '跑步 40 分钟', note: '晨跑后专注力明显提升。' },
    { name: '压力', value: '35 / 100', note: '处于较低压力区间。' },
    { name: '身体信号', value: '颈部轻微酸痛', note: '下午 3 点后需要拉伸休息。' }
  ];

  var moodRecords = [
    { day: 1, weekday: '周五', time: '08:20', score: 75, weather: '晴朗', sleep: 7.0, pressure: 40, energy: 72, feeling: '平静', note: '上午效率稳定，阳光让人更愿意开始。', tags: ['阳光天气', '计划清晰'] },
    { day: 2, weekday: '周六', time: '10:10', score: 60, weather: '多云', sleep: 6.4, pressure: 48, energy: 58, feeling: '普通', note: '休息日节奏偏散，但没有明显压力。', tags: ['社交活动'] },
    { day: 3, weekday: '周日', time: '21:30', score: 70, weather: '微晴', sleep: 7.5, pressure: 38, energy: 68, feeling: '放松', note: '整理房间后心情轻一点。', tags: ['独处时光'] },
    { day: 4, weekday: '周一', time: '09:00', score: 80, weather: '晴朗', sleep: 7.8, pressure: 35, energy: 82, feeling: '专注', note: '完成重要汇报，掌控感比较强。', tags: ['工作压力', '高效'] },
    { day: 5, weekday: '周二', time: '22:15', score: 78, weather: '晴朗', sleep: 7.2, pressure: 35, energy: 80, feeling: '平静', note: '早起散步，今天很稳。', tags: ['阳光天气', '运动'] },
    { day: 6, weekday: '周三', time: '20:40', score: 62, weather: '多云', sleep: 6.6, pressure: 52, energy: 55, feeling: '疲惫', note: '会议较多，晚上需要早点停下来。', tags: ['信息过载', '睡眠不足'] },
    { day: 7, weekday: '周四', time: '19:50', score: 66, weather: '微晴', sleep: 6.8, pressure: 45, energy: 64, feeling: '一般', note: '和朋友聊过后状态回升。', tags: ['朋友', '聊天'] },
    { day: 8, weekday: '周五', time: '08:45', score: 85, weather: '晴朗', sleep: 8.0, pressure: 30, energy: 88, feeling: '轻快', note: '年度体检完成，安心很多。', tags: ['健康', '阳光天气'] },
    { day: 9, weekday: '周六', time: '23:10', score: 48, weather: '阴雨', sleep: 5.3, pressure: 70, energy: 42, feeling: '低落', note: '计划被打乱，晚上刷手机太久。', tags: ['计划被打乱', '睡眠不足'] },
    { day: 10, weekday: '周日', time: '11:20', score: 90, weather: '晴朗', sleep: 8.3, pressure: 24, energy: 90, feeling: '愉快', note: '和家人吃饭，能量被补回来。', tags: ['家人相处', '社交活动'] },
    { day: 11, weekday: '周一', time: '20:40', score: 58, weather: '多云', sleep: 5.3, pressure: 70, energy: 48, feeling: '疲惫', note: '工作有点堆积，压力上来了。', tags: ['工作压力', '计划被打乱'] },
    { day: 12, weekday: '周二', time: '22:15', score: 68, weather: '微晴', sleep: 6.1, pressure: 55, energy: 62, feeling: '缓和', note: '晚上有点累，但和朋友聊天后好多了。', tags: ['朋友', '聊天'] },
    { day: 13, weekday: '周三', time: '09:30', score: 78, weather: '晴朗', sleep: 7.2, pressure: 35, energy: 80, feeling: '平静', note: '早上起来阳光很好，心情也跟着明亮起来。', tags: ['高效', '阳光', '独处时光'] }
  ];

  var mockMoments = [
    { id: 'm8', type: '记忆', icon: '◌', time: '21:40', date: '05-11', title: '和老朋友重逢', copy: '两年没见的大学室友，从下午聊到深夜，发现彼此都变得更松弛了。', location: '本月值得记住', people: ['张敏', '李想'], mood: '温暖', photos: ['photo-cafe', 'photo-night'], tags: ['记忆', '朋友', '本月值得记住'], linkedView: 'monthly' },
    { id: 'm9', type: '健康', icon: '♡', time: '07:10', date: '05-10', title: '健康与身体：年度体检完成', copy: '指标整体正常，医生建议继续保持运动，减少久坐。', location: '健康与身体', people: [], mood: '安心', photos: ['photo-office'], tags: ['健康', '身体信号'], linkedView: 'health' },
    { id: 'm10', type: '项目', icon: '▤', time: '16:00', date: '05-09', title: '项目与目标：个人网站首页评审', copy: '主视觉方向确定，下一步补齐作品集详情页和联系表单。', location: '项目与目标', people: ['May', '陈昊'], mood: '充实', photos: ['photo-office', 'photo-book'], tags: ['项目', '作品集', '工作'], linkedView: 'projects' },
    { id: 'm11', type: '愿望', icon: '♢', time: '22:20', date: '05-08', title: '愿望冷却：Apple Watch Series 9', copy: '剩余 1 天，当前想要程度 40%，用于健康和运动数据记录。', location: '愿望冷却箱', people: [], mood: '期待', photos: ['photo-book'], tags: ['愿望', '数码', '冷却中'], linkedWish: 'w6' },
    { id: 'm12', type: '关系', icon: '♟', time: '18:30', date: '05-07', title: '关系温度：爸爸', copy: '最近联系：3 天前 · 电话；亲密度 78/100，下次联系 12 天后。', location: '关系温度', people: ['爸爸'], mood: '平静', photos: [], tags: ['关系', '家人'], linkedRelationship: 'r2' },
    { id: 'm13', type: '决策', icon: '♎', time: '11:00', date: '05-06', title: '是否继续租现在的房子？', copy: '通勤便利，但房租上涨明显，需要对比搬家成本。', location: '上海 · 徐汇', people: [], mood: '纠结', photos: ['photo-office'], tags: ['决策', '居住', '冷却中'], linkedDecision: 'd4' },
    { id: 'm14', type: '旅行', icon: '✈', time: '14:30', date: '05-04', title: '本月值得记住：杭州西湖散步', copy: '阴天的湖边很安静，走了很长一段路，心情慢慢沉下来。', location: '本月值得记住', people: ['Emma'], mood: '平静', photos: ['photo-garden', 'photo-river'], tags: ['旅行', '朋友'], linkedView: 'monthly' },
    { id: 'm15', type: '记忆', icon: '☾', time: '23:10', date: '05-03', title: '资源库：睡前读完一本书', copy: '读完《被讨厌的勇气》，关于课题分离的部分很有启发。', location: '资源库', people: [], mood: '安静', photos: ['photo-book'], tags: ['记忆', '学习', '阅读'], linkedView: 'resources' },
    { id: 'm16', type: '项目', icon: '✓', time: '10:40', date: '04-28', title: '项目与目标：作品集摄影筛选', copy: '从 400 张照片里选出了 36 张候选，风格开始统一。', location: '项目与目标', people: ['阿木'], mood: '专注', photos: ['photo-camera', 'photo-mountain'], tags: ['项目', '作品', '摄影'], linkedView: 'projects' },
    { id: 'm17', type: '健康', icon: '☁', time: '20:20', date: '04-26', title: '情绪天气：连续两天睡眠不足', copy: '晚上脑子停不下来，第二天明显注意力下降。', location: '情绪天气站', people: [], mood: '疲惫', photos: [], tags: ['健康', '睡眠不足', '情绪天气'], linkedView: 'mood' }
  ];

  var mockDecisions = [
    {
      id: 'd4',
      status: '冷却中',
      title: '是否继续租现在的房子？',
      date: '2026-05-06',
      category: '居住',
      choice: '暂缓决定',
      confidence: 55,
      background: '当前房子通勤便利、生活圈成熟，但续租租金上涨 12%，需要对比搬家成本和生活质量。',
      reason: ['先确认房东最终报价。', '对比同区域两套备选房源。', '把搬家时间成本计入总成本。'],
      risks: ['拖延太久可能错过合适房源。', '频繁看房会消耗精力。'],
      options: [
        ['继续续租', '保持现状', '徐汇', '租金上涨 12%', '稳定便利'],
        ['搬到新房', '重新选择', '静安/长宁', '押金 + 搬家成本', '可能更舒适']
      ],
      reviewDate: '2026-06-06',
      result: '仍在收集信息，暂不做最终决定。'
    },
    {
      id: 'd5',
      status: '已归档',
      title: '是否买入门级钢琴？',
      date: '2025-11-18',
      category: '生活',
      choice: '先租琴三个月',
      confidence: 68,
      background: '想恢复音乐练习，但担心冲动购买后使用频率不足。',
      reason: ['租琴能验证真实练习频率。', '三个月后再看是否值得购买。'],
      risks: ['租赁体验可能影响练习动力。'],
      options: [
        ['直接购买', '长期投入', '家', '¥8,999', '仪式感强'],
        ['先租琴', '低成本验证', '家', '¥900/3个月', '风险低']
      ],
      reviewDate: '2026-02-18',
      result: '三个月练习 31 次，决定暂缓购买。'
    },
    {
      id: 'd6',
      status: '待复盘',
      title: '是否减少社交媒体使用？',
      date: '2026-04-05',
      category: '健康',
      choice: '限制到每天 30 分钟',
      confidence: 76,
      background: '最近信息摄入过多，影响睡眠和专注力。',
      reason: ['晚上刷手机会推迟入睡。', '减少碎片信息可以改善专注。'],
      risks: ['可能错过朋友动态和行业信息。'],
      options: [
        ['严格限制', '每天 30 分钟', '手机', '0', '专注力提升'],
        ['保持现状', '自由使用', '手机', '0', '无切换成本']
      ],
      reviewDate: '2026-05-20',
      result: '第一阶段有效，晚间睡眠有所改善。'
    }
  ];

  var mockRelationships = [
    { id: 'r6', name: '姐姐', role: '姐姐', group: '家人', last: '2 周前', channel: '微信', score: 64, next: '7 天后', trend: [44, 50, 56, 52, 60, 64], dates: ['生日 1988-08-15'], notes: ['她最近工作很忙，计划周末视频。'], memories: ['厦门旅行', '一起插花'] },
    { id: 'r7', name: '李想', role: '前同事', group: '朋友', last: '20 天前', channel: '微信', score: 68, next: '3 天后', trend: [55, 50, 62, 58, 63, 68], dates: ['认识纪念日 2019-06-12'], notes: ['约了下周咖啡。'], memories: ['产品发布', '深夜加班'] },
    { id: 'r8', name: '陈昊', role: '设计伙伴', group: '同事', last: '1 天前', channel: '飞书', score: 83, next: '9 天后', trend: [68, 72, 74, 80, 78, 83], dates: ['合作开始 2026-01-08'], notes: ['讨论了首页动效和作品集排版。'], memories: ['官网评审', '设计冲刺'] },
    { id: 'r9', name: 'Emma', role: '旅行伙伴', group: '朋友', last: '昨天', channel: '微信', score: 86, next: '6 天后', trend: [60, 68, 76, 82, 80, 86], dates: ['第一次旅行 2024-05-04'], notes: ['一起规划夏天的短途旅行。'], memories: ['杭州西湖', '南京书店'] },
    { id: 'r10', name: '周老师', role: '人生导师', group: '重要联系人', last: '28 天前', channel: '电话', score: 85, next: '30 天后', trend: [76, 80, 78, 84, 82, 85], dates: ['第一次咨询 2022-03-18'], notes: ['提醒我在重大选择里区分事实和恐惧。'], memories: ['年度复盘', '职业咨询'] }
  ];

  var mockWishes = [
    { id: 'w6', status: '愿望冷却中', category: '生活', name: '周末陶艺体验课', reason: '想给自己一段不用屏幕的创作时间。', days: 9, due: '2026-05-22', desire: 61, price: '¥268', alternatives: ['先在家做手账', '找免费的城市活动'], plan: ['确认课程时间', '问 Emma 是否一起去'], photo: 'photo-book' },
    { id: 'w7', status: '可以决定', category: '健康', name: '买一张游泳月卡', reason: '希望用低冲击运动改善肩颈和睡眠。', days: 0, due: '2026-05-13', desire: 74, price: '¥699', alternatives: ['继续跑步', '每周去单次票'], plan: ['今晚确认泳池距离', '周末试游一次'], photo: 'photo-river' },
    { id: 'w8', status: '已放弃', category: '数码', name: 'iPad Pro 11 英寸', reason: '一时冲动，实际使用场景不多。', days: 0, due: '2026-04-30', desire: 28, price: '¥6,799', alternatives: ['继续使用电脑', '借朋友设备测试'], plan: ['已放弃，半年后再看'], photo: 'photo-office' },
    { id: 'w9', status: '已实现', category: '学习', name: '读完 3 本书', reason: '本月希望恢复阅读节奏。', days: 0, due: '2026-05-01', desire: 90, price: '¥145', alternatives: [], plan: ['已完成并写入月度回顾'], photo: 'photo-book' }
  ];

  var mockProjects = [
    { name: '月度生活报告生成器', progress: 42, status: '摘要模板还需要打磨', next: '补齐情绪和关系模块的摘要规则', people: '个人项目' },
    { name: '家庭照片归档', progress: 25, status: '老照片命名不统一', next: '按年份和人物做第一轮整理', people: '家人协作' },
    { name: '城市散步地图', progress: 73, status: '路线素材足够，缺少文字整理', next: '完成徐汇滨江路线说明', people: '与 Emma 协作' },
    { name: '副业验证计划', progress: 30, status: '目标用户访谈不足', next: '约 3 位潜在用户做访谈', people: '个人目标' }
  ];

  var mockHealth = [
    { name: '饮水', value: '1.8 L', note: '比上周稳定，下午咖啡减少后心悸也减少。' },
    { name: '颈椎拉伸', value: '完成 2 次', note: '久坐后拉伸能明显缓解紧绷。' },
    { name: '经期信号', value: '前 2 天', note: '情绪敏感度上升，适合减少高压任务。' },
    { name: '专注力', value: '74 / 100', note: '上午明显优于晚上，适合把深度工作前置。' }
  ];

  var resourceAssets = [
    { name: '照片素材', value: '186 张', meta: '旅行、家人、城市散步、作品集候选' },
    { name: '月报归档', value: '18 份', meta: '支持按月份回看高光、情绪、决策' },
    { name: '复盘模板', value: '6 个', meta: '决策复盘、关系回看、愿望冷却、年度总结' },
    { name: '导出档案', value: '4 份', meta: 'PDF 月报、图片墙、CSV 数据快照' },
    { name: '地点库', value: '32 个', meta: '上海、苏州、杭州、南京、新疆、京都' },
    { name: '标签库', value: '47 个', meta: '健康、项目、家人、职业发展、睡眠不足' }
  ];

  function withMockData(baseItems, mockItems) {
    return mockMode ? baseItems.concat(mockItems) : baseItems.slice();
  }

  var colors = {
    '健康': 'green',
    '旅行': 'amber',
    '项目': 'blue',
    '关系': 'red',
    '决策': 'amber',
    '愿望': 'blue',
    '情绪': 'amber',
    '记忆': 'green'
  };

  var typeIcons = {
    '记忆': 'memory',
    '决定': 'decision',
    '决策': 'decision',
    '情绪': 'mood',
    '关系': 'relationship',
    '愿望': 'wish',
    '健康': 'health',
    '项目': 'project',
    '旅行': 'travel'
  };

  var moodIcons = {
    '晴朗': 'sun',
    '平静': 'calm',
    '愉快': 'smile',
    '充实': 'star',
    '焦虑': 'anxious',
    '疲惫': 'cloud',
    '低落': 'cloud',
    '生气': 'anxious',
    '其他': 'mood'
  };

  var iconSvgs = {
    flow: '<path d="M4 11.5 12 5l8 6.5v7a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5v-7Z"/><path d="M9 20v-6h6v6"/>',
    timeline: '<path d="M5 7h14"/><path d="M5 12h14"/><path d="M5 17h14"/><path d="M8 4v16"/><path d="M16 4v16"/>',
    decision: '<path d="M12 4v15"/><path d="M6 7h12"/><path d="M8 7l-3 6h6L8 7Z"/><path d="M16 7l-3 6h6l-3-6Z"/><path d="M8 19h8"/>',
    mood: '<path d="M4 14.5a8 8 0 0 1 15.5-2.8"/><path d="M19 6v5h-5"/><path d="M8 14h.01"/><path d="M14 14h.01"/><path d="M9 18c1.8 1.2 4.2 1.2 6 0"/>',
    relationship: '<path d="M16.5 18.5v-1.2c0-1.8-1.6-3.3-3.5-3.3h-2c-1.9 0-3.5 1.5-3.5 3.3v1.2"/><circle cx="12" cy="8" r="3"/><path d="M4 19c.4-2.4 1.8-4.1 3.8-4.8"/><path d="M20 19c-.4-2.4-1.8-4.1-3.8-4.8"/>',
    wish: '<path d="M5 9h14v11H5z"/><path d="M12 9v11"/><path d="M4 9h16"/><path d="M8.5 9C6.5 7.6 6.4 5 8.4 4.5c2-.5 3.2 2.2 3.6 4.5"/><path d="M15.5 9c2-1.4 2.1-4 .1-4.5-2-.5-3.2 2.2-3.6 4.5"/>',
    monthly: '<path d="M7 4h10a1 1 0 0 1 1 1v16l-6-3-6 3V5a1 1 0 0 1 1-1Z"/>',
    add: '<path d="M12 5v14"/><path d="M5 12h14"/>',
    project: '<rect x="5" y="4" width="14" height="16" rx="2"/><path d="M9 4v3h6V4"/><path d="m8.5 13 2 2 5-5"/>',
    health: '<path d="M20.2 6.6a5 5 0 0 0-7.1 0L12 7.7l-1.1-1.1a5 5 0 1 0-7.1 7.1L12 21l8.2-7.3a5 5 0 0 0 0-7.1Z"/><path d="M8 12h2.2l1.1-2.4 2 5 1.1-2.6H16"/>',
    review: '<path d="M5 5h14v14H5z"/><path d="m8 12 2.2 2.2L16 8.5"/>',
    resource: '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="M4 7.5 12 12l8-4.5"/><path d="M12 12v9"/>',
    profile: '<circle cx="12" cy="8" r="4"/><path d="M5 20c1-4 4-6 7-6s6 2 7 6"/>',
    settings: '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="M4 12h2"/><path d="M18 12h2"/><path d="m6.3 6.3 1.4 1.4"/><path d="m16.3 16.3 1.4 1.4"/><path d="M12 4v2"/><path d="M12 18v2"/><path d="m17.7 6.3-1.4 1.4"/><path d="m7.7 16.3-1.4 1.4"/>',
    trash: '<path d="M5 7h14"/><path d="M9 7V5h6v2"/><path d="m7 7 1 13h8l1-13"/><path d="M10 11v5"/><path d="M14 11v5"/>',
    search: '<circle cx="11" cy="11" r="6"/><path d="m16 16 4 4"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.1 0l1.4-1.4a5 5 0 0 0-7.1-7.1L10.5 5"/><path d="M14 11a5 5 0 0 0-7.1 0l-1.4 1.4a5 5 0 0 0 7.1 7.1l.9-.9"/>',
    image: '<rect x="4" y="5" width="16" height="14" rx="2"/><circle cx="9" cy="10" r="1.5"/><path d="m7 17 3.5-4 2.5 3 2-2.2 2.5 3.2"/>',
    mic: '<path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z"/><path d="M19 11a7 7 0 0 1-14 0"/><path d="M12 18v3"/><path d="M8 21h8"/>',
    file: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/>',
    location: '<path d="M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
    people: '<path d="M16.5 19v-1c0-2-1.8-3.5-4-3.5h-1c-2.2 0-4 1.5-4 3.5v1"/><circle cx="12" cy="8" r="3"/><path d="M4.5 18c.2-1.8 1.2-3 2.8-3.6"/><path d="M19.5 18c-.2-1.8-1.2-3-2.8-3.6"/>',
    memory: '<path d="M7 4h10a1 1 0 0 1 1 1v16l-6-3-6 3V5a1 1 0 0 1 1-1Z"/><path d="M9 9h6"/><path d="M9 13h4"/>',
    travel: '<path d="M3 13 21 5l-6 16-3.5-6.5L3 13Z"/><path d="m21 5-9.5 9.5"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.9 4.9 1.4 1.4"/><path d="m17.7 17.7 1.4 1.4"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m4.9 19.1 1.4-1.4"/><path d="m17.7 6.3 1.4-1.4"/>',
    calm: '<path d="M4 10c1.7 1.5 3.3 1.5 5 0s3.3-1.5 5 0 3.3 1.5 5 0"/><path d="M4 15c1.7 1.5 3.3 1.5 5 0s3.3-1.5 5 0 3.3 1.5 5 0"/>',
    smile: '<circle cx="12" cy="12" r="8"/><path d="M9 10h.01"/><path d="M15 10h.01"/><path d="M8.8 14.5c1.8 1.8 4.6 1.8 6.4 0"/>',
    star: '<path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z"/>',
    anxious: '<circle cx="12" cy="12" r="8"/><path d="M9 10h.01"/><path d="M15 10h.01"/><path d="M9 16c1.8-1.2 4.2-1.2 6 0"/>',
    cloud: '<path d="M6.5 18h10.8a4 4 0 0 0 .4-8 6 6 0 0 0-11.4 2A3 3 0 0 0 6.5 18Z"/>'
  };

  function svgIcon(name) {
    return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + (iconSvgs[name] || iconSvgs.memory) + '</svg>';
  }

  function iconHtml(name, extraClass) {
    var safeName = iconSvgs[name] ? name : 'memory';
    return '<span class="life-svg-icon icon-' + escapeHtml(safeName) + (extraClass ? ' ' + extraClass : '') + '" data-icon="' + escapeHtml(safeName) + '">' + svgIcon(safeName) + '</span>';
  }

  function hydrateStaticIcons(root) {
    Array.prototype.forEach.call((root || document).querySelectorAll('.life-svg-icon'), function(node) {
      if (node.querySelector('svg')) return;
      var name = node.getAttribute('data-icon') || '';
      if (!name) {
        Array.prototype.some.call(node.classList, function(className) {
          if (className.indexOf('icon-') === 0) {
            name = className.slice(5);
            return true;
          }
          return false;
        });
      }
      if (iconSvgs[name]) node.innerHTML = svgIcon(name);
    });
  }

  function iconForType(type) {
    return typeIcons[type] || 'memory';
  }

  function escapeHtml(value) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(value == null ? '' : String(value)));
    return div.innerHTML;
  }

  function getStoredMoments() {
    try {
      return JSON.parse(localStorage.getItem(mockMode ? MOCK_STORAGE_KEY : STORAGE_KEY) || '[]');
    } catch (err) {
      return [];
    }
  }

  function saveStoredMoments(items) {
    localStorage.setItem(mockMode ? MOCK_STORAGE_KEY : STORAGE_KEY, JSON.stringify(items));
  }

  function axisStorageKey() {
    return mockMode ? MOCK_AXIS_STORAGE_KEY : AXIS_STORAGE_KEY;
  }

  function getAxisStore() {
    try {
      var raw = JSON.parse(localStorage.getItem(axisStorageKey()) || '{}');
      return {
        added: raw.added || [],
        deleted: raw.deleted || [],
        edits: raw.edits || {}
      };
    } catch (err) {
      return { added: [], deleted: [], edits: {} };
    }
  }

  function saveAxisStore(store) {
    localStorage.setItem(axisStorageKey(), JSON.stringify(store));
  }

  function decisionStorageKey() {
    return mockMode ? MOCK_DECISION_STORAGE_KEY : DECISION_STORAGE_KEY;
  }

  function getStoredDecisions() {
    try {
      return JSON.parse(localStorage.getItem(decisionStorageKey()) || '[]');
    } catch (err) {
      return [];
    }
  }

  function saveStoredDecisions(items) {
    localStorage.setItem(decisionStorageKey(), JSON.stringify(items));
  }

  function moodStorageKey() {
    return mockMode ? MOCK_MOOD_STORAGE_KEY : MOOD_STORAGE_KEY;
  }

  function getMoodStore() {
    try {
      var raw = JSON.parse(localStorage.getItem(moodStorageKey()) || '{}');
      return {
        added: raw.added || [],
        edits: raw.edits || {},
        deleted: raw.deleted || []
      };
    } catch (err) {
      return { added: [], edits: {}, deleted: [] };
    }
  }

  function saveMoodStore(store) {
    localStorage.setItem(moodStorageKey(), JSON.stringify(store));
  }

  function relationshipStorageKey() {
    return mockMode ? MOCK_RELATIONSHIP_STORAGE_KEY : RELATIONSHIP_STORAGE_KEY;
  }

  function getRelationshipStore() {
    try {
      var raw = JSON.parse(localStorage.getItem(relationshipStorageKey()) || '{}');
      return {
        added: raw.added || [],
        edits: raw.edits || {},
        deleted: raw.deleted || []
      };
    } catch (err) {
      return { added: [], edits: {}, deleted: [] };
    }
  }

  function saveRelationshipStore(store) {
    localStorage.setItem(relationshipStorageKey(), JSON.stringify(store));
  }

  function wishStorageKey() {
    return mockMode ? MOCK_WISH_STORAGE_KEY : WISH_STORAGE_KEY;
  }

  function getWishStore() {
    try {
      var raw = JSON.parse(localStorage.getItem(wishStorageKey()) || '{}');
      return {
        added: raw.added || [],
        edits: raw.edits || {},
        deleted: raw.deleted || []
      };
    } catch (err) {
      return { added: [], edits: {}, deleted: [] };
    }
  }

  function saveWishStore(store) {
    localStorage.setItem(wishStorageKey(), JSON.stringify(store));
  }

  function monthlyStorageKey() {
    return mockMode ? MOCK_MONTHLY_STORAGE_KEY : MONTHLY_STORAGE_KEY;
  }

  function getMonthlyStore() {
    try {
      var raw = JSON.parse(localStorage.getItem(monthlyStorageKey()) || '{}');
      return {
        bookmarked: raw.bookmarked || {},
        reports: raw.reports || {},
        archived: raw.archived || {},
        letters: raw.letters || {},
        quotes: raw.quotes || {}
      };
    } catch (err) {
      return { bookmarked: {}, reports: {}, archived: {}, letters: {}, quotes: {} };
    }
  }

  function saveMonthlyStore(store) {
    localStorage.setItem(monthlyStorageKey(), JSON.stringify(store));
  }

  function projectStorageKey() {
    return mockMode ? MOCK_PROJECT_STORAGE_KEY : PROJECT_STORAGE_KEY;
  }

  function healthStorageKey() {
    return mockMode ? MOCK_HEALTH_STORAGE_KEY : HEALTH_STORAGE_KEY;
  }

  function getSimpleStore(key) {
    try {
      return JSON.parse(localStorage.getItem(key) || '[]');
    } catch (err) {
      return [];
    }
  }

  function saveSimpleStore(key, items) {
    localStorage.setItem(key, JSON.stringify(items));
  }

  function decisionMetaKey() {
    return decisionStorageKey() + '_meta';
  }

  function getDecisionMeta() {
    try {
      var raw = JSON.parse(localStorage.getItem(decisionMetaKey()) || '{}');
      return {
        edits: raw.edits || {},
        reviewed: raw.reviewed || {},
        confidence: raw.confidence || {},
        bookmarks: raw.bookmarks || [],
        deleted: raw.deleted || []
      };
    } catch (err) {
      return { edits: {}, reviewed: {}, confidence: {}, bookmarks: [], deleted: [] };
    }
  }

  function saveDecisionMeta(meta) {
    localStorage.setItem(decisionMetaKey(), JSON.stringify(meta));
  }

  function allMoments() {
    return getStoredMoments().concat(seedMoments).concat(mockMode ? mockMoments : []);
  }

  function allDecisions() {
    return getStoredDecisions().concat(withMockData(decisions, mockDecisions));
  }

  function moodDateId(year, month, day) {
    return 'mood-' + year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
  }

  function moodDateValue(year, month, day) {
    return year + '-' + String(month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
  }

  function parseMoodDate(value) {
    var parts = String(value || '').split('-').map(Number);
    return {
      year: parts[0] || 2026,
      month: Math.max(0, (parts[1] || 5) - 1),
      day: parts[2] || 13
    };
  }

  function normalizeMoodRecord(item) {
    var year = Number(item.year || 2026);
    var month = Number(item.month == null ? 4 : item.month);
    var day = Number(item.day || 1);
    return Object.assign({
      id: moodDateId(year, month, day),
      year: year,
      month: month,
      day: day,
      date: moodDateValue(year, month, day),
      weekday: moodWeekdayText(year, month, day),
      source: 'seed'
    }, item);
  }

  function moodSortAsc(a, b) {
    return (a.date + ' ' + a.time).localeCompare(b.date + ' ' + b.time);
  }

  function allMoodRecords() {
    var store = getMoodStore();
    var deleted = store.deleted || [];
    var seedItems = moodRecords.map(normalizeMoodRecord).map(function(item) {
      return Object.assign({}, item, store.edits[item.id] || {});
    });
    var addedItems = (store.added || []).map(normalizeMoodRecord);
    return seedItems.concat(addedItems).filter(function(item) {
      return deleted.indexOf(item.id) < 0;
    }).sort(moodSortAsc);
  }

  function currentMonthMoodRecords() {
    return allMoodRecords().filter(function(item) {
      return Number(item.year) === Number(state.moodYear) && Number(item.month) === Number(state.moodMonth);
    });
  }

  function moodRecordForMonth(day, year, month) {
    return allMoodRecords().filter(function(item) {
      return Number(item.year) === Number(year) && Number(item.month) === Number(month) && Number(item.day) === Number(day);
    })[0] || null;
  }

  function selectedMoodRecord() {
    return moodRecordForMonth(state.selectedMoodDay, state.moodYear, state.moodMonth);
  }

  function normalizeRelationship(item) {
    var normalized = Object.assign({
      id: item.id || 'r-local-' + Date.now(),
      role: '',
      group: '朋友',
      last: '今天',
      channel: '微信',
      score: 70,
      next: '7 天后',
      nextDate: '2026-05-20',
      trend: [60, 64, 66, 70, 68, 72],
      dates: [],
      notes: [],
      memories: [],
      gifts: [],
      places: [],
      avatar: item.avatar || '',
      avatarUrl: item.avatarUrl || '',
      memo: '保持稳定、温暖、不过度打扰的连接。',
      reminded: false,
      source: 'seed'
    }, item);
    normalized.memories = normalizeRelationshipMedia(normalized.memories);
    normalized.gifts = normalizeRelationshipMedia(normalized.gifts);
    normalized.places = normalizeRelationshipMedia(normalized.places);
    return normalized;
  }

  function normalizeRelationshipMedia(items) {
    return (items || []).map(function(item) {
      if (typeof item === 'string') return { text: item, image: '' };
      return {
        text: item.text || item.name || item.title || '',
        image: item.image || item.imageUrl || '',
        date: item.date || ''
      };
    }).filter(function(item) { return item.text || item.image; });
  }

  function allRelationships() {
    var store = getRelationshipStore();
    var deleted = store.deleted || [];
    var baseItems = withMockData(relationships, mockRelationships).map(normalizeRelationship).map(function(item) {
      return normalizeRelationship(Object.assign({}, item, store.edits[item.id] || {}));
    });
    var addedItems = (store.added || []).map(normalizeRelationship).map(function(item) {
      return normalizeRelationship(Object.assign({}, item, store.edits[item.id] || {}));
    });
    return baseItems.concat(addedItems).filter(function(item) {
      return deleted.indexOf(item.id) < 0;
    });
  }

  function normalizeWish(item) {
    var normalized = Object.assign({
      id: item.id || 'w-local-' + Date.now(),
      status: '愿望冷却中',
      category: '生活',
      name: '未命名愿望',
      reason: '',
      days: 21,
      due: '2026-06-03',
      desire: 50,
      price: '待定',
      alternatives: [],
      plan: [],
      photo: 'photo-book',
      addedAt: '2026-05-13',
      coolStart: '2026-05-01',
      priceHistory: '最低记录：¥11,999（2026-04-28）',
      notes: '',
      counterReasons: [],
      future: '可以更自由地记录和表达，让生活更有仪式感。',
      completedPlan: []
    }, item);
    normalized.days = Math.max(0, Number(normalized.days || 0));
    normalized.desire = Math.max(0, Math.min(100, Number(normalized.desire || 0)));
    normalized.alternatives = Array.isArray(normalized.alternatives) ? normalized.alternatives : splitLines(normalized.alternatives, []);
    normalized.plan = Array.isArray(normalized.plan) ? normalized.plan : splitLines(normalized.plan, []);
    normalized.counterReasons = Array.isArray(normalized.counterReasons) ? normalized.counterReasons : splitLines(normalized.counterReasons, []);
    normalized.completedPlan = Array.isArray(normalized.completedPlan) ? normalized.completedPlan : [];
    return normalized;
  }

  function allWishes() {
    var store = getWishStore();
    var deleted = store.deleted || [];
    var baseItems = withMockData(wishes, mockWishes).map(normalizeWish).map(function(item) {
      return normalizeWish(Object.assign({}, item, store.edits[item.id] || {}));
    });
    var addedItems = (store.added || []).map(normalizeWish).map(function(item) {
      return normalizeWish(Object.assign({}, item, store.edits[item.id] || {}));
    });
    return baseItems.concat(addedItems).filter(function(item) {
      return deleted.indexOf(item.id) < 0;
    });
  }

  function allProjects() {
    return getSimpleStore(projectStorageKey()).concat(withMockData(projects, mockProjects));
  }

  function allHealth() {
    return getSimpleStore(healthStorageKey()).concat(withMockData(health, mockHealth));
  }

  function allResources() {
    if (mockMode) return resourceAssets.slice();
    return [
      { name: '照片素材', value: '128 张', meta: '默认原型素材' },
      { name: '月报归档', value: '4 份', meta: '默认原型归档' },
      { name: '复盘模板', value: '6 个', meta: '默认原型模板' },
      { name: '导出档案', value: '2 份', meta: '默认原型导出' }
    ];
  }

  function mockNotice() {
    if (!mockMode) return '';
    return '<section class="life-panel" style="margin-bottom:14px;border-color:#f0ca8e;background:#fffaf0"><div class="life-row-head"><div><h2 class="life-panel-title">测试数据模式</h2><p class="life-panel-sub">当前页面追加了隔离 mock 数据，仅用于功能页面测试；新增与编辑会写入独立的 life_mock_* 存储，不会混入真实保存数据。</p></div><span class="life-badge amber">Mock Only</span></div></section>';
  }

  function queryMatch(text) {
    var q = state.query.trim().toLowerCase();
    return !q || String(text).toLowerCase().indexOf(q) !== -1;
  }

  function tagsHtml(tags) {
    return (tags || []).map(function(tag) {
      return '<span class="life-badge ' + (colors[tag] || 'gray') + '">' + escapeHtml(tag) + '</span>';
    }).join('');
  }

  function photosHtml(photos) {
    if (!photos || !photos.length) return '';
    return '<div class="life-media-row">' + photos.map(function(photo) {
      return '<span class="life-photo ' + photo + '"></span>';
    }).join('') + '</div>';
  }

  function sparkline(values) {
    return '<div class="life-sparkline">' + values.map(function(value) {
      return '<span style="--h:' + value + '%"></span>';
    }).join('') + '</div>';
  }

  function progress(value, color) {
    return '<div class="life-progress"><span style="--value:' + value + '%; --color:' + (color || 'var(--life-accent)') + '"></span></div>';
  }

  function findById(items, id) {
    return (items || []).filter(function(item) {
      return item.id === id;
    })[0] || null;
  }

  function targetFromMoment(moment) {
    if (!moment) return { type: '', id: '' };
    if (moment.linkedDecision) return { type: 'decision', id: moment.linkedDecision };
    if (moment.linkedRelationship) return { type: 'relationship', id: moment.linkedRelationship };
    if (moment.linkedWish) return { type: 'wish', id: moment.linkedWish };
    if (moment.linkedMoodDate) return { type: 'mood', id: moment.linkedMoodDate };
    if (moment.linkedView) return { type: 'view', id: moment.linkedView };
    if (Array.isArray(moment.linkedModules)) {
      var moduleMap = {
        '情绪天气站': 'mood',
        '健康轨迹': 'health',
        '健康与身体': 'health',
        '关系温度': 'relationships',
        '愿望冷却箱': 'wishes',
        '决策档案馆': 'decisions',
        '项目与目标': 'projects',
        '资源库': 'resources',
        '本月值得记住': 'monthly',
        '复盘与回顾': 'review'
      };
      var matched = moment.linkedModules.map(function(name) { return moduleMap[name]; }).filter(Boolean)[0];
      if (matched) return { type: 'view', id: matched };
    }
    if (moment.type === '决策' || moment.type === '决定') return { type: 'view', id: 'decisions' };
    if (moment.type === '关系') return { type: 'view', id: 'relationships' };
    if (moment.type === '愿望') return { type: 'view', id: 'wishes' };
    if (moment.type === '情绪') return { type: 'view', id: 'mood' };
    if (moment.type === '项目') return { type: 'view', id: 'projects' };
    if (moment.type === '健康') return { type: 'view', id: 'health' };
    return { type: 'view', id: 'monthly' };
  }

  function momentTargetAttrs(moment) {
    var target = targetFromMoment(moment);
    return ' data-moment-id="' + escapeHtml(moment.id) + '"' +
      (target.type ? ' data-moment-target="' + escapeHtml(target.type) + '"' : '') +
      (target.id ? ' data-target-id="' + escapeHtml(target.id) + '"' : '');
  }

  function showToast(message) {
    els.toast.textContent = message;
    els.toast.classList.add('show');
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(function() {
      els.toast.classList.remove('show');
    }, 1800);
  }

  function setView(view) {
    state.view = view;
    if (view !== 'timeline') state.timelineFilter = '全部';
    render();
  }

  function openMomentTarget(momentId, targetType, targetId) {
    state.selectedMomentId = momentId;
    var moment = findById(allMoments(), momentId);
    var target = targetType ? { type: targetType, id: targetId } : targetFromMoment(moment);
    if (target.type === 'decision') {
      var decision = findById(decisionArchiveItems(), target.id);
      state.selectedDecisionId = target.id;
      if (decision) state.decisionFilter = decisionBucket(decision);
      state.decisionFormMode = null;
      state.view = 'decisions';
      render();
      return;
    }
    if (target.type === 'relationship') {
      var relationship = findById(allRelationships(), target.id);
      state.selectedRelationshipId = target.id;
      if (relationship) state.relationshipFilter = relationship.group;
      state.relationshipFormMode = null;
      state.relationshipEditingId = '';
      state.relationshipInlineEditor = '';
      state.view = 'relationships';
      render();
      return;
    }
    if (target.type === 'wish') {
      var wish = findById(allWishes(), target.id);
      state.selectedWishId = target.id;
      state.wishCategory = '全部';
      if (wish) state.wishFilter = wish.status;
      state.wishFormMode = null;
      state.view = 'wishes';
      render();
      return;
    }
    if (target.type === 'mood') {
      var parsed = parseMoodDate(target.id);
      state.moodYear = parsed.year;
      state.moodMonth = parsed.month;
      state.selectedMoodDay = parsed.day;
      state.moodTab = 'overview';
      state.moodFormMode = null;
      state.moodEditingId = '';
      state.view = 'mood';
      render();
      return;
    }
    if (target.type === 'view' && target.id) {
      setView(target.id);
      return;
    }
    renderTimeline();
  }

  function updateChrome() {
    els.title.textContent = (state.view === 'life-axis' || state.view === 'decisions' || state.view === 'mood' || state.view === 'add') ? '生活航迹' : (viewTitles[state.view] || '生活航迹');
    document.body.setAttribute('data-life-view', state.view);
    Array.prototype.forEach.call(document.querySelectorAll('.life-nav-item'), function(btn) {
      btn.classList.toggle('active', btn.getAttribute('data-view') === state.view);
    });
    if (els.mockModeBtn) {
      els.mockModeBtn.textContent = mockMode ? '关闭测试数据' : '测试数据';
      els.mockModeBtn.classList.toggle('active', mockMode);
    }
    var addBtn = document.querySelector('.life-topbar [data-action="go-add"]');
    if (addBtn) addBtn.textContent = state.view === 'life-axis' ? '+ 添加里程碑' : (state.view === 'decisions' ? '+ 添加决定' : (state.view === 'mood' ? '+ 记录情绪' : (state.view === 'wishes' ? '+ 添加愿望' : '+ 添加一刻')));
    if (els.search) {
      els.search.placeholder = state.view === 'life-axis' ? '搜索地点、事件、人物、决定...' : (state.view === 'wishes' ? '搜索愿望、原因、标签...' : (state.view === 'decisions' || state.view === 'mood' ? '搜索记录、地点、人物...' : '搜索记录、地点、人物、决策...'));
    }
    var session = accountSession();
    var accountBtn = document.querySelector('[data-account-action="profile"]');
    if (accountBtn) accountBtn.textContent = session ? session.name : '登录';
    var profile = document.querySelector('.life-profile');
    if (profile) {
      var nameNode = profile.querySelector('strong');
      var copyNode = profile.querySelector('span');
      var avatarNode = profile.querySelector('.life-avatar');
      if (nameNode) nameNode.textContent = session ? session.name : '未登录';
      if (copyNode) copyNode.textContent = session ? '记录生活，理解自己' : '登录后同步个人档案';
      if (avatarNode && session) {
        avatarNode.classList.add('account-avatar');
        avatarNode.innerHTML = relationshipAvatarHtml({ avatar: accountAvatarKey(session) }, '');
      } else if (avatarNode) {
        avatarNode.classList.remove('account-avatar');
        avatarNode.innerHTML = 'L';
      }
    }
    hydrateStaticIcons(document);
  }

  function renderStats() {
    return '<section class="life-stats">' +
      stat('人生记录', '628 条') +
      stat('走过天数', '9,862 天') +
      stat('去过城市', '28 个') +
      stat('重要决定', '37 个') +
      stat('心情平均值', '68 /100') +
      stat('连续记录', '127 天') +
    '</section>';
  }

  function stat(label, value) {
    return '<div class="life-stat"><span>' + label + '</span><strong>' + value + '</strong></div>';
  }

  function momentCard(moment, index, items) {
    var timeParts = String(moment.date).split(' ');
    var dayLabel = timeParts.length > 1 ? timeParts[0] : '';
    var dateLabel = timeParts.length > 1 ? timeParts.slice(1).join(' ') : moment.date;
    var previous = index > 0 ? items[index - 1] : null;
    var isNewDay = !previous || previous.date !== moment.date;
    var dayBlock = isNewDay
      ? '<div class="life-day-rail ' + (dayLabel === '昨天' ? 'muted' : '') + '"><strong>' + escapeHtml(dayLabel || '记录') + '</strong><span>' + escapeHtml(dateLabel) + '</span><span>' + (dayLabel === '昨天' ? '周二' : '周三') + '</span></div>'
      : '';
    var cardExtra = moment.id === 'm1' ? renderTodayWeatherInset() : '';
    return '<article class="life-moment">' +
      '<div class="life-moment-date">' + dayBlock + '</div>' +
      '<div class="life-moment-time"><span>' + escapeHtml(moment.time) + '</span></div>' +
      '<div class="life-moment-dot">' + iconHtml(iconForType(moment.type)) + '</div>' +
      '<div class="life-card clickable ' + (state.selectedMomentId === moment.id ? 'active' : '') + '"' + momentTargetAttrs(moment) + '>' +
        '<div class="life-row-head"><div><h3 class="life-card-title">' + escapeHtml(moment.title) + '</h3><p class="life-card-copy">' + escapeHtml(moment.copy) + '</p></div>' +
        '<span class="life-badge ' + (colors[moment.type] || 'gray') + '">' + escapeHtml(moment.type) + '</span></div>' +
        photosHtml(moment.photos) +
        cardExtra +
        '<div class="life-meta"><span>' + iconHtml('location') + ' ' + escapeHtml(moment.location) + '</span>' +
        (moment.people.length ? '<span>' + iconHtml('people') + ' ' + escapeHtml(moment.people.join('、')) + '</span>' : '') +
        tagsHtml(moment.tags) + '</div>' +
      '</div>' +
    '</article>';
  }

  function renderTodayWeatherInset() {
    return '<div class="life-weather-inset"><div><span class="life-muted">最近情绪</span><strong>' + iconHtml('sun') + ' 晴朗 <em>78/100</em></strong></div><div class="life-energy-note">精力充沛，适合推进重要的事。</div><div class="life-weather-metrics"><span>情绪天气</span><span>睡眠 <strong>7.2h</strong> 良好</span><span>压力 <strong>35/100</strong> 较低</span><span>精力 <strong>80/100</strong> 充沛</span><span>感受 平静</span></div></div>';
  }

  function homeMomentCard(moment, index, items) {
    var timeParts = String(moment.date).split(' ');
    var dayLabel = timeParts.length > 1 ? timeParts[0] : '';
    var dateLabel = timeParts.length > 1 ? timeParts.slice(1).join(' ') : moment.date;
    var previous = index > 0 ? items[index - 1] : null;
    var isNewDay = !previous || previous.date !== moment.date;
    var weekday = dayLabel === '昨天' ? '周二' : '周三';
    var dayBlock = isNewDay
      ? '<div class="life-day-rail ' + (dayLabel === '昨天' ? 'muted' : '') + '"><strong>' + escapeHtml(dayLabel || '记录') + '</strong><span>' + escapeHtml(dateLabel) + '</span><span>' + weekday + '</span></div>'
      : '';
    return '<article class="life-moment life-home-moment">' +
      '<div class="life-moment-date">' + dayBlock + '</div>' +
      '<div class="life-moment-time"><span>' + escapeHtml(moment.time) + '</span></div>' +
      '<div class="life-moment-dot ' + (colors[moment.type] || 'gray') + '">' + iconHtml(iconForType(moment.type)) + '</div>' +
      renderHomeCard(moment) +
    '</article>';
  }

  function renderHomeCard(moment) {
    if (moment.id === 'm1') return renderMorningCard(moment);
    if (moment.id === 'm2') return renderDecisionHomeCard(moment);
    if (moment.id === 'm3') return renderRelationshipHomeCard(moment);
    if (moment.id === 'm4') return renderWishHomeCard(moment);
    if (moment.id === 'm5') return renderMemoryHomeCard(moment);
    if (moment.id === 'm6') return renderProjectHomeCard(moment);
    if (moment.id === 'm7') return renderSleepHomeCard(moment);
    return '<div class="life-home-card life-card clickable"' + momentTargetAttrs(moment) + '><div class="life-row-head"><div><h3 class="life-card-title">' + escapeHtml(moment.title) + '</h3><p class="life-card-copy">' + escapeHtml(moment.copy) + '</p></div><span class="life-badge ' + (colors[moment.type] || 'gray') + '">' + escapeHtml(moment.type) + '</span></div>' + photosHtml(moment.photos) + '<div class="life-meta"><span>' + iconHtml('location') + ' ' + escapeHtml(moment.location) + '</span>' + tagsHtml(moment.tags) + '</div></div>';
  }

  function renderMorningCard(moment) {
    var record = moodRecordForMonth(13, 2026, 4) || selectedMoodRecord() || { weather: '晴朗', score: 78, sleep: 7.2, pressure: 35, energy: 80, feeling: '平静' };
    return '<div class="life-home-card life-card life-weather-card clickable"' + momentTargetAttrs(moment) + '>' +
      '<div class="life-morning-main"><div class="life-home-type-icon amber">' + iconHtml(moodIcons[record.weather] || 'sun') + '</div><div><h3 class="life-card-title">' + escapeHtml(moment.title) + '</h3><p class="life-card-copy">' + escapeHtml(moment.copy) + '</p><div class="life-meta"><span>' + iconHtml('location') + ' ' + escapeHtml(moment.location) + '</span>' + tagsHtml(moment.tags) + '</div></div><span class="life-photo photo-river life-main-photo"></span></div>' +
      '<div class="life-mood-row"><span class="life-muted">最近情绪</span><div class="life-mood-now">' + iconHtml('sun') + '<strong>晴朗</strong><span>78/100</span></div><span class="life-energy-note">精力充沛，适合推进重要的事。</span></div>' +
      '<div class="life-weather-metrics"><span>情绪天气</span><span>睡眠 <strong>' + escapeHtml(record.sleep) + 'h</strong> 良好</span><span>压力 <strong>' + escapeHtml(record.pressure) + '/100</strong> 较低</span><span>精力 <strong>' + escapeHtml(record.energy) + '/100</strong> 充沛</span><span>感受 <strong>' + escapeHtml(record.feeling) + '</strong></span></div>' +
    '</div>';
  }

  function renderDecisionHomeCard(moment) {
    var decision = findById(decisionArchiveItems(), moment.linkedDecision) || {};
    return '<div class="life-home-card life-card life-decision-card clickable"' + momentTargetAttrs(moment) + '>' +
      '<div class="life-card-label amber">重要决定</div><div class="life-home-card-main"><h3 class="life-card-title">' + escapeHtml(moment.title) + ' <span class="life-badge amber">' + escapeHtml(decision.status || '待复盘') + '</span> <span class="life-card-date">记录于 ' + escapeHtml(decision.date || '2026-04-20') + '</span></h3><p class="life-card-copy">我的选择：<strong>' + escapeHtml(decision.choice || '接受新 Offer') + '</strong><span class="life-gap"></span>信心：' + escapeHtml(decision.confidence || 70) + '/100</p><p class="life-card-copy">' + escapeHtml((decision.reason || [moment.copy])[0]) + '</p><button class="life-link-btn" type="button">查看详情 →</button></div><div class="life-review-box"><span>下次复盘日</span><strong>' + escapeHtml(decision.reviewDate || '2026-10-20') + '</strong><span>决策档案馆</span></div>' +
    '</div>';
  }

  function renderRelationshipHomeCard(moment) {
    var relationship = findById(allRelationships(), moment.linkedRelationship) || { name: '张敏', score: 88, last: '昨天', channel: '微信', next: '4 天后' };
    return '<div class="life-home-card life-card life-relationship-card clickable"' + momentTargetAttrs(moment) + '>' +
      '<div class="life-card-label red">关系提醒</div><div class="life-home-card-main"><h3 class="life-card-title">' + escapeHtml(moment.title) + '</h3><p class="life-card-copy">最近联系：' + escapeHtml(relationship.last) + ' · ' + escapeHtml(relationship.channel) + '；亲密度 ' + escapeHtml(relationship.score) + '/100</p></div><div class="life-relation-change"><span>下次联系</span><strong>' + escapeHtml(relationship.next) + '</strong><i></i><strong>' + escapeHtml(relationship.group || '朋友') + '</strong></div><div class="life-avatar-pair"><span>' + escapeHtml(relationship.name.slice(0, 1)) + '</span><span>' + escapeHtml(relationship.name.slice(-1)) + '</span></div><div class="life-distance-badge">去关系温度</div>' +
    '</div>';
  }

  function renderWishHomeCard(moment) {
    var wish = findById(allWishes(), moment.linkedWish) || { status: '愿望冷却中', days: 12, desire: 72, due: '2026-05-25' };
    return '<div class="life-home-card life-card life-wish-card clickable"' + momentTargetAttrs(moment) + '>' +
      '<div class="life-card-label blue">' + escapeHtml(wish.status) + '</div><div class="life-home-card-main"><h3 class="life-card-title">' + escapeHtml(moment.title) + '</h3><p class="life-card-copy">剩余 ' + escapeHtml(wish.days) + ' 天</p><p class="life-card-copy">当前想要程度：' + escapeHtml(wish.desire) + '/100</p></div><div class="life-cool-box"><span>冷却至</span><strong>' + escapeHtml(wish.due) + '</strong><span>愿望冷却箱</span></div>' +
    '</div>';
  }

  function renderMemoryHomeCard(moment) {
    return '<div class="life-home-card life-card life-memory-card clickable"' + momentTargetAttrs(moment) + '>' +
      '<div class="life-card-label blue">本月值得记住</div><div class="life-home-card-main"><h3 class="life-card-title">' + escapeHtml(moment.title) + '</h3><p class="life-card-copy">' + escapeHtml(moment.copy) + '</p><div class="life-meta"><span>' + iconHtml('location') + ' ' + escapeHtml(moment.location) + '</span></div></div><div class="life-memory-photos"><span class="life-photo photo-garden"></span><span class="life-photo photo-river"></span><span class="life-photo photo-mountain"></span><span class="life-photo photo-night"></span></div><div class="life-memory-actions"><span>❤ 12</span><span>♡ 3</span></div>' +
    '</div>';
  }

  function renderProjectHomeCard(moment) {
    var project = allProjects()[0] || { name: '项目进展', progress: 60, next: '完成首页视觉稿', people: '团队协作 8/10' };
    return '<div class="life-home-card life-card life-compact-card clickable"' + momentTargetAttrs(moment) + '>' +
      '<div class="life-home-type-icon green">' + iconHtml('project') + '</div><div class="life-home-card-main"><h3 class="life-card-title">' + escapeHtml(moment.title || project.name) + '</h3><p class="life-card-copy">下一步：' + escapeHtml(project.next) + ' <span class="life-badge amber">项目</span></p></div><div class="life-team-note"><span>' + escapeHtml(project.people) + '</span><strong>' + escapeHtml(project.progress) + '%</strong><span class="life-avatar-row"><i></i><i></i><i></i><i></i> +2</span></div>' +
    '</div>';
  }

  function renderSleepHomeCard(moment) {
    var sleep = allHealth()[0] || { name: '睡眠', value: '7.2 小时', note: moment.copy };
    return '<div class="life-home-card life-card life-compact-card clickable"' + momentTargetAttrs(moment) + '>' +
      '<div class="life-home-type-icon purple">' + iconHtml('calm') + '</div><div class="life-home-card-main"><h3 class="life-card-title">' + escapeHtml(moment.title || sleep.name) + '</h3><p class="life-card-copy">' + escapeHtml(sleep.note) + ' <span class="life-badge green">健康</span></p></div><div class="life-sleep-note"><span>' + escapeHtml(sleep.name) + '</span><p>' + escapeHtml(sleep.value) + '</p></div><span class="life-photo photo-book life-small-photo"></span>' +
    '</div>';
  }

  function filteredMoments() {
    return allMoments().filter(function(item) {
      var inType = state.timelineFilter === '全部' || item.type === state.timelineFilter || item.tags.indexOf(state.timelineFilter) >= 0;
      var text = [item.title, item.copy, item.location, item.type, item.tags.join(' '), item.people.join(' ')].join(' ');
      return inType && queryMatch(text);
    });
  }

  function renderTimeline() {
    var moments = filteredMoments();
    els.content.innerHTML = mockNotice() +
      '<section class="life-river-layout">' +
        '<div class="life-panel life-river-panel">' +
          '<div class="life-river-head"><div><h2 class="life-panel-title">时间河流 <span class="life-down-mark">⌄</span></h2><p class="life-panel-sub">记录生命的每一刻，连接过去与未来</p></div></div>' +
          '<div class="life-timeline">' + (moments.length ? moments.map(function(item, idx) { return homeMomentCard(item, idx, moments); }).join('') : '<div class="life-empty">没有匹配的生活记录</div>') + '</div>' +
        '</div>' +
      '</section>';
    els.aside.innerHTML = renderAddMini() + renderPendingReview() + renderMonthlyMini();
  }

  function renderDecisionMini() {
    var items = allDecisions();
    return '<section class="life-panel"><div class="life-panel-head"><div><h2 class="life-panel-title">决策档案馆</h2><p class="life-panel-sub">近期需要复盘的决定</p></div><button class="life-mini-btn" data-action="view-decisions">全部 (' + items.length + ')</button></div>' +
      '<div class="life-list">' + items.map(function(item) {
        return '<div class="life-row clickable" data-decision-id="' + item.id + '"><div class="life-row-head"><h3 class="life-row-title">' + escapeHtml(item.title) + '</h3><span class="life-badge ' + (item.status === '待复盘' ? 'amber' : 'green') + '">' + item.status + '</span></div><p class="life-card-copy">我的选择：' + escapeHtml(item.choice) + ' · 信心 ' + item.confidence + '%</p>' + progress(item.confidence, 'var(--life-accent)') + '</div>';
      }).join('') + '</div></section>';
  }

  function renderMoodMini() {
    return '<section class="life-panel">' +
      '<div class="life-weather"><div class="life-sun">' + iconHtml('sun') + '</div><div><h2 class="life-panel-title">今日心情</h2><div><span class="life-score">78<small> /100</small></span></div><p class="life-panel-sub">晴朗，感觉平静而满足</p></div></div>' +
      '<div class="life-kpi-grid"><div class="life-kpi"><span>睡眠</span><strong>7.2 小时</strong></div><div class="life-kpi"><span>压力</span><strong>35 /100</strong></div><div class="life-kpi"><span>精力</span><strong>80 /100</strong></div></div>' +
      '<div class="life-line-chart">' + [46, 82, 58, 42, 86, 48, 76].map(function(v) { return '<span class="life-bar" style="height:' + v + '%"></span>'; }).join('') + '</div>' +
    '</section>';
  }

  function renderAddMini() {
    return '<section class="life-detail-card life-quick-add"><div class="life-detail-head"><div><h2 class="life-detail-title">添加一刻</h2></div><span class="life-muted">今天</span></div>' +
      '<button class="life-quick-input" type="button" data-action="go-add">今天发生了什么？</button>' +
      '<div class="life-quick-types">' +
      [['mood','情绪'], ['decision','决定'], ['relationship','关系'], ['wish','愿望'], ['location','地点']].map(function(item) { return '<button type="button" data-action="go-add">' + iconHtml(item[0]) + '<span>' + item[1] + '</span></button>'; }).join('') +
      '</div><div class="life-quick-tools"><span>' + iconHtml('memory') + '</span><span>' + iconHtml('monthly') + '</span><span>' + iconHtml('add') + '</span><span>' + iconHtml('project') + '</span><button class="life-primary-btn" data-action="go-add">记录</button></div></section>';
  }

  function renderPendingReview() {
    var items = allDecisions();
    return '<section class="life-detail-card"><div class="life-detail-head"><h2 class="life-detail-title">待复盘</h2><span class="life-muted">全部 ' + items.length + '</span></div><div class="life-list" style="margin-top:12px">' +
      items.map(function(item, idx) {
        return '<div class="life-row life-side-row"><span class="life-side-icon ' + (idx === 0 ? 'danger' : idx === 1 ? 'green' : '') + '">' + iconHtml(idx === 2 ? 'wish' : 'decision') + '</span><div><h3 class="life-row-title">' + escapeHtml(item.title) + '</h3><p class="life-panel-sub">记录于 ' + item.date + '</p></div><span class="life-badge ' + (idx === 0 ? 'red' : 'gray') + '">' + (idx === 0 ? '已逾期 28 天' : '还剩 ' + (idx * 7 + 5) + ' 天') + '</span></div>';
      }).join('') + '</div><button class="life-card-link" type="button" data-action="view-decisions">查看全部 →</button></section>';
  }

  function renderMonthlyMini() {
    return '<section class="life-detail-card"><div class="life-detail-head"><div><h2 class="life-detail-title">本月值得记住</h2><p class="life-panel-sub">5 月 · 8 条记录</p></div></div><div class="life-list" style="margin-top:12px">' +
      ['苏州一日游', '完成年度体检', '拿到驾照', '妈妈生日'].map(function(item, idx) {
        return '<div class="life-row life-memory-row"><span class="life-side-icon ' + ['blue','green','amber','danger'][idx] + '">' + iconHtml(['monthly','health','decision','relationship'][idx]) + '</span><span class="life-memory-date">05-' + ['13','08','05','01'][idx] + '</span><strong>' + item + '</strong><span class="life-badge ' + ['amber','green','blue','red'][idx] + '">' + ['旅行','健康','里程碑','家庭'][idx] + '</span>' + (idx === 0 ? '<span class="life-photo photo-garden"></span>' : '') + '</div>';
      }).join('') + '</div><button class="life-card-link" type="button" data-action="view-monthly">查看全部 →</button></section>';
  }

  function renderLifeAxis() {
    var items = filteredAxisMilestones();
    var allItems = axisMilestones();
    var selected = items.filter(function(item) { return item.id === state.selectedAxisId; })[0] || items[0];
    if (!selected) selected = allItems.filter(function(item) { return item.id === state.selectedAxisId; })[0] || allItems[0];
    if (selected) state.selectedAxisId = selected.id;
    els.content.innerHTML = mockNotice() + '<section class="life-axis-page">' +
      '<div class="life-axis-titlebar"><h2>人生时间轴</h2><button class="life-secondary-btn ' + (state.axisFilterOpen ? 'active' : '') + '" data-axis-action="toggle-filter">' + iconHtml('search') + ' 筛选</button></div>' +
      (state.axisFilterOpen ? renderAxisFilterPanel(items.length, allItems.length) : '') +
      '<div class="life-axis-category-tabs">' + ['全部','旅行','项目','健康','关系','居住','工作','作品'].map(function(item) { return '<button class="' + (state.axisCategory === item ? 'active' : '') + '" data-axis-category="' + item + '">' + item + '</button>'; }).join('') + '</div>' +
      '<div class="life-axis-year-tabs">' + ['全部','2026','2025','2024','2023','2022','2021','2020','2019','2018','更早'].map(function(item) { return '<button class="' + (state.axisYear === item ? 'active' : '') + '" data-axis-year="' + item + '">' + item + '</button>'; }).join('') + '</div>' +
      '<div class="life-axis-stage-strip">' +
        renderAxisStageButton('探索与尝试', '2018-2020', 'blue') +
        renderAxisStageButton('建立与成长', '2021-2023', 'green') +
        renderAxisStageButton('突破与蜕变', '2024-2025', 'amber') +
        renderAxisStageButton('未来想象', '2026+', 'dashed') +
      '</div>' +
      '<div class="life-axis-list">' + (items.length ? renderAxisYears(items, selected.id) : '<div class="life-empty">没有匹配的里程碑</div>') + '</div>' +
    '</section>';
    els.aside.innerHTML = renderAxisAside(selected);
  }

  function renderAxisStageButton(name, years, tone) {
    return '<button class="life-axis-stage ' + tone + (state.axisStage === name ? ' active' : '') + '" data-axis-stage="' + name + '"><strong>' + name + '</strong><span>' + years + '</span></button>';
  }

  function renderAxisFilterPanel(count, total) {
    var activeFilters = [state.axisCategory, state.axisYear, state.axisStage].filter(function(item) { return item !== '全部'; });
    return '<div class="life-axis-filter-panel"><div><strong>当前筛选</strong><span>' + (activeFilters.length ? activeFilters.join(' / ') : '全部里程碑') + '</span></div><div><strong>' + count + '</strong><span>/ ' + total + ' 条</span></div><button class="life-mini-btn" data-axis-action="clear-filter">清空筛选</button></div>';
  }

  function axisMilestones() {
    var baseItems = [
      { id: 'a1', year: '2026', season: '春', day: '03-05', title: '开始自由职业', desc: '成为独立设计师，建立自己的工作节奏与客户体系。', type: '工作', icon: 'project', place: '上海', date: '2026-03-01', photos: ['photo-book'], people: 0 },
      { id: 'a2', year: '2026', season: '夏', day: '07-20', title: '计划东南亚之旅', desc: '准备年中出发，去看看更广阔的世界。', type: '旅行', icon: 'travel', place: '待出发', date: '2026-07', photos: ['photo-river'], action: true },
      { id: 'a3', year: '2025', season: '冬', day: '12-02', title: '完成个人品牌官网', desc: '网站上线，开始接到来自不同领域的合作邀请。', type: '项目', icon: 'project', place: '上海', date: '2025-01-15', photos: ['photo-office'], people: 5 },
      { id: 'a4', year: '2025', season: '秋', day: '09-11', title: '九寨沟 & 成都之旅', desc: '期待已久的自然之旅，治愈和放松。', type: '旅行', icon: 'travel', place: '四川', date: '2025-10-03', photos: ['photo-mountain','photo-river','photo-garden'], people: 0 },
      { id: 'a5', year: '2025', season: '夏', day: '06-08', title: '学习潜水（OW）', desc: '在海南完成开放水域潜水员认证。', type: '健康', icon: 'health', place: '海南 · 万宁', date: '2025-07-20', photos: ['photo-river'], people: 0 },
      { id: 'a6', year: '2025', season: '春', day: '03-05', title: '搬到上海徐汇', desc: '新环境，新生活的开始。', type: '居住', icon: 'flow', place: '上海', date: '2025-04-12', photos: ['photo-river'], people: 0 },
      { id: 'a7', year: '2024', season: '秋', day: '10-12', title: '决定辞职，给自己一年时间', desc: '经过长时间的思考，决定跳出舒适区，重新探索人生方向。', type: '重要决定', icon: 'star', place: '上海', date: '2024-11-01', photos: ['photo-book','photo-office','photo-river'], people: 7 },
      { id: 'a8', year: '2024', season: '夏', day: '06-08', title: '独自去日本旅行', desc: '第一次独自出国，自由而充实。', type: '旅行', icon: 'travel', place: '日本', date: '2024-07-18', photos: ['photo-night','photo-mountain','photo-garden'], people: 0 },
      { id: 'a9', year: '2024', season: '春', day: '03-05', title: '开始正念练习', desc: '每天冥想 10 分钟，关注自己的内心。', type: '健康', icon: 'health', place: '上海', date: '2024-03-10', photos: ['photo-garden'], people: 0 },
      { id: 'a10', year: '2023', season: '秋', day: '09-11', title: '参与公益设计项目', desc: '为山区儿童设计阅读空间，收获很多感动。', type: '项目', icon: 'project', place: '云南 · 大理', date: '2023-10-22', photos: ['photo-office','photo-cafe'], people: 5 },
      { id: 'a11', year: '2023', season: '夏', day: '06-08', title: '新疆自驾之旅', desc: '辽阔到让人安静的土地。', type: '旅行', icon: 'travel', place: '新疆', date: '2023-07-05', photos: ['photo-mountain','photo-garden','photo-river'], people: 0 }
    ];
    var store = getAxisStore();
    return baseItems.concat(store.added).filter(function(item) {
      return store.deleted.indexOf(item.id) < 0;
    }).map(function(item) {
      if (!store.edits[item.id]) return item;
      var edited = Object.assign({}, item, store.edits[item.id]);
      return edited;
    }).sort(function(a, b) {
      return String(b.date).localeCompare(String(a.date));
    });
  }

  function filteredAxisMilestones() {
    return axisMilestones().filter(function(item) {
      var text = [item.year, item.season, item.day, item.title, item.desc, item.type, item.place, item.date].join(' ');
      var categoryMatch = state.axisCategory === '全部' || item.type === state.axisCategory || (state.axisCategory === '项目' && item.type === '作品');
      var yearMatch = state.axisYear === '全部' || item.year === state.axisYear || (state.axisYear === '更早' && Number(item.year) < 2018);
      var stageMatch = state.axisStage === '全部' || axisStageIncludes(state.axisStage, item.year);
      return categoryMatch && yearMatch && stageMatch && queryMatch(text);
    });
  }

  function axisStageIncludes(stage, year) {
    var value = Number(year);
    if (stage === '探索与尝试') return value >= 2018 && value <= 2020;
    if (stage === '建立与成长') return value >= 2021 && value <= 2023;
    if (stage === '突破与蜕变') return value >= 2024 && value <= 2025;
    if (stage === '未来想象') return value >= 2026;
    return true;
  }

  function renderAxisYears(items, selectedId) {
    var years = [];
    items.forEach(function(item) {
      if (years.indexOf(item.year) < 0) years.push(item.year);
    });
    return years.map(function(year) {
      var yearItems = items.filter(function(item) { return item.year === year; });
      var isCurrentYear = yearItems.some(function(item) { return item.id === selectedId; });
      return '<section class="life-axis-year-block ' + (isCurrentYear ? 'current' : '') + '"><div class="life-axis-year-label">' + year + '</div><div class="life-axis-year-marker"></div><div class="life-axis-events">' + yearItems.map(function(item) { return renderAxisEvent(item, selectedId); }).join('') + '</div></section>';
    }).join('');
  }

  function renderAxisEvent(item, selectedId) {
    return '<article class="life-axis-event ' + (item.id === selectedId ? 'active' : '') + '" data-axis-id="' + item.id + '">' +
      '<div class="life-axis-date"><span>' + escapeHtml(item.season) + '</span><strong>' + escapeHtml(item.day) + '</strong></div>' +
      '<div class="life-axis-event-main"><h3>' + escapeHtml(item.title) + '<span class="life-badge ' + axisColor(item.type) + '">' + escapeHtml(item.type) + '</span></h3><p>' + escapeHtml(item.desc) + '</p></div>' +
      '<div class="life-axis-place"><span>' + escapeHtml(item.place) + '</span><strong>' + escapeHtml(item.date) + '</strong></div>' +
      '<div class="life-axis-media">' + (item.action ? '<button class="life-axis-add" data-axis-action="add-near">+ 添加</button>' : renderAxisThumbs(item)) + '</div>' +
    '</article>';
  }

  function renderAxisThumbs(item) {
    if (item.photos && item.photos.length) {
      return item.photos.slice(0, 3).map(function(photo) { return axisPhotoHtml(photo, ''); }).join('');
    }
    if (item.people) {
      return '<div class="life-axis-people"><span></span><span></span><span></span>' + (item.people > 3 ? '<em>+' + (item.people - 3) + '</em>' : '') + '</div>';
    }
    return '';
  }

  function axisColor(type) {
    if (type === '重要决定') return 'amber';
    if (type === '旅行') return 'blue';
    if (type === '健康') return 'green';
    if (type === '居住') return 'green';
    if (type === '工作') return 'blue';
    if (type === '项目') return 'blue';
    return 'gray';
  }

  function axisLocationMeta(item) {
    if (item.locationMeta) return item.locationMeta;
    if (item.place === '待出发') return '行程尚未开始';
    if (item.place === '上海') return '中国 · 上海市';
    if (item.place === '日本') return '日本';
    if (item.place === '新疆') return '中国 · 新疆';
    if (item.place === '四川') return '中国 · 四川省';
    if (item.place === '海南 · 万宁') return '中国 · 海南省';
    if (item.place === '云南 · 大理') return '中国 · 云南省';
    return item.place ? '记录地点 · ' + item.place : '未记录地点';
  }

  function axisLocationPhoto(item) {
    var photos = item.photos || [];
    return photos[0] || (item.type === '旅行' ? 'photo-mountain' : (item.type === '项目' ? 'photo-office' : 'photo-river'));
  }

  function axisPhotoHtml(photo, extraClass) {
    var value = String(photo || '').trim();
    var className = extraClass ? ' ' + extraClass : '';
    if (/^(data:image\/|https?:\/\/|\.\/|\/)/.test(value)) {
      return '<span class="life-photo life-photo-upload' + className + '"><img src="' + escapeHtml(value) + '" alt=""></span>';
    }
    return '<span class="life-photo ' + escapeHtml(value) + className + '"></span>';
  }

  function axisLinkedRelationships(item) {
    var keys = [item.title, item.place, item.year, item.date].filter(Boolean);
    return allRelationships().filter(function(person) {
      var searchable = [
        person.name,
        person.role,
        person.group,
        relationshipMediaText(person.memories),
        relationshipMediaText(person.places),
        relationshipMediaText(person.gifts),
        (person.notes || []).join(' '),
        (person.dates || []).join(' '),
        person.memo
      ].join(' ');
      return keys.some(function(key) {
        return key && searchable.indexOf(key) !== -1;
      });
    });
  }

  function axisPeopleHtml(item) {
    var people = axisLinkedRelationships(item);
    if (!people.length) return '<p class="life-axis-empty-copy">暂无从关系温度关联到的人物</p>';
    return '<div class="life-axis-face-row">' + people.slice(0, 4).map(function(person) {
      return relationshipAvatarHtml(person, 'small');
    }).join('') + (people.length > 4 ? '<em>+' + (people.length - 4) + '</em>' : '') + '</div>';
  }

  function axisRelatedDecisions(item) {
    var keys = [item.title, item.desc, item.place, item.type].filter(Boolean);
    return decisionArchiveItems().filter(function(decision) {
      var searchable = [decision.title, decision.background, decision.category, decision.choice, decision.date].join(' ');
      var categoryMatch = item.type === '重要决定' || decision.category === item.type || searchable.indexOf(item.place || '') !== -1;
      var textMatch = keys.some(function(key) {
        if (!key || key.length < 2) return false;
        return searchable.indexOf(key) !== -1 || key.indexOf(decision.category) !== -1;
      });
      return categoryMatch && textMatch;
    }).slice(0, 3);
  }

  function axisMoodDetail(item) {
    var exact = allMoodRecords().filter(function(record) {
      return record.date === item.date;
    })[0];
    if (!exact) return null;
    return {
      date: exact.date,
      score: exact.score,
      label: exact.feeling || exact.weather || '已记录',
      dimensions: [
        ['睡眠', Math.round(Number(exact.sleep || 0) * 10), (exact.sleep || '--') + 'h'],
        ['压力', Number(exact.pressure || 0), exact.pressure <= 40 ? '较低' : '偏高'],
        ['精力', Number(exact.energy || 0), exact.energy >= 70 ? '充沛' : '一般'],
        ['心情', Number(exact.score || 0), exact.weather || exact.feeling || '记录']
      ]
    };
  }

  function axisTags(item) {
    if (item.tags && item.tags.length) return item.tags;
    return [item.type, item.year, item.place].filter(Boolean).slice(0, 4);
  }

  function axisDecisionRows(item) {
    var rows = axisRelatedDecisions(item);
    if (!rows.length) return '<p class="life-axis-empty-copy">暂无相关决定</p>';
    return rows.map(function(row) {
      var pending = row.status !== '已复盘';
      return '<div class="life-axis-decision-row">' + iconHtml('review') + '<strong>' + escapeHtml(row.title) + '</strong><span>' + escapeHtml(row.date) + '</span><em class="' + (pending ? 'pending' : '') + '">' + escapeHtml(row.status) + '</em></div>';
    }).join('') + '<button class="life-card-link" data-action="view-decisions">查看全部相关决定 →</button>';
  }

  function axisMoodHtml(item) {
    var mood = axisMoodDetail(item);
    if (!mood) return '<p class="life-axis-empty-copy">暂无同日期情绪记录</p>';
    return '<div class="life-axis-mood-box"><div><strong>' + escapeHtml(mood.score) + '</strong><span>/100</span><p>' + escapeHtml(mood.label) + '</p></div><ul>' +
      mood.dimensions.map(function(row) {
        return '<li><span>' + escapeHtml(row[0]) + '</span><b style="--w:' + Number(row[1] || 0) + '%"></b><em>' + escapeHtml(row[1]) + ' ' + escapeHtml(row[2]) + '</em></li>';
      }).join('') +
    '</ul></div>';
  }

  function splitAxisList(value) {
    return String(value || '').split(/[,，\\n]/).map(function(item) { return item.trim(); }).filter(Boolean);
  }

  function renderAxisAside(item) {
    if (!item) return '';
    if (state.axisEditing) return renderAxisEditForm(item);
    var detailPhotos = (item.photos && item.photos.length ? item.photos : ['photo-book','photo-office','photo-river']).slice(0, 4);
    var peopleCount = axisLinkedRelationships(item).length;
    var mood = axisMoodDetail(item);
    return '<section class="life-axis-detail-card">' +
      '<div class="life-axis-detail-head"><div class="life-axis-detail-icon ' + axisColor(item.type) + '">' + iconHtml(item.icon) + '</div><div><h2>' + escapeHtml(item.title) + '</h2><p>' + iconHtml('location') + ' ' + escapeHtml(item.place) + '<span>' + escapeHtml(item.date) + '</span></p></div><span class="life-badge ' + axisColor(item.type) + '">' + escapeHtml(item.type) + '</span></div>' +
      '<p class="life-axis-detail-copy">' + escapeHtml(item.desc) + '</p>' +
      '<div class="life-axis-detail-photos">' + detailPhotos.map(function(photo) { return axisPhotoHtml(photo, ''); }).join('') + '</div>' +
      '<div class="life-axis-detail-section"><h3>相关人物 <span>' + peopleCount + '</span></h3>' + axisPeopleHtml(item) + '</div>' +
      '<div class="life-axis-detail-section"><h3>地点</h3><div class="life-axis-location">' + axisPhotoHtml(axisLocationPhoto(item), '') + '<div><strong>' + escapeHtml(item.place || '未记录地点') + '</strong><p>' + escapeHtml(axisLocationMeta(item)) + '</p></div><div class="life-map-pin">' + iconHtml('location') + '</div></div></div>' +
      '<div class="life-axis-detail-section"><h3>相关决定 <span>' + axisRelatedDecisions(item).length + '</span></h3>' + axisDecisionRows(item) + '</div>' +
      '<div class="life-axis-detail-section"><div class="life-axis-mood-head"><h3>当时的情绪</h3><span>' + (mood ? '记录于 ' + escapeHtml(mood.date) : '来自情绪天气站') + '</span></div>' + axisMoodHtml(item) + '</div>' +
      '<div class="life-axis-detail-section"><h3>标签</h3><div class="life-chip-row">' + axisTags(item).map(function(tag) { return '<span class="life-badge gray">' + escapeHtml(tag) + '</span>'; }).join('') + '</div></div>' +
      '<div class="life-axis-actions"><button class="life-secondary-btn" data-axis-action="edit">' + iconHtml('add') + ' 编辑</button><button class="life-danger-btn" data-axis-action="delete">删除</button><button class="life-kebab" data-axis-action="more">⋮</button></div>' +
    '</section>';
  }

  function renderAxisEditForm(item) {
    return '<section class="life-axis-detail-card"><form id="lifeAxisEditForm" class="life-form life-axis-edit-form"><div class="life-detail-head"><h2 class="life-detail-title">编辑里程碑</h2><button class="life-mini-btn" type="button" data-axis-action="cancel-edit">取消</button></div>' +
      '<label>标题<input class="life-input" name="title" value="' + escapeHtml(item.title) + '"></label>' +
      '<label>说明<textarea class="life-textarea" name="desc">' + escapeHtml(item.desc) + '</textarea></label>' +
      '<div class="life-two-grid"><label>年份<input class="life-input" name="year" value="' + escapeHtml(item.year) + '"></label><label>日期<input class="life-input" name="date" value="' + escapeHtml(item.date) + '"></label></div>' +
      '<div class="life-two-grid"><label>季节<input class="life-input" name="season" value="' + escapeHtml(item.season) + '"></label><label>日期标签<input class="life-input" name="day" value="' + escapeHtml(item.day) + '"></label></div>' +
      '<div class="life-two-grid"><label>分类<input class="life-input" name="type" value="' + escapeHtml(item.type) + '"></label><label>地点<input class="life-input" name="place" value="' + escapeHtml(item.place) + '"></label></div>' +
      '<label>图片<input class="life-input" name="photos" value="' + escapeHtml((item.photos || []).join(', ')) + '" placeholder="图片地址或样式名，用逗号分隔"></label>' +
      '<input type="hidden" name="uploadedPhoto" data-axis-uploaded-photo>' +
      '<div class="life-axis-upload-row"><label class="life-media-file-label">上传图片<input type="file" accept="image/*" data-axis-image-upload></label><div class="life-axis-upload-preview" data-axis-upload-preview>' + (item.photos && item.photos[0] ? axisPhotoHtml(item.photos[0], '') : '<span>未选择图片</span>') + '</div></div>' +
      '<button class="life-primary-btn" type="submit">保存修改</button></form></section>';
  }

  function addAxisMilestone(template) {
    var store = getAxisStore();
    var source = template || { year: '2026', season: '秋', day: '09-01', type: '项目', icon: 'project', place: '上海', photos: ['photo-office'] };
    var item = {
      id: 'a-local-' + Date.now(),
      year: source.year,
      season: source.season,
      day: source.day,
      title: '新增里程碑',
      desc: '从按钮添加的一条测试里程碑，可继续编辑。',
      type: source.type,
      icon: source.icon,
      place: source.place,
      date: source.year + '-09-01',
      photos: source.photos || ['photo-office'],
      people: 0
    };
    store.added.push(item);
    saveAxisStore(store);
    state.selectedAxisId = item.id;
    state.axisYear = item.year;
    state.axisStage = '全部';
    state.axisEditing = true;
    showToast('已添加里程碑，可在右侧编辑');
    renderLifeAxis();
  }

  function deleteSelectedAxis() {
    var store = getAxisStore();
    if (store.deleted.indexOf(state.selectedAxisId) < 0) store.deleted.push(state.selectedAxisId);
    saveAxisStore(store);
    var remaining = filteredAxisMilestones();
    state.selectedAxisId = remaining[0] ? remaining[0].id : '';
    showToast('里程碑已删除');
    renderLifeAxis();
  }

  function saveAxisEdit(form) {
    var store = getAxisStore();
    var title = form.elements.title.value.trim() || '未命名里程碑';
    var desc = form.elements.desc.value.trim() || '暂无说明';
    var year = form.elements.year.value.trim() || '2026';
    var date = form.elements.date.value.trim() || year + '-01-01';
    var type = form.elements.type.value.trim() || '项目';
    var uploadedPhoto = form.elements.uploadedPhoto ? form.elements.uploadedPhoto.value : '';
    store.edits[state.selectedAxisId] = {
      title: title,
      desc: desc,
      year: year,
      date: date,
      season: form.elements.season.value.trim() || '春',
      day: form.elements.day.value.trim() || date.slice(5) || '01-01',
      type: type,
      icon: type === '旅行' ? 'travel' : (type === '健康' ? 'health' : (type === '重要决定' ? 'star' : 'project')),
      place: form.elements.place.value.trim() || '未记录地点',
      photos: splitAxisList(form.elements.photos.value).concat(uploadedPhoto ? [uploadedPhoto] : [])
    };
    saveAxisStore(store);
    state.axisEditing = false;
    showToast('里程碑已保存');
    renderLifeAxis();
  }

  function renderDecisions() {
    var items = decisionArchiveItems();
    var list = items.filter(function(item) {
      return decisionMatchesFilter(item) && queryMatch([item.title, item.choice, item.category, item.background, item.date].join(' '));
    });
    var selected = list.filter(function(item) { return item.id === state.selectedDecisionId; })[0] || list[0] || items[0];
    if (selected) state.selectedDecisionId = selected.id;
    var detail = state.decisionFormMode === 'create' ? renderDecisionForm(null, 'create') : (state.decisionFormMode === 'edit' ? renderDecisionForm(selected, 'edit') : (state.decisionFormMode === 'review' ? renderDecisionReviewForm(selected) : renderDecisionDetail(selected)));
    els.content.innerHTML = mockNotice() + '<section class="life-decision-page">' +
      '<aside class="life-decision-list-panel">' +
        '<h2>决策档案馆</h2>' +
        '<div class="life-decision-tabs">' + ['重要决定','冷却中','已归档'].map(function(item) { return '<button class="' + (state.decisionFilter === item ? 'active' : '') + '" data-decision-filter="' + item + '">' + item + '</button>'; }).join('') + '</div>' +
        '<div class="life-decision-flow"><span>重要决定</span><i></i><span>冷却中</span><i></i><span>已归档</span><p>新决定先进入重要决定；需要观察时进入冷却中；完成复盘或主动归档后进入已归档。</p></div>' +
        '<label class="life-decision-search">' + iconHtml('search') + '<input type="search" data-decision-search placeholder="搜索决定..." value="' + escapeHtml(state.query) + '"><button type="button" data-decision-action="toggle-filter">' + iconHtml('search') + '</button></label>' +
        '<div class="life-decision-list">' + (list.length ? list.map(function(item) { return renderDecisionListItem(item, selected && selected.id === item.id); }).join('') : '<div class="life-empty">没有匹配的决定</div>') + '</div>' +
        '<div class="life-decision-count">共 ' + items.length + ' 项决定 <button type="button" data-decision-action="settings">' + iconHtml('settings') + '</button></div>' +
      '</aside>' +
      detail +
    '</section>';
    els.aside.innerHTML = state.decisionFormMode ? renderDecisionFormAside(selected, state.decisionFormMode) : renderDecisionAside(selected);
  }

  function decisionArchiveItems() {
    var meta = getDecisionMeta();
    return allDecisions().concat([
      { id: 'd-extra-1', status: '已归档', title: '是否购买这套房子？', date: '2025-11-18', category: '居住', choice: '暂不购买', confidence: 64, background: '房子位置不错，但总价和未来现金流压力偏高。', reason: ['先保留现金流安全边际。', '继续观察家庭居住需求。'], risks: ['可能错过合适房源。'], options: [['购买', '两居室', '上海', '首付压力大', '居住稳定'], ['暂不购买', '继续租住', '上海', '现金流安全', '选择灵活']], reviewDate: '2026-05-18', result: '已归档，继续观察市场。' },
      { id: 'd-extra-2', status: '已复盘', title: '是否结束这段关系？', date: '2025-08-30', category: '关系', choice: '保持边界', confidence: 72, background: '关系消耗感较强，需要重新定义边界。', reason: ['沟通成本长期偏高。', '需要优先保护自己的状态。'], risks: ['短期情绪波动。'], options: [['继续投入', '修复关系', '线上', '高精力', '不确定'], ['保持边界', '减少消耗', '线上', '中等', '更稳定']], reviewDate: '2026-02-28', result: '已复盘，状态更稳定。' },
      { id: 'd-extra-3', status: '冷却中', title: '是否辞去稳定工作？', date: '2025-07-12', category: '职业发展', choice: '继续观察', confidence: 58, background: '工作稳定但成长空间有限，需要确认真实动机。', reason: ['先做副业验证。', '评估现金流。'], risks: ['冲动决策风险。'], options: [['辞职', '自由职业', '上海', '收入不稳', '成长快'], ['继续工作', '保持稳定', '上海', '风险低', '成长慢']], reviewDate: '2026-01-12', result: '仍在冷却中。' },
      { id: 'd-extra-4', status: '冷却中', title: '是否购买相机？', date: '2026-05-08', category: '数码', choice: '冷却 30 天', confidence: 52, background: '想系统学习摄影，但要验证真实使用频率。', reason: ['先租赁体验。'], risks: ['冲动消费。'], options: [['购买', 'A7C II', '线上', '¥8,999', '体验好'], ['先租', '短期验证', '线上', '¥300', '风险低']], reviewDate: '2026-06-08', result: '冷却中。' }
    ]).filter(function(item) {
      return meta.deleted.indexOf(item.id) < 0;
    }).map(function(item) {
      var edited = Object.assign({}, item, meta.edits[item.id] || {});
      if (meta.confidence[item.id] != null) edited.confidence = meta.confidence[item.id];
      if (meta.reviewed[item.id]) {
        edited.status = '已复盘';
        edited.result = meta.reviewed[item.id].result || edited.result;
        edited.reviewSummary = meta.reviewed[item.id];
      }
      return edited;
    });
  }

  function decisionBucket(item) {
    var status = decisionStatus(item);
    if (status === '冷却中') return '冷却中';
    if (status === '已归档' || status === '已复盘') return '已归档';
    return '重要决定';
  }

  function decisionMatchesFilter(item) {
    return decisionBucket(item) === state.decisionFilter;
  }

  function decisionTone(item) {
    var status = decisionStatus(item);
    if (status === '待复盘') return 'amber';
    if (status === '冷却中') return 'blue';
    if (status === '已复盘' || status === '已归档') return 'green';
    return 'gray';
  }

  function decisionStatus(item) {
    return item.status;
  }

  function isDecisionArchived(item) {
    return decisionBucket(item) === '已归档';
  }

  function renderDecisionListItem(item, active) {
    return '<article class="life-decision-list-item ' + (active ? 'active' : '') + '" data-decision-id="' + item.id + '">' +
      '<span class="life-decision-list-icon ' + decisionTone(item) + '">' + iconHtml(item.category === '关系' ? 'relationship' : item.category === '居住' ? 'flow' : item.category === '数码' ? 'memory' : 'decision') + '</span>' +
      '<div><h3>' + escapeHtml(item.title) + '</h3><p>' + escapeHtml(item.date) + '</p></div><span class="life-badge ' + decisionTone(item) + '">' + escapeHtml(decisionStatus(item)) + '</span>' +
    '</article>';
  }

  function renderDecisionDetail(item) {
    if (!item) return '<article class="life-decision-detail"><div class="life-empty">没有可查看的决定</div></article>';
    var meta = getDecisionMeta();
    var bookmarked = meta.bookmarks.indexOf(item.id) >= 0;
    return '<article class="life-decision-detail"><div class="life-decision-detail-top"><button class="life-back-btn" data-view="timeline">← 返回</button><div class="life-decision-actions"><button class="life-icon-btn ' + (bookmarked ? 'active' : '') + '" data-decision-action="bookmark">' + iconHtml('monthly') + '</button><button class="life-icon-btn" data-decision-action="more">···</button>' + (state.decisionMoreOpen ? '<div class="life-decision-menu"><button data-decision-action="edit-decision">编辑决定</button><button data-decision-action="move-cooling">移入冷却中</button><button data-decision-action="archive-decision">归档决定</button><button class="danger" data-decision-action="delete-decision">删除决定</button></div>' : '') + '</div></div>' +
      '<h2>' + escapeHtml(item.title) + '</h2><div class="life-decision-meta">' + iconHtml('monthly') + ' 记录于 ' + escapeHtml(item.date) + '<span class="life-badge blue">' + escapeHtml(item.category) + '</span><span class="life-badge ' + decisionTone(item) + '">' + escapeHtml(decisionStatus(item)) + '</span></div>' +
      '<section class="life-decision-section"><h3>背景</h3><p>' + escapeHtml(item.background) + '</p></section>' +
      '<section class="life-decision-section"><h3>可选方案</h3><table class="life-decision-table"><thead><tr><th>方案</th><th>A. ' + escapeHtml(item.options[0][0]) + '</th><th>B. ' + escapeHtml(item.options[1][0]) + '</th></tr></thead><tbody>' + ['职位','地点','年薪（含奖金）','发展空间','工作强度','生活成本'].map(function(label, idx) { return '<tr><td>' + label + '</td><td>' + escapeHtml(item.options[0][idx + 1] || '-') + '</td><td>' + escapeHtml(item.options[1][idx + 1] || '-') + '</td></tr>'; }).join('') + '</tbody></table></section>' +
      '<section class="life-decision-section"><h3>选择理由</h3>' + item.reason.map(function(text) { return '<p class="life-point good">' + iconHtml('health') + escapeHtml(text) + '</p>'; }).join('') + '</section>' +
      '<section class="life-decision-section"><h3>风险</h3>' + item.risks.map(function(text) { return '<p class="life-point risk">' + iconHtml('anxious') + escapeHtml(text) + '</p>'; }).join('') + '</section>' +
      '<section class="life-my-choice"><div><h3>' + iconHtml('add') + ' 我的选择</h3><p><strong>我选择：</strong>' + escapeHtml(item.choice) + '</p><span>选择日期：' + escapeHtml(item.date) + '</span></div><div><h3>给未来的自己</h3><p>勇敢走出去，拥抱变化，相信自己的学习能力和适应力。</p></div></section></article>';
  }

  function renderDecisionAside(item) {
    if (!item) return '';
    var archived = isDecisionArchived(item);
    var resultAction = archived ? '' : '<button class="life-mini-btn" data-decision-action="edit-result">' + iconHtml('add') + '</button>';
    return '<section class="life-decision-side-card"><h2>信心 <strong data-confidence-value>' + item.confidence + '</strong><span>/100</span></h2>' + progress(item.confidence, 'var(--life-amber)') + '<p>详情页只展示当时信心；进入编辑决定后才能调整。</p></section>' +
      '<section class="life-decision-side-card"><div class="life-detail-head"><h2>实际结果</h2>' + resultAction + '</div><dl><dt>状态</dt><dd><span class="life-badge green">已在新公司工作中</span></dd><dt>入职日期</dt><dd>2026-05-18</dd></dl><p>' + escapeHtml(item.result) + '</p><button class="life-card-link" data-decision-action="records">查看全部记录 →</button></section>' +
      '<section class="life-decision-side-card"><h2>当时情绪 <span>（记录时）</span></h2><div class="life-decision-emotion">' + iconHtml('smile') + '<strong>偏紧张</strong><span>期待 60%</span><span>焦虑 40%</span></div><p>关键词：不确定、兴奋、担心、期待</p></section>' +
      '<section class="life-decision-side-card"><h2>相关记忆</h2><div class="life-decision-memory-grid"><span class="life-photo photo-river"></span><span class="life-photo photo-night"></span><span class="life-photo photo-book"></span><span class="life-photo photo-cafe"></span></div><button class="life-card-link" data-action="back-timeline">全部记忆（4）→</button></section>' +
      renderDecisionReviewCard(item);
  }

  function renderDecisionReviewCard(item) {
    if (isDecisionArchived(item)) {
      var reviewed = decisionStatus(item) === '已复盘';
      var summary = item.reviewSummary || {};
      return '<section class="life-decision-side-card"><h2>' + (reviewed ? '复盘结果' : '归档记录') + '</h2><p><span class="life-badge green">' + escapeHtml(decisionStatus(item)) + '</span></p><p>' + escapeHtml(summary.learning || item.result || '这条决定已归档，无需再次复盘。') + '</p></section>';
    }
    return '<section class="life-decision-side-card"><h2>半年后复盘</h2><p>计划复盘日期：' + escapeHtml(item.reviewDate) + ' <span class="life-badge amber">待复盘</span></p><button class="life-primary-btn" style="width:100%" data-decision-action="start-review">开始复盘</button></section>';
  }

  function renderDecisionForm(item, mode) {
    var source = item || {
      status: '待复盘',
      title: '',
      date: '2026-05-13',
      category: '人生规划',
      choice: '',
      confidence: 60,
      background: '',
      reason: [''],
      risks: [''],
      options: [['接受方案', '', '', '', ''], ['保留现状', '', '', '', '']],
      reviewDate: '2026-11-13'
    };
    var optionA = source.options && source.options[0] ? source.options[0] : ['', '', '', '', ''];
    var optionB = source.options && source.options[1] ? source.options[1] : ['', '', '', '', ''];
    return '<article class="life-decision-detail life-decision-form-shell">' +
      '<div class="life-decision-detail-top"><button class="life-back-btn" type="button" data-decision-action="cancel-form">← 返回决定</button></div>' +
      '<form id="lifeDecisionForm" class="life-form life-decision-form">' +
        '<div class="life-form-title"><h2>' + (mode === 'edit' ? '编辑决定' : '添加决定') + '</h2><p>把背景、选项、选择理由和复盘日期一次记录完整，保存后会进入对应状态栏。</p></div>' +
        '<div class="life-two-grid"><label>决定标题<input class="life-input" name="title" value="' + escapeHtml(source.title) + '" placeholder="例如：是否接受新的 Offer"></label><label>分类<input class="life-input" name="category" value="' + escapeHtml(source.category) + '" placeholder="职业发展 / 关系 / 居住"></label></div>' +
        '<div class="life-three-grid"><label>状态<select class="life-select" name="status">' + ['待复盘','冷却中','已归档','已复盘'].map(function(status) { return '<option value="' + status + '"' + (source.status === status ? ' selected' : '') + '>' + status + '</option>'; }).join('') + '</select></label><label>记录日期<input class="life-input" type="date" name="date" value="' + escapeHtml(source.date) + '"></label><label>复盘日期<input class="life-input" type="date" name="reviewDate" value="' + escapeHtml(source.reviewDate) + '"></label></div>' +
        '<label>背景<textarea class="life-textarea" name="background" placeholder="为什么现在要做这个决定？">' + escapeHtml(source.background) + '</textarea></label>' +
        '<div class="life-decision-form-confidence"><div><strong>信心 <span data-confidence-value>' + source.confidence + '</span>/100</strong><p>拖动后保存到这条决定。</p></div><input class="life-confidence-slider" type="range" min="0" max="100" name="confidence" value="' + source.confidence + '" data-form-confidence-range></div>' +
        '<div class="life-two-grid"><label>我的选择<input class="life-input" name="choice" value="' + escapeHtml(source.choice) + '" placeholder="最终选择或暂定方向"></label><label>主要结果<input class="life-input" name="result" value="' + escapeHtml(source.result || '尚未产生结果。') + '" placeholder="已有结果可先记录"></label></div>' +
        '<section class="life-decision-form-section"><h3>可选方案</h3><div class="life-decision-options-grid"><label>方案 A<input class="life-input" name="optionA" value="' + escapeHtml(optionA[0]) + '"></label><label>A 角色/内容<input class="life-input" name="optionARole" value="' + escapeHtml(optionA[1]) + '"></label><label>A 地点<input class="life-input" name="optionAPlace" value="' + escapeHtml(optionA[2]) + '"></label><label>A 成本<input class="life-input" name="optionACost" value="' + escapeHtml(optionA[3]) + '"></label><label>A 成长<input class="life-input" name="optionAGrowth" value="' + escapeHtml(optionA[4]) + '"></label><label>方案 B<input class="life-input" name="optionB" value="' + escapeHtml(optionB[0]) + '"></label><label>B 角色/内容<input class="life-input" name="optionBRole" value="' + escapeHtml(optionB[1]) + '"></label><label>B 地点<input class="life-input" name="optionBPlace" value="' + escapeHtml(optionB[2]) + '"></label><label>B 成本<input class="life-input" name="optionBCost" value="' + escapeHtml(optionB[3]) + '"></label><label>B 成长<input class="life-input" name="optionBGrowth" value="' + escapeHtml(optionB[4]) + '"></label></div></section>' +
        '<div class="life-two-grid"><label>选择理由<textarea class="life-textarea" name="reason" placeholder="一行一个理由">' + escapeHtml((source.reason || []).join('\n')) + '</textarea></label><label>风险<textarea class="life-textarea" name="risks" placeholder="一行一个风险">' + escapeHtml((source.risks || []).join('\n')) + '</textarea></label></div>' +
        '<div class="life-decision-form-actions">' + (mode === 'edit' ? '<button class="life-danger-btn" type="button" data-decision-action="delete-decision">删除决定</button>' : '') + '<button class="life-secondary-btn" type="button" data-decision-action="cancel-form">取消</button><button class="life-primary-btn" type="submit">' + (mode === 'edit' ? '保存修改' : '保存决定') + '</button></div>' +
      '</form>' +
    '</article>';
  }

  function renderDecisionReviewForm(item) {
    if (!item) return '<article class="life-decision-detail"><div class="life-empty">没有可复盘的决定</div></article>';
    var summary = item.reviewSummary || {};
    return '<article class="life-decision-detail life-decision-form-shell">' +
      '<div class="life-decision-detail-top"><button class="life-back-btn" type="button" data-decision-action="cancel-form">← 返回决定</button></div>' +
      '<form id="lifeDecisionReviewForm" class="life-form life-decision-form life-decision-review-form">' +
        '<div class="life-form-title"><h2>复盘：' + escapeHtml(item.title) + '</h2><p>复盘完成后，这条决定会进入「已归档」，保留原始决定和结果记录。</p></div>' +
        '<label>实际结果<textarea class="life-textarea" name="result" placeholder="这个决定最终发生了什么？">' + escapeHtml(summary.result || item.result || '') + '</textarea></label>' +
        '<div class="life-two-grid"><label>状态<select class="life-select" name="status"><option value="已复盘">已复盘</option><option value="已归档">仅归档</option></select></label><label>复盘日期<input class="life-input" type="date" name="reviewedAt" value="' + escapeHtml(summary.reviewedAt || '2026-05-13') + '"></label></div>' +
        '<label>学到什么<textarea class="life-textarea" name="learning" placeholder="哪些判断是对的？哪些信息当时缺失？">' + escapeHtml(summary.learning || '') + '</textarea></label>' +
        '<label>下一次会怎么做<textarea class="life-textarea" name="next" placeholder="把经验转成下一次决策准则。">' + escapeHtml(summary.next || '') + '</textarea></label>' +
        '<div class="life-decision-form-actions"><button class="life-secondary-btn" type="button" data-decision-action="cancel-form">取消</button><button class="life-primary-btn" type="submit">保存复盘</button></div>' +
      '</form>' +
    '</article>';
  }

  function renderDecisionFormAside(item, mode) {
    return '<section class="life-decision-side-card"><h2>状态流转</h2><div class="life-decision-status-flow"><span>重要决定</span><i></i><span>冷却中</span><i></i><span>已归档</span></div><p>待复盘的新决定显示在重要决定；改为冷却中会进入冷却列表；完成复盘或主动归档后进入已归档。</p></section>' +
      '<section class="life-decision-side-card"><h2>生命周期操作</h2><div class="life-decision-lifecycle-actions"><button class="life-secondary-btn" type="button" data-decision-action="move-cooling" ' + (!item || mode === 'create' ? 'disabled' : '') + '>移入冷却中</button><button class="life-secondary-btn" type="button" data-decision-action="archive-decision" ' + (!item || mode === 'create' ? 'disabled' : '') + '>归档决定</button><button class="life-danger-btn" type="button" data-decision-action="delete-decision" ' + (!item || mode === 'create' ? 'disabled' : '') + '>删除决定</button></div><p>删除会从当前原型数据中移除这条决定，并清理它的编辑、收藏和复盘状态。</p></section>' +
      '<section class="life-decision-side-card"><h2>填写检查</h2><p>标题、背景、可选方案、理由、风险和复盘日期都会用于后续回看，不再只是静态展示。</p></section>';
  }

  function getSelectedDecision() {
    return decisionArchiveItems().filter(function(item) { return item.id === state.selectedDecisionId; })[0] || null;
  }

  function addDecision() {
    state.decisionFormMode = 'create';
    state.decisionMoreOpen = false;
    renderDecisions();
  }

  function createDecisionFromForm(form) {
    var stored = getStoredDecisions();
    var title = form.elements.title.value.trim() || '新的重要决定';
    var category = form.elements.category.value.trim() || '人生规划';
    var choice = form.elements.choice.value.trim() || '暂未决定';
    var confidence = Number(form.elements.confidence.value || 50);
    var item = {
      id: 'd-local-' + Date.now(),
      status: form.elements.status.value,
      title: title,
      date: form.elements.date.value || '2026-05-13',
      category: category,
      choice: choice,
      confidence: confidence,
      background: form.elements.background.value.trim() || '暂无背景。',
      reason: splitLines(form.elements.reason.value, ['先补充背景信息。']),
      risks: splitLines(form.elements.risks.value, ['信息还不充分。']),
      options: [
        [form.elements.optionA.value || '方案 A', form.elements.optionARole.value || '-', form.elements.optionAPlace.value || '-', form.elements.optionACost.value || '-', form.elements.optionAGrowth.value || '-'],
        [form.elements.optionB.value || '方案 B', form.elements.optionBRole.value || '-', form.elements.optionBPlace.value || '-', form.elements.optionBCost.value || '-', form.elements.optionBGrowth.value || '-']
      ],
      reviewDate: form.elements.reviewDate.value || '2026-11-13',
      result: form.elements.result.value.trim() || '尚未产生结果。'
    };
    stored.unshift(item);
    saveStoredDecisions(stored);
    state.selectedDecisionId = item.id;
    state.decisionFilter = decisionBucket(item);
    state.decisionFormMode = null;
    showToast('已添加决定');
    renderDecisions();
  }

  function saveDecisionEdit(form) {
    var meta = getDecisionMeta();
    meta.edits[state.selectedDecisionId] = {
      title: form.elements.title.value.trim() || '未命名决定',
      category: form.elements.category.value.trim() || '人生规划',
      choice: form.elements.choice.value.trim() || '暂未决定',
      status: form.elements.status.value,
      date: form.elements.date.value || '2026-05-13',
      confidence: Number(form.elements.confidence.value || 50),
      background: form.elements.background.value.trim() || '暂无背景。',
      reason: splitLines(form.elements.reason.value, ['先补充背景信息。']),
      risks: splitLines(form.elements.risks.value, ['信息还不充分。']),
      reviewDate: form.elements.reviewDate.value || '2026-11-13',
      result: form.elements.result.value.trim() || '尚未产生结果。',
      options: [
        [form.elements.optionA.value || '方案 A', form.elements.optionARole.value || '-', form.elements.optionAPlace.value || '-', form.elements.optionACost.value || '-', form.elements.optionAGrowth.value || '-'],
        [form.elements.optionB.value || '方案 B', form.elements.optionBRole.value || '-', form.elements.optionBPlace.value || '-', form.elements.optionBCost.value || '-', form.elements.optionBGrowth.value || '-']
      ]
    };
    meta.confidence[state.selectedDecisionId] = meta.edits[state.selectedDecisionId].confidence;
    saveDecisionMeta(meta);
    state.decisionFormMode = null;
    state.decisionFilter = decisionBucket(Object.assign({}, getSelectedDecision(), meta.edits[state.selectedDecisionId]));
    showToast('决定已保存');
    renderDecisions();
  }

  function splitLines(value, fallback) {
    var lines = String(value || '').split('\n').map(function(item) { return item.trim(); }).filter(Boolean);
    return lines.length ? lines : fallback;
  }

  function toggleDecisionBookmark() {
    var meta = getDecisionMeta();
    var index = meta.bookmarks.indexOf(state.selectedDecisionId);
    if (index >= 0) {
      meta.bookmarks.splice(index, 1);
      showToast('已取消收藏');
    } else {
      meta.bookmarks.push(state.selectedDecisionId);
      showToast('已收藏决定');
    }
    saveDecisionMeta(meta);
    renderDecisions();
  }

  function startDecisionReview() {
    var selected = getSelectedDecision();
    if (selected && isDecisionArchived(selected)) {
      showToast('已归档决定无需复盘');
      return;
    }
    state.decisionFormMode = 'review';
    state.decisionMoreOpen = false;
    renderDecisions();
  }

  function setDecisionStatus(status) {
    var selected = getSelectedDecision();
    if (!selected) return;
    var meta = getDecisionMeta();
    meta.edits[selected.id] = Object.assign({}, meta.edits[selected.id] || {}, { status: status });
    saveDecisionMeta(meta);
    state.decisionFilter = decisionBucket(Object.assign({}, selected, { status: status }));
    state.decisionMoreOpen = false;
    showToast(status === '冷却中' ? '已移入冷却中' : '已归档');
    renderDecisions();
  }

  function deleteSelectedDecision() {
    var selected = getSelectedDecision();
    if (!selected) return;
    if (!window.confirm('确认删除「' + selected.title + '」吗？删除后会从当前原型数据中移除，并清理它的编辑、收藏和复盘状态。')) return;
    var stored = getStoredDecisions().filter(function(item) {
      return item.id !== selected.id;
    });
    var meta = getDecisionMeta();
    if (meta.deleted.indexOf(selected.id) < 0) meta.deleted.push(selected.id);
    delete meta.edits[selected.id];
    delete meta.reviewed[selected.id];
    delete meta.confidence[selected.id];
    meta.bookmarks = meta.bookmarks.filter(function(id) {
      return id !== selected.id;
    });
    saveStoredDecisions(stored);
    saveDecisionMeta(meta);
    var remaining = decisionArchiveItems();
    var next = remaining.filter(decisionMatchesFilter)[0] || remaining[0] || null;
    if (next) {
      state.selectedDecisionId = next.id;
      state.decisionFilter = decisionBucket(next);
    } else {
      state.selectedDecisionId = '';
    }
    state.decisionFormMode = null;
    state.decisionMoreOpen = false;
    showToast('决定已删除');
    renderDecisions();
  }

  function saveDecisionReview(form) {
    var selected = getSelectedDecision();
    if (!selected) return;
    var meta = getDecisionMeta();
    var status = form.elements.status.value;
    var summary = {
      status: status,
      reviewedAt: form.elements.reviewedAt.value || '2026-05-13',
      result: form.elements.result.value.trim() || selected.result || '已完成复盘。',
      learning: form.elements.learning.value.trim() || '继续沉淀判断依据。',
      next: form.elements.next.value.trim() || '下一次决策前先补齐关键信息。'
    };
    meta.reviewed[selected.id] = summary;
    meta.edits[selected.id] = Object.assign({}, meta.edits[selected.id] || {}, {
      status: status,
      result: summary.result
    });
    saveDecisionMeta(meta);
    state.decisionFormMode = null;
    state.decisionFilter = '已归档';
    showToast('复盘已保存');
    renderDecisions();
  }

  function renderMood() {
    els.content.innerHTML = mockNotice() + '<section class="life-mood-page">' +
      '<div class="life-mood-page-head"><div><h2>情绪天气站</h2><p>理解情绪的天气，照顾当下的自己</p></div>' + renderMoodTabs() + '</div>' +
      renderMoodEditor() +
      renderMoodMainByTab() +
      '</section>';
    els.aside.innerHTML = renderMoodAside();
  }

  function renderMoodTabs() {
    return '<div class="life-mood-tabs">' + [
      ['overview', '概览'],
      ['calendar', '情绪日历'],
      ['trend', '趋势分析'],
      ['triggers', '触发因素'],
      ['body', '身体信号']
    ].map(function(tab) {
      return '<button type="button" class="' + (state.moodTab === tab[0] ? 'active' : '') + '" data-mood-tab="' + tab[0] + '">' + tab[1] + '</button>';
    }).join('') + '</div>';
  }

  function renderMoodMainByTab() {
    if (state.moodTab === 'calendar') {
      return '<div class="life-mood-focus-grid">' + renderMoodCalendarCard() + renderMoodRecentCard() + '</div>';
    }
    if (state.moodTab === 'trend') {
      return '<div class="life-mood-focus-grid">' + renderMoodTrendCard(true) + renderMoodDistributionCard() + '</div>';
    }
    if (state.moodTab === 'triggers') {
      return '<div class="life-mood-focus-grid">' + renderMoodTriggersPanel() + renderMoodWeeklyCard() + '</div>';
    }
    if (state.moodTab === 'body') {
      return '<div class="life-mood-focus-grid">' + renderMoodBodySignalsCard(true) + renderMoodSleepCard(true) + '</div>';
    }
    return renderMoodCalendarCard() +
      '<div class="life-mood-analytics-row">' + renderMoodTrendCard(false) + renderMoodDistributionCard() + '</div>' +
      '<div class="life-mood-bottom-row">' + renderMoodRecentCard() + renderMoodBodySignalsCard(false) + '</div>';
  }

  function moodMonthTitle(year, month) {
    return year + '年' + (month + 1) + '月';
  }

  function moodWeekdayText(year, month, day) {
    return ['周日','周一','周二','周三','周四','周五','周六'][new Date(year, month, day).getDay()];
  }

  function moodRecordDateLabel(item) {
    return String(item.month + 1).padStart(2, '0') + '-' + String(item.day).padStart(2, '0');
  }

  function moodRecordDisplayDate(item) {
    return moodRecordDateLabel(item) + ' ' + item.time + ' 记录';
  }

  function findMoodRecordById(id) {
    return allMoodRecords().filter(function(item) { return item.id === id; })[0] || null;
  }

  function nextAvailableMoodDay() {
    var daysInMonth = new Date(state.moodYear, state.moodMonth + 1, 0).getDate();
    var start = Math.min(Math.max(state.selectedMoodDay, 1), daysInMonth);
    for (var offset = 0; offset < daysInMonth; offset += 1) {
      var day = ((start + offset - 1) % daysInMonth) + 1;
      if (!moodRecordForMonth(day, state.moodYear, state.moodMonth)) return day;
    }
    return start;
  }

  function moodDraftRecord() {
    var source = state.moodFormMode === 'edit' ? findMoodRecordById(state.moodEditingId) : null;
    if (source) return source;
    var day = nextAvailableMoodDay();
    return {
      id: moodDateId(state.moodYear, state.moodMonth, day),
      year: state.moodYear,
      month: state.moodMonth,
      day: day,
      date: moodDateValue(state.moodYear, state.moodMonth, day),
      weekday: moodWeekdayText(state.moodYear, state.moodMonth, day),
      time: '09:30',
      score: 70,
      weather: '微晴',
      sleep: 7,
      pressure: 40,
      energy: 70,
      feeling: '平静',
      note: '',
      tags: ['情绪记录']
    };
  }

  function renderMoodEditor() {
    if (!state.moodFormMode) return '';
    var item = moodDraftRecord();
    var dateValue = item.date || moodDateValue(item.year, item.month, item.day);
    return '<section class="life-mood-card life-mood-editor-card">' +
      '<form id="lifeMoodForm" class="life-form life-mood-form">' +
        '<div class="life-form-title"><h2>' + (state.moodFormMode === 'edit' ? '编辑情绪记录' : '新增情绪记录') + '</h2><p>情绪天气站的记录在这里完成新增、修改和删除；添加一刻的跨模块新增稍后统一处理。</p></div>' +
        '<div class="life-three-grid"><label>记录日期<input class="life-input" type="date" name="date" value="' + escapeHtml(dateValue) + '"></label><label>记录时间<input class="life-input" type="time" name="time" value="' + escapeHtml(item.time || '09:30') + '"></label><label>天气<select class="life-select" name="weather">' + ['晴朗','微晴','多云','阴雨','低落'].map(function(weather) { return '<option value="' + weather + '"' + (item.weather === weather ? ' selected' : '') + '>' + weather + '</option>'; }).join('') + '</select></label></div>' +
        '<div class="life-mood-form-score"><div><strong>情绪分数 <span data-mood-score-value>' + item.score + '</span>/100</strong><p>只有进入新增或编辑表单时才允许调整分数。</p></div><input class="life-confidence-slider" type="range" min="0" max="100" name="score" value="' + item.score + '" data-mood-score-range></div>' +
        '<div class="life-four-grid"><label>睡眠（小时）<input class="life-input" type="number" step="0.1" min="0" max="16" name="sleep" value="' + escapeHtml(item.sleep) + '"></label><label>压力<input class="life-input" type="number" min="0" max="100" name="pressure" value="' + escapeHtml(item.pressure) + '"></label><label>精力<input class="life-input" type="number" min="0" max="100" name="energy" value="' + escapeHtml(item.energy) + '"></label><label>感受<input class="life-input" name="feeling" value="' + escapeHtml(item.feeling) + '"></label></div>' +
        '<label>记录内容<textarea class="life-textarea" name="note" placeholder="今天的情绪发生了什么？">' + escapeHtml(item.note) + '</textarea></label>' +
        '<label>标签<input class="life-input" name="tags" value="' + escapeHtml((item.tags || []).join('，')) + '" placeholder="用逗号分隔，例如：睡眠不足，工作压力"></label>' +
        '<div class="life-mood-form-actions">' + (state.moodFormMode === 'edit' ? '<button class="life-danger-btn" type="button" data-mood-action="delete-record">删除记录</button>' : '') + '<button class="life-secondary-btn" type="button" data-mood-action="cancel-form">取消</button><button class="life-primary-btn" type="submit">' + (state.moodFormMode === 'edit' ? '保存修改' : '保存记录') + '</button></div>' +
      '</form>' +
    '</section>';
  }

  function renderMoodRangeControl(kind, label, options) {
    return '<div class="life-mood-range-control"><button type="button" data-mood-range="' + kind + '">' + label + '⌄</button>' +
      (state.moodRangeMenu === kind ? '<div class="life-mood-range-menu">' + options.map(function(option) {
        return '<button type="button" class="' + (option === label ? 'active' : '') + '" data-mood-range-option="' + kind + ':' + option + '">' + option + '</button>';
      }).join('') + '</div>' : '') + '</div>';
  }

  function moodIconByScore(score) {
    if (score >= 75) return 'sun';
    if (score >= 60) return 'mood';
    if (score >= 40) return 'cloud';
    return 'anxious';
  }

  function moodToneClass(score) {
    if (score >= 80) return 'sunny';
    if (score >= 60) return 'soft';
    if (score >= 40) return 'cloudy';
    return 'low';
  }

  function renderMoodCalendarCard() {
    return '<section class="life-mood-card life-mood-calendar-card"><div class="life-mood-section-head"><div><h3>本月情绪</h3></div>' +
      '<div class="life-mood-month-control"><strong>' + moodMonthTitle(state.moodYear, state.moodMonth) + '</strong><button type="button" data-mood-action="prev-month">‹</button><button type="button" data-mood-action="next-month">›</button><button type="button" data-mood-action="today">今天</button></div></div>' +
      '<div class="life-scroll-x"><div class="life-mood-calendar">' + renderMoodCalendar() + '</div></div>' +
      '<div class="life-mood-legend">' + [
        ['sunny', '晴朗 80-100'],
        ['soft', '微晴 60-79'],
        ['cloudy', '多云 40-59'],
        ['rainy', '阴雨 20-39'],
        ['low', '低落 0-19'],
        ['empty', '未记录']
      ].map(function(item) {
        return '<span class="' + item[0] + '"><i></i>' + item[1] + '</span>';
      }).join('') + '</div></section>';
  }

  function renderMoodCalendar() {
    var year = state.moodYear;
    var month = state.moodMonth;
    var firstDay = new Date(year, month, 1);
    var firstWeekday = (firstDay.getDay() + 6) % 7;
    var daysInMonth = new Date(year, month + 1, 0).getDate();
    var daysInPrevMonth = new Date(year, month, 0).getDate();
    var totalCells = Math.ceil((firstWeekday + daysInMonth) / 7) * 7;
    var cells = [];
    for (var prev = firstWeekday; prev > 0; prev -= 1) {
      cells.push({ label: String(daysInPrevMonth - prev + 1), muted: true, adjacent: 'prev' });
    }
    for (var day = 1; day <= daysInMonth; day += 1) {
      cells.push({ label: String(day), day: day });
    }
    var nextDay = 1;
    while (cells.length < totalCells) {
      cells.push({ label: String(nextDay), muted: true, adjacent: 'next' });
      nextDay += 1;
    }
    var html = ['周一','周二','周三','周四','周五','周六','周日'].map(function(dayName) {
      return '<div class="life-mood-weekday">' + dayName + '</div>';
    }).join('');
    html += cells.map(function(cell) {
      var record = moodRecordForMonth(cell.day, year, month);
      var cellClass = 'life-mood-day' + (cell.muted ? ' muted' : '') + (cell.day === state.selectedMoodDay ? ' selected' : '') + (record ? ' has-record ' + moodToneClass(record.score) : ' empty');
      var content = record
        ? iconHtml(moodIconByScore(record.score)) + '<strong>' + record.score + '</strong>'
        : '<span class="life-mood-dash">--</span>';
      var attr = cell.day ? 'data-mood-day="' + cell.day + '"' : 'data-mood-action="' + (cell.adjacent === 'prev' ? 'prev-month' : 'next-month') + '"';
      return '<button type="button" class="' + cellClass + '" ' + attr + '><span>' + cell.label + '</span><div>' + content + '</div></button>';
    }).join('');
    return html;
  }

  function renderMoodTrendCard(expanded) {
    var points = allMoodRecords().slice(-10);
    if (!points.length) points = [moodDraftRecord()];
    var values = points.map(function(item) { return item.score; });
    var max = Math.max.apply(null, values.concat([100]));
    var step = points.length > 1 ? 580 / (points.length - 1) : 0;
    var path = points.map(function(item, idx) {
      var x = 22 + idx * step;
      var y = 118 - (item.score / max) * 86;
      return { x: x, y: y, item: item };
    });
    var d = path.map(function(point, idx) { return (idx ? 'L' : 'M') + point.x + ' ' + point.y; }).join(' ');
    return '<section class="life-mood-card life-mood-trend-card ' + (expanded ? 'expanded' : '') + '"><div class="life-mood-section-head"><h3>最近情绪趋势</h3>' + renderMoodRangeControl('trend', state.moodRange, ['近 7 天', '近 14 天', '近 30 天']) + '</div>' +
      '<div class="life-mood-line-wrap"><div class="life-mood-axis-labels"><span>晴朗 100</span><span>微晴 75</span><span>多云 50</span><span>阴雨 25</span><span>低落 0</span></div><svg class="life-mood-line" viewBox="0 0 640 150" role="img" aria-label="最近情绪趋势">' +
      '<path d="M20 118H620" class="grid"/><path d="M20 96H620" class="grid"/><path d="M20 74H620" class="grid"/><path d="M20 52H620" class="grid"/><path d="' + d + '" class="trend"/>' +
      path.map(function(point) { return '<circle cx="' + point.x + '" cy="' + point.y + '" r="' + (point.item.day === state.selectedMoodDay && point.item.month === state.moodMonth && point.item.year === state.moodYear ? 5 : 4) + '" class="' + moodToneClass(point.item.score) + '"/>'; }).join('') +
      '</svg><div class="life-mood-date-row">' + points.map(function(item) { return '<span>' + moodRecordDateLabel(item) + '</span>'; }).join('') + '</div></div>' +
      '<p class="life-mood-green-note">5月整体状态平稳，晴朗日较多；继续保持规律作息和积极的生活节奏。</p></section>';
  }

  function renderMoodDistributionCard() {
    var records = currentMonthMoodRecords();
    var total = records.length || 1;
    var average = records.length ? Math.round(records.reduce(function(sum, item) { return sum + Number(item.score || 0); }, 0) / records.length) : 0;
    var groups = [
      ['晴朗', records.filter(function(item) { return item.score >= 80; }).length, 'sunny'],
      ['微晴', records.filter(function(item) { return item.score >= 60 && item.score < 80; }).length, 'soft'],
      ['多云', records.filter(function(item) { return item.score >= 40 && item.score < 60; }).length, 'cloudy'],
      ['阴雨', records.filter(function(item) { return item.score >= 20 && item.score < 40; }).length, 'rainy'],
      ['低落', records.filter(function(item) { return item.score < 20; }).length, 'low']
    ];
    return '<section class="life-mood-card life-mood-distribution-card"><h3>情绪分布</h3><div class="life-mood-distribution"><div class="life-mood-donut"><span>本月平均<strong>' + average + '</strong><em>/100</em></span></div><ul>' + groups.map(function(item) {
      var percent = Math.round(item[1] / total * 100);
      return '<li><i class="' + item[2] + '"></i><span>' + item[0] + '</span><strong>' + item[1] + ' 天</strong><em>' + percent + '%</em></li>';
    }).join('') + '</ul></div></section>';
  }

  function renderMoodRecentCard() {
    var recent = allMoodRecords().slice(-6).reverse();
    return '<section class="life-mood-card life-mood-recent-card"><div class="life-mood-section-head"><h3>最近记录</h3><button type="button" data-mood-action="all-records">全部记录 ›</button></div><div class="life-mood-record-list">' +
      recent.map(function(item) {
        return '<button type="button" class="life-mood-record-row ' + (item.day === state.selectedMoodDay && item.month === state.moodMonth && item.year === state.moodYear ? 'active' : '') + '" data-mood-date="' + escapeHtml(item.date) + '">' +
          '<span class="life-mood-record-date">' + moodRecordDateLabel(item) + '<small>' + item.time + '</small></span>' +
          '<span class="life-mood-record-icon">' + iconHtml(moodIconByScore(item.score)) + '</span>' +
          '<span class="life-mood-record-main"><strong>' + item.weather + ' <em>' + item.score + ' 分</em></strong><p>' + escapeHtml(item.note) + '</p><b>' + item.tags.map(function(tag) { return '<em>' + escapeHtml(tag) + '</em>'; }).join('') + '</b></span>' +
          '<span class="life-mood-record-meta"><strong>' + item.sleep + 'h</strong><small>睡眠</small><strong>' + item.pressure + '</strong><small>压力</small></span>' +
          '</button>';
      }).join('') + (!recent.length ? '<div class="life-empty">还没有情绪记录</div>' : '') + '</div></section>';
  }

  function renderMoodBodySignalsCard(expanded) {
    return '<section class="life-mood-card life-mood-body-card ' + (expanded ? 'expanded' : '') + '"><div><h3>身体信号</h3><p>了解身体如何影响情绪</p></div><div class="life-mood-signal-list">' + [
      ['calm', '睡眠不足', '近 3 天睡眠 < 6 小时，情绪评分偏低'],
      ['amber', '久坐时间长', '今日久坐 8.5 小时，建议适量活动'],
      ['amber', '咖啡因摄入', '今日咖啡因摄入偏多（3 杯），可能影响睡眠'],
      ['red', '经期阶段', '经期前 2 天，情绪可能更敏感']
    ].map(function(item) {
      return '<div class="life-mood-signal-row"><i class="' + item[0] + '"></i><span><strong>' + item[1] + '</strong><em>' + item[2] + '</em></span></div>';
    }).join('') + '</div><button type="button" data-mood-action="more-body">更多记录 ›</button></section>';
  }

  function renderMoodTriggersPanel() {
    return '<section class="life-mood-card life-mood-trigger-panel"><div class="life-mood-section-head"><h3>触发因素</h3>' + renderMoodRangeControl('trigger', state.moodTriggerRange, ['近 7 天', '近 14 天', '近 30 天']) + '</div><div class="life-mood-trigger-grid">' +
      ['工作压力','信息过载','睡眠不足','熬夜','计划被打乱','与家人相处','运动','读书','阳光天气','独处时光','咖啡因','社交活动','财务担忧'].map(function(tag, idx) {
        return '<button type="button" class="' + (idx < 5 ? 'warm' : idx < 10 ? 'cool' : '') + '" data-mood-action="trigger">' + tag + '</button>';
      }).join('') + '<button type="button" data-mood-action="add-trigger">＋ 添加</button></div><p>点击标签可查看在情绪变化中的影响。</p></section>';
  }

  function renderMoodSleepCard(expanded) {
    var records = allMoodRecords().slice(-14);
    var dots = records.map(function(item, idx) {
      var x = 42 + idx * (records.length > 1 ? 460 / (records.length - 1) : 0);
      var y = 142 - item.score;
      return '<circle cx="' + x + '" cy="' + y + '" r="5"/>';
    }).join('');
    return '<section class="life-mood-card life-mood-sleep-card ' + (expanded ? 'expanded' : '') + '"><div class="life-mood-section-head"><h3>睡眠关联</h3>' + renderMoodRangeControl('sleep', state.moodSleepRange, ['近 7 天', '近 14 天', '近 30 天']) + '</div><div class="life-mood-sleep-grid"><p>睡眠时长越稳定，情绪评分越高。<br>尽量保持 7-8 小时的规律睡眠。</p><svg viewBox="0 0 560 170" role="img" aria-label="睡眠与情绪评分散点图"><path d="M30 140H540M30 100H540M30 60H540" class="grid"/><path d="M45 124 C180 92 330 76 520 48" class="line"/>' + dots + '<text x="28" y="34">情绪评分</text><text x="260" y="162">睡眠时长（小时）</text></svg></div></section>';
  }

  function renderMoodWeeklyCard() {
    return '<section class="life-mood-card life-mood-weekly-card"><div class="life-mood-section-head"><h3>每周回看</h3>' + renderMoodRangeControl('week', state.moodWeekRange, ['04-27 ~ 05-03', '05-04 ~ 05-10', '05-11 ~ 05-17']) + '</div><p>这周整体不错，有几个高光时刻，也遇到了一些挑战。</p><div><article><strong>高光时刻</strong><span>周一完成了重要汇报</span><span>周二和朋友深度聊天</span><span>周五的运动让我很放松</span></article><article><strong>挑战与学习</strong><span>周四信息过载，效率下降</span><span>周末熬夜影响了睡眠</span><span>下周要更专注于优先级</span></article></div><footer><strong>下周关注</strong><span>睡眠质量</span><span>专注力</span><span>情绪稳定</span><button type="button" data-mood-action="edit-record">' + iconHtml('project') + '</button></footer></section>';
  }

  function renderMoodAside() {
    var item = selectedMoodRecord();
    var selectedDate = moodDateValue(state.moodYear, state.moodMonth, state.selectedMoodDay);
    if (!item) {
      return '<section class="life-mood-side-card life-mood-today-card life-mood-empty-side"><div class="life-mood-section-head"><h3>当前日期</h3><span>' + escapeHtml(selectedDate) + '</span></div><div class="life-empty">这一天还没有情绪记录。</div><button class="life-primary-btn" type="button" data-mood-action="new-record">新增情绪记录</button></section>' +
        renderMoodSleepCard(false) + renderMoodTriggersPanel() + renderMoodWeeklyCard();
    }
    return '<section class="life-mood-side-card life-mood-today-card"><div class="life-mood-section-head"><h3>当前心情</h3><span>' + escapeHtml(moodRecordDisplayDate(item)) + '</span></div><div class="life-mood-today-main"><div class="life-mood-big-sun">' + iconHtml(moodIconByScore(item.score)) + '</div><div><strong>' + item.weather + ' <em>' + item.score + '</em><small>/100</small></strong><p>充满能量，适合推进重要的事。</p></div></div><div class="life-mood-metric-grid">' + [
      ['睡眠', item.sleep + ' 小时', '良好'],
      ['压力', item.pressure + '/100', '较低'],
      ['精力', item.energy + '/100', '充沛'],
      ['感受', item.feeling, '']
    ].map(function(metric) {
      return '<div><span>' + metric[0] + '</span><strong>' + metric[1] + '</strong><em>' + metric[2] + '</em></div>';
    }).join('') + '</div><blockquote>' + escapeHtml(item.note) + '<button type="button" data-mood-action="edit-record">' + iconHtml('project') + '</button></blockquote><div class="life-mood-side-actions"><button class="life-secondary-btn" type="button" data-mood-action="edit-record">编辑记录</button><button class="life-danger-btn" type="button" data-mood-action="delete-record">删除记录</button></div></section>' +
      renderMoodSleepCard(false) + renderMoodTriggersPanel() + renderMoodWeeklyCard();
  }

  function startMoodCreate() {
    state.moodFormMode = 'create';
    state.moodEditingId = '';
    state.moodRangeMenu = null;
    state.selectedMoodDay = nextAvailableMoodDay();
    renderMood();
  }

  function startMoodEdit() {
    var item = selectedMoodRecord();
    if (!item) {
      startMoodCreate();
      return;
    }
    state.moodFormMode = 'edit';
    state.moodEditingId = item.id;
    state.moodRangeMenu = null;
    renderMood();
  }

  function cancelMoodForm() {
    state.moodFormMode = null;
    state.moodEditingId = '';
    renderMood();
  }

  function moodTagsFromValue(value) {
    var tags = String(value || '').split(/[,，]/).map(function(tag) { return tag.trim(); }).filter(Boolean);
    return tags.length ? tags : ['情绪记录'];
  }

  function moodRecordFromForm(form) {
    var parsed = parseMoodDate(form.elements.date.value || moodDateValue(state.moodYear, state.moodMonth, state.selectedMoodDay));
    var score = Math.max(0, Math.min(100, Number(form.elements.score.value || 0)));
    return {
      id: moodDateId(parsed.year, parsed.month, parsed.day),
      year: parsed.year,
      month: parsed.month,
      day: parsed.day,
      date: moodDateValue(parsed.year, parsed.month, parsed.day),
      weekday: moodWeekdayText(parsed.year, parsed.month, parsed.day),
      time: form.elements.time.value || '09:30',
      score: score,
      weather: form.elements.weather.value,
      sleep: Number(form.elements.sleep.value || 0),
      pressure: Math.max(0, Math.min(100, Number(form.elements.pressure.value || 0))),
      energy: Math.max(0, Math.min(100, Number(form.elements.energy.value || 0))),
      feeling: form.elements.feeling.value.trim() || '平静',
      note: form.elements.note.value.trim() || '记录了当下的情绪状态。',
      tags: moodTagsFromValue(form.elements.tags.value)
    };
  }

  function upsertMoodAdded(store, item) {
    store.added = (store.added || []).filter(function(record) {
      return record.id !== item.id;
    });
    store.added.unshift(item);
  }

  function saveMoodForm(form) {
    var store = getMoodStore();
    var item = moodRecordFromForm(form);
    var mode = state.moodFormMode;
    var editingId = state.moodFormMode === 'edit' ? state.moodEditingId : '';
    if (editingId && editingId !== item.id) {
      store.deleted = (store.deleted || []).filter(function(id) { return id !== item.id; });
      delete store.edits[editingId];
      store.added = (store.added || []).filter(function(record) { return record.id !== editingId; });
      if (store.deleted.indexOf(editingId) < 0) store.deleted.push(editingId);
    }
    var seedExists = moodRecords.map(normalizeMoodRecord).some(function(seed) {
      return seed.id === item.id;
    });
    if (seedExists) {
      store.edits[item.id] = item;
      store.added = (store.added || []).filter(function(record) { return record.id !== item.id; });
      store.deleted = (store.deleted || []).filter(function(id) { return id !== item.id; });
    } else {
      delete store.edits[item.id];
      store.deleted = (store.deleted || []).filter(function(id) { return id !== item.id; });
      upsertMoodAdded(store, item);
    }
    saveMoodStore(store);
    state.moodYear = item.year;
    state.moodMonth = item.month;
    state.selectedMoodDay = item.day;
    state.moodFormMode = null;
    state.moodEditingId = '';
    showToast(mode === 'edit' ? '情绪记录已保存' : '情绪记录已新增');
    renderMood();
  }

  function deleteSelectedMoodRecord() {
    var item = state.moodFormMode === 'edit' ? findMoodRecordById(state.moodEditingId) : selectedMoodRecord();
    if (!item) return;
    if (!window.confirm('确认删除 ' + moodRecordDisplayDate(item) + ' 的情绪记录吗？删除后会从当前原型数据中移除。')) return;
    var store = getMoodStore();
    store.added = (store.added || []).filter(function(record) {
      return record.id !== item.id;
    });
    delete store.edits[item.id];
    if ((store.deleted || []).indexOf(item.id) < 0) store.deleted.push(item.id);
    saveMoodStore(store);
    var fallback = currentMonthMoodRecords().filter(function(record) {
      return record.id !== item.id;
    }).slice(-1)[0];
    if (fallback) {
      state.moodYear = fallback.year;
      state.moodMonth = fallback.month;
      state.selectedMoodDay = fallback.day;
    }
    state.moodFormMode = null;
    state.moodEditingId = '';
    showToast('情绪记录已删除');
    renderMood();
  }

  function renderRelationships() {
    var items = relationshipItems();
    var selected = getSelectedRelationship(items);
    if (selected && selected.id !== state.selectedRelationshipId) state.selectedRelationshipId = selected.id;
    els.content.innerHTML = mockNotice() + '<section class="life-relationship-page">' +
      '<div class="life-relationship-head"><div><h2 class="life-panel-title">关系温度 <span class="life-info-dot">i</span></h2><p class="life-panel-sub">记录与重要之人的连接，关注彼此的距离与温度</p></div><div class="life-relationship-toolbar"><button class="life-secondary-btn" type="button" data-relationship-action="sort">排序：' + escapeHtml(state.relationshipSort) + '⌄</button><button class="life-secondary-btn" type="button" data-relationship-action="filter">筛选⌄</button><button class="life-primary-btn" type="button" data-relationship-action="add">添加关系</button></div></div>' +
      renderRelationshipFilters() +
      renderRelationshipForm() +
      renderRelationshipList(items, selected) +
      '</section>';
    els.aside.innerHTML = renderRelationshipAside(selected);
  }

  function relationshipItems() {
    var list = allRelationships().filter(function(item) {
      var matchesFilter = state.relationshipFilter === '全部' || item.group === state.relationshipFilter;
      return matchesFilter && queryMatch(item.name + item.role + item.group + item.channel + item.notes.join(' '));
    });
    return list.sort(function(a, b) {
      if (state.relationshipSort === '下次联系') return relationshipDays(a.next) - relationshipDays(b.next);
      if (state.relationshipSort === '最近联系') return relationshipDays(a.last) - relationshipDays(b.last);
      return Number(b.score || 0) - Number(a.score || 0);
    });
  }

  function relationshipDays(text) {
    if (String(text).indexOf('今天') >= 0 || String(text).indexOf('昨天') >= 0) return String(text).indexOf('昨天') >= 0 ? 1 : 0;
    var match = String(text).match(/(\d+)/);
    return match ? Number(match[1]) : 99;
  }

  function getSelectedRelationship(items) {
    var all = allRelationships();
    return all.filter(function(item) { return item.id === state.selectedRelationshipId; })[0] || items[0] || all[0] || null;
  }

  function relationshipGroupCounts() {
    var all = allRelationships();
    return ['全部','家人','朋友','同事','重要联系人'].map(function(group) {
      var count = group === '全部' ? all.length : all.filter(function(item) { return item.group === group; }).length;
      return [group, count];
    });
  }

  function renderRelationshipFilters() {
    return '<div class="life-relationship-tabs">' + relationshipGroupCounts().map(function(item) {
      return '<button type="button" class="' + (state.relationshipFilter === item[0] ? 'active' : '') + '" data-relationship-filter="' + item[0] + '">' + item[0] + ' <span>' + item[1] + '</span></button>';
    }).join('') + '</div>';
  }

  function renderRelationshipList(items, selected) {
    var groups = ['家人','朋友','同事','重要联系人'];
    var blocks = groups.map(function(group) {
      var rows = items.filter(function(item) { return item.group === group; });
      if (!rows.length) return '';
      return '<section class="life-relationship-group"><div class="life-relationship-list-head"><h3>' + group + '</h3><span>上次联系</span><span>亲密度</span><span>趋势</span><span>下次联系</span></div>' +
        rows.map(function(item) { return renderRelationshipRow(item, selected && selected.id === item.id); }).join('') + '</section>';
    }).join('');
    return blocks || '<section class="life-panel"><div class="life-empty">没有匹配的关系记录</div></section>';
  }

  function renderRelationshipRow(item, active) {
    return '<button type="button" class="life-relationship-row ' + (active ? 'active' : '') + '" data-relationship-id="' + item.id + '">' +
      '<span class="life-person">' + relationshipAvatarHtml(item, 'small') + '<span><strong>' + escapeHtml(item.name) + ' <em>' + escapeHtml(item.group) + '</em></strong><small>' + escapeHtml(item.role) + '</small></span></span>' +
      '<span><strong>' + escapeHtml(item.last) + '</strong><small>' + escapeHtml(item.channel) + '</small></span>' +
      '<span class="life-relationship-score"><strong>' + item.score + '</strong><small>' + relationshipScoreLabel(item.score) + '</small>' + progress(item.score, item.score >= 75 ? 'var(--life-accent)' : 'var(--life-amber)') + '</span>' +
      '<span class="life-relationship-spark">' + relationshipSparkline(item.trend, item.score) + '</span>' +
      '<span><strong>' + escapeHtml(item.next) + '</strong><small>' + escapeHtml(item.nextDate || '待定') + '</small></span>' +
      '<span class="life-relationship-bell">' + iconHtml(item.reminded ? 'health' : 'monthly') + '</span>' +
    '</button>';
  }

  function relationshipScoreLabel(score) {
    if (score >= 85) return '很亲密';
    if (score >= 70) return '亲密';
    return '一般';
  }

  function relationshipSparkline(values, score) {
    var max = Math.max.apply(null, values.concat([100]));
    var step = values.length > 1 ? 86 / (values.length - 1) : 0;
    var points = values.map(function(value, idx) {
      return { x: 2 + idx * step, y: 32 - value / max * 26 };
    });
    var path = points.map(function(point, idx) { return (idx ? 'L' : 'M') + point.x + ' ' + point.y; }).join(' ');
    return '<svg viewBox="0 0 96 36" role="img" aria-label="关系趋势"><path d="' + path + '" class="' + (score >= 70 ? 'warm' : 'cool') + '"/>' + points.map(function(point) { return '<circle cx="' + point.x + '" cy="' + point.y + '" r="2"/>'; }).join('') + '</svg>';
  }

  function relationshipAvatarKey(item) {
    if (item.avatar === 'custom') return 'custom';
    if (item.avatar && /^q[1-6]$/.test(item.avatar)) return item.avatar;
    if (item.name === '妈妈') return 'q1';
    if (item.name === '爸爸') return 'q2';
    if (item.group === '家人') return 'q3';
    if (item.group === '同事') return 'q5';
    if (item.group === '重要联系人') return 'q6';
    return 'q4';
  }

  function relationshipFormAvatarValue(form, current) {
    var selected = form.querySelector('input[name="avatar"]:checked');
    return selected ? selected.value : relationshipAvatarKey(current || {});
  }

  function relationshipAvatarHtml(item, size) {
    var url = item.avatar === 'custom' ? item.avatarUrl || '' : '';
    var style = url ? ' style="background-image:url(' + escapeHtml(url) + ')"' : '';
    var customClass = url ? ' custom' : '';
    var avatarClass = relationshipAvatarKey(item);
    if (avatarClass === 'custom') avatarClass = 'q1';
    return '<span class="life-avatar-token ' + avatarClass + ' ' + (size || '') + customClass + '"' + style + '><i></i></span>';
  }

  function relationshipMediaText(items) {
    return normalizeRelationshipMedia(items).map(function(item) { return item.text; }).join('\n');
  }

  function relationshipMediaFromLines(value, currentItems) {
    var current = normalizeRelationshipMedia(currentItems);
    var lines = splitLines(value, []);
    return lines.map(function(text) {
      var old = current.filter(function(item) { return item.text === text; })[0];
      return { text: text, image: old ? old.image : '', date: old ? old.date : '' };
    });
  }

  function relationshipMediaClasses(kind, idx) {
    var pools = {
      memory: ['photo-cafe','photo-garden','photo-river','photo-mountain','photo-book'],
      gift: ['photo-book','photo-garden','photo-office','photo-cafe','photo-river'],
      place: ['photo-river','photo-garden','photo-mountain','photo-office','photo-cafe']
    };
    var list = pools[kind] || pools.memory;
    return list[idx % list.length];
  }

  function relationshipMediaThumb(item, kind, idx) {
    var media = typeof item === 'string' ? { text: item, image: '' } : item;
    if (media.image) return '<span class="life-media-thumb"><img src="' + escapeHtml(media.image) + '" alt=""></span>';
    return '<span class="life-media-thumb placeholder ' + relationshipMediaClasses(kind, idx) + '"></span>';
  }

  function renderRelationshipMediaCards(items, kind) {
    var media = normalizeRelationshipMedia(items);
    if (!media.length) return '<p class="life-card-copy">暂无记录</p>';
    return '<div class="life-media-grid">' + media.map(function(item, idx) {
      return '<article class="life-media-card">' + relationshipMediaThumb(item, kind, idx) + '<strong>' + escapeHtml(item.text || '未命名') + '</strong>' + (item.date ? '<small>' + escapeHtml(item.date) + '</small>' : '') + '</article>';
    }).join('') + '</div>';
  }

  function renderRelationshipMediaMini(items, kind, fallback) {
    var media = normalizeRelationshipMedia(items && items.length ? items : fallback);
    if (!media.length) return '<p class="life-card-copy">暂无记录</p>';
    return '<div class="life-media-mini-grid">' + media.slice(0, 4).map(function(item, idx) {
      return '<article>' + relationshipMediaThumb(item, kind, idx) + '<span>' + escapeHtml(item.text || '未命名') + '</span></article>';
    }).join('') + '</div>';
  }

  function renderRelationshipMediaFormPreview(items, kind) {
    var media = normalizeRelationshipMedia(items);
    if (!media.length) return '';
    return '<div class="life-media-form-preview">' + media.slice(0, 6).map(function(item, idx) {
      return '<article>' + relationshipMediaThumb(item, kind, idx) + '<span>' + escapeHtml(item.text || '未命名') + '</span></article>';
    }).join('') + '</div>';
  }

  function renderRelationshipMediaEditor(field, label, items, kind, placeholder) {
    var media = normalizeRelationshipMedia(items);
    return '<section class="life-media-editor" data-relationship-media-field="' + field + '" data-relationship-media-kind="' + kind + '">' +
      '<div class="life-section-title"><h3>' + label + '</h3><button type="button" data-relationship-action="add-media-item" data-media-field="' + field + '" data-media-kind="' + kind + '">＋ 添加</button></div>' +
      '<div class="life-media-editor-list">' + (media.length ? media.map(function(item, idx) { return relationshipMediaEditorRow(field, kind, item, idx); }).join('') : relationshipMediaEditorRow(field, kind, { text: '', image: '' }, 0, placeholder)) + '</div>' +
    '</section>';
  }

  function renderRelationshipMediaSummary(label, items, kind, actionName) {
    var media = normalizeRelationshipMedia(items);
    var names = media.slice(0, 3).map(function(item) { return item.text || '未命名'; }).join('、') || '暂无记录';
    return '<section class="life-media-summary compact"><div><h3>' + label + '</h3><p>' + media.length + ' 条图片记录 · ' + escapeHtml(names) + '</p></div><button type="button" data-relationship-action="' + actionName + '">到右侧管理</button></section>';
  }

  function relationshipMediaEditorRow(field, kind, item, idx, placeholder) {
    var media = item || { text: '', image: '' };
    var thumb = relationshipMediaThumb(media, kind, idx);
    return '<article class="life-media-edit-row" data-relationship-media-row data-media-field="' + field + '" data-media-kind="' + kind + '">' +
      '<div class="life-media-edit-preview" data-relationship-media-preview>' + thumb + '</div>' +
      '<label>名称<input class="life-input" data-relationship-media-text value="' + escapeHtml(media.text || '') + '" placeholder="' + escapeHtml(placeholder || '输入名称') + '"></label>' +
      '<label>图片地址<input class="life-input" data-relationship-media-image value="' + escapeHtml(media.image || '') + '" placeholder="https://..."></label>' +
      '<label class="life-media-file-label">上传图片<input type="file" accept="image/*" data-relationship-editor-image-upload></label>' +
      '<button class="life-danger-btn" type="button" data-relationship-action="delete-media-item">删除</button>' +
    '</article>';
  }

  function readRelationshipMediaEditor(form, field) {
    return Array.prototype.map.call(form.querySelectorAll('[data-relationship-media-field="' + field + '"] [data-relationship-media-row]'), function(row) {
      var textInput = row.querySelector('[data-relationship-media-text]');
      var imageInput = row.querySelector('[data-relationship-media-image]');
      return {
        text: textInput ? textInput.value.trim() : '',
        image: imageInput ? imageInput.value.trim() : ''
      };
    }).filter(function(item) { return item.text || item.image; });
  }

  function refreshRelationshipMediaRowPreview(row) {
    if (!row) return;
    var imageInput = row.querySelector('[data-relationship-media-image]');
    var textInput = row.querySelector('[data-relationship-media-text]');
    var preview = row.querySelector('[data-relationship-media-preview]');
    var image = imageInput ? imageInput.value.trim() : '';
    var kind = row.getAttribute('data-media-kind') || 'memory';
    var text = textInput ? textInput.value.trim() : '';
    if (preview) preview.innerHTML = relationshipMediaThumb({ text: text, image: image }, kind, 0);
  }

  function renderRelationshipAvatarPicker(item) {
    var selected = relationshipAvatarKey(item);
    return '<div class="life-avatar-picker">' + ['q1','q2','q3','q4','q5','q6'].map(function(key, idx) {
      return '<label class="' + (selected === key ? 'active' : '') + '" data-avatar-choice="' + key + '"><input type="radio" name="avatar" value="' + key + '"' + (selected === key ? ' checked' : '') + '><span class="life-avatar-token ' + key + '"><i></i></span><em>Q' + (idx + 1) + '</em></label>';
    }).join('') + '<label class="' + (selected === 'custom' ? 'active' : '') + '" data-avatar-choice="custom"><input type="radio" name="avatar" value="custom"' + (selected === 'custom' ? ' checked' : '') + '><span class="life-avatar-token custom-option"><i></i></span><em>上传</em></label></div>';
  }

  function renderRelationshipForm() {
    if (!state.relationshipFormMode) return '';
    var source = state.relationshipFormMode === 'edit' ? getSelectedRelationship(allRelationships()) : null;
    var item = source || normalizeRelationship({ id: 'r-local-' + Date.now(), name: '', role: '', group: '朋友', last: '今天', channel: '微信', score: 70, next: '7 天后', nextDate: '2026-05-20', dates: ['生日 1990-01-01'], notes: ['最近聊到：'], memories: ['第一次见面'], gifts: [], places: [], memo: '' });
    return '<section class="life-relationship-form-card">' +
      '<form id="lifeRelationshipForm" class="life-form life-relationship-form">' +
        '<div class="life-form-title"><h2>' + (state.relationshipFormMode === 'edit' ? '编辑关系' : '添加关系') + '</h2><p>联系人资料、联系节奏、重要日期和备注都会保存到关系温度模块。</p></div>' +
        '<label>头像' + renderRelationshipAvatarPicker(item) + '</label><label data-avatar-url-field class="' + (relationshipAvatarKey(item) === 'custom' ? '' : 'is-hidden') + '">上传头像 / 图片地址<input class="life-input" name="avatarUrl" value="' + escapeHtml(item.avatar === 'custom' ? item.avatarUrl || '' : '') + '" placeholder="选择“上传”后粘贴头像图片地址"></label>' +
        '<div class="life-three-grid"><label>姓名<input class="life-input" name="name" value="' + escapeHtml(item.name) + '" placeholder="例如：妈妈"></label><label>身份<input class="life-input" name="role" value="' + escapeHtml(item.role) + '" placeholder="母亲 / 同学 / 同事"></label><label>分组<select class="life-select" name="group">' + ['家人','朋友','同事','重要联系人'].map(function(group) { return '<option value="' + group + '"' + (item.group === group ? ' selected' : '') + '>' + group + '</option>'; }).join('') + '</select></label></div>' +
        '<div class="life-four-grid"><label>上次联系<input class="life-input" name="last" value="' + escapeHtml(item.last) + '"></label><label>渠道<input class="life-input" name="channel" value="' + escapeHtml(item.channel) + '"></label><label>下次联系<input class="life-input" name="next" value="' + escapeHtml(item.next) + '"></label><label>下次日期<input class="life-input" type="date" name="nextDate" value="' + escapeHtml(item.nextDate || '2026-05-20') + '"></label></div>' +
        '<div class="life-relationship-form-score"><div><strong>亲密度 <span data-relationship-score-value>' + item.score + '</span>/100</strong><p>编辑状态下调整，保存后列表和详情同步。</p></div><input class="life-confidence-slider" type="range" min="0" max="100" name="score" value="' + item.score + '" data-relationship-score-range></div>' +
        '<div class="life-two-grid"><label>重要日期<textarea class="life-textarea" name="dates" placeholder="一行一个日期">' + escapeHtml((item.dates || []).join('\n')) + '</textarea></label><label>最近聊到<textarea class="life-textarea" name="notes" placeholder="一行一条最近记录">' + escapeHtml((item.notes || []).join('\n')) + '</textarea></label></div>' +
        '<div class="life-two-grid life-media-main-grid">' + renderRelationshipMediaSummary('共同记忆', item.memories, 'memory', 'view-memories') + '<label class="life-memo-editor">我的备注<textarea class="life-textarea" name="memo">' + escapeHtml(item.memo || '') + '</textarea></label></div>' +
        '<div class="life-two-grid life-media-pair-grid">' + renderRelationshipMediaSummary('送的礼物', item.gifts, 'gift', 'view-gifts') + renderRelationshipMediaSummary('一起去过的地方', item.places, 'place', 'view-places') + '</div>' +
        '<div class="life-relationship-form-actions">' + (state.relationshipFormMode === 'edit' ? '<button class="life-danger-btn" type="button" data-relationship-action="delete">删除关系</button>' : '') + '<button class="life-secondary-btn" type="button" data-relationship-action="cancel-form">取消</button><button class="life-primary-btn" type="submit">' + (state.relationshipFormMode === 'edit' ? '保存修改' : '保存关系') + '</button></div>' +
      '</form></section>';
  }

  function renderRelationshipAside(item) {
    if (!item) return '<section class="life-detail-card"><div class="life-empty">没有关系记录</div><button class="life-primary-btn" type="button" data-relationship-action="add">添加关系</button></section>';
    return '<section class="life-relationship-detail"><div class="life-relationship-profile">' + relationshipAvatarHtml(item, 'large') + '<div><h2>' + escapeHtml(item.name) + ' <em>' + escapeHtml(item.group) + '</em></h2><p>' + escapeHtml(item.role) + '</p></div><div class="life-relationship-profile-actions"><button type="button" data-relationship-action="favorite">' + iconHtml('health') + '</button><button class="life-secondary-btn" type="button" data-relationship-action="remind">提醒联系</button><button type="button" data-relationship-action="edit">···</button></div></div>' +
      '<div class="life-relationship-metrics"><div><span>亲密度</span><strong>' + item.score + '</strong><em>' + relationshipScoreLabel(item.score) + '</em>' + progress(item.score, item.score >= 75 ? 'var(--life-accent)' : 'var(--life-amber)') + '</div><div><span>上次联系</span><strong>' + escapeHtml(item.last) + '</strong><em>' + escapeHtml(item.channel) + '</em></div><div><span>下次联系</span><strong>' + escapeHtml(item.next) + '</strong><em>' + escapeHtml(item.nextDate || '待定') + '</em></div><div><span>关系趋势</span>' + relationshipSparkline(item.trend, item.score) + '</div></div>' +
      renderRelationshipInlineEditor(item) +
      '<div class="life-relationship-detail-grid"><section><div class="life-section-title"><h3>重要日期</h3><button type="button" data-relationship-action="add-date">＋ 添加日期</button></div>' + relationshipDateList(item) + '<h3>关系状态</h3><p class="life-status-line">' + iconHtml('health') + ' 亲密稳定</p><p class="life-status-line">' + iconHtml('relationship') + ' 距离感 -5，比上月更近了</p></section><section><div class="life-section-title"><h3>最近聊到</h3><button type="button" data-relationship-action="add-note">＋ 添加记录</button></div>' + relationshipNotesList(item) + '<button class="life-link-btn" type="button" data-relationship-action="view-notes">查看全部 →</button></section></div>' +
      '<section class="life-relationship-memories"><div class="life-section-title"><h3>共同记忆</h3><button type="button" data-relationship-action="view-memories">查看全部（' + item.memories.length + '）</button></div>' + renderRelationshipMediaCards(item.memories, 'memory') + '</section>' +
      '<div class="life-relationship-bottom-grid"><section><h3>送的礼物</h3>' + renderRelationshipMediaMini(item.gifts, 'gift', ['围巾 2026-01', '照片书 2025-05']) + '<button class="life-link-btn" type="button" data-relationship-action="view-gifts">查看全部</button></section><section><h3>一起去过的地方</h3>' + renderRelationshipMediaMini(item.places, 'place', ['杭州西湖 2024-04', '桂林 2023-10', '厦门鼓浪屿 2022-08']) + '<button class="life-link-btn" type="button" data-relationship-action="view-places">查看全部</button></section><section><h3>我的备注</h3><p>' + escapeHtml(item.memo || '她很在意我的工作和健康，多分享生活中的小确幸会让她更开心。') + '</p><button class="life-link-btn" type="button" data-relationship-action="edit-memo">编辑备注</button></section></div>' +
      '<div class="life-relationship-lifecycle"><button class="life-secondary-btn" type="button" data-relationship-action="edit">编辑关系</button><button class="life-danger-btn" type="button" data-relationship-action="delete">删除关系</button></div></section>';
  }

  function renderRelationshipInlineEditor(item) {
    if (!state.relationshipInlineEditor) return '';
    var type = state.relationshipInlineEditor;
    var configs = {
      date: ['添加重要日期', 'dates', '例如：生日 1958-06-21'],
      note: ['添加最近记录', 'notes', '写下这次聊到的内容'],
      notes: ['全部最近记录', 'notes', '补充一条最近记录'],
      gift: ['礼物记录', 'gifts', '例如：照片书 2025-05', 'gift'],
      place: ['一起去过的地方', 'places', '例如：杭州西湖 2024-04', 'place'],
      memory: ['共同记忆', 'memories', '例如：2024 春节', 'memory'],
      memo: ['编辑我的备注', 'memo', '写下相处提醒和偏好']
    };
    var config = configs[type] || configs.note;
    var mediaKind = config[3] || '';
    var values = config[1] === 'memo' ? [item.memo || ''] : (item[config[1]] || []);
    var list = config[1] === 'memo'
      ? ''
      : (mediaKind ? renderRelationshipMediaCards(values, mediaKind) : '<div class="life-inline-list">' + values.map(function(value) { return '<span>' + escapeHtml(value) + '</span>'; }).join('') + '</div>');
    var field = config[1] === 'memo'
      ? '<textarea class="life-textarea" name="entry">' + escapeHtml(item.memo || '') + '</textarea>'
      : (mediaKind ? renderRelationshipMediaEditor(config[1], config[0], values, mediaKind, config[2]) : '<input class="life-input" name="entry" placeholder="' + escapeHtml(config[2]) + '">');
    return '<section class="life-relationship-inline-editor"><form id="lifeRelationshipInlineForm"><input type="hidden" name="type" value="' + type + '"><input type="hidden" name="field" value="' + config[1] + '"><div class="life-section-title"><h3>' + config[0] + '</h3><button type="button" data-relationship-action="close-inline">关闭</button></div>' + list + field + '<div class="life-inline-actions"><button class="life-secondary-btn" type="button" data-relationship-action="close-inline">取消</button><button class="life-primary-btn" type="submit">保存到关系档案</button></div></form></section>';
  }

  function relationshipDateList(item) {
    return (item.dates || []).map(function(text) {
      return '<p class="life-date-line">' + iconHtml('monthly') + '<span>' + escapeHtml(text) + '</span></p>';
    }).join('') || '<p class="life-card-copy">暂无重要日期</p>';
  }

  function relationshipNotesList(item) {
    return (item.notes || []).slice(0, 3).map(function(text, idx) {
      return '<article class="life-note-card"><p>' + escapeHtml(text) + '</p><span>' + ['2026-05-13','2026-05-10','2026-05-08'][idx % 3] + '</span></article>';
    }).join('') || '<p class="life-card-copy">暂无最近记录</p>';
  }

  function relationshipMiniList(items) {
    return items.map(function(text) {
      return '<p class="life-mini-pill">' + escapeHtml(text) + '</p>';
    }).join('');
  }

  function startRelationshipCreate() {
    state.relationshipFormMode = 'create';
    state.relationshipEditingId = '';
    renderRelationships();
  }

  function startRelationshipEdit() {
    var selected = getSelectedRelationship(allRelationships());
    if (!selected) {
      startRelationshipCreate();
      return;
    }
    state.relationshipFormMode = 'edit';
    state.relationshipEditingId = selected.id;
    renderRelationships();
  }

  function relationshipFromForm(form) {
    var current = state.relationshipFormMode === 'edit' ? getSelectedRelationship(allRelationships()) : null;
    var score = Math.max(0, Math.min(100, Number(form.elements.score.value || 0)));
    return normalizeRelationship(Object.assign({}, current || {}, {
      id: current ? current.id : 'r-local-' + Date.now(),
      name: form.elements.name.value.trim() || '未命名联系人',
      role: form.elements.role.value.trim() || '重要的人',
      group: form.elements.group.value,
      avatar: relationshipFormAvatarValue(form, current),
      avatarUrl: relationshipFormAvatarValue(form, current) === 'custom' ? form.elements.avatarUrl.value.trim() : '',
      last: form.elements.last.value.trim() || '今天',
      channel: form.elements.channel.value.trim() || '微信',
      score: score,
      next: form.elements.next.value.trim() || '7 天后',
      nextDate: form.elements.nextDate.value || '2026-05-20',
      trend: (current && current.trend ? current.trend.slice(-5) : [60, 64, 68, 72, 70]).concat([score]),
      dates: splitLines(form.elements.dates.value, []),
      notes: splitLines(form.elements.notes.value, []),
      memories: current ? current.memories : [],
      gifts: current ? current.gifts : [],
      places: current ? current.places : [],
      memo: form.elements.memo.value.trim()
    }));
  }

  function saveRelationshipForm(form) {
    var store = getRelationshipStore();
    var item = relationshipFromForm(form);
    var seedExists = withMockData(relationships, mockRelationships).some(function(seed) { return seed.id === item.id; });
    if (seedExists) {
      store.edits[item.id] = item;
      store.added = (store.added || []).filter(function(record) { return record.id !== item.id; });
      store.deleted = (store.deleted || []).filter(function(id) { return id !== item.id; });
    } else {
      delete store.edits[item.id];
      store.added = (store.added || []).filter(function(record) { return record.id !== item.id; });
      store.added.unshift(item);
    }
    saveRelationshipStore(store);
    state.selectedRelationshipId = item.id;
    state.relationshipFilter = '全部';
    state.relationshipFormMode = null;
    state.relationshipEditingId = '';
    showToast('关系已保存');
    renderRelationships();
  }

  function persistRelationshipUpdate(item, toastMessage) {
    var store = getRelationshipStore();
    var seedExists = withMockData(relationships, mockRelationships).some(function(seed) { return seed.id === item.id; });
    if (seedExists) {
      store.edits[item.id] = item;
    } else {
      delete store.edits[item.id];
      store.added = (store.added || []).filter(function(record) { return record.id !== item.id; });
      store.added.unshift(item);
    }
    saveRelationshipStore(store);
    state.selectedRelationshipId = item.id;
    if (toastMessage) showToast(toastMessage);
  }

  function deleteSelectedRelationship() {
    var selected = getSelectedRelationship(allRelationships());
    if (!selected) return;
    if (!window.confirm('确认删除「' + selected.name + '」这条关系记录吗？删除后会从当前原型数据中移除。')) return;
    var store = getRelationshipStore();
    store.added = (store.added || []).filter(function(item) { return item.id !== selected.id; });
    delete store.edits[selected.id];
    if ((store.deleted || []).indexOf(selected.id) < 0) store.deleted.push(selected.id);
    saveRelationshipStore(store);
    var remaining = allRelationships().filter(function(item) { return item.id !== selected.id; });
    state.selectedRelationshipId = remaining[0] ? remaining[0].id : '';
    state.relationshipFormMode = null;
    state.relationshipEditingId = '';
    showToast('关系已删除');
    renderRelationships();
  }

  function openRelationshipInlineEditor(type) {
    state.relationshipInlineEditor = type;
    renderRelationships();
  }

  function closeRelationshipInlineEditor() {
    state.relationshipInlineEditor = '';
    renderRelationships();
  }

  function saveRelationshipInlineForm(form) {
    var selected = getSelectedRelationship(allRelationships());
    if (!selected) return;
    var field = form.elements.field.value;
    var type = form.elements.type.value;
    var value = (form.elements.entry ? form.elements.entry.value : '').trim();
    var next = Object.assign({}, selected);
    if (field === 'memo') {
      next.memo = value;
    } else if (field === 'memories' || field === 'gifts' || field === 'places') {
      next[field] = readRelationshipMediaEditor(form, field);
    } else if (value) {
      var current = Array.isArray(next[field]) ? next[field].slice() : [];
      next[field] = field === 'notes' ? [value].concat(current) : current.concat([value]);
    }
    persistRelationshipUpdate(normalizeRelationship(next), field === 'memo' ? '备注已保存' : '关系档案已更新');
    state.relationshipInlineEditor = type === 'notes' || type === 'gift' || type === 'place' || type === 'memory' ? type : '';
    renderRelationships();
  }

  function remindRelationship() {
    var selected = getSelectedRelationship(allRelationships());
    if (!selected) return;
    persistRelationshipUpdate(normalizeRelationship(Object.assign({}, selected, { reminded: true, next: '已提醒', nextDate: '2026-05-13' })), '已加入联系提醒');
    renderRelationships();
  }

  function activateRelationshipAvatarChoice(choice) {
    var picker = choice.closest('.life-avatar-picker');
    if (!picker) return;
    picker.querySelectorAll('[data-avatar-choice]').forEach(function(item) {
      item.classList.toggle('active', item === choice);
    });
    var input = choice.querySelector('input');
    if (input) input.checked = true;
    var current = getSelectedRelationship(allRelationships());
    var form = choice.closest('#lifeRelationshipForm');
    if (form) {
      var avatarUrl = form.querySelector('input[name="avatarUrl"]');
      var avatarUrlField = form.querySelector('[data-avatar-url-field]');
      var avatarValue = choice.getAttribute('data-avatar-choice') || relationshipAvatarKey(current || {});
      if (avatarUrl && avatarValue !== 'custom') avatarUrl.value = '';
      if (avatarUrlField) avatarUrlField.classList.toggle('is-hidden', avatarValue !== 'custom');
    }
    if (current && form) {
      els.aside.innerHTML = renderRelationshipAside(Object.assign({}, current, {
        avatar: choice.getAttribute('data-avatar-choice') || relationshipAvatarKey(current),
        avatarUrl: choice.getAttribute('data-avatar-choice') === 'custom' ? (form.querySelector('input[name="avatarUrl"]') || {}).value || '' : ''
      }));
    }
  }

  function addRelationshipMediaEditorRow(button) {
    var field = button.getAttribute('data-media-field');
    var kind = button.getAttribute('data-media-kind') || 'memory';
    var editor = button.closest('[data-relationship-media-field]');
    var list = editor && editor.querySelector('.life-media-editor-list');
    if (!list) return;
    list.insertAdjacentHTML('beforeend', relationshipMediaEditorRow(field, kind, { text: '', image: '' }, list.querySelectorAll('[data-relationship-media-row]').length));
  }

  function deleteRelationshipMediaEditorRow(button) {
    var row = button.closest('[data-relationship-media-row]');
    var list = row && row.parentNode;
    if (!row || !list) return;
    if (list.querySelectorAll('[data-relationship-media-row]').length <= 1) {
      var textInput = row.querySelector('[data-relationship-media-text]');
      var imageInput = row.querySelector('[data-relationship-media-image]');
      if (textInput) textInput.value = '';
      if (imageInput) imageInput.value = '';
      refreshRelationshipMediaRowPreview(row);
      return;
    }
    row.remove();
  }

  function wishCategories(items) {
    var fixed = ['全部', '数码', '旅行', '学习', '生活', '关系', '职业', '健康'];
    items.forEach(function(item) {
      if (fixed.indexOf(item.category) < 0) fixed.push(item.category);
    });
    return fixed;
  }

  function wishStatusTabs(items) {
    return ['全部', '愿望冷却中', '可以决定', '已放弃', '已实现'].map(function(status) {
      return {
        status: status,
        count: status === '全部' ? items.length : items.filter(function(item) { return item.status === status; }).length
      };
    });
  }

  function wishMatchesFilters(item) {
    return (state.wishFilter === '全部' || item.status === state.wishFilter) &&
      (state.wishCategory === '全部' || item.category === state.wishCategory) &&
      queryMatch([item.name, item.reason, item.category, item.status, item.price].join(' '));
  }

  function wishSortValue(item) {
    if (state.wishSort === '按想要程度排序') return -item.desire;
    if (state.wishSort === '按价格排序') return Number(String(item.price).replace(/[^\d.]/g, '') || 0);
    return item.status === '愿望冷却中' ? item.days : 999 + item.desire;
  }

  function sortedWishes(items) {
    return items.slice().sort(function(a, b) {
      var delta = wishSortValue(a) - wishSortValue(b);
      if (delta !== 0) return delta;
      return a.name.localeCompare(b.name);
    });
  }

  function selectedWish(items) {
    return items.filter(function(item) { return item.id === state.selectedWishId; })[0] || items[0] || null;
  }

  function wishTone(status) {
    if (status === '愿望冷却中') return 'blue';
    if (status === '可以决定') return 'green';
    if (status === '已放弃') return 'gray';
    if (status === '已实现') return 'amber';
    return 'gray';
  }

  function wishPhoto(item) {
    var byCategory = {
      '数码': 'photo-camera',
      '旅行': 'photo-mountain',
      '学习': 'photo-book',
      '生活': 'photo-cafe',
      '关系': 'photo-garden',
      '职业': 'photo-office',
      '健康': 'photo-river'
    };
    return item.photo || byCategory[item.category] || 'photo-book';
  }

  function wishProgressColor(item) {
    if (item.status === '已放弃') return 'var(--life-red)';
    if (item.status === '已实现' || item.status === '可以决定') return 'var(--life-green)';
    return item.desire >= 70 ? 'var(--life-red)' : 'var(--life-amber)';
  }

  function addDateDays(value, days) {
    var parts = String(value || '2026-05-13').split('-').map(Number);
    var date = new Date(parts[0] || 2026, (parts[1] || 5) - 1, parts[2] || 13);
    date.setDate(date.getDate() + days);
    return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0');
  }

  function persistWishUpdate(item, message) {
    var store = getWishStore();
    var normalized = normalizeWish(item);
    var addedIndex = (store.added || []).findIndex(function(entry) { return entry.id === normalized.id; });
    if (addedIndex >= 0 || normalized.id.indexOf('w-local-') === 0) {
      if (addedIndex >= 0) store.added[addedIndex] = normalized;
      else store.added.push(normalized);
    } else {
      store.edits[normalized.id] = normalized;
    }
    saveWishStore(store);
    state.selectedWishId = normalized.id;
    if (message) showToast(message);
    renderWishes();
  }

  function deleteSelectedWish() {
    var current = selectedWish(allWishes());
    if (!current) return;
    if (!window.confirm('确认删除这个愿望吗？删除后不会进入当前列表。')) return;
    var store = getWishStore();
    store.added = (store.added || []).filter(function(item) { return item.id !== current.id; });
    if (store.edits) delete store.edits[current.id];
    if (current.id.indexOf('w-local-') !== 0 && (store.deleted || []).indexOf(current.id) < 0) store.deleted.push(current.id);
    saveWishStore(store);
    var next = allWishes()[0];
    state.selectedWishId = next ? next.id : '';
    state.wishFormMode = null;
    showToast('愿望已删除');
    renderWishes();
  }

  function startWishCreate() {
    state.wishFormMode = 'create';
    state.selectedWishId = '';
    renderWishes();
  }

  function startWishEdit() {
    if (!selectedWish(allWishes())) return;
    state.wishFormMode = 'edit';
    renderWishes();
  }

  function cycleWishSort() {
    state.wishSort = state.wishSort === '按剩余天数排序' ? '按想要程度排序' : (state.wishSort === '按想要程度排序' ? '按价格排序' : '按剩余天数排序');
    renderWishes();
  }

  function applyWishAction(actionName) {
    var current = selectedWish(allWishes());
    if (!current) return;
    var next = normalizeWish(Object.assign({}, current));
    if (actionName === 'extend') {
      next.days += 7;
      next.due = addDateDays(next.due, 7);
      next.status = '愿望冷却中';
      persistWishUpdate(next, '冷却期已延长 7 天');
      return;
    }
    if (actionName === 'drop') {
      if (!window.confirm('确认把这个愿望放入放弃区吗？')) return;
      next.status = '已放弃';
      next.days = 0;
      persistWishUpdate(next, '已放入放弃区');
      return;
    }
    if (actionName === 'decide') {
      next.status = '可以决定';
      next.days = 0;
      persistWishUpdate(next, '已进入可以决定');
      return;
    }
    if (actionName === 'realize') {
      next.status = '已实现';
      next.days = 0;
      persistWishUpdate(next, '愿望已标记为实现');
      return;
    }
  }

  function renderWishes() {
    var items = sortedWishes(allWishes());
    var filtered = items.filter(wishMatchesFilters);
    var selected = state.wishFormMode === 'create' ? null : selectedWish(items);
    if (selected && state.wishFormMode !== 'edit' && !filtered.some(function(item) { return item.id === selected.id; })) selected = filtered[0] || selected;
    if (selected) state.selectedWishId = selected.id;
    var groups = ['愿望冷却中', '可以决定', '已放弃', '已实现'];
    els.content.innerHTML = mockNotice() + '<section class="life-wishes-page">' +
      '<div class="life-wish-titlebar"><div><h2 class="life-page-title">愿望冷却箱</h2><p>给冲动一点时间，让重要决定更清醒。</p></div></div>' +
      '<div class="life-wish-category-tabs">' + wishCategories(items).map(function(category) { return '<button type="button" class="' + (state.wishCategory === category ? 'active' : '') + '" data-wish-category="' + escapeHtml(category) + '">' + escapeHtml(category) + '</button>'; }).join('') + '</div>' +
      '<div class="life-wish-statusbar"><div class="life-wish-status-tabs">' + wishStatusTabs(items).map(function(tab) { return '<button type="button" class="' + (state.wishFilter === tab.status ? 'active' : '') + '" data-wish-filter="' + escapeHtml(tab.status) + '">' + escapeHtml(tab.status) + ' <span>(' + tab.count + ')</span></button>'; }).join('') + '</div><div class="life-wish-tools"><button type="button" class="life-secondary-btn" data-wish-action="sort">' + escapeHtml(state.wishSort) + '⌄</button><button type="button" class="life-icon-btn" data-wish-action="toggle-view">' + iconHtml('resources') + '</button></div></div>' +
      '<div class="life-wish-list">' + groups.map(function(status) {
        var groupItems = filtered.filter(function(item) { return item.status === status; });
        if (!groupItems.length) return '';
        return '<section class="life-wish-group"><h3>' + escapeHtml(status) + '</h3>' + groupItems.map(function(item) { return renderWishRow(item, selected && selected.id === item.id); }).join('') + '</section>';
      }).join('') + (!filtered.length ? '<section class="life-empty">没有符合条件的愿望。</section>' : '') + '</div></section>';
    els.aside.innerHTML = state.wishFormMode ? renderWishForm(state.wishFormMode === 'create' ? null : selected) : (selected ? renderWishDetail(selected) : '');
  }

  function renderWishRow(item, active) {
    var remaining = item.status === '愿望冷却中' ? '<strong>剩余 <b>' + item.days + '</b> 天</strong><span>冷却期至 ' + escapeHtml(item.due) + '</span>' : '<strong>' + escapeHtml(item.status) + '</strong><span>' + (item.status === '已实现' ? '实现于 ' : '冷却期至 ') + escapeHtml(item.due) + '</span>';
    return '<article class="life-wish-row clickable ' + (active ? 'active' : '') + '" data-wish-id="' + escapeHtml(item.id) + '">' +
      '<span class="life-photo ' + wishPhoto(item) + '"></span><div class="life-wish-main"><h4>' + escapeHtml(item.name) + '</h4><p>为什么想要：' + escapeHtml(item.reason) + '</p><span class="life-badge ' + wishTone(item.status) + '">' + escapeHtml(item.category) + '</span></div>' +
      '<div class="life-wish-remaining">' + remaining + '</div><div class="life-wish-desire"><span>当前想要程度</span><strong>' + item.desire + '%</strong>' + progress(item.desire, wishProgressColor(item)) + '</div><div class="life-wish-price"><span>价格</span><strong>' + escapeHtml(item.price) + '</strong></div></article>';
  }

  function renderWishDetail(item) {
    return '<article class="life-wish-detail"><div class="life-wish-detail-head"><span class="life-photo ' + wishPhoto(item) + '"></span><div><h2>' + escapeHtml(item.name) + '</h2><p>添加于 ' + escapeHtml(item.addedAt) + '<span>' + escapeHtml(item.category) + '</span></p></div><span class="life-badge ' + wishTone(item.status) + '">' + escapeHtml(item.status) + '</span><button class="life-mini-btn" type="button" data-wish-action="edit">编辑</button></div>' +
      '<section class="life-wish-hero"><div><span>剩余</span><strong>' + item.days + '</strong><em>天</em></div><div><h3>仍然想要吗？ <b>' + item.desire + '%</b></h3>' + progress(item.desire, wishProgressColor(item)) + '</div></section>' +
      '<section class="life-wish-section"><h3>原始理由</h3><p>' + escapeHtml(item.reason) + '</p></section>' +
      '<div class="life-wish-reason-grid"><section><h3>补充说明</h3><p>' + escapeHtml(item.notes || '暂时没有更多补充。') + '</p></section><section><h3>可能的反对理由</h3>' + (item.counterReasons.length ? item.counterReasons : ['还需要更多信息']).map(function(text) { return '<p>• ' + escapeHtml(text) + '</p>'; }).join('') + '</section></div>' +
      '<div class="life-wish-facts"><div><span>价格</span><strong>' + escapeHtml(item.price) + '</strong><button type="button" data-wish-action="price-history">价格历史</button><small>' + escapeHtml(item.priceHistory) + '</small></div><div><span>冷却期</span><strong>' + escapeHtml(item.coolStart) + ' ~ ' + escapeHtml(item.due) + '</strong><button type="button" data-wish-action="adjust-cooling">调整冷却期</button></div></div>' +
      '<section class="life-wish-section"><h3>替代方案</h3><div class="life-wish-options">' + (item.alternatives.length ? item.alternatives : ['暂无替代方案']).map(function(text, idx) { return '<div><span>' + (idx + 1) + '</span><p>' + escapeHtml(text) + '</p><button type="button" data-wish-action="view-option">查看方案</button></div>'; }).join('') + '</div></section>' +
      '<section class="life-wish-section"><h3>想象拥有后的生活</h3><p>' + escapeHtml(item.future) + '</p></section>' +
      '<section class="life-wish-section"><h3>下一步计划</h3><div class="life-wish-plan">' + (item.plan.length ? item.plan : ['补充下一步计划']).map(function(text, idx) { return '<label><input type="checkbox" data-wish-plan-index="' + idx + '"' + (item.completedPlan.indexOf(String(idx)) >= 0 ? ' checked' : '') + '> ' + escapeHtml(text) + '</label>'; }).join('') + '</div></section>' +
      '<footer class="life-wish-actions"><button class="life-secondary-btn" type="button" data-wish-action="extend">延长冷却期</button>' + (item.status === '已放弃' ? '<button class="life-secondary-btn" type="button" data-wish-action="decide">重新考虑</button>' : '<button class="life-secondary-btn" type="button" data-wish-action="drop">放入放弃区</button>') + (item.status === '已实现' ? '' : '<button class="life-primary-btn" type="button" data-wish-action="decide">可以决定了</button><button class="life-primary-btn amber" type="button" data-wish-action="realize">已实现</button>') + '</footer></article>';
  }

  function renderWishForm(item) {
    var source = item || normalizeWish({
      id: 'w-local-' + Date.now(),
      name: '',
      category: state.wishCategory === '全部' ? '生活' : state.wishCategory,
      reason: '',
      price: '',
      days: 21,
      due: '2026-06-03',
      desire: 50,
      alternatives: [''],
      plan: ['']
    });
    var title = state.wishFormMode === 'edit' ? '编辑愿望' : '添加愿望';
    return '<form id="lifeWishForm" class="life-wish-detail life-wish-form"><div class="life-form-title"><h2>' + title + '</h2><p>记录想要的原因、冷却期、替代方案和下一步计划，保存后进入对应状态栏。</p></div>' +
      '<input type="hidden" name="id" value="' + escapeHtml(source.id) + '">' +
      '<div class="life-two-grid"><label>愿望名称<input class="life-input" name="name" value="' + escapeHtml(source.name) + '" required></label><label>分类<select class="life-select" name="category">' + ['数码','旅行','学习','生活','关系','职业','健康'].map(function(category) { return '<option value="' + category + '"' + (source.category === category ? ' selected' : '') + '>' + category + '</option>'; }).join('') + '</select></label></div>' +
      '<div class="life-three-grid"><label>状态<select class="life-select" name="status">' + ['愿望冷却中','可以决定','已放弃','已实现'].map(function(status) { return '<option value="' + status + '"' + (source.status === status ? ' selected' : '') + '>' + status + '</option>'; }).join('') + '</select></label><label>剩余天数<input class="life-input" type="number" min="0" name="days" value="' + escapeHtml(source.days) + '"></label><label>冷却到<input class="life-input" type="date" name="due" value="' + escapeHtml(source.due) + '"></label></div>' +
      '<div class="life-two-grid"><label>价格<input class="life-input" name="price" value="' + escapeHtml(source.price) + '"></label><label>图片样式<select class="life-select" name="photo">' + ['photo-camera','photo-mountain','photo-office','photo-book','photo-cafe','photo-garden','photo-river'].map(function(photo) { return '<option value="' + photo + '"' + (wishPhoto(source) === photo ? ' selected' : '') + '>' + photo.replace('photo-', '') + '</option>'; }).join('') + '</select></label></div>' +
      '<label class="life-wish-range">当前想要程度 <strong><span data-wish-desire-value>' + source.desire + '</span>/100</strong><input type="range" min="0" max="100" name="desire" value="' + escapeHtml(source.desire) + '" data-wish-desire-range></label>' +
      '<label>原始理由<textarea class="life-textarea" name="reason" required>' + escapeHtml(source.reason) + '</textarea></label>' +
      '<label>补充说明<textarea class="life-textarea" name="notes">' + escapeHtml(source.notes || '') + '</textarea></label>' +
      '<label>可能的反对理由<textarea class="life-textarea" name="counterReasons" placeholder="一行一个反对理由">' + escapeHtml((source.counterReasons || []).join('\n')) + '</textarea></label>' +
      '<label>替代方案<textarea class="life-textarea" name="alternatives" placeholder="一行一个替代方案">' + escapeHtml((source.alternatives || []).join('\n')) + '</textarea></label>' +
      '<label>下一步计划<textarea class="life-textarea" name="plan" placeholder="一行一个计划">' + escapeHtml((source.plan || []).join('\n')) + '</textarea></label>' +
      '<label>想象拥有后的生活<textarea class="life-textarea" name="future">' + escapeHtml(source.future || '') + '</textarea></label>' +
      '<footer class="life-wish-actions"><button class="life-secondary-btn" type="button" data-wish-action="cancel-form">取消</button>' + (state.wishFormMode === 'edit' ? '<button class="life-secondary-btn danger" type="button" data-wish-action="delete">删除愿望</button>' : '') + '<button class="life-primary-btn" type="submit">保存愿望</button></footer></form>';
  }

  function wishFromForm(form) {
    var existing = state.wishFormMode === 'edit' ? selectedWish(allWishes()) : null;
    var item = normalizeWish(Object.assign({}, existing || {}, {
      id: form.elements.id.value || 'w-local-' + Date.now(),
      name: form.elements.name.value.trim() || '未命名愿望',
      category: form.elements.category.value,
      status: form.elements.status.value,
      days: Number(form.elements.days.value || 0),
      due: form.elements.due.value || '2026-06-03',
      desire: Number(form.elements.desire.value || 0),
      price: form.elements.price.value.trim() || '待定',
      photo: form.elements.photo.value,
      reason: form.elements.reason.value.trim(),
      notes: form.elements.notes.value.trim(),
      counterReasons: splitLines(form.elements.counterReasons.value, []),
      alternatives: splitLines(form.elements.alternatives.value, []),
      plan: splitLines(form.elements.plan.value, []),
      future: form.elements.future.value.trim() || '可以更自由地记录和表达，让生活更有仪式感。',
      addedAt: (existing && existing.addedAt) || '2026-05-13',
      coolStart: (existing && existing.coolStart) || '2026-05-01',
      completedPlan: existing && existing.id === form.elements.id.value ? existing.completedPlan : []
    }));
    if (item.status !== '愿望冷却中') item.days = 0;
    return item;
  }

  function saveWishForm(form) {
    var item = wishFromForm(form);
    state.wishFormMode = null;
    persistWishUpdate(item, '愿望已保存');
  }

  function toggleWishPlan(target) {
    var current = selectedWish(allWishes());
    if (!current) return;
    var index = target.getAttribute('data-wish-plan-index');
    var completed = current.completedPlan.slice();
    if (target.checked && completed.indexOf(index) < 0) completed.push(index);
    if (!target.checked) completed = completed.filter(function(item) { return item !== index; });
    persistWishUpdate(Object.assign({}, current, { completedPlan: completed }), '计划进度已更新');
  }

  function monthlyKey() {
    return state.monthlyYear + '-' + String(state.monthlyMonth + 1).padStart(2, '0');
  }

  function monthlyTitle() {
    return state.monthlyYear + ' 年 ' + (state.monthlyMonth + 1) + ' 月';
  }

  function monthlyDateText(day) {
    return String(state.monthlyMonth + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
  }

  function getMonthlyMeta() {
    var store = getMonthlyStore();
    var key = monthlyKey();
    return {
      bookmarked: store.bookmarked[key] !== false,
      report: store.reports[key] || null,
      archived: !!store.archived[key],
      quote: store.quotes[key] || '在探索与连接中，我更靠近自己想要的生活。',
      letter: store.letters[key] || {
        title: '写给 3 个月后的自己',
        date: '2026-05-13 写下',
        body: '希望那时的你，还记得今天想要的生活是什么样子。也希望你依然在勇敢地选择自己。'
      }
    };
  }

  function monthlySet(key, value, message) {
    var store = getMonthlyStore();
    var month = monthlyKey();
    if (key === 'bookmarked') store.bookmarked[month] = value;
    if (key === 'report') store.reports[month] = value;
    if (key === 'archived') store.archived[month] = value;
    if (key === 'letter') store.letters[month] = value;
    if (key === 'quote') store.quotes[month] = value;
    saveMonthlyStore(store);
    if (message) showToast(message);
    renderMonthly();
  }

  function shiftMonthly(delta) {
    state.monthlyMonth += delta;
    if (state.monthlyMonth < 0) {
      state.monthlyMonth = 11;
      state.monthlyYear -= 1;
    }
    if (state.monthlyMonth > 11) {
      state.monthlyMonth = 0;
      state.monthlyYear += 1;
    }
    state.monthlyLetterMode = false;
    state.monthlyQuoteMode = false;
    renderMonthly();
  }

  function monthlyMomentDay(item) {
    var match = String(item.date || '').match(/(\d{2})-(\d{2})/);
    if (!match) return 1;
    return Number(match[2] || 1);
  }

  function monthlyMediaImageHtml(item) {
    if (item.image) return '<span class="life-photo life-uploaded-photo"><img src="' + escapeHtml(item.image) + '" alt=""></span>';
    return '<span class="life-photo ' + escapeHtml(item.photo || 'photo-book') + '"></span>';
  }

  function monthlyMediaCandidates() {
    var candidates = [];
    allMoments().filter(function(item) {
      return item.photos && item.photos.length && String(item.date || '').indexOf(String(state.monthlyMonth + 1).padStart(2, '0') + '-') >= 0;
    }).forEach(function(item, idx) {
      candidates.push({
        id: 'moment-' + item.id,
        day: monthlyMomentDay(item),
        title: item.title,
        copy: item.copy,
        tag: (item.tags || [item.type])[0] || item.type,
        source: '时间河流',
        view: 'timeline',
        likes: 12 + idx,
        photo: item.photos[0]
      });
    });
    allRelationships().forEach(function(person) {
      [
        ['memories', '共同记忆', 'memory'],
        ['gifts', '送的礼物', 'gift'],
        ['places', '一起去过的地方', 'place']
      ].forEach(function(config) {
        normalizeRelationshipMedia(person[config[0]]).forEach(function(media, idx) {
          candidates.push({
            id: 'relationship-' + person.id + '-' + config[0] + '-' + idx,
            day: [3, 5, 8, 10, 13][idx % 5],
            title: media.text || person.name + '的' + config[1],
            copy: person.name + ' · ' + (person.notes || ['重要关系图片记录'])[0],
            tag: config[1],
            source: '关系温度',
            view: 'relationships',
            likes: person.score ? Math.max(8, Math.round(person.score / 8)) : 10,
            image: media.image || '',
            photo: relationshipMediaClasses(config[2], idx)
          });
        });
      });
    });
    allWishes().filter(function(item) {
      return item.photo;
    }).forEach(function(item, idx) {
      candidates.push({
        id: 'wish-' + item.id,
        day: Number((String(item.due || '').split('-')[2] || 13)),
        title: item.name,
        copy: item.reason,
        tag: item.status,
        source: '愿望冷却箱',
        view: 'wishes',
        likes: Math.max(8, Math.round(item.desire / 6)),
        photo: wishPhoto(item)
      });
    });
    return candidates;
  }

  function monthlyHighlights() {
    var picked = [];
    var used = {};
    function pickFrom(sourceName, fallbackIndex) {
      var item = monthlyMediaCandidates().filter(function(candidate) {
        return candidate.source === sourceName && !used[candidate.id];
      })[fallbackIndex || 0];
      if (item) {
        used[item.id] = true;
        picked.push(item);
      }
    }
    pickFrom('时间河流', 0);
    pickFrom('关系温度', 0);
    pickFrom('愿望冷却箱', 0);
    pickFrom('时间河流', 1);
    monthlyMediaCandidates().forEach(function(item) {
      if (picked.length < 4 && !used[item.id]) {
        used[item.id] = true;
        picked.push(item);
      }
    });
    return picked.slice(0, 4);
  }

  function monthlyMoodScores() {
    return allMoodRecords().filter(function(item) {
      return Number(item.year) === Number(state.monthlyYear) && Number(item.month) === Number(state.monthlyMonth);
    }).map(function(item) { return item.score; });
  }

  function monthlyMoodSvg(scores) {
    var values = scores.length ? scores : [64, 70, 58, 76, 68, 72, 66, 80, 74, 62, 78, 70];
    var width = 520;
    var height = 150;
    var points = values.map(function(score, idx) {
      var x = 20 + idx * ((width - 40) / Math.max(values.length - 1, 1));
      var y = height - 24 - ((score - 35) / 60) * (height - 44);
      return { x: Math.round(x), y: Math.round(Math.max(18, Math.min(height - 20, y))), score: score };
    });
    return '<svg class="life-monthly-mood-svg" viewBox="0 0 ' + width + ' ' + height + '" aria-label="本月情绪曲线">' +
      '<defs><linearGradient id="monthlyMoodBg" x1="0" x2="1"><stop offset="0" stop-color="#fdf7e6"/><stop offset="0.48" stop-color="#fff2f2"/><stop offset="1" stop-color="#eef8ee"/></linearGradient></defs>' +
      '<rect width="' + width + '" height="' + height + '" rx="10" fill="url(#monthlyMoodBg)"/>' +
      '<path d="' + points.map(function(point, idx) { return (idx ? 'L' : 'M') + point.x + ' ' + point.y; }).join(' ') + '" fill="none" stroke="#0b8f8d" stroke-width="2.2"/>' +
      points.map(function(point) { return '<circle cx="' + point.x + '" cy="' + point.y + '" r="4" fill="#fff" stroke="#0b8f8d" stroke-width="2"/>'; }).join('') +
      '<g fill="#667b78" font-size="11"><text x="18" y="136">05-01</text><text x="180" y="136">05-10</text><text x="342" y="136">05-20</text><text x="462" y="136">05-31</text></g></svg>';
  }

  function renderMonthlyHighlightCard(item, idx) {
    return '<article class="life-monthly-highlight ' + (idx === 0 ? 'featured' : '') + '" data-view="' + escapeHtml(item.view || 'timeline') + '">' + monthlyMediaImageHtml(item) + '<div><small>' + monthlyDateText(item.day) + ' · 来自' + escapeHtml(item.source || '时间河流') + '</small><h3>' + escapeHtml(item.title) + '</h3><p>' + escapeHtml(item.copy) + '</p><footer><span class="life-badge ' + (idx === 0 ? 'amber' : idx === 1 ? 'green' : idx === 2 ? 'red' : 'blue') + '">' + escapeHtml(item.tag) + '</span><span>❤ ' + item.likes + '</span></footer></div></article>';
  }

  function renderMonthlyDecisionRows() {
    return allDecisions().slice(0, 4).map(function(item, idx) {
      return '<div class="life-monthly-line"><span class="life-side-icon ' + (idx % 2 ? 'green' : 'amber') + '">' + iconHtml('decision') + '</span><span>' + monthlyDateText([5, 10, 12, 13][idx]) + '</span><strong>' + escapeHtml(item.title) + '</strong><span class="life-badge ' + decisionTone(item) + '">' + escapeHtml(decisionStatus(item)) + '</span><em>选择：' + escapeHtml(item.choice) + '　|　信心：' + item.confidence + '%</em></div>';
    }).join('');
  }

  function renderMonthlyPeople() {
    return allRelationships().slice(0, 4).map(function(item, idx) {
      var note = (item.notes || [])[0] || '有一段温暖的交流。';
      return '<article class="life-monthly-person"><header><span class="life-monthly-person-face">' + relationshipAvatarHtml(item, 'sm') + '</span><div><strong>' + escapeHtml(item.name) + '</strong><small>见面 ' + (idx === 0 ? 2 : 1) + ' 次</small></div></header><p>' + escapeHtml(note) + '</p></article>';
    }).join('');
  }

  function renderMonthlyPlaces() {
    return [
      ['苏州 · 拙政园', 'photo-garden'],
      ['上海 · 外滩', 'photo-river'],
      ['杭州 · 西湖', 'photo-mountain'],
      ['南京 · 先锋书店', 'photo-cafe'],
      ['家附近的公园', 'photo-book']
    ].map(function(item) {
      return '<article class="life-monthly-place"><span class="life-photo ' + item[1] + '"></span><strong>' + item[0] + '</strong></article>';
    }).join('');
  }

  function renderMonthlyWishResults() {
    return allWishes().filter(function(item) {
      return ['愿望冷却中', '可以决定', '已实现'].indexOf(item.status) >= 0;
    }).slice(0, 3).map(function(item) {
      return '<div class="life-monthly-wish"><span class="life-side-icon green">' + iconHtml('wish') + '</span><div class="life-monthly-wish-main"><div><strong>' + escapeHtml(item.name) + '</strong><span class="life-badge green">' + escapeHtml(item.status) + '</span>' + (item.days ? '<em>还有 ' + item.days + ' 天</em>' : '') + '</div><p>' + escapeHtml(item.reason) + '</p></div><span class="life-photo ' + wishPhoto(item) + '"></span></div>';
    }).join('');
  }

  function renderMonthlyLearned() {
    return ['睡眠比我想象中更影响情绪，早睡真的有用。', '把大目标拆成小任务，行动会更轻松。', '真诚地沟通，可以减少很多误解和内耗。', '给自己留出独处的时间，才能听见内心的声音。', '慢慢来，比匆忙赶路更重要。'].map(function(text, idx) {
      return '<button type="button" class="life-monthly-learning-row" data-monthly-action="view-learnings"><span class="life-monthly-learn-icon">' + ['❤', '💡', '👤', '★', '☘'][idx] + '</span><strong>' + escapeHtml(text) + '</strong></button>';
    }).join('');
  }

  function renderMonthly() {
    var meta = getMonthlyMeta();
    var scores = monthlyMoodScores();
    els.content.innerHTML = mockNotice() + '<section class="life-monthly-page"><header class="life-monthly-header"><div><h2>本月值得记住 <button type="button" class="life-monthly-bookmark ' + (meta.bookmarked ? 'active' : '') + '" data-monthly-action="bookmark">' + iconHtml('monthly') + '</button></h2></div><div class="life-monthly-month"><button type="button" data-monthly-action="prev-month">‹</button><strong>' + monthlyTitle() + '</strong><button type="button" data-monthly-action="next-month">›</button></div></header>' +
      '<section class="life-monthly-highlights">' + monthlyHighlights().map(renderMonthlyHighlightCard).join('') + '</section>' +
      '<section class="life-monthly-grid two"><article class="life-monthly-card"><div class="life-monthly-card-head"><h3>做过的决定</h3><span>4 个决定</span><button type="button" data-monthly-action="view-decisions">查看全部 →</button></div><div class="life-monthly-lines">' + renderMonthlyDecisionRows() + '</div></article><article class="life-monthly-card life-monthly-mood-card"><div class="life-monthly-card-head"><h3>情绪模式</h3><span>整体感受：<b>良好</b></span><button type="button" data-monthly-action="view-mood">查看情绪 →</button></div><p class="life-monthly-sub">本月情绪曲线</p><div class="life-monthly-mood-wrap"><div class="life-monthly-mood-scale"><span>晴朗</span><span>微笑</span><span>平静</span><span>低落</span></div>' + monthlyMoodSvg(scores) + '</div></article></section>' +
      '<section class="life-monthly-grid two compact"><article class="life-monthly-card"><div class="life-monthly-card-head"><h3>见过的人</h3><span>' + allRelationships().length + ' 位</span></div><div class="life-monthly-people">' + renderMonthlyPeople() + '</div></article><article class="life-monthly-card"><div class="life-monthly-card-head"><h3>去过的地方</h3><span>5 个地点</span><button type="button" data-monthly-action="view-map">查看地图 →</button></div><div class="life-monthly-places">' + renderMonthlyPlaces() + '</div></article></section>' +
      '<section class="life-monthly-grid three"><article class="life-monthly-card"><div class="life-monthly-card-head"><h3>愿望结果</h3><span>3 个结果</span></div>' + renderMonthlyWishResults() + '<button class="life-link-btn" type="button" data-view="wishes">查看全部 →</button></article><article class="life-monthly-card"><div class="life-monthly-card-head"><h3>学到的事</h3><span>5 条</span></div><div class="life-monthly-learned">' + renderMonthlyLearned() + '</div><button class="life-link-btn" type="button" data-monthly-action="view-learnings">查看全部 →</button></article><article class="life-monthly-card"><div class="life-monthly-card-head"><h3>总结感受</h3></div><div class="life-monthly-summary"><p>这个月是充实又温柔的一个月。</p><p>工作上有突破，生活中也有很多温暖的连接。我开始更清楚地知道，什么对我来说很重要：健康的身体、真诚的关系、持续成长，以及自由的时间。</p><p>下个月，希望继续保持这份节奏，也给自己更多的耐心和信任。</p></div></article></section></section>';
    els.aside.innerHTML = renderMonthlyAside(meta);
  }

  function renderMonthlyAside(meta) {
    var reportText = meta.report ? '已生成于 ' + meta.report.createdAt : '记录、统计、故事，一键生成';
    var archiveText = meta.archived ? '本月内容已归档，后续可在复盘与回顾中查看。' : '将本月回顾内容归档保存，便于未来随时回顾与对比';
    return '<section class="life-monthly-side-card quote"><div class="life-monthly-card-head"><h3>本月一句话</h3>' + (state.monthlyQuoteMode ? '<span>编辑中</span>' : '<button type="button" data-monthly-action="edit-quote">修改</button>') + '</div>' + (state.monthlyQuoteMode ? renderMonthlyQuoteForm(meta.quote) : '<div class="life-monthly-handwriting">' + escapeHtml(meta.quote) + '</div><span class="life-monthly-heart">♡</span><span class="life-photo photo-book"></span>') + '</section>' +
      '<section class="life-monthly-side-card"><div class="life-monthly-card-head"><h3>写给未来的自己</h3><span>1 封信</span></div>' + (state.monthlyLetterMode ? renderMonthlyLetterForm(meta.letter) : '<article class="life-monthly-letter"><strong>' + escapeHtml(meta.letter.title) + '</strong><small>' + escapeHtml(meta.letter.date) + '</small><p>' + escapeHtml(meta.letter.body) + '</p><button type="button" data-monthly-action="write-letter">' + iconHtml('add') + ' 编辑信件</button></article>') + '</section>' +
      '<section class="life-monthly-side-card report"><h3>生成月报</h3><p>自动生成本月生活月报</p><span>' + reportText + '</span><button class="life-secondary-btn" type="button" data-monthly-action="generate-report">' + iconHtml('star') + ' 生成月报</button></section>' +
      '<section class="life-monthly-side-card archive"><h3>归档本月</h3><p>' + archiveText + '</p><button class="life-secondary-btn" type="button" data-monthly-action="archive-month">' + iconHtml('resource') + ' ' + (meta.archived ? '已归档' : '归档') + '</button><span class="life-photo photo-cafe"></span></section>';
  }

  function renderMonthlyQuoteForm(quote) {
    return '<form id="lifeMonthlyQuoteForm" class="life-monthly-quote-form"><label>一句话<textarea class="life-textarea" name="quote" maxlength="80">' + escapeHtml(quote) + '</textarea></label><div><button class="life-secondary-btn" type="button" data-monthly-action="cancel-quote">取消</button><button class="life-primary-btn" type="submit">保存一句话</button></div></form>';
  }

  function renderMonthlyLetterForm(letter) {
    return '<form id="lifeMonthlyLetterForm" class="life-monthly-letter-form"><label>标题<input class="life-input" name="title" value="' + escapeHtml(letter.title) + '"></label><label>内容<textarea class="life-textarea" name="body">' + escapeHtml(letter.body) + '</textarea></label><div><button class="life-secondary-btn" type="button" data-monthly-action="cancel-letter">取消</button><button class="life-primary-btn" type="submit">保存信件</button></div></form>';
  }

  function saveMonthlyQuote(form) {
    state.monthlyQuoteMode = false;
    monthlySet('quote', form.elements.quote.value.trim() || '在探索与连接中，我更靠近自己想要的生活。', '本月一句话已保存');
  }

  function saveMonthlyLetter(form) {
    state.monthlyLetterMode = false;
    monthlySet('letter', {
      title: form.elements.title.value.trim() || '写给 3 个月后的自己',
      date: '2026-05-13 写下',
      body: form.elements.body.value.trim() || '希望那时的你，还记得今天想要的生活是什么样子。'
    }, '信件已保存');
  }

  function handleMonthlyAction(actionName) {
    var meta = getMonthlyMeta();
    if (actionName === 'prev-month') shiftMonthly(-1);
    if (actionName === 'next-month') shiftMonthly(1);
    if (actionName === 'bookmark') monthlySet('bookmarked', !meta.bookmarked, meta.bookmarked ? '已取消本月收藏' : '已收藏本月');
    if (actionName === 'edit-quote') {
      state.monthlyQuoteMode = true;
      state.monthlyLetterMode = false;
      renderMonthly();
    }
    if (actionName === 'cancel-quote') {
      state.monthlyQuoteMode = false;
      renderMonthly();
    }
    if (actionName === 'write-letter') {
      state.monthlyQuoteMode = false;
      state.monthlyLetterMode = true;
      renderMonthly();
    }
    if (actionName === 'cancel-letter') {
      state.monthlyLetterMode = false;
      renderMonthly();
    }
    if (actionName === 'generate-report') monthlySet('report', { createdAt: '2026-05-13 09:30', records: allMoments().length, moodAverage: 64 }, '月报已生成');
    if (actionName === 'archive-month') {
      if (!meta.archived && !window.confirm('确认归档本月回顾吗？归档后仍可继续查看。')) return;
      monthlySet('archived', true, '本月已归档');
    }
    if (actionName === 'view-decisions') setView('decisions');
    if (actionName === 'view-map') showToast('地图视图已筛选本月地点');
    if (actionName === 'view-mood') setView('mood');
    if (actionName === 'view-learnings') setView('review');
  }

  function addTypeList() {
    return ['记忆', '决定', '情绪', '关系', '愿望', '健康', '项目'];
  }

  function currentAddType(form) {
    var active = form && form.querySelector('[data-add-type].active');
    return active ? active.getAttribute('data-add-type') : '记忆';
  }

  function addValue(form, name, fallback) {
    return form.elements[name] ? form.elements[name].value.trim() || fallback || '' : fallback || '';
  }

  function addDateParts(form) {
    var date = addValue(form, 'date', '2026-05-13');
    var time = addValue(form, 'time', '15:30');
    return { date: date, time: time, day: Number(date.split('-')[2] || 13) };
  }

  function addSelectedMood(form) {
    var activeMood = form.querySelector('[data-add-mood].active');
    return activeMood ? activeMood.getAttribute('data-add-mood') : '晴朗';
  }

  function addTags(form) {
    return addValue(form, 'tags', '').split(',').map(function(item) { return item.trim(); }).filter(Boolean);
  }

  function addPeople(form) {
    return addValue(form, 'people', '').split(',').map(function(item) { return item.trim(); }).filter(Boolean);
  }

  function addSelectedAssociations() {
    return Array.prototype.slice.call(document.querySelectorAll('[data-add-association].active')).map(function(btn) {
      return btn.getAttribute('data-add-association');
    });
  }

  function addTitleForType(type, form) {
    if (type === '决定') return addValue(form, 'decisionTitle', '是否接受新的 Offer？');
    if (type === '情绪') return addSelectedMood(form) + ' ' + addValue(form, 'moodScore', '78') + ' 分';
    if (type === '关系') return '和 ' + addValue(form, 'relationshipName', addValue(form, 'people', '张敏')) + ' 的互动';
    if (type === '愿望') return addValue(form, 'wishName', '相机 Sony A7C II');
    if (type === '健康') return addValue(form, 'healthSignal', '身体状态记录');
    if (type === '项目') return addValue(form, 'projectName', '个人网站改版');
    return addValue(form, 'memoryTitle', '今天在江边散步');
  }

  function renderAddTypeButtons(extraClass) {
    return '<div class="' + extraClass + '">' + addTypeList().map(function(type, idx) {
      return '<button class="life-type-option ' + (idx === 0 ? 'active' : '') + '" type="button" data-add-type="' + type + '">' + addTypeIcon(type) + '<span>' + type + '</span></button>';
    }).join('') + '</div>';
  }

  function addTypeIcon(type) {
    var map = {
      '记忆': 'memory',
      '决定': 'decision',
      '情绪': 'mood',
      '关系': 'relationship',
      '愿望': 'wish',
      '健康': 'health',
      '项目': 'project'
    };
    var icon = map[type] || 'memory';
    return '<span class="life-add-prototype-icon life-add-prototype-icon-' + icon + '" aria-hidden="true"><img src="assets/icons/life/' + icon + '.svg" alt=""></span>';
  }

  function renderAddCard(number, title, theme, body, extraClass, moduleType) {
    return '<section class="life-add-map-card life-add-theme-' + theme + (extraClass ? ' ' + extraClass : '') + (moduleType ? '" data-add-module="' + moduleType : '') + '"><div class="life-add-map-card-head"><span class="life-add-map-number">' + number + '</span><h3>' + title + '</h3></div>' + body + '</section>';
  }

  function renderAddToolbar() {
    return '<div class="life-add-editor-tools"><button type="button">B</button><button type="button">I</button><button type="button">U</button><button type="button">≡</button><button type="button">≣</button><button type="button">“”</button><button type="button">' + iconHtml('link') + '</button><button type="button">' + iconHtml('image') + '</button><button type="button">' + iconHtml('mood') + '</button><button type="button">' + iconHtml('mic') + '</button></div>';
  }

  function renderAddMoodPicker(compact) {
    var moods = ['晴朗','平静','愉快','充实','焦虑','疲惫','低落','生气','其他'];
    return '<div class="' + (compact ? 'life-add-mood-strip' : 'life-add-mood-grid') + '">' + moods.map(function(mood, idx) {
      return '<button class="life-mood-option ' + (idx === 0 ? 'active' : '') + '" type="button" data-add-mood="' + mood + '">' + iconHtml(moodIcons[mood]) + '<span>' + mood + '</span></button>';
    }).join('') + '</div>';
  }

  function renderAddPhotoRail() {
    return '<div class="life-add-photo-rail"><span class="life-photo photo-river"></span><span class="life-photo photo-cafe"></span><span class="life-photo photo-night"></span><span class="life-photo photo-book"></span><button class="life-add-upload-tile" type="button">+<span>添加更多</span></button></div>';
  }

  function renderAdd() {
    els.content.innerHTML = mockNotice() + '<section class="life-add-workbench-page"><div class="life-add-workbench-head"><h2>添加一刻</h2><p>记录此刻的生活片段，丰富你的时间河流</p></div><form class="life-add-workbench" id="lifeAddForm">' +
      '<section class="life-add-editor-card">' + renderAddTypeButtons('life-add-primary-tabs') +
      '<div class="life-add-section"><label class="life-add-body-label">今天发生了什么？<textarea class="life-textarea life-add-body" name="body" data-add-body-source maxlength="2000" placeholder="记录这一刻的想法、经历或感受...">下午在江边散步，阳光很好，江风很舒服。路过一家咖啡馆，坐下来写了会儿笔记，感觉很治愈。</textarea><span data-add-count>126/2000</span></label>' + renderAddToolbar() + '</div>' +
      '<div class="life-add-section life-add-module-shell">' + renderAddWorkbenchPanels() + '</div>' +
      '<div class="life-add-section"><div class="life-two-grid"><label>添加人物<input class="life-input" name="people" placeholder="选择或搜索人物..." value="张敏, Emma"></label><label>添加地点<input class="life-input" name="location" placeholder="选择或搜索地点..." value="上海 · 徐汇滨江"></label></div></div>' +
      '<div class="life-add-section"><label>上传图片 / 附件' + renderAddPhotoRail() + '</label></div>' +
      '<div class="life-add-section"><div class="life-two-grid"><div class="life-two-grid"><label>日期<input class="life-input" type="date" name="date" value="2026-05-13"></label><label>时间<input class="life-input" type="time" name="time" value="15:30"></label></div><label>标签<input class="life-input" name="tags" value="日常, 散步, 咖啡馆, 笔记"></label></div></div>' +
      '<div class="life-add-footer-row"><label><input type="checkbox" name="linkTimeline" checked> 关联到时间河流</label><label><select class="life-select" name="privacy"><option>仅自己可见</option><option>可进入月度回顾</option></select></label><button class="life-secondary-btn" type="button" data-action="preview-add">预览</button><button class="life-primary-btn" type="submit">保存这一刻</button></div></section>' +
      '<aside class="life-add-side-rail"><section class="life-detail-card life-add-preview-panel"><h2 class="life-detail-title">预览</h2><p class="life-panel-sub">在时间河流中的样子</p><div id="lifeAddPreview"></div></section><section class="life-detail-card life-association-card"><h2 class="life-detail-title">智能关联建议</h2><div class="life-association-list" id="lifeAssociationList"></div></section><section class="life-detail-card life-add-tip"><h2 class="life-detail-title">小贴士</h2><p class="life-card-copy">切换类型后，只填写当前模块需要的内容。保存后会同步写入时间河流和对应功能页。</p></section></aside>' +
      '</form></section>';
    els.aside.innerHTML = '';
    setAddType('记忆');
    updateAddPreview();
  }

  function renderAddWorkbenchPanels() {
    return '<section class="life-add-module-panel life-add-memory-panel" data-add-module="记忆"><label>选择心情' + renderAddMoodPicker(false) + '</label><input type="hidden" name="memoryTitle" value="今天在江边散步"></section>' +
      '<section class="life-add-module-panel life-add-theme-orange is-hidden" data-add-module="决定"><div class="life-add-inline-title">' + addTypeIcon('决定') + '<strong>决策信息</strong><span>记录选择、信心和复盘计划</span></div><label>决定背景（可选）<input class="life-input" name="decisionTitle" value="是否接受新工作的 Offer？"></label>' + renderDecisionOptionEditor() + '<div class="life-two-grid"><label>我的倾向<select class="life-select" name="decisionChoice"><option>A. 接受 Offer</option><option>B. 暂不接受</option><option>C. 继续观望</option></select></label><label>复盘计划<input class="life-input" type="date" name="decisionReviewDate" value="2026-11-13"></label></div><label class="life-range-line">信心<input type="range" min="0" max="100" name="decisionConfidence" value="70"><b>70/100</b></label><label>关键风险 / 顾虑<input class="life-input" name="decisionRisks" value="适应期压力大；家庭时间可能减少。"></label></section>' +
      '<section class="life-add-module-panel life-add-theme-rose is-hidden" data-add-module="情绪"><label>选择心情' + renderAddMoodPicker(false) + '</label><label class="life-range-line">强度<input type="range" min="0" max="100" name="moodScore" value="78"><b>78/100</b></label><div class="life-three-grid"><label>睡眠<input class="life-input" name="moodSleep" value="7.2"></label><label>压力<input class="life-input" type="number" min="0" max="100" name="moodPressure" value="35"></label><label>触发因素<input class="life-input" name="moodTriggers" value="阳光, 散步, 独处"></label></div><div class="life-add-chip-group"><span>身体信号</span><button type="button">精力充沛</button><button type="button">肩颈酸痛</button><button type="button">睡眠不足</button><button type="button">专注良好</button></div></section>' +
      '<section class="life-add-module-panel life-add-theme-purple is-hidden" data-add-module="关系"><div class="life-add-inline-title">' + addTypeIcon('关系') + '<strong>关系信息</strong><span>更新联系人互动、温度和下次提醒</span></div><div class="life-two-grid"><label>选择 / 搜索人物<input class="life-input" name="relationshipName" value="张敏（大学同学）"></label><label>上次联系<input class="life-input" name="relationshipLast" value="2026-05-10（微信）"></label></div><label>最近聊到<input class="life-input" name="relationshipNote" value="聊到各自的工作近况和下次聚会时间。"></label><div class="life-two-grid"><label>下次联系提醒<input class="life-input" type="date" name="relationshipNextDate" value="2026-05-24"></label><label class="life-heart-line">关系温度<input type="range" min="0" max="100" name="relationshipScore" value="80"><span>4/5</span></label></div></section>' +
      '<section class="life-add-module-panel life-add-theme-rose is-hidden" data-add-module="愿望"><div class="life-add-inline-title">' + addTypeIcon('愿望') + '<strong>愿望信息</strong><span>记录想要程度和冷却计划</span></div><div class="life-three-grid"><label>愿望名称<input class="life-input" name="wishName" value="相机 Sony A7C II"></label><label>冷却期<input class="life-input" type="number" name="wishDays" value="21"></label><label>价格<input class="life-input" name="wishPrice" value="¥12,999"></label></div><label class="life-range-line">当前想要程度<input type="range" min="0" max="100" name="wishDesire" value="65"><b>65%</b></label><div class="life-add-radio-box"><label><input type="radio" name="wishStatus" value="愿望冷却中" checked> 继续冷却</label><label><input type="radio" name="wishStatus" value="可以决定"> 可以决定了</label></div><label>替代方案<input class="life-input" name="wishAlternatives" value="先用手机练习；租借体验；观望新品"></label></section>' +
      '<section class="life-add-module-panel life-add-theme-green is-hidden" data-add-module="健康"><div class="life-add-inline-title">' + addTypeIcon('健康') + '<strong>健康信息</strong><span>记录身体状态和后续提醒</span></div><div class="life-three-grid"><label>睡眠<input class="life-input" name="healthSleep" value="7.2 小时"></label><label>精力<input class="life-input" type="number" min="0" max="100" name="healthEnergy" value="80"></label><label>运动<input class="life-input" name="healthExercise" value="散步 40 分钟"></label></div><label>身体信号<input class="life-input" name="healthSignal" value="下午有点累，注意休息。"></label><label>后续提醒<input class="life-input" type="date" name="healthReminder" value="2026-05-15"></label></section>' +
      '<section class="life-add-module-panel life-add-theme-blue is-hidden" data-add-module="项目"><div class="life-add-inline-title">' + addTypeIcon('项目') + '<strong>项目信息</strong><span>更新进度和下一步</span></div><div class="life-two-grid"><label>项目 / 任务<input class="life-input" name="projectName" value="个人网站改版"></label><label class="life-range-line">进度<input type="range" min="0" max="100" name="projectProgress" value="60"><b>60%</b></label></div><label>当前阻碍<input class="life-input" name="projectBlocker" value="设计稿还未最终确定"></label><label>下一步行动<input class="life-input" name="projectNext" value="完成首页视觉稿"></label><div class="life-file-chip">' + iconHtml('file') + ' 首页设计稿 v2.fig</div></section>';
  }

  function renderDecisionOptionEditor() {
    var rows = [
      ['接受 Offer', '发展空间大，薪酬更高', '工作强度高，通勤长', '70'],
      ['暂不接受', '保持现状，生活稳定', '可能错过窗口', '40'],
      ['继续观望', '时间更充裕', '不确定性增加', '55']
    ];
    return '<section class="life-decision-option-editor"><div class="life-section-title"><h3>选项对比</h3><button class="life-mini-btn" type="button" data-add-action="add-decision-option">+ 新增选项</button></div><div class="life-decision-option-head"><span></span><span>选项</span><span>优点</span><span>顾虑</span><span>评分</span><span></span></div><div class="life-decision-option-list">' + rows.map(function(row, idx) { return renderDecisionOptionRow(row, idx); }).join('') + '</div></section>';
  }

  function renderDecisionOptionRow(row, idx) {
    var letter = String.fromCharCode(65 + idx);
    return '<div class="life-decision-option-row" data-option-index="' + idx + '"><strong class="life-decision-option-letter">' + letter + '.</strong><label><span>选项</span><input class="life-input" name="decisionOptionName" value="' + escapeHtml(row[0]) + '"></label><label><span>优点</span><input class="life-input" name="decisionOptionPros" value="' + escapeHtml(row[1]) + '"></label><label><span>顾虑</span><input class="life-input" name="decisionOptionCons" value="' + escapeHtml(row[2]) + '"></label><label><span>评分</span><input class="life-input" type="number" min="0" max="100" name="decisionOptionScore" value="' + escapeHtml(row[3]) + '"></label><button class="life-mini-btn danger" type="button" data-add-action="remove-decision-option">删除</button></div>';
  }

  function syncAddDecisionOptions(form) {
    var shell = form || document.getElementById('lifeAddForm');
    if (!shell) return;
    var rows = Array.prototype.slice.call(shell.querySelectorAll('.life-decision-option-row'));
    var select = shell.elements.decisionChoice;
    var previous = select ? select.value : '';
    rows.forEach(function(row, idx) {
      var letter = String.fromCharCode(65 + idx);
      row.setAttribute('data-option-index', idx);
      var letterNode = row.querySelector('.life-decision-option-letter');
      if (letterNode) letterNode.textContent = letter + '.';
    });
    if (!select) return;
    select.innerHTML = rows.map(function(row, idx) {
      var letter = String.fromCharCode(65 + idx);
      var name = row.querySelector('[name="decisionOptionName"]');
      var label = letter + '. ' + (name && name.value.trim() ? name.value.trim() : '未命名选项');
      return '<option value="' + escapeHtml(label) + '">' + escapeHtml(label) + '</option>';
    }).join('');
    if (previous && Array.prototype.some.call(select.options, function(option) { return option.value === previous; })) {
      select.value = previous;
    }
  }

  function addDecisionOptionRow(button) {
    var form = button.closest('#lifeAddForm');
    var list = form && form.querySelector('.life-decision-option-list');
    if (!list) return;
    var next = list.querySelectorAll('.life-decision-option-row').length;
    list.insertAdjacentHTML('beforeend', renderDecisionOptionRow(['新选项', '填写优点', '填写顾虑', '50'], next));
    syncAddDecisionOptions(form);
    updateAddPreview();
  }

  function removeDecisionOptionRow(button) {
    var form = button.closest('#lifeAddForm');
    var list = form && form.querySelector('.life-decision-option-list');
    if (!list) return;
    var rows = list.querySelectorAll('.life-decision-option-row');
    if (rows.length <= 1) {
      showToast('至少保留一个选项');
      return;
    }
    var row = button.closest('.life-decision-option-row');
    if (row) row.remove();
    syncAddDecisionOptions(form);
    updateAddPreview();
  }

  function renderAddTypePanel(type, idx) {
    var hidden = idx ? ' is-hidden' : '';
    var body = {
      '记忆': '<div class="life-two-grid"><label>记忆标题<input class="life-input" name="memoryTitle" value="今天在江边散步"></label><label>归档到<select class="life-select" name="memoryBucket"><option>时间河流（默认）</option><option>本月值得记住</option></select></label></div>',
      '决定': '<div class="life-two-grid"><label>决定标题<input class="life-input" name="decisionTitle" value="是否接受新的 Offer？"></label><label>我的倾向<select class="life-select" name="decisionChoice"><option>接受 Offer</option><option>暂不接受</option><option>继续观望</option></select></label></div><div class="life-two-grid"><label>信心 <input class="life-input" type="number" min="0" max="100" name="decisionConfidence" value="70"></label><label>复盘日期<input class="life-input" type="date" name="decisionReviewDate" value="2026-11-13"></label></div><label>关键风险 / 顾虑<input class="life-input" name="decisionRisks" value="适应期压力大；家庭时间可能减少。"></label>',
      '情绪': '<div class="life-three-grid"><label>心情评分<input class="life-input" type="number" min="0" max="100" name="moodScore" value="78"></label><label>睡眠<input class="life-input" name="moodSleep" value="7.2"></label><label>压力<input class="life-input" type="number" min="0" max="100" name="moodPressure" value="35"></label></div><label>触发因素<input class="life-input" name="moodTriggers" value="阳光, 散步, 独处"></label>',
      '关系': '<div class="life-two-grid"><label>人物<input class="life-input" name="relationshipName" value="张敏"></label><label>关系温度<input class="life-input" type="number" min="0" max="100" name="relationshipScore" value="80"></label></div><div class="life-two-grid"><label>上次联系<input class="life-input" name="relationshipLast" value="今天"></label><label>下次提醒<input class="life-input" type="date" name="relationshipNextDate" value="2026-05-24"></label></div><label>最近聊到<input class="life-input" name="relationshipNote" value="聊到各自的工作近况和下次聚会时间。"></label>',
      '愿望': '<div class="life-three-grid"><label>愿望名称<input class="life-input" name="wishName" value="相机 Sony A7C II"></label><label>冷却期<input class="life-input" type="number" min="0" name="wishDays" value="21"></label><label>价格<input class="life-input" name="wishPrice" value="¥12,999"></label></div><div class="life-two-grid"><label>当前想要程度<input class="life-input" type="number" min="0" max="100" name="wishDesire" value="65"></label><label>状态<select class="life-select" name="wishStatus"><option>愿望冷却中</option><option>可以决定</option></select></label></div><label>替代方案<input class="life-input" name="wishAlternatives" value="先租手机练习；租借体验；观望新品"></label>',
      '健康': '<div class="life-three-grid"><label>睡眠<input class="life-input" name="healthSleep" value="7.2 小时"></label><label>精力<input class="life-input" type="number" min="0" max="100" name="healthEnergy" value="80"></label><label>运动<input class="life-input" name="healthExercise" value="散步 40 分钟"></label></div><label>身体信号<input class="life-input" name="healthSignal" value="下午有点累，注意休息。"></label><label>后续提醒<input class="life-input" type="date" name="healthReminder" value="2026-05-15"></label>',
      '项目': '<div class="life-two-grid"><label>项目 / 任务<input class="life-input" name="projectName" value="个人网站改版"></label><label>进度<input class="life-input" type="number" min="0" max="100" name="projectProgress" value="60"></label></div><label>当前阻碍<input class="life-input" name="projectBlocker" value="设计稿还未最终确定"></label><label>下一步行动<input class="life-input" name="projectNext" value="完成首页视觉稿"></label>'
    }[type];
    return '<section class="life-add-module-panel' + hidden + '" data-add-panel="' + type + '"><div class="life-section-title"><h3>' + type + '子组件</h3><span>保存时同步写入对应模块</span></div>' + body + '</section>';
  }

  function renderAddAside() {
    return '<section class="life-detail-card life-add-preview-panel"><h2 class="life-detail-title">预览</h2><p class="life-panel-sub">在时间河流中的样子</p><div id="lifeAddPreview" style="margin-top:14px"></div></section>' +
      '<section class="life-detail-card life-association-card"><h2 class="life-detail-title">智能关联建议</h2><div class="life-association-list" id="lifeAssociationList"></div></section>' +
      '<section class="life-detail-card life-add-tip"><h2 class="life-detail-title">小贴士</h2><p class="life-card-copy">关联后可以在时间轴、情绪天气站、关系温度等页面中快速找到这一刻。</p></section>';
  }

  function updateAddTypePanels(type) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-add-module]'), function(panel) {
      var isActive = panel.getAttribute('data-add-module') === type;
      panel.classList.toggle('is-active', isActive);
      panel.classList.toggle('is-hidden', !isActive);
    });
  }

  function setAddType(type) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-add-type]'), function(btn) {
      btn.classList.toggle('active', btn.getAttribute('data-add-type') === type);
    });
    updateAddTypePanels(type);
    if (type === '决定') syncAddDecisionOptions(document.getElementById('lifeAddForm'));
    updateAddPreview();
  }

  function addAssociationSuggestions(type) {
    var map = {
      '记忆': [['情绪天气站', '今日心情记录'], ['关系温度', '与 Emma 的互动'], ['决策档案馆', '咖啡馆选择记录']],
      '决定': [['时间河流', '生成一条决定记录'], ['愿望冷却箱', '关联相机愿望'], ['复盘与回顾', '创建复盘提醒']],
      '情绪': [['情绪天气站', '写入今日心情'], ['健康轨迹', '关联睡眠和压力'], ['时间河流', '同步为生活片段']],
      '关系': [['关系温度', '更新联系人档案'], ['本月值得记住', '收录共同记忆'], ['时间河流', '生成互动记录']],
      '愿望': [['愿望冷却箱', '创建冷却愿望'], ['决策档案馆', '关联后续决定'], ['时间河流', '记录愿望来源']],
      '健康': [['健康轨迹', '写入身体信号'], ['情绪天气站', '关联睡眠压力'], ['时间河流', '生成健康记录']],
      '项目': [['项目与目标', '更新项目进展'], ['资源库', '归档附件'], ['时间河流', '生成项目记录']]
    };
    return map[type] || map['记忆'];
  }

  function updateAddPreview() {
    var preview = document.getElementById('lifeAddPreview');
    var form = document.getElementById('lifeAddForm');
    if (!preview || !form) return;
    var type = currentAddType(form);
    var body = addValue(form, 'body', '记录这一刻的想法、经历或感受...');
    var location = addValue(form, 'location', '未选择地点');
    var people = addPeople(form);
    var mood = addSelectedMood(form);
    var dateParts = addDateParts(form);
    var title = addTitleForType(type, form);
    var countNode = form.querySelector('[data-add-count]');
    var associationList = document.getElementById('lifeAssociationList');
    if (countNode) countNode.textContent = body.length + ' / 2000';
    if (associationList) {
      associationList.innerHTML = addAssociationSuggestions(type).map(function(item, idx) {
        return '<div class="life-association-row"><span>可能相关联到</span><strong>' + item[0] + ' - ' + item[1] + '</strong><button class="life-mini-btn ' + (idx === 0 ? 'active' : '') + '" type="button" data-add-association="' + item[0] + '">关联</button></div>';
      }).join('');
    }
    preview.innerHTML = '<article class="life-add-preview-card"><div class="life-add-preview-head"><span>今日</span><strong>' + escapeHtml(dateParts.time) + '</strong><i>' + iconHtml(iconForType(type)) + '</i></div><div class="life-add-preview-main"><span class="life-badge">' + escapeHtml(type) + '</span><h3>' + escapeHtml(title) + '</h3><p>' + escapeHtml(body) + '</p><div class="life-add-preview-photos"><span class="life-photo photo-river"></span><span class="life-photo photo-cafe"></span><span class="life-photo photo-night"></span><span class="life-photo photo-book"></span></div><div class="life-add-preview-meta"><span>' + iconHtml('location') + escapeHtml(location) + '</span><span>' + iconHtml(moodIcons[mood]) + escapeHtml(mood) + '</span>' + (people.length ? '<span>' + iconHtml('people') + people.length + '</span>' : '') + '</div></div></article>';
  }

  function saveMomentFromForm(form) {
    var body = addValue(form, 'body', '');
    if (!body) {
      showToast('请先写下这一刻发生了什么');
      return;
    }
    var type = currentAddType(form);
    var dateParts = addDateParts(form);
    var tags = addTags(form);
    var people = addPeople(form);
    var mood = addSelectedMood(form);
    var stored = getStoredMoments();
    var moment = {
      id: 'local-' + Date.now(),
      type: type,
      icon: '☀',
      time: dateParts.time,
      date: '今天 ' + dateParts.date.slice(5),
      title: addTitleForType(type, form),
      copy: body,
      location: addValue(form, 'location', '未选择地点'),
      people: people,
      mood: mood,
      photos: ['photo-river', 'photo-cafe', 'photo-night', 'photo-book'],
      tags: (tags.length ? tags : ['日常']).concat([type]),
      linkedModules: addSelectedAssociations()
    };
    stored.unshift(moment);
    saveStoredMoments(stored);
    saveAddModuleRecord(type, form, moment, dateParts);
    state.selectedMomentId = moment.id;
    state.view = 'timeline';
    showToast('已保存，并同步到' + type + '模块');
    render();
  }

  function saveAddModuleRecord(type, form, moment, dateParts) {
    if (type === '决定') saveAddDecision(form, moment, dateParts);
    if (type === '情绪') saveAddMood(form, moment, dateParts);
    if (type === '关系') saveAddRelationship(form, moment);
    if (type === '愿望') saveAddWish(form, moment, dateParts);
    if (type === '健康') saveAddHealth(form, moment);
    if (type === '项目') saveAddProject(form, moment);
  }

  function saveAddDecision(form, moment, dateParts) {
    var stored = getStoredDecisions();
    stored.unshift({
      id: 'd-local-' + Date.now(),
      status: '待复盘',
      title: addValue(form, 'decisionTitle', moment.title),
      date: dateParts.date,
      category: '生活决策',
      choice: addValue(form, 'decisionChoice', '继续观察'),
      confidence: Number(addValue(form, 'decisionConfidence', '70')),
      background: moment.copy,
      reason: splitLines(moment.copy, [moment.copy]),
      risks: splitLines(addValue(form, 'decisionRisks', ''), []),
      options: [
        [addValue(form, 'decisionChoice', '接受'), '当前倾向', moment.location, '待评估', '信心 ' + addValue(form, 'decisionConfidence', '70') + '/100'],
        ['暂缓', '继续观察', moment.location, '机会成本', '信息更充分']
      ],
      reviewDate: addValue(form, 'decisionReviewDate', '2026-11-13'),
      result: '由“添加一刻”创建，等待后续复盘。'
    });
    saveStoredDecisions(stored);
    state.selectedDecisionId = stored[0].id;
  }

  function saveAddMood(form, moment, dateParts) {
    var store = getMoodStore();
    var score = Number(addValue(form, 'moodScore', '78'));
    store.added.unshift({
      id: 'mood-local-' + Date.now(),
      year: 2026,
      month: 4,
      day: dateParts.day,
      date: dateParts.date,
      time: dateParts.time,
      score: score,
      weather: addSelectedMood(form),
      sleep: Number(addValue(form, 'moodSleep', '7.2')),
      pressure: Number(addValue(form, 'moodPressure', '35')),
      energy: Number(addValue(form, 'healthEnergy', String(Math.min(100, score + 2)))),
      feeling: addSelectedMood(form),
      note: moment.copy,
      tags: splitLines(addValue(form, 'moodTriggers', '').replace(/,/g, '\n'), ['日常'])
    });
    saveMoodStore(store);
  }

  function saveAddRelationship(form, moment) {
    var name = addValue(form, 'relationshipName', (moment.people[0] || '未命名联系人'));
    var current = allRelationships().filter(function(item) { return item.name === name; })[0];
    var note = addValue(form, 'relationshipNote', moment.copy);
    var next = normalizeRelationship(Object.assign({}, current || {}, {
      id: current ? current.id : 'r-local-' + Date.now(),
      name: name,
      role: current ? current.role : '重要的人',
      group: current ? current.group : '朋友',
      last: addValue(form, 'relationshipLast', '今天'),
      channel: '微信',
      score: Number(addValue(form, 'relationshipScore', '80')),
      next: '待提醒',
      nextDate: addValue(form, 'relationshipNextDate', '2026-05-24'),
      notes: [note].concat(current && current.notes ? current.notes : []),
      memories: current ? current.memories : [{ text: moment.title, image: '' }]
    }));
    var store = getRelationshipStore();
    var seedExists = withMockData(relationships, mockRelationships).some(function(seed) { return seed.id === next.id; });
    if (seedExists) store.edits[next.id] = next;
    else {
      store.added = (store.added || []).filter(function(item) { return item.id !== next.id; });
      store.added.unshift(next);
    }
    saveRelationshipStore(store);
    state.selectedRelationshipId = next.id;
  }

  function saveAddWish(form, moment, dateParts) {
    var store = getWishStore();
    var days = Number(addValue(form, 'wishDays', '21'));
    var item = normalizeWish({
      id: 'w-local-' + Date.now(),
      status: addValue(form, 'wishStatus', '愿望冷却中'),
      category: '生活',
      name: addValue(form, 'wishName', moment.title),
      reason: moment.copy,
      days: days,
      due: addDateDays(dateParts.date, days),
      desire: Number(addValue(form, 'wishDesire', '65')),
      price: addValue(form, 'wishPrice', '待定'),
      alternatives: splitLines(addValue(form, 'wishAlternatives', '').replace(/；/g, '\n'), []),
      plan: ['冷却期结束前再确认真实需求'],
      photo: 'photo-camera',
      addedAt: dateParts.date,
      coolStart: dateParts.date
    });
    store.added.unshift(item);
    saveWishStore(store);
    state.selectedWishId = item.id;
  }

  function saveAddHealth(form, moment) {
    var stored = getSimpleStore(healthStorageKey());
    stored.unshift({
      name: addValue(form, 'healthSignal', '身体状态记录'),
      value: addValue(form, 'healthSleep', '7.2 小时') + ' · 精力 ' + addValue(form, 'healthEnergy', '80') + '/100',
      note: moment.copy + ' 运动：' + addValue(form, 'healthExercise', '散步 40 分钟') + '。提醒：' + addValue(form, 'healthReminder', '2026-05-15') + '。'
    });
    saveSimpleStore(healthStorageKey(), stored);
  }

  function saveAddProject(form, moment) {
    var stored = getSimpleStore(projectStorageKey());
    stored.unshift({
      name: addValue(form, 'projectName', moment.title),
      progress: Number(addValue(form, 'projectProgress', '60')),
      status: addValue(form, 'projectBlocker', '暂无阻碍'),
      next: addValue(form, 'projectNext', '继续推进'),
      people: moment.people.length ? '协作：' + moment.people.join('、') : '个人项目'
    });
    saveSimpleStore(projectStorageKey(), stored);
  }

  function accountStatusPanel() {
    var session = accountSession();
    if (!session) {
      return '<section class="life-account-empty"><div><h3>登录后启用个人档案</h3><p>生活航迹账号与旅游记账、续费雷达完全独立。登录后可管理资料、密码、安全状态和账号生命周期。</p></div><button class="life-primary-btn" type="button" data-account-action="login">去登录</button></section>';
    }
    var lifecycleCount = (session.lifecycle || []).length;
    var lastLifecycle = (session.lifecycle || [])[lifecycleCount - 1];
    return '<section class="life-account-card"><div class="life-account-head">' +
      relationshipAvatarHtml({ avatar: accountAvatarKey(session) }, 'large') +
      '<div><span>当前账号 · ' + accountRoleText(session) + '</span><h3>' + escapeHtml(session.name) + '</h3><p>' + escapeHtml(session.email) + '</p></div><em>active</em></div>' +
      '<form id="lifeAccountForm" class="life-account-form"><div class="life-two-grid"><label>昵称<input class="life-input" name="name" value="' + escapeHtml(session.name) + '"></label><label>邮箱<input class="life-input" name="email" value="' + escapeHtml(session.email) + '"></label></div>' +
      '<div class="life-avatar-picker">' + ['Q1','Q2','Q3','Q4','Q5','Q6'].map(function(item) {
        var key = item.toLowerCase();
        return '<label class="' + (accountAvatarKey(session) === key ? 'active' : '') + '"><input type="radio" name="avatar" value="' + item + '" ' + (accountAvatarKey(session) === key ? 'checked' : '') + '>' + relationshipAvatarHtml({ avatar: key }, '') + '<em>' + item + '</em></label>';
      }).join('') + '</div>' +
      '<label class="life-account-toggle"><input type="checkbox" name="reminder" ' + (session.preferences && session.preferences.reminder ? 'checked' : '') + '> 开启重要复盘提醒</label>' +
      '<div class="life-account-actions"><button class="life-secondary-btn" type="button" data-account-action="logout">退出登录</button><button class="life-primary-btn" type="submit">保存资料</button></div></form>' +
      '<div class="life-account-log-summary"><span>操作日志</span><strong>' + lifecycleCount + ' 条</strong><small>最近：' + escapeHtml(lastLifecycle ? lastLifecycle.date : '暂无') + '</small></div></section>' + accountAdminPanel(session);
  }

  function accountAdminPanel(session) {
    if (!lifeAccount() || !session || session.role !== 'admin') return '';
    var accounts = lifeAccount().listAccounts();
    var userCount = accounts.filter(function(account) { return account.role !== 'admin'; }).length;
    var adminCount = accounts.filter(function(account) { return account.role === 'admin'; }).length;
    var createForm = state.accountAdminCreateOpen ? '<form id="lifeAccountAdminCreateForm" class="life-account-admin-create">' +
      '<label>昵称<input class="life-input" name="name" placeholder="例如 Alex" required></label>' +
      '<label>邮箱<input class="life-input" type="email" name="email" placeholder="user@example.com" required></label>' +
      '<label>初始密码<input class="life-input" type="password" name="password" placeholder="至少 6 位" required></label>' +
      '<label>角色<select class="life-input" name="role"><option value="user">普通用户</option><option value="admin">管理员</option></select></label>' +
      '<div class="life-account-admin-actions"><button class="life-secondary-btn" type="button" data-account-action="admin-create-cancel">取消</button><button class="life-primary-btn" type="submit">创建账号</button></div>' +
      '</form>' : '';
    return '<section id="lifeAccountAdminPanel" class="life-account-card life-account-admin-panel"><div class="life-account-admin-head"><div><span>管理员入口</span><h3>账号管理</h3><p>创建普通用户或管理员，删除不再使用的账号。当前账号不能在这里删除。</p></div><button class="life-primary-btn" type="button" data-account-action="admin-create-toggle">' + (state.accountAdminCreateOpen ? '收起创建' : '+ 创建账号') + '</button></div>' +
      '<div class="life-account-admin-kpis"><div><span>全部账号</span><strong>' + accounts.length + '</strong></div><div><span>管理员</span><strong>' + adminCount + '</strong></div><div><span>普通用户</span><strong>' + userCount + '</strong></div></div>' +
      createForm +
      '<div class="life-account-admin-list">' + accounts.map(function(account) {
        var self = account.id === session.accountId;
        return '<article class="life-account-admin-row"><div>' + relationshipAvatarHtml({ avatar: accountAvatarKey(account) }, '') + '<span><strong>' + escapeHtml(account.name) + '</strong><small>' + escapeHtml(account.email) + ' · ' + accountRoleText(account) + ' · ' + escapeHtml(account.status || 'active') + '</small></span></div><button type="button" data-account-action="admin-delete" data-account-id="' + escapeHtml(account.id) + '" ' + (self ? 'disabled' : '') + '>' + (self ? '当前账号' : '删除') + '</button></article>';
      }).join('') + '</div></section>';
  }

  function accountSecurityPanel() {
    var session = accountSession();
    if (!session) return '<section class="life-detail-card"><h2 class="life-detail-title">账号生命周期</h2><p class="life-card-copy">注册、登录、资料维护、重置密码、停用和删除均由生活航迹独立管理。</p></section>';
    var adminEntry = session.role === 'admin' ? '<section class="life-detail-card life-account-side life-account-admin-entry"><h2 class="life-detail-title">账号管理</h2><p class="life-card-copy">你当前是管理员，可创建普通用户或管理员账号，也可删除其他账号。</p><a class="life-primary-btn" href="#lifeAccountAdminPanel">打开账号管理</a></section>' : '';
    return adminEntry + '<section class="life-detail-card life-account-side"><h2 class="life-detail-title">账号安全</h2><form id="lifeAccountPasswordForm" class="life-account-password-form"><label>当前密码<input class="life-input" type="password" name="currentPassword" placeholder="当前密码"></label><label>新密码<input class="life-input" type="password" name="nextPassword" placeholder="至少 6 位"></label><button class="life-primary-btn" type="submit">修改密码</button></form></section>' +
      '<section class="life-detail-card life-account-side"><h2 class="life-detail-title">生命周期操作</h2><p class="life-card-copy">停用会退出登录；删除会从本机可登录账号中移除。</p><div class="life-account-danger"><button type="button" data-account-action="deactivate">停用账号</button><button type="button" data-account-action="delete">删除账号</button></div></section>';
  }

  function saveAccountProfile(form) {
    if (!lifeAccount()) return;
    var selected = form.querySelector('input[name="avatar"]:checked');
    try {
      lifeAccount().updateProfile({
        name: form.elements.name.value,
        email: form.elements.email.value,
        avatar: selected ? selected.value : 'Q1',
        preferences: { reminder: !!form.elements.reminder.checked }
      });
      showToast('账号资料已保存');
      render();
    } catch (err) {
      showToast(err.message || '保存失败');
    }
  }

  function saveAccountPassword(form) {
    if (!lifeAccount()) return;
    try {
      lifeAccount().changePassword(form.elements.currentPassword.value, form.elements.nextPassword.value);
      showToast('密码已修改');
      render();
    } catch (err) {
      showToast(err.message || '修改失败');
    }
  }

  function saveAdminAccount(form) {
    if (!lifeAccount()) return;
    try {
      lifeAccount().adminCreateAccount({
        name: form.elements.name.value,
        email: form.elements.email.value,
        password: form.elements.password.value,
        role: form.elements.role.value,
        adminCode: 'LIFE-ADMIN',
        avatar: form.elements.role.value === 'admin' ? 'Q1' : 'Q2'
      });
      state.accountAdminCreateOpen = false;
      showToast('账号已创建');
      render();
    } catch (err) {
      showToast(err.message || '创建失败');
    }
  }

  function handleAccountAction(action, actionBtn) {
    if (action === 'profile') {
      if (!accountSession()) window.location.href = 'login.html';
      else setView('profile');
      return;
    }
    if (action === 'login') {
      window.location.href = 'login.html';
      return;
    }
    if (!lifeAccount()) return;
    if (action === 'logout') {
      lifeAccount().signOut();
      showToast('已退出登录');
      render();
      return;
    }
    if (action === 'admin-create-toggle') {
      state.accountAdminCreateOpen = !state.accountAdminCreateOpen;
      render();
      return;
    }
    if (action === 'admin-create-cancel') {
      state.accountAdminCreateOpen = false;
      render();
      return;
    }
    if (action === 'admin-delete') {
      var target = actionBtn && actionBtn.getAttribute('data-account-id');
      if (!target) return;
      if (!window.confirm('确认删除这个账号？删除后该账号无法再登录。')) return;
      try {
        lifeAccount().adminDeleteAccount(target);
        showToast('账号已删除');
        render();
      } catch (err) {
        showToast(err.message || '删除失败');
      }
      return;
    }
    if (action === 'deactivate') {
      if (!window.confirm('确认停用当前账号？停用后会退出登录。')) return;
      lifeAccount().deactivateAccount();
      showToast('账号已停用');
      render();
      return;
    }
    if (action === 'delete') {
      if (!window.confirm('确认删除当前账号？此操作会退出登录，并从可登录账号中移除。')) return;
      lifeAccount().deleteAccount();
      showToast('账号已删除');
      render();
    }
  }

  function renderSimpleView(kind) {
    var simpleProjects = allProjects();
    var simpleHealth = allHealth();
    var simpleDecisions = allDecisions();
    var simpleResources = allResources();
    var config = {
      projects: ['项目与目标', simpleProjects.map(function(item) { return '<article class="life-row"><div class="life-row-head"><h3 class="life-row-title">' + item.name + '</h3><span class="life-badge blue">' + item.progress + '%</span></div><p class="life-card-copy">当前阻碍：' + item.status + '</p>' + progress(item.progress, 'var(--life-blue)') + '<p class="life-card-copy">下一步：' + item.next + ' · ' + item.people + '</p></article>'; }).join('')],
      health: ['健康与身体', simpleHealth.map(function(item) { return '<article class="life-row"><div class="life-row-head"><h3 class="life-row-title">' + item.name + '</h3><strong>' + item.value + '</strong></div><p class="life-card-copy">' + item.note + '</p></article>'; }).join('')],
      review: ['复盘与回顾', simpleDecisions.map(function(item) { return '<article class="life-row"><div class="life-row-head"><h3 class="life-row-title">' + item.title + '</h3><span class="life-badge amber">' + item.reviewDate + '</span></div><p class="life-card-copy">' + item.result + '</p></article>'; }).join('')],
      resources: ['资源库', simpleResources.map(function(item) { return '<article class="life-row"><div class="life-row-head"><div><h3 class="life-row-title">' + item.name + ' · ' + item.value + '</h3><p class="life-card-copy">' + item.meta + '</p></div><button class="life-mini-btn">查看</button></div></article>'; }).join('')],
      profile: ['个人档案', '<div class="life-wide-grid">' + [['记录总数','628 条'],['走过天数','9,862 天'],['城市','28 个'],['关系联系人','23 位'],['愿望完成','12 个'],['月度回顾','18 份']].map(function(item) { return '<div class="life-kpi"><span>' + item[0] + '</span><strong>' + item[1] + '</strong></div>'; }).join('') + '</div>' + accountStatusPanel()]
    }[kind];
    els.content.innerHTML = mockNotice() + '<section class="life-panel"><div class="life-panel-head"><div><h2 class="life-panel-title">' + config[0] + '</h2><p class="life-panel-sub">精简视图，保持与主应用一致的记录结构。</p></div><button class="life-secondary-btn">筛选</button></div><div class="life-list">' + config[1] + '</div></section>';
    els.aside.innerHTML = kind === 'profile' ? accountSecurityPanel() : '<section class="life-detail-card"><h2 class="life-detail-title">关联洞察</h2><p class="life-card-copy">这些内容会被时间河流、月度回顾和个人档案统一引用，避免记录散落在不同页面里。</p></section><section class="life-detail-card"><h2 class="life-detail-title">本周关注</h2><div class="life-chip-row"><span class="life-chip active">睡眠质量</span><span class="life-chip">专注力</span><span class="life-chip">情绪稳定</span></div></section>';
  }

  function render() {
    updateChrome();
    if (state.view === 'timeline') renderTimeline();
    else if (state.view === 'life-axis') renderLifeAxis();
    else if (state.view === 'decisions') renderDecisions();
    else if (state.view === 'mood') renderMood();
    else if (state.view === 'relationships') renderRelationships();
    else if (state.view === 'wishes') renderWishes();
    else if (state.view === 'monthly') renderMonthly();
    else if (state.view === 'add') renderAdd();
    else renderSimpleView(state.view);
  }

  document.addEventListener('click', function(event) {
    var accountAction = event.target.closest('[data-account-action]');
    if (accountAction) {
      handleAccountAction(accountAction.getAttribute('data-account-action'), accountAction);
      return;
    }
    if (event.target.closest('#mockModeBtn')) {
      var url = new URL(window.location.href);
      if (mockMode) {
        url.searchParams.delete('mock');
      } else {
        url.searchParams.set('mock', '1');
      }
      window.location.href = url.toString();
      return;
    }
    var nav = event.target.closest('[data-view]');
    if (nav) {
      setView(nav.getAttribute('data-view'));
      return;
    }
    var action = event.target.closest('[data-action]');
    if (action) {
      var actionName = action.getAttribute('data-action');
      if (actionName === 'go-add') {
        if (state.view === 'life-axis') addAxisMilestone();
        else if (state.view === 'decisions') addDecision();
        else if (state.view === 'mood') startMoodCreate();
        else if (state.view === 'wishes') startWishCreate();
        else setView('add');
      }
      if (actionName === 'view-decisions') setView('decisions');
      if (actionName === 'view-monthly') setView('monthly');
      if (actionName === 'back-timeline') setView('timeline');
      if (actionName === 'preview-add') updateAddPreview();
      if (actionName === 'link-suggestion') showToast('已关联到当前记录草稿');
      return;
    }
    var monthlyAction = event.target.closest('[data-monthly-action]');
    if (monthlyAction) {
      handleMonthlyAction(monthlyAction.getAttribute('data-monthly-action'));
      return;
    }
    var axisAction = event.target.closest('[data-axis-action]');
    if (axisAction) {
      var axisActionName = axisAction.getAttribute('data-axis-action');
      if (axisActionName === 'toggle-filter') {
        state.axisFilterOpen = !state.axisFilterOpen;
        renderLifeAxis();
      }
      if (axisActionName === 'clear-filter') {
        state.axisCategory = '全部';
        state.axisYear = '全部';
        state.axisStage = '全部';
        state.query = '';
        if (els.search) els.search.value = '';
        renderLifeAxis();
      }
      if (axisActionName === 'add-near') {
        var nearId = axisAction.closest('[data-axis-id]');
        var near = axisMilestones().filter(function(item) { return nearId && item.id === nearId.getAttribute('data-axis-id'); })[0];
        addAxisMilestone(near);
      }
      if (axisActionName === 'edit') {
        state.axisEditing = true;
        renderLifeAxis();
      }
      if (axisActionName === 'cancel-edit') {
        state.axisEditing = false;
        renderLifeAxis();
      }
      if (axisActionName === 'delete') deleteSelectedAxis();
      if (axisActionName === 'more') showToast('更多操作已展开：编辑、删除、关联决定');
      return;
    }
    var axisCategory = event.target.closest('[data-axis-category]');
    if (axisCategory) {
      state.axisCategory = axisCategory.getAttribute('data-axis-category');
      state.axisEditing = false;
      renderLifeAxis();
      return;
    }
    var axisYear = event.target.closest('[data-axis-year]');
    if (axisYear) {
      state.axisYear = axisYear.getAttribute('data-axis-year');
      state.axisStage = '全部';
      state.axisEditing = false;
      renderLifeAxis();
      return;
    }
    var axisStage = event.target.closest('[data-axis-stage]');
    if (axisStage) {
      var stage = axisStage.getAttribute('data-axis-stage');
      state.axisStage = state.axisStage === stage ? '全部' : stage;
      state.axisYear = '全部';
      state.axisEditing = false;
      renderLifeAxis();
      return;
    }
    var timelineFilter = event.target.closest('[data-timeline-filter]');
    if (timelineFilter) {
      state.timelineFilter = timelineFilter.getAttribute('data-timeline-filter');
      renderTimeline();
      return;
    }
    var decisionFilter = event.target.closest('[data-decision-filter]');
    if (decisionFilter) {
      state.decisionFilter = decisionFilter.getAttribute('data-decision-filter');
      state.decisionFormMode = null;
      state.decisionMoreOpen = false;
      renderDecisions();
      return;
    }
    var moodTab = event.target.closest('[data-mood-tab]');
    if (moodTab) {
      state.moodTab = moodTab.getAttribute('data-mood-tab');
      state.moodFormMode = null;
      renderMood();
      return;
    }
    var moodDate = event.target.closest('[data-mood-date]');
    if (moodDate) {
      var parsedMoodDate = parseMoodDate(moodDate.getAttribute('data-mood-date'));
      state.moodYear = parsedMoodDate.year;
      state.moodMonth = parsedMoodDate.month;
      state.selectedMoodDay = parsedMoodDate.day;
      state.moodFormMode = null;
      state.moodEditingId = '';
      state.moodRangeMenu = null;
      renderMood();
      return;
    }
    var moodDay = event.target.closest('[data-mood-day]');
    if (moodDay) {
      state.selectedMoodDay = Number(moodDay.getAttribute('data-mood-day'));
      state.moodFormMode = null;
      state.moodEditingId = '';
      state.moodRangeMenu = null;
      renderMood();
      return;
    }
    var moodRange = event.target.closest('[data-mood-range]');
    if (moodRange) {
      var rangeName = moodRange.getAttribute('data-mood-range');
      state.moodRangeMenu = state.moodRangeMenu === rangeName ? null : rangeName;
      renderMood();
      return;
    }
    var moodRangeOption = event.target.closest('[data-mood-range-option]');
    if (moodRangeOption) {
      var rangeParts = moodRangeOption.getAttribute('data-mood-range-option').split(':');
      if (rangeParts[0] === 'trend') state.moodRange = rangeParts[1];
      if (rangeParts[0] === 'sleep') state.moodSleepRange = rangeParts[1];
      if (rangeParts[0] === 'trigger') state.moodTriggerRange = rangeParts[1];
      if (rangeParts[0] === 'week') state.moodWeekRange = rangeParts[1];
      state.moodRangeMenu = null;
      renderMood();
      return;
    }
    var moodAction = event.target.closest('[data-mood-action]');
    if (moodAction) {
      var moodActionName = moodAction.getAttribute('data-mood-action');
      state.moodRangeMenu = null;
      if (moodActionName === 'today') {
        state.moodYear = 2026;
        state.moodMonth = 4;
        state.selectedMoodDay = 13;
      }
      if (moodActionName === 'prev-month') {
        state.moodMonth -= 1;
        if (state.moodMonth < 0) {
          state.moodMonth = 11;
          state.moodYear -= 1;
        }
        state.selectedMoodDay = Math.min(state.selectedMoodDay, new Date(state.moodYear, state.moodMonth + 1, 0).getDate());
      }
      if (moodActionName === 'next-month') {
        state.moodMonth += 1;
        if (state.moodMonth > 11) {
          state.moodMonth = 0;
          state.moodYear += 1;
        }
        state.selectedMoodDay = Math.min(state.selectedMoodDay, new Date(state.moodYear, state.moodMonth + 1, 0).getDate());
      }
      if (moodActionName === 'trigger') showToast('已筛选该触发因素的情绪记录');
      if (moodActionName === 'add-trigger') showToast('已添加一个触发因素占位');
      if (moodActionName === 'all-records') state.moodTab = 'calendar';
      if (moodActionName === 'more-body') state.moodTab = 'body';
      if (moodActionName === 'new-record') {
        startMoodCreate();
        return;
      }
      if (moodActionName === 'edit-record') {
        startMoodEdit();
        return;
      }
      if (moodActionName === 'delete-record') {
        deleteSelectedMoodRecord();
        return;
      }
      if (moodActionName === 'cancel-form') {
        cancelMoodForm();
        return;
      }
      renderMood();
      return;
    }
    var decisionAction = event.target.closest('[data-decision-action]');
    if (decisionAction) {
      var decisionActionName = decisionAction.getAttribute('data-decision-action');
      if (decisionActionName === 'bookmark') toggleDecisionBookmark();
      if (decisionActionName === 'more') {
        state.decisionMoreOpen = !state.decisionMoreOpen;
        renderDecisions();
      }
      if (decisionActionName === 'edit-decision') {
        state.decisionFormMode = 'edit';
        state.decisionMoreOpen = false;
        renderDecisions();
      }
      if (decisionActionName === 'move-cooling') setDecisionStatus('冷却中');
      if (decisionActionName === 'archive-decision') setDecisionStatus('已归档');
      if (decisionActionName === 'delete-decision') deleteSelectedDecision();
      if (decisionActionName === 'cancel-form') {
        state.decisionFormMode = null;
        state.decisionMoreOpen = false;
        renderDecisions();
      }
      if (decisionActionName === 'toggle-filter') showToast('可通过上方搜索框和标签筛选决定');
      if (decisionActionName === 'settings') showToast('决策列表设置已打开');
      if (decisionActionName === 'edit-result') startDecisionReview();
      if (decisionActionName === 'records') setView('timeline');
      if (decisionActionName === 'start-review') startDecisionReview();
      return;
    }
    var wishFilter = event.target.closest('[data-wish-filter]');
    if (wishFilter) {
      state.wishFilter = wishFilter.getAttribute('data-wish-filter');
      state.wishFormMode = null;
      renderWishes();
      return;
    }
    var wishCategory = event.target.closest('[data-wish-category]');
    if (wishCategory) {
      state.wishCategory = wishCategory.getAttribute('data-wish-category');
      state.wishFormMode = null;
      renderWishes();
      return;
    }
    var moment = event.target.closest('[data-moment-id]');
    if (moment) {
      openMomentTarget(
        moment.getAttribute('data-moment-id'),
        moment.getAttribute('data-moment-target'),
        moment.getAttribute('data-target-id')
      );
      return;
    }
    var axisItem = event.target.closest('[data-axis-id]');
    if (axisItem) {
      state.selectedAxisId = axisItem.getAttribute('data-axis-id');
      renderLifeAxis();
      return;
    }
    var decision = event.target.closest('[data-decision-id]');
    if (decision) {
      state.selectedDecisionId = decision.getAttribute('data-decision-id');
      state.view = 'decisions';
      render();
      return;
    }
    var relationship = event.target.closest('[data-relationship-id]');
    if (relationship) {
      state.selectedRelationshipId = relationship.getAttribute('data-relationship-id');
      state.relationshipFormMode = null;
      state.relationshipEditingId = '';
      renderRelationships();
      return;
    }
    var relationshipFilter = event.target.closest('[data-relationship-filter]');
    if (relationshipFilter) {
      state.relationshipFilter = relationshipFilter.getAttribute('data-relationship-filter');
      state.relationshipFormMode = null;
      renderRelationships();
      return;
    }
    var relationshipAvatarChoice = event.target.closest('[data-avatar-choice]');
    if (relationshipAvatarChoice) {
      activateRelationshipAvatarChoice(relationshipAvatarChoice);
      return;
    }
    var relationshipAction = event.target.closest('[data-relationship-action]');
    if (relationshipAction) {
      var relationshipActionName = relationshipAction.getAttribute('data-relationship-action');
      if (relationshipActionName === 'add') {
        state.relationshipInlineEditor = '';
        startRelationshipCreate();
      }
      if (relationshipActionName === 'edit') {
        state.relationshipInlineEditor = '';
        startRelationshipEdit();
      }
      if (relationshipActionName === 'delete') deleteSelectedRelationship();
      if (relationshipActionName === 'cancel-form') {
        state.relationshipFormMode = null;
        state.relationshipEditingId = '';
        renderRelationships();
      }
      if (relationshipActionName === 'sort') {
        state.relationshipSort = state.relationshipSort === '亲密度' ? '下次联系' : (state.relationshipSort === '下次联系' ? '最近联系' : '亲密度');
        renderRelationships();
      }
      if (relationshipActionName === 'filter') {
        state.relationshipFilter = state.relationshipFilter === '全部' ? '家人' : '全部';
        renderRelationships();
      }
      if (relationshipActionName === 'remind') remindRelationship();
      if (relationshipActionName === 'favorite') showToast('已标记为重要关系');
      if (relationshipActionName === 'add-date') openRelationshipInlineEditor('date');
      if (relationshipActionName === 'add-note') openRelationshipInlineEditor('note');
      if (relationshipActionName === 'view-notes') openRelationshipInlineEditor('notes');
      if (relationshipActionName === 'view-memories') openRelationshipInlineEditor('memory');
      if (relationshipActionName === 'view-gifts') openRelationshipInlineEditor('gift');
      if (relationshipActionName === 'view-places') openRelationshipInlineEditor('place');
      if (relationshipActionName === 'edit-memo') openRelationshipInlineEditor('memo');
      if (relationshipActionName === 'close-inline') closeRelationshipInlineEditor();
      if (relationshipActionName === 'add-media-item') addRelationshipMediaEditorRow(relationshipAction);
      if (relationshipActionName === 'delete-media-item') deleteRelationshipMediaEditorRow(relationshipAction);
      return;
    }
    var wish = event.target.closest('[data-wish-id]');
    if (wish) {
      state.selectedWishId = wish.getAttribute('data-wish-id');
      renderWishes();
      return;
    }
    var wishAction = event.target.closest('[data-wish-action]');
    if (wishAction) {
      var wishActionName = wishAction.getAttribute('data-wish-action');
      if (wishActionName === 'add') startWishCreate();
      if (wishActionName === 'edit') startWishEdit();
      if (wishActionName === 'delete') deleteSelectedWish();
      if (wishActionName === 'cancel-form') {
        state.wishFormMode = null;
        renderWishes();
      }
      if (wishActionName === 'sort') cycleWishSort();
      if (wishActionName === 'toggle-view') showToast('当前为列表视图，已按原型保留高密度展示');
      if (wishActionName === 'price-history') showToast('价格历史已在详情中展示');
      if (wishActionName === 'adjust-cooling') applyWishAction('extend');
      if (wishActionName === 'view-option') showToast('替代方案已加入对比清单');
      if (['extend', 'drop', 'decide', 'realize'].indexOf(wishActionName) >= 0) applyWishAction(wishActionName);
      return;
    }
    var wishPlan = event.target.closest('[data-wish-plan-index]');
    if (wishPlan) {
      toggleWishPlan(wishPlan);
      return;
    }
    var addAction = event.target.closest('[data-add-action]');
    if (addAction) {
      var addActionName = addAction.getAttribute('data-add-action');
      if (addActionName === 'add-decision-option') addDecisionOptionRow(addAction);
      if (addActionName === 'remove-decision-option') removeDecisionOptionRow(addAction);
      return;
    }
    var typeBtn = event.target.closest('[data-add-type]');
    if (typeBtn) {
      setAddType(typeBtn.getAttribute('data-add-type'));
      return;
    }
    var addAssociation = event.target.closest('[data-add-association]');
    if (addAssociation) {
      addAssociation.classList.toggle('active');
      showToast(addAssociation.classList.contains('active') ? '已加入关联' : '已取消关联');
      return;
    }
    var moodBtn = event.target.closest('[data-add-mood]');
    if (moodBtn) {
      Array.prototype.forEach.call(document.querySelectorAll('[data-add-mood]'), function(btn) { btn.classList.remove('active'); });
      moodBtn.classList.add('active');
      updateAddPreview();
    }
  });

  document.addEventListener('input', function(event) {
    if (event.target.matches('[data-form-confidence-range]')) {
      var formValue = Number(event.target.value || 0);
      var formShell = event.target.closest('.life-decision-form');
      var formValueNode = formShell && formShell.querySelector('[data-confidence-value]');
      if (formValueNode) formValueNode.textContent = formValue;
      return;
    }
    if (event.target.matches('[data-mood-score-range]')) {
      var moodValue = Number(event.target.value || 0);
      var moodForm = event.target.closest('.life-mood-form');
      var moodValueNode = moodForm && moodForm.querySelector('[data-mood-score-value]');
      if (moodValueNode) moodValueNode.textContent = moodValue;
      return;
    }
    if (event.target.matches('[data-relationship-score-range]')) {
      var relationshipValue = Number(event.target.value || 0);
      var relationshipForm = event.target.closest('.life-relationship-form');
      var relationshipValueNode = relationshipForm && relationshipForm.querySelector('[data-relationship-score-value]');
      if (relationshipValueNode) relationshipValueNode.textContent = relationshipValue;
      return;
    }
    if (event.target.matches('[data-wish-desire-range]')) {
      var wishValue = Number(event.target.value || 0);
      var wishForm = event.target.closest('.life-wish-form');
      var wishValueNode = wishForm && wishForm.querySelector('[data-wish-desire-value]');
      if (wishValueNode) wishValueNode.textContent = wishValue;
      return;
    }
    if (event.target === els.search || event.target.matches('[data-decision-search]')) {
      state.query = els.search.value;
      if (event.target.matches('[data-decision-search]')) state.query = event.target.value;
      render();
      if (event.target === els.search) els.search.focus();
      return;
    }
    if (event.target.matches('[data-relationship-media-image]')) {
      refreshRelationshipMediaRowPreview(event.target.closest('[data-relationship-media-row]'));
      return;
    }
    if (event.target.matches('[data-add-body-source]')) {
      Array.prototype.forEach.call(document.querySelectorAll('[data-add-body-source]'), function(node) {
        if (node !== event.target) node.value = event.target.value;
      });
    }
    if (event.target.closest('.life-decision-option-editor')) {
      syncAddDecisionOptions(event.target.closest('#lifeAddForm'));
    }
    if (event.target.closest('#lifeAddForm')) updateAddPreview();
  });

  document.addEventListener('change', function(event) {
    if (event.target.matches('[data-axis-image-upload]')) {
      var axisFile = event.target.files && event.target.files[0];
      var axisForm = event.target.closest('#lifeAxisEditForm');
      var axisHidden = axisForm && axisForm.querySelector('[data-axis-uploaded-photo]');
      var axisPreview = axisForm && axisForm.querySelector('[data-axis-upload-preview]');
      if (!axisFile || !axisHidden || typeof FileReader === 'undefined') return;
      var axisReader = new FileReader();
      axisReader.onload = function() {
        axisHidden.value = String(axisReader.result || '');
        if (axisPreview) axisPreview.innerHTML = axisPhotoHtml(axisHidden.value, '') + '<em>' + escapeHtml(axisFile.name) + '</em>';
      };
      axisReader.readAsDataURL(axisFile);
      return;
    }
    if (!event.target.matches('[data-relationship-editor-image-upload]')) return;
    var file = event.target.files && event.target.files[0];
    var row = event.target.closest('[data-relationship-media-row]');
    if (row) {
      var imageInput = row.querySelector('[data-relationship-media-image]');
      if (!file || !imageInput || typeof FileReader === 'undefined') return;
      var rowReader = new FileReader();
      rowReader.onload = function() {
        imageInput.value = String(rowReader.result || '');
        refreshRelationshipMediaRowPreview(row);
      };
      rowReader.readAsDataURL(file);
      return;
    }
    var form = event.target.closest('#lifeRelationshipInlineForm');
    var hidden = form && form.querySelector('[data-relationship-image-data]');
    var preview = form && form.querySelector('[data-relationship-upload-preview]');
    if (!file || !hidden || typeof FileReader === 'undefined') return;
    var reader = new FileReader();
    reader.onload = function() {
      hidden.value = String(reader.result || '');
      if (preview) preview.innerHTML = '<span class="life-media-thumb"><img src="' + escapeHtml(hidden.value) + '" alt=""></span><em>' + escapeHtml(file.name) + '</em>';
    };
    reader.readAsDataURL(file);
  });

  document.addEventListener('submit', function(event) {
    var accountForm = event.target.closest('#lifeAccountForm');
    if (accountForm) {
      event.preventDefault();
      saveAccountProfile(accountForm);
      return;
    }
    var accountPasswordForm = event.target.closest('#lifeAccountPasswordForm');
    if (accountPasswordForm) {
      event.preventDefault();
      saveAccountPassword(accountPasswordForm);
      return;
    }
    var accountAdminCreateForm = event.target.closest('#lifeAccountAdminCreateForm');
    if (accountAdminCreateForm) {
      event.preventDefault();
      saveAdminAccount(accountAdminCreateForm);
      return;
    }
    var axisForm = event.target.closest('#lifeAxisEditForm');
    if (axisForm) {
      event.preventDefault();
      saveAxisEdit(axisForm);
      return;
    }
    var decisionForm = event.target.closest('#lifeDecisionForm');
    if (decisionForm) {
      event.preventDefault();
      if (state.decisionFormMode === 'edit') saveDecisionEdit(decisionForm);
      else createDecisionFromForm(decisionForm);
      return;
    }
    var decisionReviewForm = event.target.closest('#lifeDecisionReviewForm');
    if (decisionReviewForm) {
      event.preventDefault();
      saveDecisionReview(decisionReviewForm);
      return;
    }
    var moodForm = event.target.closest('#lifeMoodForm');
    if (moodForm) {
      event.preventDefault();
      saveMoodForm(moodForm);
      return;
    }
    var relationshipForm = event.target.closest('#lifeRelationshipForm');
    if (relationshipForm) {
      event.preventDefault();
      saveRelationshipForm(relationshipForm);
      return;
    }
    var relationshipInlineForm = event.target.closest('#lifeRelationshipInlineForm');
    if (relationshipInlineForm) {
      event.preventDefault();
      saveRelationshipInlineForm(relationshipInlineForm);
      return;
    }
    var monthlyLetterForm = event.target.closest('#lifeMonthlyLetterForm');
    if (monthlyLetterForm) {
      event.preventDefault();
      saveMonthlyLetter(monthlyLetterForm);
      return;
    }
    var monthlyQuoteForm = event.target.closest('#lifeMonthlyQuoteForm');
    if (monthlyQuoteForm) {
      event.preventDefault();
      saveMonthlyQuote(monthlyQuoteForm);
      return;
    }
    var wishForm = event.target.closest('#lifeWishForm');
    if (wishForm) {
      event.preventDefault();
      saveWishForm(wishForm);
      return;
    }
    var form = event.target.closest('#lifeAddForm');
    if (!form) return;
    event.preventDefault();
    saveMomentFromForm(form);
  });

  hydrateStaticIcons(document);
  render();
})();
