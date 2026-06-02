from decimal import Decimal


def simulate_execution(
    *,
    side: str,
    quantity: float,
    reference_price: float,
    adv_notional: float | None = None,
    fill_ratio: float = 1.0,
) -> dict:
    qty = Decimal(str(max(quantity, 0)))
    ref = Decimal(str(reference_price))
    ratio = Decimal(str(min(max(fill_ratio, 0.0), 1.0)))
    adv = Decimal(str(adv_notional)) if adv_notional is not None else None

    order_notional = qty * ref
    adv_ratio = (order_notional / adv) if adv and adv > 0 else Decimal("0")
    # 简化滑点模型：2bp 基础 + 20bp * (订单金额/ADV)
    slippage_bps = Decimal("2") + Decimal("20") * adv_ratio
    slip = ref * slippage_bps / Decimal("10000")
    exec_price = ref + slip if side in {"buy", "add"} else ref - slip

    filled_qty = qty * ratio
    fill_notional = filled_qty * exec_price
    expected_notional = filled_qty * ref
    implementation_shortfall = fill_notional - expected_notional

    return {
        "side": side,
        "reference_price": float(ref),
        "executed_price": float(exec_price),
        "order_quantity": float(qty),
        "filled_quantity": float(filled_qty),
        "fill_ratio": float(ratio),
        "slippage_bps": float(slippage_bps),
        "order_notional": float(order_notional),
        "filled_notional": float(fill_notional),
        "implementation_shortfall": float(implementation_shortfall),
    }
