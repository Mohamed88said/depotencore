import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from store.models import Conversation, Message, Notification
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        if await self.has_access():
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        user = self.scope['user']

        message = await self.save_message(message_content)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'sender': user.username,
                'sent_at': message.sent_at.isoformat(),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'sent_at': event['sent_at'],
        }))

    @database_sync_to_async
    def has_access(self):
        try:
            conversation = Conversation.objects.filter(id=self.conversation_id).first()
            if not conversation:
                return False
            return self.scope['user'].is_authenticated and (
                self.scope['user'] == conversation.initiator or
                self.scope['user'] == conversation.recipient
            )
        except Conversation.MultipleObjectsReturned:
            return False

    @database_sync_to_async
    def save_message(self, content):
        from django.db import transaction
        with transaction.atomic():
            conversation = Conversation.objects.get(id=self.conversation_id)
            return Message.objects.create(
                conversation=conversation,
                sender=self.scope['user'],
                content=content,
            )

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if isinstance(self.scope['user'], AnonymousUser) or not self.scope['user'].is_authenticated:
            await self.close()
            return

        self.user_id = self.scope['user'].id
        self.room_group_name = f'notifications_{self.user_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):  # Vérification ajoutée
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def new_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'notification_type': event['notification_type'],
            'timestamp': event['timestamp'],
        }))