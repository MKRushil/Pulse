# -*- coding: utf-8 -*-
"""
輔助函數
"""

import uuid

def gen_trace_id(prefix="SCBR"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
