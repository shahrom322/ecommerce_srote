﻿### Техническое задание

Написать на Django интернет-магазин.  

- Спроектировать архитектуру БД для хранения данных о товарах и торговых операциях пользователей.
- Реализовать возможность добавления и удаления товаров из корзины.  Учитывать все возможные скидки и промокод. При изменении состояния корзины итоговая стоимость отображалась на странице.
- У пользователя имеется возможность сохранить свои данные для дальнейшего использования.
- Добавить возможность регистрации и авторизации.
- Реализовать поиск и пагинацию.
 
<hr>

### Демо

<img src="https://media.giphy.com/media/eojzM52WveNPjRIjRm/giphy.gif" width="600" height="400">

Добавляем несколько товаров в корзину, взаимодействуем с ними, в полях для ввода адреса и оплаты выбираем сохраненные данные.

<hr>

### О проекте

Для управления авторизации и регистрации пользователя использовал allauth. Вся бизнес-логика связанная с моделями и взаимодействие с ними размещена в файле models.py.

Вся верстка сайта была написана с использованием Bootstrap. Простой и типичный интерфейс интернет-магазина. 

Модуль settings разделен для более удобного пользования. base.py отвечает за базовые настройки проекта, от него наследуется development.py - файл с настройками для разработки, настройками debug_toolbar и sqlite3 БД. И файл production.py - настройки для деплоя сайта, будет работать на PostgreSQL.

Интегрирована система Stripe для обработки электронных платежей. Для подключения к системе необходимо иметь аккаунт с банковским счетом на https://stripe.com/ и в виртуальном окружении сохранить данные своего счета STRIPE_PUBLIC_KEY и STRIPE_SECRET_KEY.

Была настроена автоматическая сборка Docker и docker-compose. Создаются три образа: web - наш сайт на Django, db - образ с базой данных postgres, nginx - веб-сервер, конфигурация которого прописана в nginx.conf. 

На сайте основное взаимодействие с товарами происходит через переадресацию на другие представления, что конечно замедляет работу сайта. В дальнейшем, такие возможности как добавить товар в корзину или поиск по сайту, хотелось бы переписать на JS и взаимодействовать через API приложения. 
