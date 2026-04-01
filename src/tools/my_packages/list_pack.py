from typing import Any, Dict, List, Optional


def _as_list(obj):
    """将输入值转换为列表。如果输入值为None，则返回None；如果输入值已经是列表，则直接返回；如果输入值是元组，则将其转换为列表；否则，将输入值放入一个新的列表中返回。"""
    if obj is None:
        return None
    
    try:
        res = obj.tolist()
    except Exception:
        res = obj

    if isinstance(res, (list, tuple)):
        return list(res)
    return [res]


def object_to_list(obj: Optional[Any]) -> Optional[List[Any]]:
    """将输入对象转换为列表。如果输入对象为None，则返回None；如果输入对象具有tolist方法，则调用该方法获取候选值；否则，直接使用输入对象作为候选值。最后，将候选值安全地转换为列表返回。"""
    if obj is None:
        return None
    try:
        if hasattr(obj, "tolist"):
            candidate = obj.tolist()
        else:
            candidate = obj
    except Exception:
        candidate = obj
    return _as_list(candidate)