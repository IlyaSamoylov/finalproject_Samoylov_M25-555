
import json
import functools
import logging
from datetime import datetime, UTC

logger = logging.getLogger("valutatrade")


def log_action(action: str, verbose: bool = False):
    """
    action: BUY / SELL / REGISTER / LOGIN
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
                "result": "OK",
            }

            try:
                result = func(self, *args, **kwargs)

                # общие поля
                if isinstance(result, dict):
                    log_data.update({
                        "currency": result.get("currency"),
                        "amount": result.get("amount"),
                        "rate": result.get("rate"),
                        "base": getattr(self, "_base_currency", None),
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
                    "error_message": str(e),
                })
                logger.error(json.dumps(log_data, ensure_ascii=False))
                raise

        return wrapper
    return decorator
