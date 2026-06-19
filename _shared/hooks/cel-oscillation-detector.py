"""
震荡检测 Hook。

检测 Agent 是否陷入迭代震荡：
1. 检查连续无改进轮次
2. 检测状态在两个方案间来回切换
3. 震荡发生时阻止继续并建议升级

此 Hook 在每轮修改后执行，更新状态文件并检测震荡。
"""

import json
import os
import sys

from cel_hook_utils import (
    format_deny,
    format_allow,
    format_additional_context,
    output,
    load_state,
    save_state,
    is_cel_active,
)


# 连续无改进轮次上限
MAX_NO_IMPROVEMENT = 3

# 震荡检测窗口大小（最近 N 轮）
OSCILLATION_WINDOW = 6

# 震荡检测：如果最近 N 轮中有 M 个重复的 action，判定为震荡
OSCILLATION_REPEAT_THRESHOLD = 3


def detect_oscillation(iterations):
    """检测最近几轮是否存在震荡。

    震荡判定条件（满足任一）：
    1. 最近 OSCILLATION_WINDOW 轮中，某个 action 出现超过 OSCILLATION_REPEAT_THRESHOLD 次
    2. 最近 N 轮的 error 值在一个小范围内来回波动
    """
    if len(iterations) < 4:
        return False, ""

    recent = iterations[-OSCILLATION_WINDOW:]
    actions = [it.get('action', '') for it in recent if it.get('action')]

    # 条件1：重复 action 检测
    from collections import Counter
    action_counts = Counter(actions)
    for action, count in action_counts.items():
        if count >= OSCILLATION_REPEAT_THRESHOLD and action:
            return True, f"检测到重复操作：'{action}' 在最近 {OSCILLATION_WINDOW} 轮中出现 {count} 次"

    # 条件2：误差值波动检测
    errors = [it.get('error_after', it.get('error_before', None)) for it in recent]
    errors = [e for e in errors if e is not None]

    if len(errors) >= 4:
        # 检查误差是否在两个值之间来回切换
        up_down = []
        for i in range(1, len(errors)):
            if errors[i] > errors[i - 1]:
                up_down.append('up')
            elif errors[i] < errors[i - 1]:
                up_down.append('down')
            else:
                up_down.append('same')

        # 如果交替出现 up/down 超过阈值
        changes = sum(1 for i in range(1, len(up_down)) if up_down[i] != up_down[i - 1] and up_down[i] != 'same')
        if changes >= 3:
            return True, f"检测到误差值震荡：最近 {len(errors)} 轮误差上下波动 {changes} 次"

    return False, ""


def check_no_improvement(iterations):
    """检查连续无改进轮次。"""
    if not iterations:
        return 0, False

    consecutive = 0
    for it in reversed(iterations):
        error_before = it.get('error_before')
        error_after = it.get('error_after')

        if error_before is not None and error_after is not None:
            if error_after >= error_before:
                consecutive += 1
            else:
                break
        else:
            # 无误差数据，不计入
            break

    return consecutive, consecutive >= MAX_NO_IMPROVEMENT


def main():
    """主入口：更新状态并检测震荡。"""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        output(format_allow())

    # CEL 未激活时直接放行，不干扰其他系统
    if not is_cel_active():
        output(format_allow())

    # 加载状态
    state = load_state()

    # 更新迭代记录（如果 Hook 输入中包含迭代信息）
    tool_name = data.get('tool_name', data.get('tool', ''))
    tool_input = data.get('tool_input', data.get('input', {}))

    iterations = state.get('iterations', [])

    # 检测震荡
    is_oscillating, oscillation_reason = detect_oscillation(iterations)

    # 检测连续无改进
    consecutive, no_improvement = check_no_improvement(iterations)

    # 更新震荡状态
    state['oscillation'] = {
        'detected': is_oscillating,
        'pattern': oscillation_reason if is_oscillating else '',
        'consecutive_no_improvement': consecutive,
    }

    # 保存状态
    save_state(state)

    # 震荡或无改进时阻止继续
    if is_oscillating:
        output(format_deny(
            f"[CEL 震荡检测] {oscillation_reason}。"
            f"请停止当前方向，总结冲突并请求用户决策。"
        ))

    if no_improvement:
        output(format_deny(
            f"[CEL 震荡检测] 连续 {consecutive} 轮无改进（上限 {MAX_NO_IMPROVEMENT}）。"
            f"请停止当前方向，尝试不同的策略或请求用户确认。"
        ))

    # 正常放行，注入状态提醒
    if consecutive > 0:
        context = (
            f"[CEL 状态提醒] 已连续 {consecutive} 轮无改进"
            f"（上限 {MAX_NO_IMPROVEMENT}）。"
            f"请考虑调整策略。"
        )
        output(format_additional_context(context))

    output(format_allow())


if __name__ == '__main__':
    main()
