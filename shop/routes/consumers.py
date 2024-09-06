import json
from channels.generic.websocket import AsyncWebsocketConsumer

class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f'order_{self.order_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'order_update',
                'message': message
            }
        )

    async def order_update(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))

class SellerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.seller_id = self.scope['url_route']['kwargs']['menu_slug']
        self.room_group_name = f'seller_{self.seller_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        print(f"Added {self.channel_name} channel to {self.room_group_name}")
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        print("Received message", text_data)
        data = json.loads(text_data)
        message = data['message']

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'seller_notification',
                'message': message
            }
        )

    async def seller_notification(self, event):
        print("Received notification")
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
