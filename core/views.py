import stripe
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView

from core.models import Item, Order, Address, Payment, Category, Refund, UserProfile
from core.forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
from core.services import create_charge_or_error, get_coupon, create_reference_code


stripe.api_key = settings.STRIPE_SECRET_KEY


class HomeView(ListView):
    """Основная страница со списком всех товаров на сайте."""

    model = Item
    template_name = 'home.html'
    paginate_by = 1

    def get_context_data(self, *, object_list=None, **kwargs):
        return {
            'items': Item.objects.all(),
            'categories': Category.objects.all()
        }


class ProductsView(ListView):
    """Страница с товарами по категориям"""
    model = Item
    template_name = 'home.html'
    paginate_by = 1

    def get_context_data(self, *, object_list=None, **kwargs):
        category = get_object_or_404(Category, id=self.kwargs.get('id'))
        items = Item.objects.filter(category=category)
        return {
            'items': items,
            'categories': Category.objects.all()
        }


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
            'couponform': CouponForm(),
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
            messages.warning(
                self.request,
                'У вас нет активного заказа. Для начала добавте продукт в корзину.')
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

            # TODO Перенаправляем на страницу по способу оплаты
            payment_option = form.cleaned_data['payment_option']
            return redirect('core:payment', payment_option='stripe')


class PaymentView(LoginRequiredMixin, View):
    """Вывод страницы с подтверждением оплаты."""

    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
        except Order.DoesNotExist:
            messages.warning(self.request, 'У вас нет активного заказа')
            return redirect('/')
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False,
                'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY
            }
            userprofile = self.request.user.userprofile
            # Получаем доступный список платежных карт пользователя
            if userprofile.one_click_purchasing:
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, 'payment.html', context)

        messages.warning(self.request, 'Вы не указали адрес доставки.')
        return redirect('/')

    def post(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
        except Order.DoesNotExist:
            messages.warning(self.request, 'У вас нет активного заказа')
            return redirect('/')

        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)

        if form.is_valid():
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')
            token = form.cleaned_data.get('stripeToken')
            # Если пользователь решил сохранить данные об оплате
            if save:
                if userprofile.stripe_customer_id:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id,
                        # source=token,
                        # expand=['sources'],
                    )
                    print('1block', customer)
                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                        source=token,
                        expand=['sources'],
                    )
                    print('2block', customer)
                    # customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.get_total())
            # Если используем данные по умолчанию, то передаем Stripe ID пользователя
            if use_default or save:
                charge = create_charge_or_error(
                    amount=amount * 100,    # в центах
                    currency='usd',
                    customer=userprofile.stripe_customer_id
                )
            # Иначе используем токен
            else:

                charge = create_charge_or_error(
                    amount=amount * 100,
                    currency='usd',
                    token=token
                )
            # Если соединение прошло
            if isinstance(charge, stripe.Charge):

                payment = Payment.objects.create(
                    stripe_charge_id=charge['id'],
                    user=self.request.user,
                    amount=amount
                )

                order.ordered = True
                order.payment = payment
                order.reference_code = create_reference_code()
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
    """Добавляет один товар в корзину пользователя."""
    item = get_object_or_404(Item, slug=slug)
    item.add_item_to_cart(request)
    return redirect(request.META.get('HTTP_REFERER'))


@login_required
def remove_from_cart(request, slug):
    """Удаляет позицию товара из корзины пользователя."""
    item = get_object_or_404(Item, slug=slug)
    item.remove_item_from_cart(request)
    return redirect(request.META.get('HTTP_REFERER'), slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    """Удаляет из корзины один экземпляр товара."""
    item = get_object_or_404(Item, slug=slug)
    item.remove_single_item_from_cart(request)
    return redirect(request.META.get('HTTP_REFERER'), slug=slug)


class AddCouponView(LoginRequiredMixin, View):
    """Добавляет скидочный купон к активному заказу пользователя."""
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST)

        if form.is_valid():
            try:
                order = Order.objects.get(user=self.request.user, ordered=False)
            except Order.DoesNotExist:
                messages.warning(self.request, 'У вас нет активного заказа')
                return redirect('/')

            code = form.cleaned_data.get('code')
            order.coupon = get_coupon(self.request, code)
            order.save()
            messages.success(self.request, 'Промокод активирован')
            return redirect('core:checkout')


class RequestRefundView(LoginRequiredMixin, View):
    """Вывод страницы для заполнения формы возврата."""

    def get(self, *args, **kwargs):
        form = RefundForm()
        return render(self.request, 'request_refund.html', {'form': form})

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            reference_code = form.cleaned_data.get('reference_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            try:
                order = Order.objects.get(reference_code=reference_code)
            except Order.DoesNotExist:
                messages.warning(self.request, 'Такого заказа не существует')
                return redirect('core:request-refund')

            order.refund_requested = True
            order.save()

            refund = Refund.objects.create(
                order=order,
                reason=message,
                email=email
            )

            messages.success(self.request, 'Ваша заявка обрабатывается.')
            return redirect('core:request-refund')

        messages.warning(self.request, 'Ошибка валидации')
        return redirect('core:request-refund')
