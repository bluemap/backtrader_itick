"""
通知推送模块

支持飞书、微信等多种通知方式
"""

import json
import time
import requests
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import queue
from abc import ABC, abstractmethod

from ..strategies.base_strategy import TradeSignal


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    max_retries: int = 3
    retry_interval: int = 60
    timeout: int = 30


class NotificationProvider(ABC):
    """通知提供者基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知提供者
        
        Args:
            config: 配置参数
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.enabled = config.get('enabled', True)
    
    @abstractmethod
    def send_message(self, message: str, **kwargs) -> bool:
        """
        发送消息
        
        Args:
            message: 消息内容
            **kwargs: 额外参数
            
        Returns:
            bool: 是否发送成功
        """
        pass
    
    @abstractmethod
    def send_card_message(self, title: str, content: str, **kwargs) -> bool:
        """
        发送卡片消息
        
        Args:
            title: 标题
            content: 内容
            **kwargs: 额外参数
            
        Returns:
            bool: 是否发送成功
        """
        pass
    
    def format_signal_message(self, signal: TradeSignal) -> str:
        """
        格式化交易信号消息
        
        Args:
            signal: 交易信号
            
        Returns:
            str: 格式化后的消息
        """
        action_emoji = "🔥" if signal.action == "BUY" else "💧"
        confidence_stars = "⭐" * int(signal.confidence * 5)
        
        message = f"""
{action_emoji} {signal.action} 信号 {action_emoji}

📈 股票代码: {signal.symbol}
💰 价格: ${signal.price:.2f}
📊 策略: {signal.strategy}
⚡ 置信度: {confidence_stars} ({signal.confidence:.1%})
🕐 时间: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

🎯 止盈: ${signal.take_profit:.2f} (+{((signal.take_profit/signal.price-1)*100):.1f}%)
🛡️ 止损: ${signal.stop_loss:.2f} ({((signal.stop_loss/signal.price-1)*100):.1f}%)

📝 原因: {signal.reason}
        """.strip()
        
        return message


class FeishuNotifier(NotificationProvider):
    """飞书通知器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化飞书通知器
        
        Args:
            config: 飞书配置
        """
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        
        if not self.webhook_url:
            self.logger.warning("飞书 Webhook URL 未配置")
            self.enabled = False
    
    def send_message(self, message: str, **kwargs) -> bool:
        """发送文本消息"""
        if not self.enabled:
            return False
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        return self._send_request(payload)
    
    def send_card_message(self, title: str, content: str, **kwargs) -> bool:
        """发送卡片消息"""
        if not self.enabled:
            return False
        
        # 构建卡片消息
        card = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": content,
                        "tag": "lark_md"
                    }
                }
            ],
            "header": {
                "title": {
                    "content": title,
                    "tag": "plain_text"
                },
                "template": "blue"
            }
        }
        
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        return self._send_request(payload)
    
    def send_signal_notification(self, signal: TradeSignal) -> bool:
        """发送交易信号通知"""
        if not self.enabled:
            return False
        
        # 确定颜色主题
        template_color = "green" if signal.action == "BUY" else "red"
        action_emoji = "📈" if signal.action == "BUY" else "📉"
        
        # 构建卡片内容
        content = f"""
**{action_emoji} {signal.action} 信号详情**

**股票代码:** {signal.symbol}
**当前价格:** ${signal.price:.2f}
**策略名称:** {signal.strategy}
**信号置信度:** {signal.confidence:.1%}
**时间:** {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

**交易建议:**
- 止盈价格: ${signal.take_profit:.2f} (+{((signal.take_profit/signal.price-1)*100):.1f}%)
- 止损价格: ${signal.stop_loss:.2f} ({((signal.stop_loss/signal.price-1)*100):.1f}%)

**信号原因:** {signal.reason}
        """.strip()
        
        card = {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": content,
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "⚠️ 投资有风险，交易需谨慎。请根据个人风险承受能力谨慎决策。"
                        }
                    ]
                }
            ],
            "header": {
                "title": {
                    "content": f"🚨 量化交易信号 - {signal.action}",
                    "tag": "plain_text"
                },
                "template": template_color
            }
        }
        
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        return self._send_request(payload)
    
    def _send_request(self, payload: Dict[str, Any]) -> bool:
        """发送请求"""
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=self.config.get('timeout', 30)
            )
            
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                self.logger.debug("飞书消息发送成功")
                return True
            else:
                self.logger.error(f"飞书消息发送失败: {result}")
                return False
        
        except Exception as e:
            self.logger.error(f"飞书消息发送异常: {e}")
            return False


class WeChatNotifier(NotificationProvider):
    """微信通知器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化微信通知器
        
        Args:
            config: 微信配置
        """
        super().__init__(config)
        self.webhook_url = config.get('webhook_url', '')
        self.server_chan_key = config.get('server_chan_key', '')
        
        if not self.webhook_url and not self.server_chan_key:
            self.logger.warning("微信通知配置不完整")
            self.enabled = False
    
    def send_message(self, message: str, **kwargs) -> bool:
        """发送文本消息"""
        if not self.enabled:
            return False
        
        if self.webhook_url:
            return self._send_webhook_message(message)
        elif self.server_chan_key:
            return self._send_server_chan_message(message, kwargs.get('title', '量化交易通知'))
        
        return False
    
    def send_card_message(self, title: str, content: str, **kwargs) -> bool:
        """发送卡片消息（微信不支持，转为文本）"""
        message = f"{title}\n\n{content}"
        return self.send_message(message, title=title)
    
    def send_signal_notification(self, signal: TradeSignal) -> bool:
        """发送交易信号通知"""
        if not self.enabled:
            return False
        
        title = f"🚨 {signal.action} 信号 - {signal.symbol}"
        content = f"""
{signal.action} 信号详情

股票代码: {signal.symbol}
当前价格: ${signal.price:.2f}
策略: {signal.strategy}
置信度: {signal.confidence:.1%}
时间: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

止盈: ${signal.take_profit:.2f} (+{((signal.take_profit/signal.price-1)*100):.1f}%)
止损: ${signal.stop_loss:.2f} ({((signal.stop_loss/signal.price-1)*100):.1f}%)

原因: {signal.reason}

⚠️ 投资有风险，交易需谨慎。
        """.strip()
        
        return self.send_message(content, title=title)
    
    def _send_webhook_message(self, message: str) -> bool:
        """通过企业微信 Webhook 发送消息"""
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=self.config.get('timeout', 30)
            )
            
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                self.logger.debug("企业微信消息发送成功")
                return True
            else:
                self.logger.error(f"企业微信消息发送失败: {result}")
                return False
        
        except Exception as e:
            self.logger.error(f"企业微信消息发送异常: {e}")
            return False
    
    def _send_server_chan_message(self, message: str, title: str) -> bool:
        """通过 Server 酱发送消息"""
        try:
            url = f"https://sctapi.ftqq.com/{self.server_chan_key}.send"
            
            payload = {
                'title': title,
                'desp': message
            }
            
            response = requests.post(url, data=payload, timeout=self.config.get('timeout', 30))
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 0:
                self.logger.debug("Server酱消息发送成功")
                return True
            else:
                self.logger.error(f"Server酱消息发送失败: {result}")
                return False
        
        except Exception as e:
            self.logger.error(f"Server酱消息发送异常: {e}")
            return False


class NotificationManager:
    """通知管理器"""
    
    def __init__(self, config_manager=None):
        """
        初始化通知管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 通知提供者
        self.providers: Dict[str, NotificationProvider] = {}
        
        # 通知队列
        self.notification_queue = queue.Queue()
        
        # 配置
        self.enabled = True
        self.batch_mode = False
        self.batch_interval = 300  # 5分钟
        self.max_retries = 3
        self.retry_interval = 60
        
        # 批量通知缓存
        self.batch_messages: List[TradeSignal] = []
        self.last_batch_time = datetime.now()
        
        # 发送状态
        self.send_stats = {
            'total_sent': 0,
            'success_count': 0,
            'failed_count': 0,
            'last_send_time': None
        }
        
        # 工作线程
        self.worker_thread = None
        self.is_running = False
        
        # 初始化提供者
        self._init_providers()
        
        self.logger.info("通知管理器初始化完成")
    
    def _init_providers(self) -> None:
        """初始化通知提供者"""
        if not self.config_manager:
            return
        
        try:
            notification_config = self.config_manager.get_notification_config()
            
            if not notification_config.enabled:
                self.enabled = False
                self.logger.info("通知功能已禁用")
                return
            
            # 初始化飞书
            if notification_config.feishu and notification_config.feishu.get('enabled', False):
                feishu_notifier = FeishuNotifier(notification_config.feishu)
                self.providers['feishu'] = feishu_notifier
                self.logger.info("飞书通知器已启用")
            
            # 初始化微信
            if notification_config.wechat and notification_config.wechat.get('enabled', False):
                wechat_notifier = WeChatNotifier(notification_config.wechat)
                self.providers['wechat'] = wechat_notifier
                self.logger.info("微信通知器已启用")
            
            # 加载频率控制配置
            if notification_config.frequency:
                self.batch_mode = notification_config.frequency.get('mode') == 'batch'
                self.batch_interval = notification_config.frequency.get('batch_interval', 5) * 60
            
            if not self.providers:
                self.logger.warning("没有可用的通知提供者")
                self.enabled = False
        
        except Exception as e:
            self.logger.error(f"初始化通知提供者失败: {e}")
            self.enabled = False
    
    def start(self) -> None:
        """启动通知管理器"""
        if not self.enabled or self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        self.logger.info("通知管理器已启动")
    
    def stop(self) -> None:
        """停止通知管理器"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        # 发送剩余的批量消息
        if self.batch_messages:
            self._send_batch_notifications()
        
        self.logger.info("通知管理器已停止")
    
    def send_signal_notification(self, signal: TradeSignal) -> None:
        """
        发送交易信号通知
        
        Args:
            signal: 交易信号
        """
        if not self.enabled:
            return
        
        try:
            if self.batch_mode:
                # 批量模式
                self.batch_messages.append(signal)
                
                # 检查是否需要发送批量消息
                if (len(self.batch_messages) >= 10 or  # 达到最大批量数
                    datetime.now() - self.last_batch_time >= timedelta(seconds=self.batch_interval)):
                    self._send_batch_notifications()
            else:
                # 立即发送模式
                self.notification_queue.put(('signal', signal))
            
        except Exception as e:
            self.logger.error(f"添加通知到队列失败: {e}")
    
    def send_message(self, message: str, title: str = "量化交易通知") -> None:
        """
        发送普通消息
        
        Args:
            message: 消息内容
            title: 消息标题
        """
        if not self.enabled:
            return
        
        self.notification_queue.put(('message', {'message': message, 'title': title}))
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while self.is_running:
            try:
                # 获取通知任务
                try:
                    notification_type, data = self.notification_queue.get(timeout=1)
                except queue.Empty:
                    # 检查是否需要发送批量消息
                    if (self.batch_mode and self.batch_messages and
                        datetime.now() - self.last_batch_time >= timedelta(seconds=self.batch_interval)):
                        self._send_batch_notifications()
                    continue
                
                # 处理通知
                success = False
                if notification_type == 'signal':
                    success = self._send_signal_to_providers(data)
                elif notification_type == 'message':
                    success = self._send_message_to_providers(data['message'], data['title'])
                elif notification_type == 'batch':
                    success = self._send_batch_to_providers(data)
                
                # 更新统计
                self.send_stats['total_sent'] += 1
                if success:
                    self.send_stats['success_count'] += 1
                else:
                    self.send_stats['failed_count'] += 1
                self.send_stats['last_send_time'] = datetime.now()
            
            except Exception as e:
                self.logger.error(f"通知工作线程异常: {e}")
    
    def _send_signal_to_providers(self, signal: TradeSignal) -> bool:
        """向所有提供者发送信号"""
        results = []
        
        for name, provider in self.providers.items():
            try:
                if hasattr(provider, 'send_signal_notification'):
                    success = provider.send_signal_notification(signal)
                else:
                    message = provider.format_signal_message(signal)
                    success = provider.send_message(message)
                
                results.append(success)
                
                if success:
                    self.logger.debug(f"通过 {name} 发送信号成功")
                else:
                    self.logger.warning(f"通过 {name} 发送信号失败")
            
            except Exception as e:
                self.logger.error(f"通过 {name} 发送信号异常: {e}")
                results.append(False)
        
        return any(results)  # 至少一个成功就算成功
    
    def _send_message_to_providers(self, message: str, title: str) -> bool:
        """向所有提供者发送消息"""
        results = []
        
        for name, provider in self.providers.items():
            try:
                success = provider.send_message(message, title=title)
                results.append(success)
                
                if success:
                    self.logger.debug(f"通过 {name} 发送消息成功")
                else:
                    self.logger.warning(f"通过 {name} 发送消息失败")
            
            except Exception as e:
                self.logger.error(f"通过 {name} 发送消息异常: {e}")
                results.append(False)
        
        return any(results)
    
    def _send_batch_notifications(self) -> None:
        """发送批量通知"""
        if not self.batch_messages:
            return
        
        # 添加到队列
        self.notification_queue.put(('batch', self.batch_messages.copy()))
        
        # 清空缓存
        self.batch_messages.clear()
        self.last_batch_time = datetime.now()
    
    def _send_batch_to_providers(self, signals: List[TradeSignal]) -> bool:
        """向所有提供者发送批量信号"""
        if not signals:
            return True
        
        # 构建批量消息
        title = f"📊 量化交易信号汇总 ({len(signals)}条)"
        
        content_lines = [f"时间范围: {signals[0].timestamp.strftime('%H:%M')} - {signals[-1].timestamp.strftime('%H:%M')}"]
        content_lines.append("")
        
        for i, signal in enumerate(signals, 1):
            action_emoji = "📈" if signal.action == "BUY" else "📉"
            content_lines.append(
                f"{i}. {action_emoji} {signal.action} {signal.symbol} @ ${signal.price:.2f} "
                f"({signal.confidence:.0%}) - {signal.strategy}"
            )
        
        content_lines.append("")
        content_lines.append("⚠️ 请查看详细信号进行交易决策")
        
        content = "\n".join(content_lines)
        
        return self._send_message_to_providers(content, title)
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """获取通知统计信息"""
        return {
            'enabled': self.enabled,
            'providers_count': len(self.providers),
            'providers': list(self.providers.keys()),
            'batch_mode': self.batch_mode,
            'queue_size': self.notification_queue.qsize(),
            'batch_pending': len(self.batch_messages),
            'send_stats': self.send_stats.copy()
        }
    
    def test_notifications(self) -> Dict[str, bool]:
        """测试所有通知提供者"""
        results = {}
        test_message = f"🧪 通知测试消息 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        for name, provider in self.providers.items():
            try:
                success = provider.send_message(test_message, title="通知测试")
                results[name] = success
                
                if success:
                    self.logger.info(f"{name} 通知测试成功")
                else:
                    self.logger.warning(f"{name} 通知测试失败")
            
            except Exception as e:
                self.logger.error(f"{name} 通知测试异常: {e}")
                results[name] = False
        
        return results