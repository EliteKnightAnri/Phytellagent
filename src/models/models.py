from typing import Optional, List, Dict

# ==========================================
# 消息数据类
# ==========================================
class Message:
    def __init__(self, role: str, content: str, attachments: Optional[List[Dict]] = None):
        self.role = role
        self.content = content
        self.attachments = attachments or []   
        self.ui_element = None
        self.is_streaming = False

    def to_dict(self):
        return {
            'role': self.role,
            'content': self.content,
            'attachments': self.attachments,   
        }

    @staticmethod
    def from_dict(d):
        return Message(
            d.get('role', ''),
            d.get('content', ''),
            d.get('attachments', []),          
        )