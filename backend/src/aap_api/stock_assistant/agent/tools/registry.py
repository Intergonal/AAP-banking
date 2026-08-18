TOOL_REGISTRY: dict[str, dict] = {}


def tool(name=None, category="core"):
    def decorator(func):
        tool_name = name or func.__name__
        TOOL_REGISTRY[tool_name] = {
            "function": func,
            "category": category,
        }
        return func

    return decorator


def get_tools(categories=None):
    if categories is None:
        return [entry["function"] for entry in TOOL_REGISTRY.values()]
    return [
        entry["function"]
        for entry in TOOL_REGISTRY.values()
        if entry["category"] in categories
    ]


def get_tool_list():
    return [
        {"name": name, "category": entry["category"]}
        for name, entry in TOOL_REGISTRY.items()
    ]
