
import functools
import json
import logging
from datetime import UTC, datetime

logger = logging.getLogger("valutatrade")


def log_action(action: str, verbose: bool = False):
    """
    Декоратор для логирования доменных операций.

    Применяется к методам usecases: biy, sell, register, login, logout, deposit.
    Фиксирует информацию об операции в формате json

    Перед выполнением операции фиксирует контекст - время, операция, данные пользователя
    При успешном выполнении логирует "result": "OK", при ошибке: "result": "ERROR", тип
    ошибки и ее сообщение.
    Ожидаемый контракт:
    - декоратор предполагает наличие self._current_user и self._base_currency, а то None
    - если операция возвращает dict, из него извлекаются доменные поля: currency, rate,
    amount, base
    - при verbose=True логируются состояния кошелька до и после операции

    Args:
        action (str): название операции
        verbose (bool): нужна ли дополнительная информация
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):

            user = getattr(self, "_current_user", None)

            log_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "action": action,
                "user_id": getattr(user, "user_id", None),
                "username": getattr(user, "username", None),
                "result": "OK"
            }

            try:
                result = func(self, *args, **kwargs)

                # общие поля
                if isinstance(result, dict):
                    log_data.update({
                        "currency": result.get("currency"),
                        "cost": result.get("cost"),
                        "rate": result.get("rate"),
                        "base": getattr(self, "_base_currency", None)
                    })

                    if verbose:
                        log_data["before"] = result.get("before")
                        log_data["after"] = result.get("after")

                logger.info(json.dumps(log_data, ensure_ascii=False))
                return result

            except Exception as e:
                log_data.update({
                    "result": "ERROR",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
                logger.error(json.dumps(log_data, ensure_ascii=False))
                raise

        return wrapper
    return decorator
