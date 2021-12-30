"""
Интернет магазин для покупки одежды.

1. Пользователь регистрируется на сайте.
2. Добавляет товар в корзину.
3. Заказ формируется, выводится итоговая стоимость и количество товаров.
4. Пользователь заполняет данные для отправки заказа.
5. Подтверждает оплату.
6. Заказ отслеживается до момента доставки.
"""
from django.db.models.signals import post_save
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.db import models
from django.urls import reverse
from django_countries.fields import CountryField


# Приоритет товара, влияет на отображение названия товара на странице.
LABEL_CHOICES = (
    ('Новинка', 'primary'),
    ('Сезон', 'secondary'),
    ('Скидка', 'danger'),
)

# Категории адресов пользователя
ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)


class Category(models.Model):
    """Модель с категориями товаров."""
    title = models.CharField('Наименование', max_length=100)

    def __str__(self):
        return self.title


class Item(models.Model):
    """Модель товара в магазине."""
    title = models.CharField('Наименование', max_length=100)
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')
    discount_price = models.DecimalField(
        max_digits=9, decimal_places=2, blank=True, null=True, verbose_name='Скидочная цена')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категория')
    label = models.CharField(choices=LABEL_CHOICES, max_length=15, verbose_name='Приоритет товара')
    slug = models.SlugField(unique=True)
    description = models.TextField('Описание')
    quantity = models.IntegerField(default=1, verbose_name='Количество')
    image = models.ImageField('Изображение')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('core:product', kwargs={'slug': self.slug})

    def get_add_to_cart_url(self):
        return reverse('core:add-to-cart', kwargs={'slug': self.slug})

    def get_remove_from_cart_url(self):
        return reverse('core:remove-from-cart', kwargs={'slug': self.slug})

    def add_item_to_cart(self, request):
        """Добавляем товар в корзину."""
        order_item, created = OrderItem.objects.get_or_create(
            item=self,
            user=request.user,
            ordered=False
        )

        order_qs = Order.objects.filter(user=request.user, ordered=False)
        if order_qs.exists():
            order = order_qs[0]
            # Проверяем, есть ли товар в корзине
            if order.items.filter(item__slug=self.slug).exists():
                order_item.quantity += 1
                order_item.save()
                return messages.info(request, 'Количество товара в корзине было изменено.')
            else:
                order.items.add(order_item)
                return messages.info(request, 'Товар был добавлен в вашу корзину.')
        else:
            # Если заказа еще не существует, то создаем его
            ordered_date = timezone.now()
            order = Order.objects.create(user=request.user, ordered_date=ordered_date)
            order.items.add(order_item)
            return messages.info(request, 'Товар был добавлен в вашу корзину.')

    def remove_item_from_cart(self, request):
        """Удаляем товар из корзины."""
        order_qs = Order.objects.filter(user=request.user, ordered=False)
        if order_qs.exists():
            order = order_qs[0]
            # Проверяем, есть ли товар в корзине
            if order.items.filter(item__slug=self.slug).exists():
                order_item = OrderItem.objects.filter(
                    item=self,
                    user=request.user,
                    ordered=False
                )[0]
                order.items.remove(order_item)
                order_item.delete()
                return messages.info(request, 'Товар был удален из вашей корзины.')
            else:
                return messages.info(request, 'Этого товара нет в вашей корзине.')
        return messages.info(request, 'У вас активной корзины. Для начала добавьте товар.')

    def remove_single_item_from_cart(self, request):
        """Удаляем один экземпляр товара из корзины."""
        order_qs = Order.objects.filter(user=request.user, ordered=False)
        if order_qs.exists():
            order = order_qs[0]
            if order.items.filter(item__slug=self.slug).exists():
                order_item = OrderItem.objects.filter(
                    item=self,
                    user=request.user,
                    ordered=False
                )[0]
                if order_item.quantity > 1:
                    order_item.quantity -= 1
                    order_item.save()
                else:
                    # Если товар в корзине последний.
                    order.items.remove(order_item)
                    return messages.info(request, 'Количество товара в корзине было изменено.')
            else:
                return messages.info(request, 'Этого товара нет в вашей корзине.')
        else:
            return messages.info(request, 'У вас активной корзины. Для начала добавьте товар.')


class OrderItem(models.Model):
    """Модель одной позиции товара в корзине пользователя."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, verbose_name='Пользователь')
    ordered = models.BooleanField(default=False, verbose_name='Заказ подтвержден')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.IntegerField(default=1, verbose_name='Количество')

    def __str__(self):
        return f'{self.quantity} of {self.item.title}'

    def get_total_item_price(self):
        """Цена одной позиции товара, с учетом его количества."""
        return self.quantity * self.item.price

    def get_total_discount_price(self):
        """Скидочная цена одной позиции товара, с учетом его стоимости."""
        return self.quantity * self.item.discount_price

    def get_amount_saved(self):
        """Разница регулярной цены и скидочной."""
        return self.get_total_item_price() - self.get_total_discount_price()

    def get_final_price(self):
        """Итоговая стоимость одной позиции в корзине."""
        if self.item.discount_price:
            return self.get_total_discount_price()
        return self.get_total_item_price()


class Order(models.Model):
    """Модель корзины пользователя."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, verbose_name='Пользователь')
    reference_code = models.CharField(
        max_length=20, blank=True, unique=True,
        null=True, verbose_name='Уникальный ключ'
    )       # TODO verbose name
    items = models.ManyToManyField(OrderItem, verbose_name='Товары')
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    ordered_date = models.DateTimeField(verbose_name='Дата подтверждения')
    ordered = models.BooleanField(default=False, verbose_name='Заказ подтвержден')
    shipping_address = models.ForeignKey(
        'Address', related_name='shipping_address', on_delete=models.SET_NULL,
        blank=True, null=True, verbose_name='Адрес доставки'
    )
    billing_address = models.ForeignKey(
        'Address', related_name='billing_address', on_delete=models.SET_NULL,
        blank=True, null=True, verbose_name='Рассчетный адрес'
    )
    payment = models.ForeignKey(
        'Payment', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Оплата')
    coupon = models.ForeignKey(
        'Coupon', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Промокод')
    being_delivered = models.BooleanField(default=False, verbose_name='Доставлено')
    received = models.BooleanField(default=False, verbose_name='Получено')
    refund_requested = models.BooleanField(default=False, verbose_name='Запрошен возврат')
    refund_granted = models.BooleanField(default=False, verbose_name='Возврат предоставлен')

    def __str__(self):
        return self.user.username

    def get_total(self):
        """Возвращает итоговую стоимость корзины с учетом промокода."""
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        if self.coupon:
            total -= self.coupon.amount
        return total

    def confirm_order_items(self):
        """Подтверждает все позиции в корзине."""
        order_items = self.items.all()
        order_items.update(ordered=True)
        for item in order_items:
            item.save()


class Address(models.Model):
    """Модель адреса пользователя, пользователь может сохранить адрес как адрес
    по умолчанию и в дальнейшем использовать его.
    CountryField из django_countries для возможности выбора страны."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE, verbose_name='Пользователь')
    street_address = models.CharField(max_length=100, verbose_name='Улица')
    apartment_address = models.CharField(max_length=100, verbose_name='Дом')
    country = CountryField(multiple=False, verbose_name='Страна')
    zip = models.CharField(max_length=100, verbose_name='ZIP код')
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES, verbose_name='Тип адреса')
    default = models.BooleanField(default=False, verbose_name='По умолчанию')

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'


class Payment(models.Model):
    """Модель для Stripe оплаты заказа."""
    stripe_charge_id = models.CharField(max_length=50, verbose_name='ID')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        blank=True, null=True, verbose_name='Пользователь'
    )
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Сумма')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')

    def __str__(self):
        return self.user.username


class Coupon(models.Model):
    """Модель скидочного промокода"""
    code = models.CharField(max_length=15, verbose_name='Код')
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Сумма скидки')

    def __str__(self):
        return self.code


class Refund(models.Model):
    """Модель возврата."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name='Заказ')
    reason = models.TextField(verbose_name='Причина')
    accepted = models.BooleanField(default=False, verbose_name='Подтвержден')
    email = models.EmailField(verbose_name='Почта')

    def __str__(self):
        return f'{self.pk}'


class UserProfile(models.Model):
    """ """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(
        max_length=50, blank=True,
        null=True, verbose_name='Stripe ID'
    )
    one_click_purchasing = models.BooleanField(
        default=False,
        verbose_name='Покупка в один клик'
    )

    def __str__(self):
        return self.user.username


def userprofile_receiver(sender, instance, created, *args, **kwargs):
    """Привязываем нашу модель UserProfile с моделью User при входящем
    сигнале о новом пользователе."""
    if created:
        userprofile = UserProfile.objects.create(user=instance)


post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)
