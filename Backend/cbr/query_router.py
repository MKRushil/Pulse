# cbr/query_router.py
from cbr.spiral_a import spiral_a_query
from cbr.spiral_b import spiral_b_query

def route_query(data: dict):
    """
    自動判斷查詢資料是否有 id（身分/個案），決定走方案A或B
    """
    query_text = data.get("query", "")
    pid = data.get("id", None)
    top_n = data.get("top_n", 5)
    if pid:
        return spiral_b_query(pid, query_text, top_n=top_n)
    else:
        return spiral_a_query(query_text, top_n=top_n)
