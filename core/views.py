import stripe
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView

from core.models import Item, Order, Address, Payment
from core.forms import CheckoutForm
from core.services import create_charge_or_error


class HomeView(ListView):
    """Основная страница со списком всех товаров на сайте."""

    model = Item
    template_name = 'home.html'
    context_object_name = 'items'
    paginate_by = 10


class CheckoutView(LoginRequiredMixin, View):
    """Вывод страницы с формой для оформления заказа."""""

    def get(self, *args, **kwargs):
        """Проверяем есть ли у пользователя действительный заказ, сохраненные адреса
        для доставки и выставления счета."""
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
        except Order.DoesNotExist:
            messages.warning(self.request, 'У вас нет активного заказа. Для начала добавте продукт в корзину.')
            return redirect('core:home')

        form = CheckoutForm()
        context = {
            'form': form,
            # 'couponform': CouponForm(),
            'order': order,
            'DISPLAY_COUPON_FORM': True
        }

        shipping_address_qs = Address.objects.filter(
            user=self.request.user,
            address_type='S',
            default=True
        )
        if shipping_address_qs.exists():
            context.update(
                {'default_shipping_address': shipping_address_qs[0]})

        billing_address_qs = Address.objects.filter(
            user=self.request.user,
            address_type='B',
            default=True
        )
        if billing_address_qs.exists():
            context.update(
                {'default_billing_address': billing_address_qs[0]})
        return render(self.request, 'checkout.html', context)

    def post(self, *args, **kwargs):
        """Валидируем форму, сохраняем."""
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
        except Order.DoesNotExist:
            messages.warning('У вас нет активного заказа. Для начала добавте продукт в корзину.')
            return redirect('core:home')

        form = CheckoutForm(self.request.POST or None)
        if form.is_valid():

            if form.cleaned_data['use_default_shipping']:
                shipping_address = form.set_default_shipping_address(self.request.user, order)
            else:
                shipping_address = form.set_new_shipping_address(self.request.user, order)

            if form.cleaned_data['same_billing_address']:
                form.set_same_billing_address(shipping_address, order)
            elif form.cleaned_data['use_default_billing']:
                form.set_default_billing_address(self.request.user, order)
            else:
                form.set_new_billing_address(self.request.user, order)
            messages.info(self.request, 'Успешно')
            return redirect('/')


class PaymentView(LoginRequiredMixin, View):
    """Вывод страницы с подтверждением оплаты."""

    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
            }
        return render(self.request, 'payment.html', context)

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)     # в центах

        charge = create_charge_or_error(amount, 'usd', token)
        # Если соединение прошло
        if isinstance(charge, stripe.Charge):
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = amount
            payment.save()

            order.ordered = True
            order.payment = payment
            order.save()
            messages.success(self.request, 'Успешно')
            return redirect('/')

        # Если нет, то функция вернула ошибку
        messages.error(self.request, charge)
        return redirect('/')


class OrderSummaryView(LoginRequiredMixin, View):
    """Вывод страницы с корзиной пользователя."""

    def get(self, *args, **kwargs):
        try:
            order = Order.objects.prefetch_related(
                'items').get(user=self.request.user, ordered=False)
            return render(self.request, 'order_summary.html', {'object': order})

        except Order.DoesNotExist:
            messages.error(self.request, 'Для начала добавьте товар в корзину')
            return redirect('/')


class ItemDetailView(DetailView):
    """Вывод страницы с информацией о товаре."""

    model = Item
    template_name = 'product.html'
    context_object_name = 'item'


@login_required
def add_item_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    item.add_item_to_cart(request)
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    item.remove_item_from_cart(request)
    return redirect(request.META.get('HTTP_REFERER'), slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    item.remove_single_item_from_cart(request)
    return redirect(request.META.get('HTTP_REFERER'), slug=slug)
