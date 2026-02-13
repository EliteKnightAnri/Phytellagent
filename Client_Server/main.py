import asyncio
import uuid
from typing import List, Optional, Dict
from nicegui import ui, app as nicegui_app
import json
import os


from models import Message
from api import BackendClient

#文件上传总类
ALLOWED_KB_EXTS = {'.pdf', '.txt', '.md', '.docx', '.csv', '.xlsx', '.xls', '.json'}
ALLOWED_CHAT_EXTS = {'.pdf', '.txt', '.md', '.docx', '.xlsx'}   # 临时分析先做常见四种
MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30MB

def _ext_ok(name: str, allowed: set[str]) -> bool:
    if not name:
        return False
    _, ext = os.path.splitext(name)
    return ext.lower() in allowed






# 单个会话的应用逻辑
class ChatSession:

    # 定义历史记录保存的文件名
    HISTORY_FILE = "local_history.json"

    def __init__(self):
        # 当前正在显示的消息列表
        self.messages: List[Message] = []
        self.session_file_ids = set()
        self.pending_attachments = []   # [{file_id, filename}]
        self.attachment_bar = None      # UI 容器引用
        # 从文件加载 
        self.chat_history: List[Dict] = []
        self.current_chat_id: Optional[str] = None

        # 1. 加载历史，并获取上次保存时选中的 ID
        saved_active_id = self._load_history_from_disk()
        
        # 2. 决定显示哪个对话
        target_session = None
        
        if self.chat_history:
            if saved_active_id:
                # 如果有记录的 ID，尝试在历史里找到它
                target_session = next((s for s in self.chat_history if s['id'] == saved_active_id), None)
            
            # 如果没找到（比如ID对应的被删了），或者没有记录ID，就默认拿最新的
            if not target_session:
                target_session = self.chat_history[0]
                
            # 加载目标会话
            self.messages = target_session['messages']
            self.current_chat_id = target_session['id']
            
        else:
            # 完全没历史，初始化新的
            self._init_demo_data()
            self._save_history_to_disk()
            self.reset_current_view()
        
        
        self.backend = BackendClient()
        self.generating = False
        self.stop_flag = False
        
        # UI 组件引用 
        self.drawer = None
        self.scroll_area = None
        self.content_container = None
        self.input_textarea = None
        self.send_btn = None   
        self.mode_label = None
        self.history_container = None 
        
        self.current_mode = "general"
        self.current_file_id: Optional[str] = None
        self.response_spinner = None
        
        # (工具列表保持不变)
        self.mcp_tools = [
            {'id': 'wechat', 'name': 'wechat_oa_mcp', 'url': 'http://localhost:8000/sse', 'selected': False},
            {'id': 'modelscope', 'name': 'ModelScope-Image-Generation', 'url': 'https://mcp.api...', 'selected': False},
            {'id': 'bing', 'name': 'bing-cn-mcp-server', 'url': 'https://mcp.api...', 'selected': False},
        ]
        self.mcp_dialog = None

    # 保存消息
    def _save_history_to_disk(self):
        # 1. 序列化消息列表
        serialized_history = []
        for session in self.chat_history:
            serialized_msgs = [m.to_dict() for m in session['messages']]
            serialized_history.append({
                'id': session['id'],
                'title': session['title'],
                'messages': serialized_msgs,
                'session_file_ids': list(getattr(session, 'session_file_ids', []))
            })
            
        # 2. 构造新的存储结构：包含 active_id 和 history
        save_data = {
            "active_id": self.current_chat_id,  # 记住当前选中的是谁
            "history": serialized_history
        }
            
        with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

    # 加载时，读取 active_id 
    def _load_history_from_disk(self):
        if not os.path.exists(self.HISTORY_FILE):
            return
        
        try:
            with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 兼容处理：防止旧格式报错
            if isinstance(data, list):
                raw_history = data
                saved_active_id = None
            else:
                raw_history = data.get('history', [])
                saved_active_id = data.get('active_id')

            # 还原 Message 对象
            self.chat_history = []
            for session in raw_history:
                restored_msgs = [Message.from_dict(m) for m in session['messages']]
                self.chat_history.append({
                    'id': session['id'],
                    'title': session['title'],
                    'messages': restored_msgs
                })
            
            # 返回保存的 active_id，供 __init__ 使用
            return saved_active_id
            
        except Exception as e:
            print(f"读取历史记录失败: {e}")
            return None


    def _init_demo_data(self):
        """初始化一条示例数据"""
        demo_msgs = [
            Message('assistant', "👋 **你好！我是你的智能助手。"),
            Message('user', "你好呀"),
            Message('assistant', "你好！"), # 确保这里的 content 有内容
            Message('user', "如何学好物理"),
            Message('assistant', "先v我50")
        ]
        self.chat_history.append({
            'id': str(uuid.uuid4()),
            'title': '示例对话',
            'messages': demo_msgs
        })

    def reset_current_view(self):
        """重置当前视图为全新的空白会话"""
        self.messages = []
        self.messages.append(Message('assistant', 
            "👋 **你好！我是聪明的智能助手。**"
            
        ))
        self.current_chat_id = None # 标记为新会话

    def build_ui(self):
        # 1. 侧边栏
        self.build_sidebar()

        # 2. 主界面
        with ui.column().classes('w-full h-screen relative bg-white gap-0'):
            
            # --- 顶部栏 ---
            with ui.row().classes('w-full p-4 absolute top-0 left-0 z-10 bg-white/90 backdrop-blur-sm justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.button(icon='menu', on_click=lambda: self.drawer.toggle()).props('flat round color=black').tooltip('Toggle Sidebar')
                    
                    with ui.button(icon='expand_more').props('flat no-caps color=black').classes('font-bold text-lg hover:bg-gray-100 rounded-lg px-3'):
                        self.mode_label = ui.label('通用模式').classes('mr-1')
                        with ui.menu().classes('bg-white shadow-lg rounded-xl border border-gray-100 p-2'):
                            def select_mode(mode_key, display_name):
                                self.current_mode = mode_key
                                self.mode_label.text = display_name
                                ui.notify(f"已切换到: {display_name}",timeout=100)

                            ui.menu_item('通用模式', on_click=lambda: select_mode('general', '通用模式 ')).classes('rounded-lg hover:bg-gray-50')
                            ui.menu_item('专业模式', on_click=lambda: select_mode('course_graph', '专业模式')).classes('rounded-lg hover:bg-gray-50')
                            
                
                # New Chat 按钮
                ui.button(icon='add', on_click=self.on_new_chat_click).props('flat round color=black').tooltip('New Chat')

            # --- 聊天区域 ---
            with ui.scroll_area().classes('w-full flex-grow px-4 pb-36 pt-20') as self.scroll_area:
                with ui.column().classes('w-full max-w-[48rem] mx-auto gap-6') as self.content_container:
                    for msg in self.messages:
                        self.render_message(msg)

            # --- 底部输入区 ---
            with ui.column().classes('absolute bottom-0 left-0 w-full bg-gradient-to-t from-white via-white to-transparent pb-6 pt-10 px-4'):
                with ui.column().classes('w-full max-w-[48rem] mx-auto relative'):
                    
                    with ui.row().classes('pl-2 pb-0 -mb-1 items-center gap-2 flex-wrap') as self.attachment_bar:
                        pass
                    
                    with ui.card().classes('w-full rounded-[26px] shadow-sm border border-gray-200 bg-[#f4f4f4] focus-within:bg-white focus-within:border-gray-300 focus-within:shadow-md transition-all gap-0 p-2'):
                        with ui.row().classes('w-full items-center gap-2 px-2'):
                            with ui.button(icon='add_circle', on_click=self.open_upload_dialog).props('flat round color=grey-6').classes('mb-1'):
                              ui.tooltip('上传文件')

                            with ui.button(icon='inventory_2', on_click=self.open_kb_manager).props('flat round color=grey-6').classes('mb-1'):
                                ui.tooltip('知识库管理')

                            with ui.button(icon='construction', on_click=self.open_mcp_dialog) \
                                .props('flat round color=grey-6').classes('mb-1'):
                              ui.tooltip('选择 MCP 工具')
                              self.mcp_indicator = ui.badge().props('floating color=green-500 rounded dot').classes('hidden')

                            self.input_textarea = ui.textarea(
                                placeholder="给 Software A 发送消息...",
                            ).props('autogrow borderless rows=1').classes('flex-grow text-gray-800 text-base chat-input max-h-[200px] overflow-y-auto')
                            
                            self.input_textarea.on('keydown.enter.prevent', self.handle_click)
                            
                            self.send_btn = ui.button(icon='arrow_upward', on_click=self.handle_click) \
                                .props('unelevated round size=sm color=black').classes('mb-1 transition-all')

                    ui.label('Software A can make mistakes. Consider checking important information.').classes('text-[11px] text-gray-400 w-full text-center mt-2')

    #侧边栏代码详细
    def build_sidebar(self):
        with ui.left_drawer(value=True).classes('bg-gray-50 w-[260px] border-r border-gray-200') as self.drawer:
            
            # New Chat 按钮
            with ui.row().classes('p-3'):
                with ui.button(on_click=self.on_new_chat_click).classes('w-full flex items-center justify-start gap-3 px-3 py-3 bg-white hover:bg-gray-200 rounded-lg border border-gray-300 shadow-sm transition-colors'):
                    ui.icon('add', size='xs').classes('text-black')
                    ui.label('New chat').classes('text-sm text-black font-medium normal-case')

            # 历史记录区域
            with ui.column().classes('w-full px-3 gap-1 mt-4'):
                ui.label('Recent').classes('text-xs font-bold text-black px-3 mb-1')
                self.history_container = ui.column().classes('w-full gap-1')
                self.refresh_history_ui()

    #===知识库处理===
    #知识库页面渲染        
    async def open_kb_manager(self):
        self.kb_dialog = ui.dialog()
        with self.kb_dialog, ui.card().classes('w-[600px] h-[500px]'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('📚 知识库管理').classes('text-lg font-bold')
                ui.button(icon='close', on_click=self.kb_dialog.close).props('flat dense')
            
            # 文件列表区域
            self.file_list_container = ui.column().classes('w-full flex-grow overflow-y-auto border rounded p-2')
            
            # 底部操作区
            with ui.row().classes('w-full items-center justify-between border-t pt-2'):
                # 🔥 修改点：把组件赋值给 self.kb_uploader
                self.kb_uploader = ui.upload(
                    label='上传新文档 (PDF/Word/TXT/MD/CSV/XLSX/JSON)', 
                    auto_upload=True,
                    on_upload=self.handle_kb_upload,
                    max_files=1 # 建议限制一次一个，避免并发逻辑复杂
                ).props(f'flat dense accept={",".join(sorted(ALLOWED_KB_EXTS))} max-file-size={MAX_UPLOAD_BYTES}').classes('w-full')
        
        self.kb_dialog.open()
        await self.refresh_file_list()
        
    #删除知识库文件
    async def handle_delete_file(self, filename):
        # 1. 提示用户
        ui.notify(f"正在删除 {filename}，请稍候...", type='warning', timeout=2000)
        
        # 2. 调用后端 API
        res = await self.backend.delete_file(filename)
        
        # 3. 处理结果
        if res.get('status') == 'success':
            ui.notify(f"🗑️ {filename} 已删除", type='positive')
            # 刷新列表
            await self.refresh_file_list()
        else:
            ui.notify(f"❌ 删除失败: {res.get('message')}", type='negative')
            
    #知识库滑动开关处理        
    async def handle_toggle_kb_file(self, filename: str, enabled: bool):
        ui.notify(f"{'正在启用' if enabled else '正在禁用'} {filename} ...",
                  type='info', timeout=1200)
     
        res = await self.backend.toggle_file(filename, enabled)
     
        if res.get('status') == 'success':
            ui.notify(res.get('message', '状态已更新'), type='positive', timeout=1500)
        else:
            ui.notify(f"❌ 操作失败: {res.get('message')}", type='negative', timeout=2500)
     
        # 无论成功失败，都刷新列表：失败也会把开关状态“还原”为后端真实状态
        await self.refresh_file_list()

    
    # 知识库文件管理面板的渲染函数
    async def refresh_file_list(self):
        self.file_list_container.clear()
     
        files = await self.backend.get_files()
     
        with self.file_list_container:
            if not files:
                ui.label("暂无文件，请上传").classes("text-gray-400 w-full text-center mt-10")
                return
     
            for f in files:
                filename = f['name']
                enabled = bool(f.get('enabled', False))
                indexed = bool(f.get('indexed', False))
     
                with ui.row().classes(
                    'w-full items-center justify-between p-3 bg-white border border-gray-200 '
                    'rounded-lg shadow-sm hover:shadow-md transition-all mb-2'
                ):
                    # 左侧信息
                    with ui.row().classes('items-center gap-3'):
                        icon_color = 'red' if filename.endswith('.pdf') else 'blue'
                        ui.icon('description', color=icon_color).classes('text-xl')
                        ui.label(filename).classes('text-base font-medium text-gray-700 truncate max-w-[240px]')
     
                        # 状态小标（可选但很直观）
                        ui.badge('启用' if enabled else '停用',
                                 color='green-6' if enabled else 'grey-6').classes('text-[10px]')
                        if enabled and not indexed:
                            ui.badge('未建索引', color='orange-6').classes('text-[10px]')
     
                    # 右侧按钮组
                    with ui.row().classes('items-center gap-2'):
                        # ✅ 开关：控制是否参与 RAG
                        ui.switch(
                            value=enabled,
                            on_change=lambda e, n=filename: self.handle_toggle_kb_file(n, e.value)
                        ).props('dense color=green').tooltip('打开后才会参与 RAG 检索')
     
                        # 查看/下载
                        download_url = f"http://127.0.0.1:8000/files/download/{filename}"
                        ui.button(
                            icon='visibility',
                            on_click=lambda e, u=download_url: ui.navigate.to(u, new_tab=True)
                        ).props('flat round dense color=grey-7').tooltip('查看/下载')
     
                        # 🗑️ 删除按钮：必须 create_task，否则 async 不会跑/不稳定
                        ui.button(
                            icon='delete',
                            on_click=lambda e, n=filename: self.handle_delete_file(n)
                        ).props('flat round dense color=red').tooltip('删除文件')


    #前端上传知识库文件（KB）的事件处理函数
    async def handle_kb_upload(self, e):
        # 1. 获取文件对象
        real_file = e.file 
        display_name = getattr(real_file, 'name', getattr(real_file, 'filename', '未知文件'))
        if not _ext_ok(display_name, ALLOWED_KB_EXTS):
            ui.notify(f"❌ 不支持的文件类型：{display_name}\n支持: {', '.join(sorted(ALLOWED_KB_EXTS))}", type='negative')
            self.kb_uploader.reset()
            return
        
        ui.notify(f"正在上传 {display_name}...", type='info', timeout=2000)
        
        # 2. 调用后端
        res = await self.backend.upload_kb_file(real_file)

        # 3. 处理结果
        if res.get('status') == 'success':
            ui.notify(f"✅ {res.get('message', '上传成功')}", type='positive')
            await self.refresh_file_list()
            
            self.kb_uploader.reset()
            
        else:
            ui.notify(f"❌ 失败: {res.get('message')}", type='negative')
            self.kb_uploader.reset()

    #  ====MCP处理===
    #  MCP 选择对话框 
    def open_mcp_dialog(self):
        with ui.dialog() as self.mcp_dialog, ui.card().classes('w-[500px] max-w-full p-0 gap-0 rounded-xl overflow-hidden'):
            # 标题栏
            with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-100 justify-between items-center'):
                ui.label('MCP 工具库').classes('font-bold text-gray-800')
                ui.button(icon='close', on_click=self.mcp_dialog.close).props('flat round dense color=grey')

            # 工具列表
            with ui.column().classes('w-full p-2 max-h-[60vh] overflow-y-auto'):
                if not self.mcp_tools:
                    ui.label('暂无可用工具').classes('p-4 text-gray-400 w-full text-center')
                
                for tool in self.mcp_tools:
                    # 每个工具的卡片行
                    with ui.row().classes('w-full items-center p-3 hover:bg-gray-50 rounded-lg transition-colors border border-transparent hover:border-gray-200'):
                        # 图标
                        ui.icon('extension', color='green' if tool['selected'] else 'grey').classes('text-2xl mr-2')
                        
                        # 文字信息
                        with ui.column().classes('flex-grow gap-0'):
                            ui.label(tool['name']).classes('font-medium text-gray-800')
                            ui.label(tool['url']).classes('text-xs text-gray-400 truncate w-64')
                        
                        # 开关
                        ui.switch(value=tool['selected'], on_change=lambda e, t=tool: self.toggle_tool(t, e.value)) \
                            .props('color=green dense')

            # 底部确认栏
            with ui.row().classes('w-full p-3 bg-gray-50 border-t border-gray-100 justify-end'):
                ui.button('完成', on_click=self.mcp_dialog.close).props('flat color=primary')
        
        self.mcp_dialog.open()
    
    #工具栏选择
    def toggle_tool(self, tool, is_selected):
        tool['selected'] = is_selected
        # 更新主界面按钮上的小点状态
        active_count = sum(1 for t in self.mcp_tools if t['selected'])
        if active_count > 0:
            self.mcp_indicator.classes(remove='hidden')
        else:
            self.mcp_indicator.classes(add='hidden')
    
    #===历史记录管理函数===
    # 历史记录管理
    def save_current_chat(self):
        """保存当前会话到 history 并写入磁盘"""
        # 如果只有欢迎语或空消息，不执行保存
        if len(self.messages) <= 1:
            return

        # 预先将 set 转换为 list，以便 JSON 存储
        current_files = list(self.session_file_ids)
        found = False

        # 1. 尝试更新内存中已有的会话记录
        if self.current_chat_id:
            for session in self.chat_history:
                if session['id'] == self.current_chat_id:
                    # ✅ 修正建议：直接在匹配到 ID 的 if 内部完成赋值
                    session['messages'] = self.messages
                    session['session_file_ids'] = current_files
                    found = True
                    break  # 找到后立即跳出循环，提高效率

        # 2. 如果是新开启的会话（未在历史记录中找到），创建新记录
        if not found:
            # 取第一条用户消息的前 18 个字作为侧边栏标题
            first_user_msg = self.messages[1].content
            title = (first_user_msg[:18] + '..') if len(first_user_msg) > 18 else first_user_msg
            
            new_id = str(uuid.uuid4())
            new_session = {
                'id': new_id,
                'title': title,
                'messages': self.messages,
                'session_file_ids': current_files  # 初始保存文件 ID 列表
            }
            # 将新会话插入到列表最前方
            self.chat_history.insert(0, new_session)
            self.current_chat_id = new_id
        
        # 3. 同步刷新 UI 侧边栏显示
        self.refresh_history_ui()
        
        # 4. 调用持久化方法，将 self.chat_history 写入 local_history.json
        self._save_history_to_disk()


     #删除指定会话 
    def delete_chat(self, chat_id: str):
        # 1. 从内存列表中移除
        self.chat_history = [c for c in self.chat_history if c['id'] != chat_id]
        
        # 2. 同步保存到硬盘
        self._save_history_to_disk()
        
        # 3. 如果删除的是当前正在看的会话，就重置界面（相当于点 New Chat）
        if self.current_chat_id == chat_id:
            self.on_new_chat_click()
        
        # 4. 刷新侧边栏 UI
        self.refresh_history_ui()
        ui.notify('会话已删除', type='info', timeout=100)

    def load_chat(self, chat_id: str):
        """加载指定的历史会话"""
        # 1. 切走前先保存当前状态
        self.save_current_chat()
        
        # 2. 查找目标
        target_session = next((s for s in self.chat_history if s['id'] == chat_id), None)
        if not target_session:
            return

        # 3. 载入数据
        self.messages = target_session['messages']
        self.current_chat_id = chat_id
        saved_ids = target_session.get('session_file_ids', [])
        self.session_file_ids = set(saved_ids)

        self.stop_flag = False
        self.generating = False
        
        # 4. 重绘
        self.content_container.clear()
        for msg in self.messages:
            self.render_message(msg)

        #切换后立刻保存到硬盘，为了更新 active_id
        self._save_history_to_disk()
            
        ui.notify(f"已加载: {target_session['title']}",timeout=100)
        
    #添加新对话
    def on_new_chat_click(self):
        """点击 New Chat"""
        self.save_current_chat()
        self.reset_current_view()
        
        self.content_container.clear()
        self.render_message(self.messages[0])
        self.pending_attachments = []
        self.refresh_attachment_bar()
        self.input_textarea.value = ""
        self.stop_flag = False
        self.generating = False

    # 侧边栏更新 
    def refresh_history_ui(self):
        """刷新侧边栏列表"""
        self.history_container.clear()
        with self.history_container:
            for session in self.chat_history:
                # 使用 row 容器把标题和删除按钮包在一起
                with ui.row().classes('w-full items-center gap-0 group rounded-lg hover:bg-gray-200 transition-colors'):
                    
                    # 左侧：加载会话的按钮 (占据剩余空间 flex-grow)
                    with ui.button(on_click=lambda s_id=session['id']: self.load_chat(s_id)) \
                        .classes('flex-grow flex items-center justify-start px-3 py-2 bg-transparent border-none shadow-none'):
                        ui.label(session['title']).classes('truncate w-36 text-left text-sm text-black font-normal normal-case')

                    
                    ui.button(icon='delete_outline', on_click=lambda s_id=session['id']: self.delete_chat(s_id)) \
                        .props('flat dense size=sm color=grey-6') \
                        .classes('mr-1 opacity-50 hover:opacity-100 hover:text-red-600') \
                        .tooltip('删除会话')

    

    #===消息/文件发送===
    # 点击发送按钮事件函数
    async def handle_click(self):
        if self.generating:
            self.stop_flag = True
            ui.notify("已停止生成", position='top',timeout=100)
            return
        await self.send_message()
    
    #发送函数
    async def send_message(self):
        prompt = (self.input_textarea.value or '').strip()
     
        # ✅ 允许“只发附件”
        if (not prompt) and (not self.pending_attachments):
            return
        if (not prompt) and self.pending_attachments:
            prompt = "请先阅读我上传的附件，并给出摘要与关键信息。"
     
        self.input_textarea.value = ""
     
        # 把附件带进 user message（进入对话气泡）
        attachments = list(self.pending_attachments)
        user_msg = Message('user', prompt, attachments=attachments)
        self.messages.append(user_msg)
        self.render_message(user_msg)
     
        # 发送后清空“待发送附件”
        self.pending_attachments = []
        self.refresh_attachment_bar()
     
        self.scroll_area.scroll_to(percent=1.2, duration=0.1)
     
        assistant_msg = Message('assistant', '')
        assistant_msg.is_streaming = True
        self.messages.append(assistant_msg)
        self.render_message(assistant_msg)
        self.scroll_area.scroll_to(percent=1.2, duration=0.1)
     
        self.generating = True
        self.stop_flag = False
        self.send_btn.props('icon=stop')
     
        full_text = ""
        target_mode = self.current_mode
     
        # ✅ 多附件：传 file_ids 给后端（下面第3步会改后端）
        file_ids = list(self.session_file_ids)
        try:
            async for chunk in self.backend.stream_chat(prompt, file_ids, target_mode):
                if self.stop_flag:
                    break
                t = chunk.get("type")
                c = chunk.get("content", "")
                if t == "markdown_chunk":
                    full_text += c
                    if assistant_msg.ui_element:
                        assistant_msg.ui_element.set_content(full_text + " ▍")
                elif t == "error":
                    ui.notify(c, type='negative', timeout=100)
        except Exception as e:
            ui.notify(str(e), type='negative', timeout=100)
     
        assistant_msg.content = full_text
        if assistant_msg.ui_element:
            assistant_msg.ui_element.set_content(full_text)
     
        if self.response_spinner:
            self.response_spinner.delete()
            self.response_spinner = None
     
        assistant_msg.is_streaming = False
        self.generating = False
        self.send_btn.props('icon=arrow_upward')
        self.scroll_area.scroll_to(percent=1.2, duration=0.1)
     
        self.save_current_chat()

    #消息渲染函数
    def render_message(self, msg: Message):
        with self.content_container:
            if msg.role == 'user':
                with ui.row().classes('w-full justify-end'):
                    with ui.column().classes('bg-[#f4f4f4] px-5 py-3 rounded-[24px] max-w-[85%] text-gray-800'):
                        # ✅ 附件区域
                        if getattr(msg, 'attachments', None):
                            with ui.column().classes('gap-2'):
                                for att in msg.attachments:
                                    with ui.row().classes('items-center gap-2 px-3 py-2 rounded-xl bg-white/70 border border-gray-200'):
                                        ui.icon('description', size='sm').classes('text-gray-600')
                                        ui.label(att['filename']).classes('text-sm text-gray-700 truncate max-w-[260px]')
                        # ✅ 文本区域
                        if msg.content:
                            ui.markdown(msg.content).classes('text-base')
            else:
                with ui.row().classes('w-full justify-start items-start gap-4'):
                    with ui.column().classes('mt-1 border border-gray-200 rounded-full p-1 h-8 w-8 flex items-center justify-center flex-shrink-0'):
                        ui.icon('smart_toy', size='xs', color='green-600')
                    
                    with ui.column().classes('flex-grow min-w-0 pt-1'):
                        ui.label('Software A').classes('font-bold text-sm text-gray-800 mb-1')
                        msg.ui_element = ui.markdown(msg.content, extras=['fenced-code-blocks', 'tables']) \
                            .classes('text-base text-gray-800 w-full overflow-hidden nicegui-markdown') 
                            # 注意：加了一个 nicegui-markdown 类名，为了让 CSS 识别它
                
                        if msg.is_streaming:
                            self.response_spinner = ui.spinner('dots', size='sm', color='grey')
    
    #附件条渲染 
    def refresh_attachment_bar(self):
        if not self.attachment_bar:
            return
        self.attachment_bar.clear()
        with self.attachment_bar:
            for att in self.pending_attachments:
                file_id = att['file_id']
                filename = att['filename']
                with ui.row().classes('items-center gap-2 px-3 py-1 rounded-full bg-gray-100 border border-gray-200'):
                    ui.icon('attach_file', size='xs').classes('text-gray-600')
                    ui.label(filename).classes('text-xs text-gray-700 max-w-[260px] truncate')
                    ui.button(icon='close', on_click=lambda fid=file_id: self.remove_attachment(fid)) \
                        .props('flat dense round size=sm color=grey-7')
   
    #附件移除
    def remove_attachment(self, file_id: str):
        self.pending_attachments = [x for x in self.pending_attachments if x['file_id'] != file_id]
        self.refresh_attachment_bar()

    # 文件上传窗口函数
    async def open_upload_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-[520px] max-w-full'):
            ui.label('上传文件').classes('text-base font-bold')
            ui.label('支持：.docx .pdf .txt .md .xlsx；').classes('text-xs text-gray-500')
     
            async def _on_upload(e):
                await self.handle_upload(e, dialog)
     
            ui.upload(
                on_upload=_on_upload,
                auto_upload=True,
                max_files=5,
            ).props('accept=.docx,.pdf,.txt,.md,.xlsx').classes('w-full')
     
        dialog.open()
     
     #文件上传函数
    async def handle_upload(self, e, dialog):
        real_file = e.file
        display_name = getattr(real_file, 'name', getattr(real_file, 'filename', '未知文件'))
     
        ui.notify(f"正在上传 {display_name}...", type='info', timeout=1500)
     
        file_id = await self.backend.upload_file(real_file)  # 返回 file_id
        if not file_id:
            ui.notify("上传失败", type='negative')
            return
     
        # 加入“待发送附件”
        self.pending_attachments.append({'file_id': file_id, 'filename': display_name})
        # 加入当前会话的文件记忆
        self.session_file_ids.add(file_id)
        self.refresh_attachment_bar()
     
       
     
        ui.notify(f"已添加附件：{display_name}", type='positive', timeout=1500)
        dialog.close()



@ui.page('/')
def main():
    # === 这里的 CSS 是界面美化的关键 ===
    ui.add_head_html('''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
        body {
            font-family: 'Inter', sans-serif;
            background-color: white;
        }
        
        /* === 1.  Markdown 标题的大小  === */
        .nicegui-markdown h1 { font-size: 1.5rem; line-height: 2rem; font-weight: 700; margin-bottom: 1rem; margin-top: 1.5rem; }
        .nicegui-markdown h2 { font-size: 1.25rem; line-height: 1.75rem; font-weight: 600; margin-bottom: 0.75rem; margin-top: 1.25rem; }
        .nicegui-markdown h3 { font-size: 1.125rem; line-height: 1.75rem; font-weight: 600; margin-bottom: 0.5rem; margin-top: 1rem; }
        
        /* === 2. 美化代码块 (类 ChatGPT 的深色风格) === */
        .nicegui-markdown pre {
            background-color: #1e1e1e;  /* 深色背景 */
            color: #d4d4d4;             /* 浅灰文字 */
            padding: 1rem;              /* 内边距 */
            border-radius: 0.5rem;      /* 圆角 */
            overflow-x: auto;           /* 横向滚动条 */
            margin: 0.75rem 0;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .nicegui-markdown code {
            /* 行内代码 (如 `variable`) 的样式 */
            background-color: #f3f4f6;
            color: #ef4444; /* 红色高亮 */
            padding: 0.2rem 0.4rem;
            border-radius: 0.25rem;
            font-family: monospace;
            font-size: 0.9em;
        }
        
        /* 修复代码块内的 code 标签不需要背景色，否则会有重叠 */
        .nicegui-markdown pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
        }

        /* === 3. 隐藏滚动条但保留功能 === */
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        
        /* === 4. 输入框调整 === */
        .chat-input textarea {
            padding-top: 12px !important;
            padding-bottom: 12px !important;
            line-height: 1.6 !important;
        }
    </style>
    ''')
    
    ui.page_title('Software A Agent')
    session = ChatSession()
    session.build_ui()

ui.run(port=8080, title="Software A", favicon="🤖")

