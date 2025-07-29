from django.test import TestCase
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from store.models import Conversation, Message, Product, Category, Notification
from .consumers import ChatConsumer, NotificationConsumer
from django.urls import reverse
from asgiref.sync import sync_to_async

User = get_user_model()

class ChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='pass123', user_type='buyer')
        cls.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='pass123', user_type='seller')
        cls.category = Category.objects.create(name='Test Category', slug='test-category')
        cls.product = Product.objects.create(
            seller=cls.user2,
            category=cls.category,
            name='Test Product',
            description='Test Description',
            price=100,
            stock=10
        )
        cls.conversation = Conversation.objects.create(
            initiator=cls.user1,
            recipient=cls.user2,
            product=cls.product
        )

    async def test_websocket_connection(self):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f'/ws/chat/{self.conversation.id}/')
        communicator.scope['user'] = self.user1
        communicator.scope['url_route'] = {'kwargs': {'conversation_id': str(self.conversation.id)}}  # Ajout du scope
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_websocket_connection_unauthorized(self):
        user3 = await sync_to_async(User.objects.create_user)(username='user3', email='user3@example.com', password='pass123', user_type='buyer')
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f'/ws/chat/{self.conversation.id}/')
        communicator.scope['user'] = user3
        communicator.scope['url_route'] = {'kwargs': {'conversation_id': str(self.conversation.id)}}
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_websocket_connection_nonexistent_conversation(self):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), '/ws/chat/999/')
        communicator.scope['user'] = self.user1
        communicator.scope['url_route'] = {'kwargs': {'conversation_id': '999'}}
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_send_and_receive_message(self):
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f'/ws/chat/{self.conversation.id}/')
        communicator.scope['user'] = self.user1
        communicator.scope['url_route'] = {'kwargs': {'conversation_id': str(self.conversation.id)}}
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        message = {'message': 'Hello, world!'}
        await communicator.send_json_to(message)
        response = await communicator.receive_json_from(timeout=5)  # Ajout d'un timeout explicite
        self.assertEqual(response['message'], 'Hello, world!')
        self.assertEqual(response['sender'], self.user1.username)

        await communicator.disconnect()

    async def test_notification_connection(self):
        communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), '/ws/notifications/')
        communicator.scope['user'] = self.user1
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_notification_connection_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser
        communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), '/ws/notifications/')
        communicator.scope['user'] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()