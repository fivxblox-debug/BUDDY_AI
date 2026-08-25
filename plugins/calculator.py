"""Safe calculator plugin for JARVIS."""
import ast, math, operator

PLUGIN = {
    "name": "calculator",
    "description": "Evaluate arithmetic and common math expressions safely. Use for calculations, percentages, powers, roots, trigonometry, and conversions that can be expressed as formulas.",
    "parameters": {"type":"OBJECT","properties":{"expression":{"type":"STRING","description":"Math expression to evaluate."}},"required":["expression"]},
}

BIN = {ast.Add:operator.add, ast.Sub:operator.sub, ast.Mult:operator.mul, ast.Div:operator.truediv,
       ast.FloorDiv:operator.floordiv, ast.Mod:operator.mod, ast.Pow:operator.pow}
UN = {ast.UAdd:operator.pos, ast.USub:operator.neg}
FUN = {k:getattr(math,k) for k in ("sqrt","sin","cos","tan","asin","acos","atan","log","log10","exp","ceil","floor","fabs")}
FUN.update({"abs":abs,"round":round,"min":min,"max":max})
CONST = {"pi":math.pi,"e":math.e,"tau":math.tau}

def _eval(n):
    if isinstance(n, ast.Expression): return _eval(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value,(int,float)): return n.value
    if isinstance(n, ast.Name) and n.id in CONST: return CONST[n.id]
    if isinstance(n, ast.UnaryOp) and type(n.op) in UN: return UN[type(n.op)](_eval(n.operand))
    if isinstance(n, ast.BinOp) and type(n.op) in BIN:
        a,b=_eval(n.left),_eval(n.right)
        if type(n.op) is ast.Pow and abs(b)>1000: raise ValueError("Exponent too large")
        return BIN[type(n.op)](a,b)
    if isinstance(n, ast.Call) and isinstance(n.func,ast.Name) and n.func.id in FUN and not n.keywords:
        return FUN[n.func.id](*[_eval(x) for x in n.args])
    raise ValueError("Unsupported expression")

def run(parameters, player=None, session_memory=None):
    try:
        expr=str((parameters or {}).get("expression","")).strip().replace("^","**")
        if not expr: return "CALC ERROR: expression is empty."
        if len(expr)>500: return "CALC ERROR: expression is too long."
        value=_eval(ast.parse(expr,mode="eval"))
        if isinstance(value,float) and not math.isfinite(value): return "CALC ERROR: result is not finite."
        return f"{expr} = {value:.12g}" if isinstance(value,float) else f"{expr} = {value}"
    except Exception as e:
        return f"CALC ERROR: {e}"
