from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from .models import Address


PAYMENT_CHOICES = (
    ('S', 'Наличный'),
    ('P', 'Безналичный')
)


def is_valid_form(values):
    for field in values:
        if not field:
            return False
    return True


class CheckoutForm(forms.Form):
    """Форма для оформления заказа. Дает возможность создать адрес по умолчанию
    и в последующих заказах пользоваться ей."""
    shipping_address = forms.CharField(required=False)
    shipping_address2 = forms.CharField(required=False)
    shipping_country = CountryField(blank_label='(Выберите страну)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    shipping_zip = forms.CharField(required=False)

    billing_address = forms.CharField(required=False)
    billing_address2 = forms.CharField(required=False)
    billing_country = CountryField(blank_label='(Выберите страну)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    billing_zip = forms.CharField(required=False)

    same_billing_address = forms.BooleanField(required=False)
    set_default_shipping = forms.BooleanField(required=False)
    use_default_shipping = forms.BooleanField(required=False)
    set_default_billing = forms.BooleanField(required=False)
    use_default_billing = forms.BooleanField(required=False)

    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT_CHOICES)

    def set_default_shipping_address(self, user, order):
        """Используем адрес доставки по умолчанию."""
        address_qs = Address.objects.filter(
            user=user,
            address_type='S',
            default=True
        )
        if address_qs.exists():
            shipping_address = address_qs[0]
            order.shipping_address = shipping_address
            return shipping_address
        raise forms.ValidationError('Адрес доставки по умолчанию не задан.')

    def set_new_shipping_address(self, user, order):
        """Пользователь ввел новый адрес доставки."""

        shipping_address1 = self.cleaned_data.get(
            'shipping_address')
        shipping_address2 = self.cleaned_data.get(
            'shipping_address2')
        shipping_country = self.cleaned_data.get(
            'shipping_country')
        shipping_zip = self.cleaned_data.get('shipping_zip')

        if shipping_address1 and shipping_country and shipping_zip:
            shipping_address = Address(
                user=user,
                street_address=shipping_address1,
                apartment_address=shipping_address2,
                country=shipping_country,
                zip=shipping_zip,
                address_type='S'
            )
            shipping_address.save()

            order.shipping_address = shipping_address
            order.save()

            # Отмечаем как адрес по умолчанию.
            if self.cleaned_data['set_default_shipping']:
                shipping_address.default = True
                shipping_address.save()
                return shipping_address

        raise forms.ValidationError('Пожалуйста, заполните обязательные поля адреса доставки.')

    def set_same_billing_address(self, address, order):
        """Если адрес счета тот же, что у адреса доставки."""
        billing_address = address
        billing_address.pk = None
        billing_address.save()
        billing_address.address_type = 'B'
        billing_address.save()
        order.billing_address = billing_address
        order.save()
        return order

    def set_default_billing_address(self, user, order):
        """Используем платежный адрес по умолчанию."""
        address_qs = Address.objects.filter(
            user=user,
            address_type='B',
            default=True
        )
        if address_qs.exists():
            billing_address = address_qs[0]
            order.billing_address = billing_address
            order.save()
            return billing_address
        raise forms.ValidationError('Сохраненный платежный адрес не найден.')

    def set_new_billing_address(self, user, order):
        """Пользователь ввел новый платежный адрес."""
        billing_address1 = self.cleaned_data.get(
            'billing_address')
        billing_address2 = self.cleaned_data.get(
            'billing_address2')
        billing_country = self.cleaned_data.get(
            'billing_country')
        billing_zip = self.cleaned_data.get('billing_zip')

        if billing_address1 and billing_country and billing_zip:
            billing_address = Address(
                user=user,
                street_address=billing_address1,
                apartment_address=billing_address2,
                country=billing_country,
                zip=billing_zip,
                address_type='B'
            )
            billing_address.save()

            order.billing_address = billing_address
            order.save()

            if self.cleaned_data['set_defaul_billing']:
                billing_address.default = True
                billing_address.save()

            return billing_address
        raise forms.ValidationError('Пожалуйста, заполните обязательные поля платежного адреса.')