import stripe
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from core.models import Coupon


def create_charge_or_error(amount, currency, token):
    """Создает соединение с STRIPE API, при успешном
    соединении возвращает экземпляр класса Charge.
    Если произошла ошибка, то возвращает информацию о ней."""

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        charge = stripe.Charge.create(
            amount=amount,
            currency=currency,
            source=token
        )
    except stripe.error.CardError as e:
        body = e.json_body
        err = body.get('error', {})
        return f'{err.get("message")}'

    except stripe.error.RateLimitError as e:
        # Too many requests made to the API too quickly
        return "Время подключения вышло."

    except stripe.error.InvalidRequestError as e:
        # Invalid parameters were supplied to Stripe's API
        return 'Не верные параметры.'

    except stripe.error.AuthenticationError as e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        return "Вы не авторизованы."

    except stripe.error.APIConnectionError as e:
        # Network communication with Stripe failed
        return "Ошибка сервиса."

    except stripe.error.StripeError as e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        return f"{e}Что-то пошло не так. Оплата не прошла, " \
               "пожалуйста попробуйте еще раз."

    except Exception as e:
        # send an email to ourselves
        return "Произошла непредвиденная ошибка."

    return charge


def get_coupon(request, code):
    """Возвращает существующий промокод."""
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except Coupon.DoesNotExist:
        messages.warning(request, 'Данный промокод не найден')
        return redirect('/')
