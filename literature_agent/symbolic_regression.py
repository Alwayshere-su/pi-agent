# -*- coding: utf-8 -*-
"""
轻量遗传编程符号回归（Symbolic Regression via Genetic Programming）
====================================================================

仅依赖 Python 标准库 + numpy，不引入任何第三方符号回归库。

核心功能：
  - 表达式树表示（+ - * / 平方/exp/log/sqrt/sin + 常量/变量终端）
  - 标准遗传编程流程：种群初始化（ramped half-half + 模板播种）、
    锦标赛选择、子树交叉、多种变异、精英保留、适应度 = MSE
  - Lamarckian 常量微调（坐标下降）：同一树结构下快速逼近最优参数，
    使 a*x^2+b*x+c 这类参数化结构可以精确恢复
  - 安全可审计的表达式字符串（c0/c1/... 为参数占位符，x/x0/x1 为变量），
    配合 predict() 可在外部重新计算，便于 R²/RMSE 校验

对外接口：
  fit(X, y, max_generations=100, pop_size=50, seed=None)
      -> (expr_str, params, mse)
  predict(expr_str, params, X) -> np.ndarray    # 由表达式字符串安全求值
  evaluate(expr_str, params, x) -> float        # 标量求值（便捷）
  __main__ 自检：合成 a*x^2+b*x+c，断言 MSE 极小
"""
from __future__ import annotations

import ast
import math
import random
import sys

import numpy as np

# ═══════════════════════════════════════════════════════════════
# 算子集合
# ═══════════════════════════════════════════════════════════════

_BINARY_OPS = ("add", "sub", "mul", "div")
_UNARY_OPS = ("square", "exp", "log", "sqrt", "sin")
_TERMINAL_CONST = "const"
_TERMINAL_VAR = "var"

_DEPTH_MIN = 2      # 随机树最小深度
_DEPTH_MAX = 5      # 随机树最大深度
_EPS = 1e-12        # 除零/对数/开方保护


# ═══════════════════════════════════════════════════════════════
# 表达式树
# ═══════════════════════════════════════════════════════════════

class _Node:
    """表达式树节点。

    字段：
      op      算子/终端名：add/sub/mul/div/square/exp/log/sqrt/sin
              或 const / var
      children 子节点元组（二元算子 2 个、一元算子 1 个、终端 0 个）
      value   终端附加值：const → 常量数值；var → 特征列索引
    """
    __slots__ = ("op", "children", "value")

    def __init__(self, op: str, children: tuple = (), value: float = 0.0):
        self.op = op
        self.children = tuple(children)
        self.value = float(value)

    # ── 结构操作 ──

    def copy(self) -> "_Node":
        return _Node(self.op, tuple(c.copy() for c in self.children), self.value)

    def depth(self) -> int:
        if not self.children:
            return 1
        return 1 + max(c.depth() for c in self.children)

    def size(self) -> int:
        return 1 + sum(c.size() for c in self.children)

    def _const_nodes(self):
        """先序收集所有常量节点。"""
        if self.op == _TERMINAL_CONST:
            yield self
        for c in self.children:
            yield from c._const_nodes()

    def _var_indices(self):
        """所有变量节点的列索引集合。"""
        if self.op == _TERMINAL_VAR:
            yield int(self.value)
        for c in self.children:
            yield from c._var_indices()

    # ── 求值 ──

    def eval(self, X: np.ndarray) -> np.ndarray:
        """向量化求值。X: (n, m) numpy 数组，返回 (n,) 数组。"""
        if self.op == _TERMINAL_CONST:
            return np.full(X.shape[0], self.value, dtype=float)
        if self.op == _TERMINAL_VAR:
            col = int(self.value)
            if col < X.shape[1]:
                return X[:, col].astype(float, copy=False)
            return np.zeros(X.shape[0], dtype=float)

        vals = [c.eval(X) for c in self.children]
        if self.op == "add":
            return vals[0] + vals[1]
        if self.op == "sub":
            return vals[0] - vals[1]
        if self.op == "mul":
            return vals[0] * vals[1]
        if self.op == "div":
            return vals[0] / (np.abs(vals[1]) + _EPS)
        if self.op == "square":
            return vals[0] * vals[0]
        if self.op == "exp":
            # 限制指数范围避免溢出
            return np.exp(np.clip(vals[0], -40.0, 40.0))
        if self.op == "log":
            return np.log(np.abs(vals[0]) + _EPS)
        if self.op == "sqrt":
            return np.sqrt(np.abs(vals[0]))
        if self.op == "sin":
            return np.sin(vals[0])
        # 未知算子（防御）：返回 0
        return np.zeros(X.shape[0], dtype=float)

    # ── 字符串化（分配 c0/c1/... 参数名）──

    def to_expr(self, const_names: dict) -> str:
        """生成表达式字符串；const_names 记录 {id(node): "cN"}。"""
        if self.op == _TERMINAL_CONST:
            name = const_names.setdefault(id(self), f"c{len(const_names)}")
            return name
        if self.op == _TERMINAL_VAR:
            return f"x{int(self.value)}" if int(self.value) > 0 else "x"
        if self.op == "add":
            return "(" + self.children[0].to_expr(const_names) + " + " \
                   + self.children[1].to_expr(const_names) + ")"
        if self.op == "sub":
            return "(" + self.children[0].to_expr(const_names) + " - " \
                   + self.children[1].to_expr(const_names) + ")"
        if self.op == "mul":
            return "(" + self.children[0].to_expr(const_names) + " * " \
                   + self.children[1].to_expr(const_names) + ")"
        if self.op == "div":
            return "(" + self.children[0].to_expr(const_names) + " / " \
                   + self.children[1].to_expr(const_names) + ")"
        if self.op == "square":
            return "(" + self.children[0].to_expr(const_names) + "^2)"
        if self.op in ("exp", "log", "sqrt", "sin"):
            inner = self.children[0].to_expr(const_names)
            return f"{self.op}({inner})"
        return "0.0"


def _simplify_expr(s: str) -> str:
    """轻度美化表达式字符串：x*x → x^2、+ - → -、去冗余外层括号。"""
    s = s.replace("(x * x)", "x^2")
    s = s.replace("+ -", "- ").replace("- -", "+ ")
    # 去掉最外层括号（仅当去掉不改变结构时）
    if s.startswith("(") and s.endswith(")"):
        depth = 0
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i < len(s) - 1:
                    return s  # 内层还有内容，保留外层括号
        s = s[1:-1]
    return s


def expr_str_of(node: _Node) -> str:
    """返回 (表达式字符串) 主入口：分配常量名后美化。"""
    const_names: dict = {}
    expr = node.to_expr(const_names)
    return _simplify_expr(expr)


def const_map_of(node: _Node) -> dict:
    """返回 {参数名: 常量值} 字典，与 expr_str_of 顺序一致。"""
    const_names: dict = {}
    node.to_expr(const_names)  # 触发同样的先序分配
    values = {}
    for node_id, name in const_names.items():
        # 通过再次遍历按同名分配（to_expr 对相同结构确定性分配）
        values[name] = 0.0
    # 安全做法：按先序重新收集常量，名称按 id 对齐
    const_nodes = list(node._const_nodes())
    ordered_ids = [n_id for n_id in const_names]  # 分配顺序
    by_id = {id(c): c for c in const_nodes}
    for n_id in ordered_ids:
        cnode = by_id.get(n_id)
        if cnode is not None:
            values[const_names[n_id]] = float(cnode.value)
    return values


# ═══════════════════════════════════════════════════════════════
# 随机树生成（ramped half-half + 模板播种）
# ═══════════════════════════════════════════════════════════════

def _random_terminal(n_vars: int, rng: random.Random) -> _Node:
    if rng.random() < 0.5:
        return _Node(_TERMINAL_CONST, value=rng.uniform(-3.0, 3.0))
    return _Node(_TERMINAL_VAR, value=rng.randrange(n_vars))


def _grow_tree(max_depth: int, n_vars: int, rng: random.Random) -> _Node:
    if max_depth <= 1 or (max_depth < _DEPTH_MAX and rng.random() < 0.4):
        return _random_terminal(n_vars, rng)
    if rng.random() < 0.35:  # 一元算子
        op = rng.choice(_UNARY_OPS)
        return _Node(op, (_grow_tree(max_depth - 1, n_vars, rng),))
    op = rng.choice(_BINARY_OPS)
    return _Node(op, (_grow_tree(max_depth - 1, n_vars, rng),
                      _grow_tree(max_depth - 1, n_vars, rng)))


def _random_tree(n_vars: int, rng: random.Random) -> _Node:
    """ramped half-half：深度在 [_DEPTH_MIN, _DEPTH_MAX] 均匀取。"""
    depth = rng.randrange(_DEPTH_MIN, _DEPTH_MAX + 1)
    return _grow_tree(depth, n_vars, rng)


def _template_poly2(n_vars: int) -> _Node:
    """c0*x^2 + c1*x + c2（仅单变量有意义；多变量退化为 x0^2 结构）。"""
    var = _Node(_TERMINAL_VAR, value=0)
    c0 = _Node(_TERMINAL_CONST, value=1.0)
    c1 = _Node(_TERMINAL_CONST, value=-1.0)
    c2 = _Node(_TERMINAL_CONST, value=1.0)
    term2 = _Node("mul", (_Node("mul", (c0, var)), var))
    term1 = _Node("mul", (c1, var))
    return _Node("add", (term2, _Node("add", (term1, c2))))


def _template_linear(n_vars: int) -> _Node:
    """c0*x + c1。"""
    var = _Node(_TERMINAL_VAR, value=0)
    c0 = _Node(_TERMINAL_CONST, value=1.0)
    c1 = _Node(_TERMINAL_CONST, value=1.0)
    return _Node("add", (_Node("mul", (c0, var)), c1))


def _template_exp(n_vars: int) -> _Node:
    """c0*exp(c1*x) + c2。"""
    var = _Node(_TERMINAL_VAR, value=0)
    c0 = _Node(_TERMINAL_CONST, value=1.0)
    c1 = _Node(_TERMINAL_CONST, value=0.3)
    c2 = _Node(_TERMINAL_CONST, value=0.0)
    return _Node("add", (_Node("mul", (c0, _Node("exp", (_Node("mul", (c1, var)),)))),
                         c2))


def _template_power(n_vars: int) -> _Node:
    """c0 * x^c1 + c2，用 exp(c1*log(x)) 表示 x^c1。"""
    var = _Node(_TERMINAL_VAR, value=0)
    c0 = _Node(_TERMINAL_CONST, value=1.0)
    c1 = _Node(_TERMINAL_CONST, value=1.5)
    c2 = _Node(_TERMINAL_CONST, value=0.0)
    logx = _Node("log", (var,))
    xp = _Node("exp", (_Node("mul", (c1, logx)),))
    return _Node("add", (_Node("mul", (c0, xp)), c2))


# ═══════════════════════════════════════════════════════════════
# 适应度 / 常量微调（Lamarckian 坐标下降）
# ═══════════════════════════════════════════════════════════════

def _mse(node: _Node, X: np.ndarray, y: np.ndarray) -> float:
    try:
        pred = node.eval(X)
    except Exception:
        return float("inf")
    if not np.all(np.isfinite(pred)):
        return float("inf")
    return float(np.mean((pred - y) ** 2))


def _tune_constants(node: _Node, X: np.ndarray, y: np.ndarray,
                    iters: int = 40) -> tuple:
    """坐标下降微调所有常量，返回 (node, mse)。

    同一表达式结构下，常量对 MSE 通常是近似光滑的，坐标下降
    配合自适应步长可在几十轮内收敛（对多项式/指数均可）。
    """
    consts = list(node._const_nodes())
    if not consts:
        return node, _mse(node, X, y)
    steps = [max(0.5 * abs(c.value), 0.05) if abs(c.value) > 1e-9 else 0.05
             for c in consts]
    best = _mse(node, X, y)
    for _ in range(iters):
        improved_any = False
        for i, c in enumerate(consts):
            improved_c = False
            for sign in (1.0, -1.0):
                c.value += sign * steps[i]
                cur = _mse(node, X, y)
                if cur < best - 1e-15:
                    best = cur
                    improved_c = True
                    improved_any = True
                else:
                    c.value -= sign * steps[i]
            if not improved_c:
                steps[i] *= 0.7  # 该常量本轮无改进，缩小步长
        if not improved_any and max(steps) < 1e-10:
            break
    return node, best


# ═══════════════════════════════════════════════════════════════
# 遗传算子
# ═══════════════════════════════════════════════════════════════

def _collect_subtrees(node: _Node) -> list:
    out = [node]
    for c in node.children:
        out.extend(_collect_subtrees(c))
    return out


def _crossover(p1: _Node, p2: _Node, rng: random.Random) -> _Node:
    """子树交叉：随机交换一个子树，控制后代深度防止爆炸。"""
    c1 = p1.copy()
    c2 = p2.copy()
    st1 = _collect_subtrees(c1)
    st2 = _collect_subtrees(c2)
    s1 = rng.choice(st1)
    s2 = rng.choice(st2)

    def _replace(node: _Node, target, repl) -> _Node:
        if node is target:
            return repl.copy()
        return _Node(node.op, tuple(_replace(c, target, repl) for c in node.children),
                     node.value)

    child1 = _replace(c1, s1, s2)
    child2 = _replace(c2, s2, s1)
    if rng.random() < 0.5:
        child = child1
    else:
        child = child2
    # 深度限制：过深的后代退化为父个体副本，避免树结构无节制膨胀
    if child.depth() > 9:
        return p1.copy()
    return child


def _mutate(node: _Node, n_vars: int, rng: random.Random) -> _Node:
    """三种变异：子树替换 / 常量扰动 / 单点算子替换。"""
    r = rng.random()
    if r < 0.4:
        # 子树替换
        sub = _collect_subtrees(node)
        target = rng.choice(sub)
        new_sub = _grow_tree(rng.randrange(1, _DEPTH_MAX), n_vars, rng)
        def _replace(n: _Node) -> _Node:
            if n is target:
                return new_sub
            return _Node(n.op, tuple(_replace(c) for c in n.children), n.value)
        return _replace(node)
    if r < 0.75:
        # 常量扰动
        consts = list(node._const_nodes())
        if not consts:
            return _mutate(node, n_vars, rng)
        c = rng.choice(consts)
        c.value += rng.gauss(0.0, 0.5)
        return node
    # 单点算子替换
    return _mutate_subtree_op(node, rng)


def _mutate_subtree_op(node: _Node, rng: random.Random) -> _Node:
    """随机替换一个内部节点的算子为同元数算子。"""
    inner = [n for n in _collect_subtrees(node)
             if n.op in _BINARY_OPS or n.op in _UNARY_OPS]
    if not inner:
        return node
    target = rng.choice(inner)
    if target.op in _BINARY_OPS:
        target.op = rng.choice(_BINARY_OPS)
    else:
        target.op = rng.choice(_UNARY_OPS)
    return node


# ═══════════════════════════════════════════════════════════════
# 主流程：fit
# ═══════════════════════════════════════════════════════════════

def fit(X, y, max_generations: int = 100, pop_size: int = 50,
        seed: int = None, verbose: bool = False):
    """运行遗传编程符号回归。

    Args:
        X: 输入特征，一维 (n,) 或多维 (n, m) 数组。
        y: 目标值，一维 (n,) 数组。
        max_generations: 最大进化代数（默认 100）。
        pop_size: 种群规模（默认 50）。
        seed: 随机种子（None 表示不固定）。
        verbose: 是否打印进化日志。

    Returns:
        (expr_str, params, mse)
          expr_str: 表达式字符串（c0/c1/... 为参数占位符，x/x0/x1 为变量）
          params:   {参数名: 值} 字典
          mse:      最优个体在训练集上的均方误差
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    if X.shape[0] != y.shape[0] or X.shape[0] < 3:
        raise ValueError("X 与 y 长度必须一致且至少 3 个样本")

    rng = random.Random(seed)
    n_vars = X.shape[1]

    # ── 种群初始化：模板播种（仅单变量）+ 随机树 ──
    population = []
    if n_vars == 1:
        population.extend([
            _template_linear(n_vars),
            _template_poly2(n_vars),
            _template_exp(n_vars),
            _template_power(n_vars),
        ])
    while len(population) < pop_size:
        population.append(_random_tree(n_vars, rng))

    # ── 适应度：粗调（每代 3 轮坐标下降，控制成本）──
    # Lamarckian 风格：直接在个体上微调常量，微调结果写回个体，
    # 使结构与常量共同进化，后代继承优化后的常量。
    def _fitness(node):
        return _tune_constants(node, X, y, iters=3)[1]

    best_node, best_mse = None, float("inf")
    gen = 0
    for gen in range(max_generations):
        scored = [(node, _fitness(node)) for node in population]
        scored.sort(key=lambda t: t[1])
        # 精英保留 top 2
        elite = [scored[0][0].copy(), scored[1][0].copy()]

        # 深度微调（每 5 代对 top-5 精确化）
        if gen % 5 == 0:
            for i in range(min(5, len(scored))):
                scored[i] = (scored[i][0], _tune_constants(scored[i][0], X, y, iters=20)[1])
            scored.sort(key=lambda t: t[1])

        if scored[0][1] < best_mse:
            best_mse = scored[0][1]
            best_node = scored[0][0].copy()

        if verbose and (gen % 20 == 0 or gen == max_generations - 1):
            print(f"[symbolic_regression] gen {gen + 1}/{max_generations} "
                  f"best MSE = {best_mse:.6e}")

        if best_mse < 1e-12:
            gen += 1
            break  # 已完美拟合，提前终止

        # ── 生成下一代：锦标赛 + 交叉/变异 ──
        next_gen = elite
        while len(next_gen) < pop_size:
            def _tournament():
                k = rng.randrange(2, 5)
                cands = rng.sample(scored, min(k, len(scored)))
                return min(cands, key=lambda t: t[1])[0]
            p1, p2 = _tournament(), _tournament()
            if rng.random() < 0.85:
                child = _crossover(p1, p2, rng)
            else:
                child = _random_tree(n_vars, rng)
            if rng.random() < 0.4:
                child = _mutate(child, n_vars, rng)
            next_gen.append(child)
        population = next_gen

    # ── 最终精确化 ──
    if best_node is None:
        best_node = _random_tree(n_vars, rng)
    best_node, best_mse = _tune_constants(best_node, X, y, iters=80)

    # 兜底：如果 GP 未优于线性模板，检查模板池
    if n_vars == 1:
        for tmpl in (_template_linear(n_vars), _template_poly2(n_vars),
                     _template_exp(n_vars), _template_power(n_vars)):
            t_node, t_mse = _tune_constants(tmpl, X, y, iters=60)
            if t_mse < best_mse:
                best_node, best_mse = t_node, t_mse

    expr_str = expr_str_of(best_node)
    params = const_map_of(best_node)
    return expr_str, params, best_mse


# ═══════════════════════════════════════════════════════════════
# 安全求值：由表达式字符串 + 参数重建预测值
# ═══════════════════════════════════════════════════════════════

def _build_evaluator(expr_str: str, params: dict):
    """把表达式字符串解析为 (X) -> np.ndarray 的求值函数。

    仅允许安全子集：数字、+ - * / ^、函数 exp/log/sqrt/sin、
    变量 x / x0.. / c{i} 参数占位符。使用 ast 而非 eval，杜绝任意代码执行。
    """
    for key in params:
        if not isinstance(key, str) or not key.startswith("c"):
            raise ValueError(f"非法参数名: {key}")

    # 用 ast 解析并转为可执行的数值表达式
    tree = ast.parse(expr_str.replace("^", "**"), mode="eval")

    # 数组安全的数学函数（predict 的输入是 numpy 数组，math.* 仅支持标量）
    # 域保护（2026-08 修复）：log/log10/sqrt/tan/exp 对域外输入（x≤0、大值）会
    # 产生 NaN/Inf，导致 predict 抛"非有限值"异常、symbolic_regression 工具崩溃。
    # 对域外输入截断到有限值——不适用的表达式由 MSE 自然淘汰，不污染整体流程。
    def _safe_log(a):
        return np.log(np.maximum(a, _EPS))

    def _safe_log10(a):
        return np.log10(np.maximum(a, _EPS))

    def _safe_sqrt(a):
        return np.sqrt(np.maximum(a, 0.0))

    def _safe_tan(a):
        return np.tan(np.clip(a, -1e9, 1e9))

    def _safe_exp(a):
        # exp 大输入溢出为 Inf：clip 到 ±700（exp(700)≈1e304，双精度安全上限内）
        return np.exp(np.clip(a, -700.0, 700.0))

    _NP_FUNCS = {
        "exp": _safe_exp, "log": _safe_log, "log10": _safe_log10, "sqrt": _safe_sqrt,
        "sin": np.sin, "cos": np.cos, "tan": _safe_tan,
        "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
        "abs": np.abs,
    }

    def _eval_node(nd, env):
        if isinstance(nd, ast.Expression):
            return _eval_node(nd.body, env)
        if isinstance(nd, ast.Constant):
            return float(nd.value)
        if isinstance(nd, ast.Name):
            name = nd.id
            if name in params:
                return params[name]
            if name == "x":
                return env["x"]
            if name.startswith("x") and name[1:].isdigit():
                idx = int(name[1:])
                return env["xcol"](idx)
            if name in _NP_FUNCS:
                return _NP_FUNCS[name]
            if hasattr(math, name):
                return getattr(math, name)
            raise ValueError(f"未知标识符: {name}")
        if isinstance(nd, ast.BinOp):
            left = _eval_node(nd.left, env)
            right = _eval_node(nd.right, env)
            if isinstance(nd.op, ast.Add):
                return left + right
            if isinstance(nd.op, ast.Sub):
                return left - right
            if isinstance(nd.op, ast.Mult):
                return left * right
            if isinstance(nd.op, ast.Div):
                return left / (np.abs(right) + _EPS)
            if isinstance(nd.op, ast.Pow):
                return left ** right
            raise ValueError(f"不支持的运算符: {type(nd.op).__name__}")
        if isinstance(nd, ast.Call):
            fn = _eval_node(nd.func, env)
            args = [_eval_node(a, env) for a in nd.args]
            return fn(*args)
        if isinstance(nd, ast.UnaryOp) and isinstance(nd.op, ast.USub):
            return -_eval_node(nd.operand, env)
        if isinstance(nd, ast.UnaryOp) and isinstance(nd.op, ast.UAdd):
            return _eval_node(nd.operand, env)
        raise ValueError(f"不支持的语法节点: {type(nd).__name__}")

    def fn(X):
        X = np.asarray(X, dtype=float)
        single = X.ndim == 0
        if X.ndim == 0:
            X = np.array([[X]])
        elif X.ndim == 1:
            X = X.reshape(-1, 1)
        env = {
            "x": X[:, 0],
            "xcol": lambda i: X[:, int(i)] if int(i) < X.shape[1]
            else np.zeros(X.shape[0]),
        }
        out = _eval_node(tree, env)
        if isinstance(out, (int, float)):
            out = np.full(X.shape[0], float(out))
        out = np.asarray(out, dtype=float)
        if not np.all(np.isfinite(out)):
            raise ValueError("表达式在给定输入上产生非有限值")
        if single:
            return float(out)
        return out

    return fn


def predict(expr_str: str, params: dict, X):
    """由表达式字符串与参数计算预测值（numpy 数组或标量）。"""
    return _build_evaluator(expr_str, params)(X)


def evaluate(expr_str: str, params: dict, x: float) -> float:
    """标量便捷求值。"""
    return float(_build_evaluator(expr_str, params)(np.array([[x]]))[0])


def r2_score(y_true, y_pred) -> float:
    """R² 计算（外部校验用）。"""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    if ss_tot <= 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


# ═══════════════════════════════════════════════════════════════
# 自检：合成 a*x^2 + b*x + c
# ═══════════════════════════════════════════════════════════════

def _self_test() -> int:
    """合成数据恢复测试：y = 2*x^2 - 3*x + 1。

    断言：
      1. fit 返回 MSE 足够小（坐标下降收敛）。
      2. 表达式在样本点上与真值一致（predict 一致性）。
    返回 0 表示通过。
    """
    x = np.linspace(-2.0, 2.0, 60)
    # 无噪声合成数据：y = 2*x^2 - 3*x + 1（保证可精确恢复）
    y = 2.0 * x ** 2 - 3.0 * x + 1.0

    expr_str, params, mse = fit(x, y, max_generations=100, pop_size=50, seed=7)
    print(f"[self-test] 恢复表达式: {expr_str}")
    print(f"[self-test] 参数: {params}")
    print(f"[self-test] MSE = {mse:.6e}")

    assert mse < 1e-8, f"自检失败: MSE={mse:.3e} 应 < 1e-8"
    # predict 一致性：表达式字符串重建结果与训练数据吻合
    y_pred = predict(expr_str, params, x)
    r2 = r2_score(y, y_pred)
    print(f"[self-test] R² = {r2:.6f}")
    assert r2 > 0.999999, f"自检失败: R²={r2:.4f} 应 > 0.999999"

    # 再验证一个指数关系（可恢复性拓展，无噪声）
    x2 = np.linspace(0.1, 2.0, 50)
    y2 = 2.5 * np.exp(0.7 * x2) + 0.2
    expr2, params2, mse2 = fit(x2, y2, max_generations=80, pop_size=40, seed=7)
    print(f"[self-test] 指数恢复表达式: {expr2}  MSE = {mse2:.3e}")
    assert mse2 < 1e-4, f"指数恢复自检失败: MSE={mse2:.3e}"
    return 0


if __name__ == "__main__":
    # Windows GBK 控制台打印 Unicode 会 UnicodeEncodeError：统一 UTF-8 输出
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    sys.exit(_self_test())
