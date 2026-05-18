"""主窗口 —— 布局组装与信号/槽编排。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStatusBar, QLabel, QMessageBox,
)

from live_agent.keyword import KeywordMatcher
from live_agent.gui.rule_store import RuleStore
from live_agent.gui.audio_manager import AudioManager
from live_agent.gui.workers import AsrWorker
from live_agent.gui.session_panel import SessionPanel
from live_agent.gui.rule_table import RuleTable
from live_agent.gui.rule_editor import RuleEditor

VOICE_SHORT = {
    "zh-CN-XiaoxiaoNeural": "晓晓",
    "zh-CN-YunxiNeural": "云希",
    "zh-CN-YunyangNeural": "云扬",
    "zh-CN-XiaohanNeural": "晓涵",
    "zh-CN-XiaoyanNeural": "晓颜",
    "zh-CN-XiaoshuangNeural": "晓双",
    "zh-CN-XiaochenNeural": "晓辰",
}


class MainWindow(QMainWindow):
    """直播语音助手主窗口。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("直播语音助手")
        self.setMinimumSize(700, 550)
        self.resize(800, 600)

        self._rule_store = RuleStore()
        self._audio_manager = AudioManager(self._rule_store.storage_dir)
        self._matcher: KeywordMatcher | None = None
        self._asr_worker: AsrWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self._session_panel = SessionPanel()
        main_layout.addWidget(self._session_panel)

        self._rule_table = RuleTable()
        main_layout.addWidget(self._rule_table, stretch=1)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._connect_signals()
        self._on_rules_changed()

        rules = self._rule_store.get_all()
        missing = [r for r in rules if not self._audio_manager.has_audio(r.id)]
        if missing:
            self._audio_manager.generate_all(missing)

    def _connect_signals(self) -> None:
        self._session_panel.start_btn.clicked.connect(self._on_start)
        self._session_panel.stop_btn.clicked.connect(self._on_stop)
        self._rule_table.add_clicked.connect(self._on_add_rule)
        self._rule_table.edit_clicked.connect(self._on_edit_rule)
        self._rule_table.delete_clicked.connect(self._on_delete_rule)
        self._rule_table.generate_clicked.connect(self._on_generate_all)
        self._rule_store.rules_changed.connect(self._on_rules_changed)
        self._audio_manager.generation_progress.connect(self._on_gen_progress)
        self._audio_manager.generation_complete.connect(self._on_gen_complete)
        self._audio_manager.rule_audio_ready.connect(self._on_audio_ready)

    # -- Session ----------------------------------------------------------

    def _on_start(self) -> None:
        if self._asr_worker is not None and self._asr_worker.isRunning():
            return
        self._matcher = KeywordMatcher(self._rule_store.get_keyword_replies())
        self._session_panel.clear()
        self._session_panel.set_listening(True)
        self._asr_worker = AsrWorker(model_dir="models")
        self._asr_worker.text_recognized.connect(self._on_text_recognized)
        self._asr_worker.error_occurred.connect(self._on_asr_error)
        self._asr_worker.start()

    def _on_stop(self) -> None:
        if self._asr_worker is not None:
            self._asr_worker.stop()
            self._asr_worker = None
        self._matcher = None
        self._session_panel.set_listening(False)

    # -- Text recognition -------------------------------------------------

    def _on_text_recognized(self, text: str) -> None:
        self._session_panel.text_display.setPlainText(text)
        if self._matcher is None:
            return
        hit = self._matcher.check(text)
        if hit is not None:
            rule = self._rule_store.get_by_keyword(hit.keyword)
            if rule is None:
                return
            voice_name = VOICE_SHORT.get(rule.voice, rule.voice)
            self._session_panel.show_hit(hit.keyword, rule.reply, voice_name)
            self._audio_manager.play(rule.id)

    def _on_asr_error(self, error: str) -> None:
        self._session_panel.set_listening(False)
        QMessageBox.critical(self, "ASR 错误", f"语音识别出错:\n{error}")

    # -- Rule CRUD --------------------------------------------------------

    def _on_add_rule(self) -> None:
        editor = RuleEditor(self)
        if editor.exec() == RuleEditor.Accepted:
            rule = editor.get_rule()
            self._rule_store.add(rule)
            self._audio_manager.generate_one(rule)

    def _on_edit_rule(self, rule_id: str) -> None:
        rule = self._rule_store.get_by_id(rule_id)
        if rule is None:
            return
        editor = RuleEditor(self, rule=rule)
        if editor.exec() == RuleEditor.Accepted:
            updated = editor.get_rule()
            self._rule_store.update(updated)
            self._audio_manager.generate_one(updated)

    def _on_delete_rule(self, rule_id: str) -> None:
        rule = self._rule_store.get_by_id(rule_id)
        if rule is None:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除规则「{rule.keyword}」吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._rule_store.delete(rule_id)

    def _on_generate_all(self) -> None:
        rules = self._rule_store.get_all()
        if rules:
            self._audio_manager.generate_all(rules)

    # -- Rule changes -----------------------------------------------------

    def _on_rules_changed(self) -> None:
        rules = self._rule_store.get_all()
        self._rule_table.refresh(rules, self._audio_manager)
        if self._matcher is not None:
            self._matcher.update_rules(self._rule_store.get_keyword_replies())
        ready = sum(1 for r in rules if self._audio_manager.has_audio(r.id))
        self._status_bar.showMessage(f"音频: {ready}/{len(rules)} 就绪", 0)

    # -- Audio generation -------------------------------------------------

    def _on_gen_progress(self, current: int, total: int) -> None:
        self._status_bar.showMessage(f"生成音频中... {current}/{total}", 0)

    def _on_gen_complete(self) -> None:
        rules = self._rule_store.get_all()
        ready = sum(1 for r in rules if self._audio_manager.has_audio(r.id))
        self._status_bar.showMessage(f"音频: {ready}/{len(rules)} 就绪", 0)
        self._rule_table.refresh(rules, self._audio_manager)

    def _on_audio_ready(self, rule_id: str) -> None:
        rules = self._rule_store.get_all()
        self._rule_table.refresh(rules, self._audio_manager)

    # -- Shutdown ---------------------------------------------------------

    def closeEvent(self, event) -> None:
        if self._asr_worker is not None:
            self._asr_worker.stop()
            self._asr_worker = None
        event.accept()
