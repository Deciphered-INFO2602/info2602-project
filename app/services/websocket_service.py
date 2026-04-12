from fastapi import WebSocket

class WebSocketService:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.room_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def connect_to_room(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
        self.room_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def disconnect_from_room(self, room_id: str, websocket: WebSocket):
        room = self.room_connections.get(room_id)
        if not room:
            return

        if websocket in room:
            room.remove(websocket)

        if len(room) == 0:
            del self.room_connections[room_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_room(self, room_id: str, message: str):
        for connection in self.room_connections.get(room_id, []):
            await connection.send_text(message)

websocket_service = WebSocketService()