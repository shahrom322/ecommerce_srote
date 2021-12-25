from datetime import timezone

from django.conf import settings
from django.contrib import messages
from django.db import models
from django.urls import reverse
from django_countries.fields import CountryField


CATEGORY_CHOICES = (
    ('S', 'Shirt'),
    ('SW', 'Sport wear'),
    ('OW', 'Outwear'),
)

LABEL_CHOICES = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger'),
)

ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)


class Item(models.Model):
    """Модель товара в магазине."""
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.CharField(choices=CATEGORY_CHOICES, max_length=2)
    label = models.CharField(choices=LABEL_CHOICES, max_length=1)
    slug = models.SlugField()
    description = models.TextField()
    quantity = models.IntegerField(default=1)

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
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f'{self.quantity} of {self.item.title}'

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_total_discount_price(self):
        return self.quantity * self.item.discount_price

    def get_amount_saved(self):
        return self.get_total_item_price() - self.get_total_discount_price()

    def get_final_price(self):
        if self.item.discount_price:
            return self.get_total_discount_price()
        return self.get_total_item_price()


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    billing_address = models.ForeignKey('Address', on_delete=models.SET_NULL,
                                        blank=True, null=True)

    def __str__(self):
        return self.user.username

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        return total


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'
