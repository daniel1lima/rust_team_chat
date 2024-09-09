import asyncio
from rustplus import RustSocket, CommandOptions, Command, ServerDetails, ChatCommand
from rustbot import register

steamId, playerToken, ip, port = register()
options = CommandOptions(prefix="!") # Use whatever prefix you want here
server_details = ServerDetails(ip, port, steamId, playerToken)
socket = RustSocket(server_details)

@Command(server_details)
async def hi(command : ChatCommand): 
    await socket.send_team_message(f"Hi, {command.sender_name}")
    print(f"Hi, {command.sender_name}")

async def main():
    await socket.connect()
    print("Connected to Rust server. Listening for commands...")
    try:
        while True:
            await asyncio.sleep(1)  # Keep the loop running
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await socket.disconnect()

if __name__ == "__main__":
    asyncio.run(main())