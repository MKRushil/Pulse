from s_cbr.sessions.spiral_session_manager import SpiralSessionManager

# 1. 初始化
mgr = SpiralSessionManager(max_sessions=5)

# 2. 創建新會話
sid = mgr.create_session("患者頭痛、失眠")
print("新會話 ID:", sid)

# 3. 獲取或創建
sess = mgr.get_or_create_session(sid, "患者頭痛、失眠")
print("會話狀態:", sess.to_dict())

# 4. 模擬使用案例、輪次
sess.increment_round()
sess.add_used_case("case_001")
print("更新後狀態:", sess.to_dict())

# 5. 重置並確認
mgr.reset_session(sid)
print("重置後會話列表:", mgr.get_sessions_info())
