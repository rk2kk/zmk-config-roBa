# ble_log.py / ble_log_unpaired.py 共通ユーティリティ
import codecs
import sys
import time
from pathlib import Path

# ログ保存先はリポジトリ直下の logs/ に固定 (実行場所に依存しない)
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def normalize_addr(value: str) -> str:
    """BLE アドレス表記ゆれ ("AA:BB:..", "0xAABB..", 大文字混在) を 12 桁小文字 hex に正規化する。

    不正な形式のときは例外を送出する。
    """
    hex_str = value.replace(":", "").replace("-", "").replace(" ", "")
    if hex_str[:2].lower() == "0x":
        hex_str = hex_str[2:]
    hex_str = hex_str.lower()
    if len(hex_str) != 12 or any(c not in "0123456789abcdef" for c in hex_str):
        raise ValueError(f"invalid BLE address: {value!r} (expected 12 hex digits, e.g. ed5b0a3eb599)")
    return hex_str


class NusLogCapture:
    """NUS ログを受信バイト列のまま追記保存するキャプチャ。

    - ファイルには bytes のまま都度書き込み + flush する。
      プロセス強制終了 (クラッシュ観測中の電源断など) でも受信済み分は残る
    - コンソール表示のみインクリメンタル decoder を使う。
      パケット (NUS MTU) 境界でマルチバイト文字が分割されても表示が化けない
    """

    def __init__(self, prefix: str = "ble_log"):
        LOG_DIR.mkdir(exist_ok=True)
        self.path = LOG_DIR / f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._file = open(self.path, "ab")

    def feed(self, data) -> None:
        if self._file.closed:
            return
        data = bytes(data)
        text = self._decoder.decode(data)
        if text:
            sys.stdout.write(text)
            sys.stdout.flush()
        try:
            self._file.write(data)
            self._file.flush()
        except ValueError:
            # close() との競合 (WinRT ハンドラのスレッドから呼ばれる場合がある)
            pass

    def close(self) -> None:
        try:
            trailing = self._decoder.decode(b"", final=True)
            if trailing:
                sys.stdout.write(trailing)
                sys.stdout.flush()
        finally:
            self._file.close()
