/**
 * 状态机模块
 * 定义悬浮条的状态及视觉映射
 */

const STATES = {
  ONLINE: 'online',
  WARNING: 'warning',
  ERROR: 'error',
  OFFLINE: 'offline'
};

const STATE_CONFIG = {
  [STATES.ONLINE]: {
    icon: '📋',
    text: '在线',
    color: '#4CAF50',
    pulse: true
  },
  [STATES.WARNING]: {
    icon: '⚠️',
    text: '警告',
    color: '#FF9800',
    pulse: false
  },
  [STATES.ERROR]: {
    icon: '❌',
    text: '错误',
    color: '#F44336',
    pulse: false
  },
  [STATES.OFFLINE]: {
    icon: '📴',
    text: '离线',
    color: '#757575',
    pulse: false
  }
};

// 状态转换规则
const TRANSITIONS = {
  [STATES.ONLINE]: [STATES.WARNING, STATES.ERROR, STATES.OFFLINE],
  [STATES.WARNING]: [STATES.ONLINE, STATES.ERROR, STATES.OFFLINE],
  [STATES.ERROR]: [STATES.ONLINE, STATES.WARNING, STATES.OFFLINE],
  [STATES.OFFLINE]: [STATES.ONLINE, STATES.WARNING, STATES.ERROR]
};

class StateMachine {
  constructor() {
    this._currentState = STATES.OFFLINE;
    this._listeners = [];
  }

  get currentState() {
    return this._currentState;
  }

  get config() {
    return STATE_CONFIG[this._currentState];
  }

  transition(newState) {
    if (this._currentState === newState) return false;

    const allowed = TRANSITIONS[this._currentState];
    if (!allowed || !allowed.includes(newState)) {
      console.warn(`Invalid transition: ${this._currentState} -> ${newState}`);
      return false;
    }

    const oldState = this._currentState;
    this._currentState = newState;

    // 通知监听器
    this._listeners.forEach(fn => fn(newState, oldState));

    return true;
  }

  onStateChange(callback) {
    this._listeners.push(callback);
    return () => {
      this._listeners = this._listeners.filter(fn => fn !== callback);
    };
  }
}

// 导出到全局
window.StateMachine = StateMachine;
window.STATES = STATES;
window.STATE_CONFIG = STATE_CONFIG;
