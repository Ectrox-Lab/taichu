from flask import Flask, request, jsonify
import logging
import json
import requests
from datetime import datetime
import sys

# 禁用输出缓冲
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

app = Flask(__name__)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/feishu-debug.log', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

MODEL_API = "http://192.168.88.253:8005/v1/chat/completions"
FEISHU_APP_ID = "cli_a911066ad3b85bca"
FEISHU_APP_SECRET = "5B12qyvp4DZuQ4c9UdLjwcEQxfSQ0BD7"
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

@app.route('/webhook/feishu', methods=['GET', 'POST'])
def feishu_webhook():
    if request.method == 'GET':
        return jsonify({"status": "ok"})
    
    data = request.get_json()
    
    # 记录请求
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    logger.info(f"="*50)
    logger.info(f"收到请求: POST")
    logger.info(f"请求数据: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
    
    # Challenge 验证
    if data.get('type') == 'url_verification':
        challenge = data.get('challenge')
        logger.info(f"处理 challenge: {challenge}")
        return jsonify({"challenge": challenge})
    
    # 处理消息事件
    header = data.get('header', {})
    event_type = header.get('event_type')
    
    if event_type == 'im.message.receive_v1':
        event = data.get('event', {})
        message = event.get('message', {})
        sender = event.get('sender', {})
        
        # 获取消息内容
        try:
            content = json.loads(message.get('content', '{}'))
            text = content.get('text', '')
        except:
            text = ''
        
        # 获取聊天类型和ID
        chat_type = message.get('chat_type', '')
        chat_id = message.get('chat_id', '')
        
        # 获取发送者信息
        sender_open_id = sender.get('sender_id', {}).get('open_id', '')
        
        logger.info(f"事件类型: {event_type}")
        logger.info(f"聊天类型: {chat_type}")
        logger.info(f"Chat ID: {chat_id}")
        logger.info(f"发送者: {sender_open_id}")
        logger.info(f"用户消息: {text}")
        
        # 群聊回复使用 chat_id
        if chat_type == 'group':
            receive_id = chat_id
            receive_id_type = 'chat_id'
        else:  # p2p
            receive_id = sender_open_id
            receive_id_type = 'open_id'
        
        logger.info(f"回复目标: {receive_id_type}={receive_id}")
        
        # 调用 AI 模型
        if text:
            logger.info(f"调用 AI 模型...")
            try:
                resp = requests.post(MODEL_API, json={
                    "model": "gpt-oss-120b",
                    "messages": [{"role": "user", "content": text}],
                    "max_tokens": 500,
                    "temperature": 0.7
                }, timeout=60)
                
                if resp.status_code == 200:
                    reply = resp.json()['choices'][0]['message']['content']
                    logger.info(f"AI 回复: {reply[:100]}...")
                    
                    # 发送回复到飞书
                    send_to_feishu(receive_id, reply, receive_id_type)
                else:
                    logger.error(f"模型调用失败: {resp.status_code}")
            except Exception as e:
                logger.error(f"模型调用异常: {e}")
    else:
        logger.info(f"其他事件类型: {event_type}")
    
    return jsonify({"code": 0, "msg": "success"})

def get_tenant_access_token():
    """获取飞书 tenant_access_token"""
    try:
        resp = requests.post(FEISHU_TOKEN_URL, json={
            "app_id": FEISHU_APP_ID,
            "app_secret": FEISHU_APP_SECRET
        })
        result = resp.json()
        if result.get('code') == 0:
            return result.get('tenant_access_token')
    except Exception as e:
        logger.error(f"获取 Token 失败: {e}")
    return None

def send_to_feishu(receive_id, text, receive_id_type):
    """发送消息到飞书"""
    if not receive_id:
        logger.error("receive_id 为空，无法发送消息")
        return
    
    token = get_tenant_access_token()
    if not token:
        logger.error("无法获取 token")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {"receive_id_type": receive_id_type}
    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    
    logger.info(f"发送消息: receive_id_type={receive_id_type}, receive_id={receive_id}")
    
    try:
        resp = requests.post(FEISHU_SEND_URL, 
                            headers=headers, 
                            params=params,
                            json=payload,
                            timeout=30)
        result = resp.json()
        logger.info(f"发送结果: {result}")
    except Exception as e:
        logger.error(f"发送失败: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=False)
