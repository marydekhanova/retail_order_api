from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework import status
import random
from django.urls import reverse
import json
from rest_framework.authtoken.models import Token
from django.test import Client
from decimal import Decimal

from products.models import ProductCard
from buyer.models import CartPosition
from buyer.models import Order, Address, OrderPosition

User = get_user_model()


class CartViewTest(APITestCase):

    def setUp(self):
        self.url = reverse('buyer:cart')
        seller_data = {'first_name': 'Ivan', 'last_name': 'Ivanov', 'email': 'ivan.ivanov@gmail.com',
                       'is_active': True, 'type': 'seller', 'password': '12345678'}
        buyer_data =  {'first_name': 'Maria', 'last_name': 'Petrova', 'email': 'maria.petrova@gmail.com',
                       'is_active': True, 'type': 'buyer', 'password': '12345678'}
        seller = User.objects.create_user(**seller_data)
        self.seller_auth_token = Token.objects.create(user=seller)
        self.buyer = User.objects.create_user(**buyer_data)
        self.buyer_auth_token = Token.objects.create(user=self.buyer)
        response = self.client.post('/api/v1/seller/shop/prices/',
                                    headers={'Authorization': f'Token {self.seller_auth_token}'},
                                    data={'url': 'https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml'})
        product_cards = ProductCard.objects.all()
        product_card = random.choice(product_cards)
        product_card.status = 'withdrawn'
        product_card.save()
        cart_positions = []
        for product_card in product_cards:
            cart_positions.append(CartPosition(user=self.buyer, product_card=product_card, quantity=3))
        self.cart = CartPosition.objects.bulk_create(cart_positions)

    def test_get_cart_with_correct_token(self):
        expected_response = {'unvailable_positions': [], 'available_positions': [], 'total': 0}
        for cart_position in self.cart:
            if cart_position.product_card.status == 'withdrawn':
                expected_response['unvailable_positions'].append({'product_card': cart_position.product_card.id,
                                                                  'quantity': cart_position.quantity,
                                                                  'price_per_quantity': str(cart_position.price_per_quantity)})
            else:
                expected_response['available_positions'].append({'product_card': cart_position.product_card.id,
                                                                 'quantity': cart_position.quantity,
                                                                 'price_per_quantity': str(cart_position.price_per_quantity)})
                expected_response['total'] += cart_position.price_per_quantity
        expected_response['total'] = str(expected_response['total'])
        response = self.client.get(self.url,
                         headers={'Authorization': f'Token {self.buyer_auth_token}'})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_response, response.json())

    def test_get_cart_with_wrong_token(self):
        response = self.client.get(self.url,
                                   headers={'Authorization': f'Token 11111'})
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Invalid token.', response.json()['detail'])

    def test_get_cart_as_seller(self):
        response = self.client.get(self.url,
                                   headers={'Authorization': f'Token {self.seller_auth_token}'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual('The user is not a buyer.', response.json()['detail'])

    def test_get_cart_without_token(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Authentication credentials were not provided.', response.json()['detail'])

    def test_get_empty_cart(self):
        for cart_position in self.cart:
            cart_position.delete()
        response = self.client.get(self.url,
                         headers={'Authorization': f'Token {self.buyer_auth_token}'})

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(0, len(response.json()))

    def test_delete_cart_with_correct_token(self):
        response = self.client.delete(self.url,
                                      headers={'Authorization': f'Token {self.buyer_auth_token}'})
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertEqual(0, len(cart))

    def test_delete_cart_with_wrong_token(self):
        response = self.client.delete(self.url,
                                      headers={'Authorization': f'Token 11111'})
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Invalid token.', response.json()['detail'])

    def test_delete_cart_without_token(self):
        response = self.client.delete(self.url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Authentication credentials were not provided.', response.json()['detail'])

    def test_delete_cart_as_seller(self):
        response = self.client.delete(self.url,
                                      headers={'Authorization': f'Token {self.seller_auth_token}'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual('The user is not a buyer.', response.json()['detail'])

    def test_delete_empty_cart(self):
        for cart_position in self.cart:
            cart_position.delete()
        response = self.client.delete(self.url,
                                      headers={'Authorization': f'Token {self.buyer_auth_token}'})
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)


class CartPositionViewTest(APITestCase):

    def get_random_product_card(self):
        product_cards = ProductCard.objects.all()
        product_card = random.choice(product_cards)
        return product_card

    def setUp(self):
        self.url = reverse('buyer:cart_position')
        seller_data = {'first_name': 'Ivan', 'last_name': 'Ivanov', 'email': 'ivan.ivanov@gmail.com',
                       'is_active': True, 'type': 'seller', 'password': '12345678'}
        buyer_data =  {'first_name': 'Maria', 'last_name': 'Petrova', 'email': 'maria.petrova@gmail.com',
                       'is_active': True, 'type': 'buyer', 'password': '12345678'}
        seller = User.objects.create_user(**seller_data)
        self.seller_auth_token = Token.objects.create(user=seller)
        self.buyer = User.objects.create_user(**buyer_data)
        self.buyer_auth_token = Token.objects.create(user=self.buyer)
        response = self.client.post('/api/v1/seller/shop/prices/',
                                    headers={'Authorization': f'Token {self.seller_auth_token}'},
                                    data={'url': 'https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml'})

    def test_add_position_with_correct_token_and_data(self):
        product_card = self.get_random_product_card()
        data = {'product_card': product_card.id,
                'quantity': 3}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        cart_position = CartPosition.objects.get(user=self.buyer)
        self.assertEqual(product_card, cart_position.product_card)
        self.assertEqual(data['quantity'], cart_position.quantity)

    def test_update_position_with_correct_token_and_data(self):
        product_card = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card, quantity=5)
        cart_position.save()
        data = {'product_card': product_card.id,
                'quantity': 2}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        cart_position_after_request = CartPosition.objects.get(user=self.buyer)
        self.assertEqual(product_card, cart_position_after_request.product_card)
        self.assertEqual(data['quantity'], cart_position_after_request.quantity)
        self.assertEqual(cart_position, cart_position_after_request)

    def test_put_position_with_wrong_token(self):
        data = {'product_card': 1,
                'quantity': 2}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token 1111'},
                                   data=data)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Invalid token.', response.json()['detail'])

    def test_put_position_without_token(self):
        data = {'product_card': 1,
                'quantity': 2}
        response = self.client.put(self.url,
                                   data=data)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Authentication credentials were not provided.', response.json()['detail'])

    def test_put_position_as_seller(self):
        data = {'product_card': 1,
                'quantity': 2}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.seller_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual('The user is not a buyer.', response.json()['detail'])

    def test_put_position_with_excess_quantity(self):
        product_card = self.get_random_product_card()
        data = {'product_card': product_card.id,
                'quantity': 30}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual({'non_field_errors': ['Quantity exceeds the actual stock of the product.']}, response.json())
        self.assertEqual(0, len(cart))

    def test_put_position_without_data(self):
        product_card = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card, quantity=5)
        cart_position.save()
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'})
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_response = {"product_card": ["This field is required."],
                             "quantity": ["This field is required."]}
        self.assertEqual(expected_response, response.json())

    def test_add_position_with_zero_quantity(self):
        product_card = self.get_random_product_card()
        data = {'product_card': product_card.id,
                'quantity': 0}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_response = {'quantity': ['Ensure this value is greater than or equal to 1.']}
        self.assertEqual(expected_response, response.json())
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(0, len(cart))

    def test_update_position_with_zero_quantity(self):
        product_card = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card, quantity=5)
        cart_position.save()
        data = {'product_card': product_card.id,
                'quantity': 0}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_response = {'quantity': ['Ensure this value is greater than or equal to 1.']}
        self.assertEqual(expected_response, response.json())
        cart_position = CartPosition.objects.get(user=self.buyer)
        self.assertEqual(5, cart_position.quantity)

    def test_put_position_with_nonexistent_product_card(self):
        data = {'product_card': 2005,
                'quantity': 1}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_response = {'product_card': ['Invalid pk "2005" - object does not exist.']}
        self.assertEqual(expected_response, response.json())
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(0, len(cart))

    def test_put_position_with_wrong_data(self):
        data = {'product_card': 'iphone',
                'quantity': 'four'}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_response = {'product_card': ['Incorrect type. Expected pk value, received str.'],
                             'quantity': ['A valid integer is required.']}
        self.assertEqual(expected_response, response.json())
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(0, len(cart))

    def test_put_position_with_unavailable_product_card(self):
        product_card = self.get_random_product_card()
        product_card.status = 'withdrawn'
        product_card.save()
        data = {'product_card': product_card.id,
                'quantity': 1}
        response = self.client.put(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_response = {'product_card': ['The product is sold or withdrawn.']}
        self.assertEqual(expected_response, response.json())
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(0, len(cart))

    def test_delete_position_with_correct_token_and_data(self):
        product_card = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card, quantity=2)
        cart_position.save()
        data = {'product_card': product_card.id}
        response = self.client.delete(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'},
                                   data=data)
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertEqual(0, len(cart))

    def test_delete_position_with_wrong_token(self):
        product_card = self.get_random_product_card()
        data = {'product_card': product_card.id}
        response = self.client.delete(self.url,
                                      headers={'Authorization': f'Token 1111'},
                                      data=data)

        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Invalid token.', response.json()['detail'])

    def test_delete_position_with_without_token(self):
        product_card = self.get_random_product_card()
        data = {'product_card': product_card.id}
        response = self.client.delete(self.url,
                                      data=data)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Authentication credentials were not provided.', response.json()['detail'])

    def test_delete_position_as_seller(self):
        product_card = self.get_random_product_card()
        data = {'product_card': product_card.id}
        response = self.client.delete(self.url,
                                      headers={'Authorization': f'Token {self.seller_auth_token}'},
                                      data=data)
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual('The user is not a buyer.', response.json()['detail'])

    def test_delete_position_without_data(self):
        product_card = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card, quantity=2)
        cart_position.save()
        response = self.client.delete(self.url,
                                      headers={'Authorization': f'Token {self.buyer_auth_token}'})
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual({'product_card': ['This field is required.']}, response.json())
        self.assertEqual(1, len(cart))

    def test_delete_position_with_nonexistent_product_card(self):
        product_card = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card, quantity=2)
        cart_position.save()
        response = self.client.delete(self.url,
                                      data={'product_card': 2005},
                                      headers={'Authorization': f'Token {self.buyer_auth_token}'})
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual({'product_card': ['Invalid pk "2005" - object does not exist.']}, response.json())
        self.assertEqual(1, len(cart))

    def test_delete_position_with_wrong_product_card(self):
        product_card = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card, quantity=2)
        cart_position.save()
        response = self.client.delete(self.url,
                                      data={'product_card': 'iphone'},
                                      headers={'Authorization': f'Token {self.buyer_auth_token}'})
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual({'product_card': ['Incorrect type. Expected pk value, received str.']}, response.json())
        self.assertEqual(1, len(cart))

    def test_delete_nonexistent_position_in_cart(self):
        product_card_1 = self.get_random_product_card()
        cart_position = CartPosition(user=self.buyer, product_card=product_card_1, quantity=2)
        cart_position.save()
        product_card_2 = self.get_random_product_card()
        while product_card_2== product_card_1:
            product_card_2 = self.get_random_product_card()
        response = self.client.delete(self.url,
                                      data={'product_card': product_card_2.id},
                                      headers={'Authorization': f'Token {self.buyer_auth_token}'})
        cart = CartPosition.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)
        self.assertEqual(f"Product card with id '{product_card_2.id}' is not in the cart.",
                         response.json()['detail'])
        self.assertEqual(1, len(cart))


class OrdersViewTest(APITestCase):

    def get_order_data(self):
        return {
            "first_name": "Иван",
            "last_name": "Иванов",
            "phone": "89167490856",
            "address": {
                "city": "Москва",
                "street": "Невского",
                "house": 41
            }
        }

    def get_random_product_card(self):
        product_cards = ProductCard.objects.all()
        product_card = random.choice(product_cards)
        return product_card

    def fill_cart(self):
        product_card_1 = self.get_random_product_card()
        product_card_2 = self.get_random_product_card()
        while product_card_2 == product_card_1:
            product_card_2 = self.get_random_product_card()
        cart_position_1 = CartPosition(user=self.buyer, product_card=product_card_1, quantity=2)
        cart_position_2 = CartPosition(user=self.buyer, product_card=product_card_2, quantity=5)
        cart_positions = CartPosition.objects.bulk_create([cart_position_1, cart_position_2])

    def setUp(self):
        self.url = reverse('buyer:orders')
        seller_data = {'first_name': 'Ivan', 'last_name': 'Ivanov', 'email': 'ivan.ivanov@gmail.com',
                       'is_active': True, 'type': 'seller', 'password': '12345678'}
        buyer_data = {'first_name': 'Maria', 'last_name': 'Petrova', 'email': 'maria.petrova@gmail.com',
                      'is_active': True, 'type': 'buyer', 'password': '12345678'}
        seller = User.objects.create_user(**seller_data)
        self.seller_auth_token = Token.objects.create(user=seller)
        self.buyer = User.objects.create_user(**buyer_data)
        self.buyer_auth_token = Token.objects.create(user=self.buyer)
        response = self.client.post('/api/v1/seller/shop/prices/',
                                    headers={'Authorization': f'Token {self.seller_auth_token}'},
                                    data={
                                        'url': 'https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml'})

    def test_get_orders_with_correct_token(self):
        address = Address(user=self.buyer, city='Moscow', street='Nevskogo', house='16')
        address.save()
        order_1 = Order(user=self.buyer, address=address, first_name='Maksim', last_name='Maksimov', phone='89372773838')
        order_1.save()
        product_card_1 = self.get_random_product_card()
        product_card_2 = self.get_random_product_card()
        while product_card_2 == product_card_1:
            product_card_2 = self.get_random_product_card()
        order_1_position_1 = OrderPosition(order=order_1, product_card=product_card_1, price=product_card_1.price, quantity=3)
        order_1_position_2 = OrderPosition(order=order_1, product_card=product_card_2, price=product_card_2.price, quantity=4)
        order_1_positions = OrderPosition.objects.bulk_create([order_1_position_1, order_1_position_2])
        order_2 = Order(user=self.buyer, address=address, first_name='Maksim', last_name='Maksimov',
                        phone='89372773838')
        order_2.save()
        order_2_position_1 = OrderPosition(order=order_2, product_card=product_card_1, price=product_card_1.price,
                                           quantity=3)
        order_2_position_1.save()
        orders = Order.objects.filter(user=self.buyer)
        expected_response = [
            {
                "id": order_2.id,
                "created_at": order_2.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "new"
            },
            {
                "id": order_1.id,
                "created_at": order_1.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "new"
            }
        ]
        response = self.client.get(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_response, response.json())

    def test_get_orders_with_wrong_token(self):
        response = self.client.get(self.url,
                                   headers={'Authorization': f'Token 1111'})
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Invalid token.', response.json()['detail'])

    def test_get_orders_without_token(self):
        response = self.client.get(self.url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Authentication credentials were not provided.', response.json()['detail'])

    def test_get_orders_as_seller(self):
        response = self.client.get(self.url,
                                   headers={'Authorization': f'Token {self.seller_auth_token}'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual('The user is not a buyer.', response.json()['detail'])

    def test_get_empty_orders_list(self):
        response = self.client.get(self.url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(0, len(response.json()))

    def test_post_order_with_new_address(self):
        self.fill_cart()
        data = self.get_order_data()
        response = self.client.post(self.url,
                                    data=data, format='json',
                                    headers={'Authorization': f'Token {self.buyer_auth_token}'})
        order = Order.objects.get(user=self.buyer)
        address = Address.objects.get(user=self.buyer)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual({'id': order.id}, response.json())
        self.assertEqual(data['address']['city'], address.city)
        self.assertEqual(2, len(order.positions.all()))

    def test_post_order_with_address_from_list(self):
        self.fill_cart()
        data_address = self.get_order_data()['address']
        address = Address(user=self.buyer, **data_address)
        address.save()
        data = self.get_order_data()
        response = self.client.post(self.url,
                                    data=data, format='json',
                                    headers={'Authorization': f'Token {self.buyer_auth_token}'})
        order = Order.objects.get(user=self.buyer)
        address = Address.objects.get(user=self.buyer)
        self.assertEqual(status.HTTP_201_CREATED, response.status_code)
        self.assertEqual({'id': order.id}, response.json())
        self.assertEqual(data['address']['city'], address.city)
        self.assertEqual(2, len(order.positions.all()))
        self.assertEqual(address.id, order.address.id)

    def test_post_order_with_sixth_active_address(self):
        self.fill_cart()
        data_address = self.get_order_data()['address']
        addresses = []
        for n in range(1, 6):
            addresses.append(Address(user=self.buyer, **data_address))
            data_address['house'] += 1
        addresses = Address.objects.bulk_create(addresses)
        data = self.get_order_data()
        data['address']['city'] = "Новосибирск"
        response = self.client.post(self.url,
                                    data=data, format='json',
                                    headers={'Authorization': f'Token {self.buyer_auth_token}'})
        orders = Order.objects.filter(user=self.buyer)
        addresses = Address.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_409_CONFLICT, response.status_code)
        self.assertEqual(0, len(orders))
        self.assertEqual(5, len(addresses))
        self.assertEqual('No more than 5 addresses per user', response.json()['detail'])

    def test_post_order_with_wrong_token(self):
        response = self.client.post(self.url,
                                    data=self.get_order_data(), format='json',
                                    headers={'Authorization': f'Token 1111'})
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Invalid token.', response.json()['detail'])

    def test_post_order_without_token(self):
        response = self.client.post(self.url,
                                    data=self.get_order_data(), format='json')
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Authentication credentials were not provided.', response.json()['detail'])

    def test_post_order_as_seller(self):
        response = self.client.post(self.url,
                                    data=self.get_order_data(), format='json',
                                    headers={'Authorization': f'Token {self.seller_auth_token}'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual('The user is not a buyer.', response.json()['detail'])

    def test_post_order_without_data(self):
        response = self.client.post(self.url,
                                    headers={'Authorization': f'Token {self.buyer_auth_token}'})
        orders = Order.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        expected_resonse = {"first_name": ["This field is required."],
                            "last_name": ["This field is required."],
                            "phone": ["This field is required."],
                            "address": ["This field is required."]}
        self.assertEqual(expected_resonse, response.json())
        self.assertEqual(0, len(orders))

    def test_post_order_with_empty_cart(self):
        response = self.client.post(self.url,
                                    data=self.get_order_data(), format='json',
                                    headers={'Authorization': f'Token {self.buyer_auth_token}'})
        orders = Order.objects.filter(user=self.buyer)
        self.assertEqual(status.HTTP_409_CONFLICT, response.status_code)
        self.assertEqual('Empty cart.', response.json()['detail'])
        self.assertEqual(0, len(orders))


class OrderDetailViewTest(APITestCase):

    @classmethod
    def get_random_product_card(cls):
        product_cards = ProductCard.objects.all()
        product_card = random.choice(product_cards)
        return product_card

    @classmethod
    def setUpTestData(cls):
        seller_data = {'first_name': 'Ivan', 'last_name': 'Ivanov', 'email': 'ivan.ivanov@gmail.com',
                       'is_active': True, 'type': 'seller', 'password': '12345678'}
        buyer_data = {'first_name': 'Maria', 'last_name': 'Petrova', 'email': 'maria.petrova@gmail.com',
                      'is_active': True, 'type': 'buyer', 'password': '12345678'}
        seller = User.objects.create_user(**seller_data)
        cls.seller_auth_token = Token.objects.create(user=seller)
        buyer = User.objects.create_user(**buyer_data)
        cls.buyer_auth_token = Token.objects.create(user=buyer)
        client = Client()
        response = client.post('/api/v1/seller/shop/prices/',
                                    headers={'Authorization': f'Token {cls.seller_auth_token}'},
                                    data={
                                        'url': 'https://raw.githubusercontent.com/netology-code/python-final-diplom/master/data/shop1.yaml'})
        cls.address = Address(user=buyer, city='Moscow', street='Nevskogo', house='16')
        cls.address.save()
        cls.order = Order(user=buyer, address=cls.address, first_name='Maksim', last_name='Maksimov',
                        phone='89372773838')
        cls.order.save()
        product_card = cls.get_random_product_card()
        cls.position = OrderPosition(order=cls.order, product_card=product_card, price=product_card.price,
                                           quantity=3)
        cls.position.save()

    def test_get_order_with_correct_token(self):
        expected_response = {
            "id": self.order.id,
            "created_at": self.order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.order.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "delivered_at": None,
            "status": self.order.status, "first_name": self.order.first_name,
            "last_name": self.order.last_name, "middle_name": self.order.middle_name,
            "email": self.order.email, "phone": self.order.phone,
            "address": {
                "id": self.address.id, "city": self.address.city,
                "street": self.address.street, "house": self.address.house,
                "building": self.address.building, "apartment": self.address.apartment},
            "positions": [
                {"product": self.position.product_card.product.name,
                 "shop": self.position.product_card.shop.name,
                 "price": str(self.position.price), "quantity": self.position.quantity,
                 "price_per_quantity": str(self.position.price * self.position.quantity),}
            ]}
        url = reverse('buyer:order_detail', kwargs={'pk': self.order.id})
        response = self.client.get(url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'})
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(expected_response, response.json())

    def test_get_order_with_incorrect_pk(self):
        url = reverse('buyer:order_detail', kwargs={'pk': 453})
        response = self.client.get(url,
                                   headers={'Authorization': f'Token {self.buyer_auth_token}'})
        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)
        self.assertEqual('Not found.', response.json()['detail'])

    def test_get_order_without_token(self):
        url = reverse('buyer:order_detail', kwargs={'pk': self.order.id})
        response = self.client.get(url)
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Authentication credentials were not provided.', response.json()['detail'])

    def test_get_order_with_incorrect_token(self):
        url = reverse('buyer:order_detail', kwargs={'pk': self.order.id})
        response = self.client.get(url,
                                   headers={'Authorization': f'Token 111'})
        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)
        self.assertEqual('Invalid token.', response.json()['detail'])

    def test_get_order_as_seller(self):
        url = reverse('buyer:order_detail', kwargs={'pk': self.order.id})
        response = self.client.get(url,
                                   headers={'Authorization': f'Token {self.seller_auth_token}'})
        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        self.assertEqual('The user is not a buyer.', response.json()['detail'])