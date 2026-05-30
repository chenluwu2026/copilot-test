"""标的代码转换：AIMS symbol ↔ AkShare / 交易所格式。"""
from app.models import Market


def parse_symbol(symbol: str) -> tuple[str, Market]:
    if "." not in symbol:
        return symbol, Market.CN_A
    code, suffix = symbol.rsplit(".", 1)
    suffix = suffix.upper()
    if suffix == "HK":
        return code, Market.HK
    if suffix in ("SH", "SZ"):
        return code, Market.CN_A
    if suffix == "US":
        return code, Market.US
    return code, Market.CN_A


def to_akshare_a_code(symbol: str) -> str:
    """600519.SH -> sh600519"""
    code, market = parse_symbol(symbol)
    if market != Market.CN_A:
        raise ValueError(f"非 A 股标的: {symbol}")
    _, suffix = symbol.rsplit(".", 1)
    prefix = "sh" if suffix.upper() == "SH" else "sz"
    return f"{prefix}{code}"


def to_akshare_hk_code(symbol: str) -> str:
    code, market = parse_symbol(symbol)
    if market != Market.HK:
        raise ValueError(f"非港股标的: {symbol}")
    return code.zfill(5) if len(code) < 5 else code
